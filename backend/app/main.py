import csv
import json
import asyncio
from io import StringIO
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import CrawlSession, CrawledPage, VideoSource, CrawlLog
from .schemas import CrawlStartRequest, CrawlSessionResponse, VideoSourceResponse, CrawlLogResponse, CrawlStats
from .crawler import CrawlEngine

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Recursive Domain Video Crawler API")

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/crawl/reset")
def reset_database(db: Session = Depends(get_db)):
    db.query(CrawlLog).delete()
    db.query(VideoSource).delete()
    db.query(CrawledPage).delete()
    db.query(CrawlSession).delete()
    db.commit()
    return {"status": "success", "message": "All database records cleared."}

@app.post("/crawl/start")
async def start_crawl(
    request: CrawlStartRequest,
    db: Session = Depends(get_db)
):
    # Completely clear the database for a single-session execution
    db.query(CrawlLog).delete()
    db.query(VideoSource).delete()
    db.query(CrawledPage).delete()
    db.query(CrawlSession).delete()
    db.commit()

    # Create the single active session
    session = CrawlSession(
        start_url=request.url,
        status="running",
        max_depth=request.depth,
        max_pages=request.max_pages,
        concurrent_workers=request.concurrent_workers
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # SSE Event Generator
    async def event_generator():
        event_queue = asyncio.Queue()

        def on_log(log_data):
            event_queue.put_nowait({"type": "log", "data": log_data})

        def on_stats(stats_data):
            event_queue.put_nowait({"type": "stats", "data": stats_data})

        def get_session_db():
            from .database import SessionLocal
            return SessionLocal()

        engine = CrawlEngine(
            session_id=session.id,
            start_url=request.url,
            max_depth=request.depth,
            max_pages=request.max_pages,
            concurrent_workers=request.concurrent_workers,
            db_session_creator=get_session_db,
            on_log_cb=on_log,
            on_stats_cb=on_stats
        )

        # Run crawler within the request context for serverless streaming
        crawl_task = asyncio.create_task(engine.run())

        while not crawl_task.done() or not event_queue.empty():
            try:
                # Non-blocking poll
                event = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                yield f"data: {json.dumps(event)}\n\n"
                event_queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Error in event stream: {e}")

        # Final check on crawl status
        try:
            await crawl_task
        except Exception as e:
            print(f"Crawl engine crashed: {e}")
            yield f"data: {json.dumps({'type': 'log', 'data': {'level': 'ERROR', 'message': f'Fatal crawl exception: {str(e)}', 'timestamp': datetime.utcnow().isoformat() + 'Z'}})}\n\n"

        # Calculate and yield final completed metrics
        db_fresh = get_session_db()
        try:
            completed_session = db_fresh.query(CrawlSession).filter_by(id=session.id).first()
            if completed_session:
                total_pages = db_fresh.query(CrawledPage).filter_by(crawl_id=session.id).count()
                total_videos = db_fresh.query(VideoSource).filter_by(crawl_id=session.id).count()
                
                type_query = db_fresh.query(VideoSource.type, func.count(VideoSource.id))\
                    .filter_by(crawl_id=session.id)\
                    .group_by(VideoSource.type)\
                    .order_by(func.count(VideoSource.id).desc())\
                    .first()
                most_common_type = type_query[0] if type_query else "N/A"
                
                elapsed = (datetime.utcnow() - completed_session.created_at).total_seconds()
                if completed_session.completed_at:
                    elapsed = (completed_session.completed_at - completed_session.created_at).total_seconds()
                    
                avg_speed = total_pages / elapsed if elapsed > 0 else 0.0

                stats_payload = {
                    "total_pages": total_pages,
                    "total_videos": total_videos,
                    "most_common_type": most_common_type,
                    "avg_speed": round(avg_speed, 2)
                }

                session_payload = {
                    "id": completed_session.id,
                    "start_url": completed_session.start_url,
                    "status": completed_session.status,
                    "max_depth": completed_session.max_depth,
                    "max_pages": completed_session.max_pages,
                    "concurrent_workers": completed_session.concurrent_workers,
                    "pages_crawled": completed_session.pages_crawled,
                    "pages_queued": completed_session.pages_queued,
                    "videos_found": completed_session.videos_found,
                    "created_at": completed_session.created_at.isoformat() + "Z",
                    "completed_at": completed_session.completed_at.isoformat() + "Z" if completed_session.completed_at else None
                }

                yield f"data: {json.dumps({'type': 'complete', 'data': {'session': session_payload, 'stats': stats_payload, 'elapsed_time': int(elapsed)}})}\n\n"
        finally:
            db_fresh.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/crawl/status")
def get_crawl_status(
    crawl_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    if crawl_id:
        session = db.query(CrawlSession).filter_by(id=crawl_id).first()
    else:
        session = db.query(CrawlSession).order_by(CrawlSession.id.desc()).first()

    if not session:
        return {"session": None, "stats": None}

    total_pages = db.query(CrawledPage).filter_by(crawl_id=session.id).count()
    total_videos = db.query(VideoSource).filter_by(crawl_id=session.id).count()
    
    type_query = db.query(VideoSource.type, func.count(VideoSource.id))\
        .filter_by(crawl_id=session.id)\
        .group_by(VideoSource.type)\
        .order_by(func.count(VideoSource.id).desc())\
        .first()
    most_common_type = type_query[0] if type_query else "N/A"
    
    elapsed = (datetime.utcnow() - session.created_at).total_seconds()
    if session.completed_at:
        elapsed = (session.completed_at - session.created_at).total_seconds()
        
    avg_speed = total_pages / elapsed if elapsed > 0 else 0.0

    stats = CrawlStats(
        total_pages=total_pages,
        total_videos=total_videos,
        most_common_type=most_common_type,
        avg_speed=round(avg_speed, 2)
    )

    return {
        "session": CrawlSessionResponse.from_orm(session),
        "stats": stats,
        "elapsed_time": int(elapsed)
    }

@app.get("/crawl/results", response_model=List[VideoSourceResponse])
def get_crawl_results(
    crawl_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    if crawl_id:
        session_id = crawl_id
    else:
        latest = db.query(CrawlSession).order_by(CrawlSession.id.desc()).first()
        if not latest:
            return []
        session_id = latest.id

    videos = db.query(VideoSource).filter_by(crawl_id=session_id).all()
    return videos

@app.get("/crawl/logs", response_model=List[CrawlLogResponse])
def get_crawl_logs(
    crawl_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    if crawl_id:
        session_id = crawl_id
    else:
        latest = db.query(CrawlSession).order_by(CrawlSession.id.desc()).first()
        if not latest:
            return []
        session_id = latest.id

    logs = db.query(CrawlLog).filter_by(crawl_id=session_id).order_by(CrawlLog.timestamp.desc()).limit(100).all()
    logs.reverse()
    return logs

@app.get("/crawl/export/json")
def export_json(
    crawl_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    if crawl_id:
        session_id = crawl_id
    else:
        latest = db.query(CrawlSession).order_by(CrawlSession.id.desc()).first()
        if not latest:
            raise HTTPException(status_code=404, detail="No crawl session found to export.")
        session_id = latest.id

    videos = db.query(VideoSource).filter_by(crawl_id=session_id).all()
    
    data = [
        {
            "id": v.id,
            "page_url": v.page_url,
            "video_url": v.video_url,
            "type": v.type,
            "discovered_at": v.discovered_at.isoformat() + "Z"
        }
        for v in videos
    ]
    
    json_str = json.dumps(data, indent=2)
    def iter_json():
        yield json_str
        
    return StreamingResponse(
        iter_json(),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=crawl_results_{session_id}.json"}
    )

@app.get("/crawl/export/csv")
def export_csv(
    crawl_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    if crawl_id:
        session_id = crawl_id
    else:
        latest = db.query(CrawlSession).order_by(CrawlSession.id.desc()).first()
        if not latest:
            raise HTTPException(status_code=404, detail="No crawl session found to export.")
        session_id = latest.id

    videos = db.query(VideoSource).filter_by(crawl_id=session_id).all()
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Source Page URL", "Video URL", "Type", "Discovered At"])
    
    for v in videos:
        writer.writerow([
            v.id,
            v.page_url,
            v.video_url,
            v.type,
            v.discovered_at.isoformat() + "Z"
        ])
        
    output.seek(0)
    def iter_csv():
        yield output.getvalue()
        
    return StreamingResponse(
        iter_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=crawl_results_{session_id}.csv"}
    )

@app.get("/crawl/download")
async def download_video(url: str, referer: Optional[str] = None):
    import os
    import httpx
    from urllib.parse import urlparse
    
    ref = referer or "https://vidzp.com/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": ref
    }
    
    async def stream_video():
        async with httpx.AsyncClient(verify=False) as client:
            try:
                async with client.stream("GET", url, headers=headers, follow_redirects=True, timeout=60.0) as r:
                    if r.status_code >= 400:
                        raise HTTPException(status_code=r.status_code, detail=f"Failed to fetch video stream: HTTP {r.status_code}")
                    async for chunk in r.iter_bytes(chunk_size=1024 * 64):
                        yield chunk
            except Exception as e:
                print(f"Error streaming video file: {e}")
                
    parsed = urlparse(url)
    filename = os.path.basename(parsed.path) or "video.mp4"
    if "." not in filename:
        filename += ".mp4"
        
    return StreamingResponse(
        stream_video(),
        media_type="video/mp4",
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\"",
            "Accept-Ranges": "bytes"
        }
    )
