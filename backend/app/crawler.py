import asyncio
from datetime import datetime
from urllib.parse import urlparse, urlunparse, urljoin
from playwright.async_api import async_playwright
from .models import CrawlSession, CrawledPage, VideoSource, CrawlLog

def normalize_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        path = parsed.path
        if path != '/' and path.endswith('/'):
            path = path[:-1]
        netloc = parsed.netloc.lower()
        # Remove default ports to keep normalization consistent
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
    url_lower = url.lower().split('?')[0] # ignore query params for extension check
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
    
    # Check if the string has query parameters but contains the media types
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
            # Check if video already saved for this session
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

        async with async_playwright() as p:
            # Configure Playwright launch arguments for Docker compatibility
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            
            workers = []
            for i in range(self.concurrent_workers):
                task = asyncio.create_task(self.worker(browser, i))
                workers.append(task)
                
            # Wait for crawler completion or shutdown event
            while not self.shutdown_event.is_set():
                await asyncio.sleep(0.5)
                # Crawler terminates when:
                # 1. Queue is empty AND all workers are idle
                # 2. Max pages limit reached
                if self.queue.empty() and self.active_workers == 0:
                    break
                if self.pages_crawled_count >= self.max_pages:
                    self.log("VISIT", f"Crawl limit reached: {self.max_pages} pages.")
                    break
                    
            self.shutdown_event.set()
            for task in workers:
                task.cancel()
            await asyncio.gather(*workers, return_exceptions=True)
            await browser.close()
            
        self.log("VISIT", f"Crawl finished. Crawled {self.pages_crawled_count} pages, found {len(self.discovered_videos)} video sources.")
        self.update_session_status("completed")
        self.update_stats()

    async def worker(self, browser, worker_id: int):
        while not self.shutdown_event.is_set():
            if self.pages_crawled_count >= self.max_pages:
                break
            try:
                # Polling queue with a short timeout to prevent hang on cancel
                url, depth = await asyncio.wait_for(self.queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
                
            self.active_workers += 1
            try:
                await self.crawl_page(browser, url, depth)
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

    async def crawl_page(self, browser, url: str, depth: int):
        # Open separate context for cookie/session isolation
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ignore_https_errors=True
        )
        page = await context.new_page()
        
        # Local video tracking to prevent redundant prints on the same page
        discovered_here = set()
        
        async def handle_request(request):
            req_url = request.url
            vtype = get_video_type(req_url)
            if vtype and req_url not in self.discovered_videos and req_url not in discovered_here:
                discovered_here.add(req_url)
                self.discovered_videos.add(req_url)
                self.log("VIDEO_FOUND", f"Found {vtype} in network traffic: {req_url}")
                self.save_video(url, req_url, vtype)
                
        page.on("request", handle_request)
        
        self.log("VISIT", f"Crawling page: {url} at depth {depth}")
        
        status_code = None
        try:
            # Navigate to URL
            response = await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            if response:
                status_code = response.status
                
            # Extra wait for network idle to catch slow-loading streams/assets
            try:
                await page.wait_for_load_state("networkidle", timeout=3000)
            except Exception:
                pass  # Carry on even if network doesn't go fully idle
                
            # Extract Video elements from DOM
            video_urls = await page.evaluate("""() => {
                const urls = [];
                document.querySelectorAll('video').forEach(v => {
                    if (v.src) urls.push(v.src);
                    v.querySelectorAll('source').forEach(s => {
                        if (s.src) urls.push(s.src);
                    });
                });
                return urls;
            }""")
            
            for src in video_urls:
                resolved_src = urljoin(url, src)
                vtype = get_video_type(resolved_src)
                if vtype and resolved_src not in self.discovered_videos:
                    self.discovered_videos.add(resolved_src)
                    self.log("VIDEO_FOUND", f"Found {vtype} in DOM video tag: {resolved_src}")
                    self.save_video(url, resolved_src, vtype)
                    
            # Extract Links for recursive BFS
            links = await page.evaluate("""() => {
                return Array.from(document.querySelectorAll('a'))
                    .map(a => a.href)
                    .filter(Boolean);
            }""")
            
            self.save_crawled_page(url, depth, status_code)
            self.pages_crawled_count += 1
            
            # Process hyperlinks
            for raw_link in links:
                resolved_link = urljoin(url, raw_link)
                normalized_link = normalize_url(resolved_link)
                
                # Check if this hyperlink is itself a video
                vtype = get_video_type(resolved_link)
                if vtype:
                    if resolved_link not in self.discovered_videos:
                        self.discovered_videos.add(resolved_link)
                        self.log("VIDEO_FOUND", f"Found {vtype} in anchor link: {resolved_link}")
                        self.save_video(url, resolved_link, vtype)
                    continue
                
                # Otherwise verify domain and queue recursively
                if is_same_domain(normalized_link, self.start_url):
                    if normalized_link not in self.visited:
                        self.visited.add(normalized_link)
                        if depth + 1 <= self.max_depth:
                            await self.queue.put((resolved_link, depth + 1))
                        else:
                            self.log("SKIP_EXTERNAL", f"Skipped: path depth too deep {resolved_link}")
                else:
                    self.log("SKIP_EXTERNAL", f"Skipped external domain: {resolved_link}")
                    
        except Exception as e:
            self.log("ERROR", f"Error during crawl of {url}: {str(e)}")
            self.save_failed_page(url, depth, str(e))
        finally:
            await page.close()
            await context.close()
