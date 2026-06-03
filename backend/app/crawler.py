import re
import asyncio
from datetime import datetime
from urllib.parse import urlparse, urlunparse, urljoin
import httpx
from bs4 import BeautifulSoup
from .models import CrawlSession, CrawledPage, VideoSource, CrawlLog

def normalize_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        path = parsed.path
        if path != '/' and path.endswith('/'):
            path = path[:-1]
        netloc = parsed.netloc.lower()
        if ":" in netloc:
            parts = netloc.split(":")
            if (parsed.scheme == "http" and parts[1] == "80") or (parsed.scheme == "https" and parts[1] == "443"):
                netloc = parts[0]
        return urlunparse((parsed.scheme.lower(), netloc, path, parsed.params, parsed.query, ''))
    except Exception:
        return url

def is_same_domain(url: str, start_url: str) -> bool:
    try:
        url_host = urlparse(url).netloc.lower().split(':')[0]
        start_host = urlparse(start_url).netloc.lower().split(':')[0]
        return url_host == start_host or url_host.endswith('.' + start_host)
    except Exception:
        return False

def get_video_type(url: str) -> str:
    url_lower = url.lower().split('?')[0]
    if url_lower.endswith('.mp4'):
        return 'MP4'
    elif url_lower.endswith('.m3u8'):
        return 'HLS'
    elif url_lower.endswith('.mpd'):
        return 'DASH'
    elif url_lower.endswith('.webm'):
        return 'WebM'
    elif url_lower.endswith('.mov'):
        return 'MOV'
    elif url_lower.endswith('.m4v'):
        return 'M4V'
    
    full_lower = url.lower()
    if '.mp4' in full_lower:
        return 'MP4'
    elif '.m3u8' in full_lower:
        return 'HLS'
    elif '.mpd' in full_lower:
        return 'DASH'
    elif '.webm' in full_lower:
        return 'WebM'
    elif '.mov' in full_lower:
        return 'MOV'
    elif '.m4v' in full_lower:
        return 'M4V'
    return ''

class CrawlEngine:
    def __init__(
        self,
        session_id: int,
        start_url: str,
        max_depth: int,
        max_pages: int,
        concurrent_workers: int,
        db_session_creator,
        on_log_cb=None,
        on_stats_cb=None
    ):
        self.session_id = session_id
        self.start_url = start_url
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.concurrent_workers = concurrent_workers
        self.db_session_creator = db_session_creator
        self.on_log_cb = on_log_cb
        self.on_stats_cb = on_stats_cb
        
        self.queue = asyncio.Queue()
        self.visited = set()
        self.discovered_videos = set()
        self.pages_crawled_count = 0
        self.active_workers = 0
        self.shutdown_event = asyncio.Event()
        self.start_time = None

    def log(self, level: str, message: str):
        print(f"[{level}] {message}")
        db = self.db_session_creator()
        try:
            db_log = CrawlLog(
                crawl_id=self.session_id,
                level=level,
                message=message,
                timestamp=datetime.utcnow()
            )
            db.add(db_log)
            db.commit()
            
            if self.on_log_cb:
                self.on_log_cb({
                    "crawl_id": self.session_id,
                    "level": level,
                    "message": message,
                    "timestamp": db_log.timestamp.isoformat() + "Z"
                })
        except Exception as e:
            db.rollback()
            print(f"Error saving log: {e}")
        finally:
            db.close()

    def update_session_status(self, status: str):
        db = self.db_session_creator()
        try:
            session = db.query(CrawlSession).filter_by(id=self.session_id).first()
            if session:
                session.status = status
                if status in ["completed", "failed", "stopped"]:
                    session.completed_at = datetime.utcnow()
                db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error updating session status: {e}")
        finally:
            db.close()

    def update_stats(self):
        db = self.db_session_creator()
        try:
            session = db.query(CrawlSession).filter_by(id=self.session_id).first()
            if session:
                session.pages_crawled = self.pages_crawled_count
                session.pages_queued = self.queue.qsize()
                session.videos_found = len(self.discovered_videos)
                db.commit()
                
                if self.on_stats_cb:
                    elapsed = (datetime.utcnow() - self.start_time).total_seconds() if self.start_time else 0
                    self.on_stats_cb({
                        "crawl_id": self.session_id,
                        "status": session.status,
                        "pages_crawled": self.pages_crawled_count,
                        "pages_queued": self.queue.qsize(),
                        "videos_found": len(self.discovered_videos),
                        "elapsed_time": int(elapsed)
                    })
        except Exception as e:
            db.rollback()
            print(f"Error updating stats: {e}")
        finally:
            db.close()

    def save_video(self, page_url: str, video_url: str, type_: str):
        db = self.db_session_creator()
        try:
            existing = db.query(VideoSource).filter_by(crawl_id=self.session_id, video_url=video_url).first()
            if not existing:
                db_video = VideoSource(
                    crawl_id=self.session_id,
                    page_url=page_url,
                    video_url=video_url,
                    type=type_
                )
                db.add(db_video)
                db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error saving video: {e}")
        finally:
            db.close()

    def save_crawled_page(self, url: str, depth: int, status_code: int):
        db = self.db_session_creator()
        try:
            db_page = CrawledPage(
                crawl_id=self.session_id,
                url=url,
                depth=depth,
                status_code=status_code,
                crawled_at=datetime.utcnow()
            )
            db.add(db_page)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error saving crawled page: {e}")
        finally:
            db.close()

    def save_failed_page(self, url: str, depth: int, error_message: str):
        db = self.db_session_creator()
        try:
            db_page = CrawledPage(
                crawl_id=self.session_id,
                url=url,
                depth=depth,
                error_message=error_message,
                crawled_at=datetime.utcnow()
            )
            db.add(db_page)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error saving failed page: {e}")
        finally:
            db.close()

    async def run(self):
        self.start_time = datetime.utcnow()
        self.update_session_status("running")
        
        normalized_start = normalize_url(self.start_url)
        self.visited.add(normalized_start)
        await self.queue.put((self.start_url, 0))
        self.update_stats()
        
        self.log("VISIT", f"Starting BFS crawl from URL: {self.start_url} (Max Depth: {self.max_depth}, Max Pages: {self.max_pages}, Workers: {self.concurrent_workers})")

        limits = httpx.Limits(max_keepalive_connections=self.concurrent_workers, max_connections=self.concurrent_workers * 2)
        async with httpx.AsyncClient(limits=limits, verify=False, follow_redirects=True, timeout=10.0) as client:
            workers = []
            for i in range(self.concurrent_workers):
                task = asyncio.create_task(self.worker(client, i))
                workers.append(task)
                
            while not self.shutdown_event.is_set():
                await asyncio.sleep(0.1)
                if self.queue.empty() and self.active_workers == 0:
                    break
                if self.pages_crawled_count >= self.max_pages:
                    self.log("VISIT", f"Crawl limit reached: {self.max_pages} pages.")
                    break
                    
            self.shutdown_event.set()
            for task in workers:
                task.cancel()
            await asyncio.gather(*workers, return_exceptions=True)
            
        self.log("VISIT", f"Crawl finished. Crawled {self.pages_crawled_count} pages, found {len(self.discovered_videos)} video sources.")
        self.update_session_status("completed")
        self.update_stats()

    async def worker(self, client: httpx.AsyncClient, worker_id: int):
        while not self.shutdown_event.is_set():
            if self.pages_crawled_count >= self.max_pages:
                break
            try:
                url, depth = await asyncio.wait_for(self.queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
                
            self.active_workers += 1
            try:
                await self.crawl_page(client, url, depth)
            except asyncio.CancelledError:
                self.queue.task_done()
                self.active_workers -= 1
                break
            except Exception as e:
                self.log("ERROR", f"Unhandled worker exception on {url}: {str(e)}")
            finally:
                self.queue.task_done()
                self.active_workers -= 1
                self.update_stats()

    async def crawl_page(self, client: httpx.AsyncClient, url: str, depth: int):
        self.log("VISIT", f"Crawling page: {url} at depth {depth}")
        
        status_code = None
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            }
            
            response = await client.get(url, headers=headers)
            status_code = response.status_code
            
            if status_code >= 400:
                self.log("ERROR", f"HTTP {status_code} returned for {url}")
                self.save_failed_page(url, depth, f"HTTP Error {status_code}")
                return
                
            # Parse DOM with BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 1. Scrape standard HTML5 video and source tags
            video_srcs = []
            for video in soup.find_all("video"):
                if video.get("src"):
                    video_srcs.append(video.get("src"))
                for src in video.find_all("source"):
                    if src.get("src"):
                        video_srcs.append(src.get("src"))
            
            for src in video_srcs:
                resolved_src = urljoin(url, src)
                vtype = get_video_type(resolved_src)
                if vtype and resolved_src not in self.discovered_videos:
                    self.discovered_videos.add(resolved_src)
                    self.log("VIDEO_FOUND", f"Found {vtype} in DOM video tag: {resolved_src}")
                    self.save_video(url, resolved_src, vtype)

            # 2. Extract iframe embed players (e.g. Vidsrc, dood, streamtape, etc.)
            for iframe in soup.find_all("iframe", src=True):
                iframe_src = iframe.get("src")
                resolved_iframe = urljoin(url, iframe_src)
                iframe_lower = resolved_iframe.lower()
                
                # Check if it looks like a video embed
                video_embed_keywords = ["embed", "player", "video", "stream", "vidsrc", "dood", "fembed", "tape", "voe", "upstream", "streamtape", "mixdrop", "jwplayer"]
                is_video_iframe = any(kw in iframe_lower for kw in video_embed_keywords)
                
                if is_video_iframe:
                    # Treat it as EMBED type unless it matches direct video extension
                    vtype = get_video_type(resolved_iframe) or "EMBED"
                    if resolved_iframe not in self.discovered_videos:
                        self.discovered_videos.add(resolved_iframe)
                        self.log("VIDEO_FOUND", f"Found {vtype} embed player in iframe: {resolved_iframe}")
                        self.save_video(url, resolved_iframe, vtype)
            
            # 3. Regex scan the raw source (HTML + Scripts) for video file URLs
            # This captures hidden stream links inside JavaScript variable configs (e.g., config.file = 'https://...m3u8')
            found_urls = re.findall(r'(https?://[^\s"\'>]+)', response.text)
            for found_url in found_urls:
                # Clean up escaped backslashes (common in JS variables or JSON objects)
                cleaned_url = found_url.replace(r'\/', '/').replace('\\', '')
                # Split off potential JS wrappers or quotes that regex might pull in
                cleaned_url = cleaned_url.split('"')[0].split("'")[0].split(')')[0].split(']')[0].split('}')[0]
                
                vtype = get_video_type(cleaned_url)
                if vtype:
                    if cleaned_url not in self.discovered_videos:
                        self.discovered_videos.add(cleaned_url)
                        self.log("VIDEO_FOUND", f"Found {vtype} in page source script: {cleaned_url}")
                        self.save_video(url, cleaned_url, vtype)
            
            # 4. Extract hyperlinks for BFS queue
            links = []
            for a in soup.find_all("a", href=True):
                links.append(a.get("href"))
                
            self.save_crawled_page(url, depth, status_code)
            self.pages_crawled_count += 1
            
            # Process links
            for raw_link in links:
                resolved_link = urljoin(url, raw_link)
                normalized_link = normalize_url(resolved_link)
                
                # Check if this link points directly to a video file
                vtype = get_video_type(resolved_link)
                if vtype:
                    if resolved_link not in self.discovered_videos:
                        self.discovered_videos.add(resolved_link)
                        self.log("VIDEO_FOUND", f"Found {vtype} in anchor link: {resolved_link}")
                        self.save_video(url, resolved_link, vtype)
                    continue
                
                # Otherwise, check domain & queue recursively
                if is_same_domain(normalized_link, self.start_url):
                    if normalized_link not in self.visited:
                        self.visited.add(normalized_link)
                        if depth + 1 <= self.max_depth:
                            await self.queue.put((resolved_link, depth + 1))
                        else:
                            self.log("SKIP_EXTERNAL", f"Skipped: depth limit reached {resolved_link}")
                else:
                    self.log("SKIP_EXTERNAL", f"Skipped external domain: {resolved_link}")
                    
        except Exception as e:
            self.log("ERROR", f"Error during crawl of {url}: {str(e)}")
            self.save_failed_page(url, depth, str(e))
