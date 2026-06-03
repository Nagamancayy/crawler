import csv
import json
import asyncio
from io import StringIO
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException, WebSocket, WebSocketDisconnect
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

# WebSocket Manager to handle real-time log and stats streaming
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                # Connection might be dead, ignore it
                pass

manager = ConnectionManager()

# Background task runner for crawler
async def run_crawler_task(
    session_id: int,
    url: str,
    depth: int,
    max_pages: int,
    workers: int
):
    def get_session_db():
        from .database import SessionLocal
        return SessionLocal()

    # WebSockets callback helpers
    def on_log(log_data):
        asyncio.create_task(manager.broadcast({
            "type": "log",
            "crawl_id": session_id,
            "data": log_data
        }))

    def on_stats(stats_data):
        asyncio.create_task(manager.broadcast({
            "type": "stats",
            "crawl_id": session_id,
            "data": stats_data
        }))

    engine = CrawlEngine(
        session_id=session_id,
        start_url=url,
        max_depth=depth,
        max_pages=max_pages,
        concurrent_workers=workers,
        db_session_creator=get_session_db,
        on_log_cb=on_log,
        on_stats_cb=on_stats
    )
    
    try:
        await engine.run()
    except Exception as e:
        print(f"Crawl engine execution failed: {e}")
        db = get_session_db()
        try:
            session = db.query(CrawlSession).filter_by(id=session_id).first()
            if session:
                session.status = "failed"
                session.completed_at = datetime.utcnow()
                db.commit()
                # Log error
                db_log = CrawlLog(
                    crawl_id=session_id,
                    level="ERROR",
                    message=f"Fatal crawler exception: {str(e)}",
                    timestamp=datetime.utcnow()
                )
                db.add(db_log)
                db.commit()
        except Exception as db_err:
            db.rollback()
            print(f"Failed to record crawl failure to DB: {db_err}")
        finally:
            db.close()

@app.post("/crawl/start", response_model=CrawlSessionResponse)
def start_crawl(
    request: CrawlStartRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # Check if there's currently a running session
    running_session = db.query(CrawlSession).filter_by(status="running").first()
    if running_session:
        # We can stop it or raise an error. Let's automatically stop the running one to start new
        running_session.status = "stopped"
        running_session.completed_at = datetime.utcnow()
        db.commit()

    # Create new session
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

    # Start crawling in BackgroundTasks
    background_tasks.add_task(
        run_crawler_task,
        session_id=session.id,
        url=request.url,
        depth=request.depth,
        max_pages=request.max_pages,
        workers=request.concurrent_workers
    )

    return session

@app.get("/crawl/status")
def get_crawl_status(crawl_id: Optional[int] = None, db: Session = Depends(get_db)):
    if crawl_id:
        session = db.query(CrawlSession).filter_by(id=crawl_id).first()
    else:
        # Get the latest session
        session = db.query(CrawlSession).order_by(CrawlSession.id.desc()).first()

    if not session:
        return {"session": None, "stats": None}

    # Calculate statistics
    total_pages = db.query(CrawledPage).filter_by(crawl_id=session.id).count()
    total_videos = db.query(VideoSource).filter_by(crawl_id=session.id).count()
    
    # Most common type
    type_query = db.query(VideoSource.type, func.count(VideoSource.id))\
        .filter_by(crawl_id=session.id)\
        .group_by(VideoSource.type)\
        .order_by(func.count(VideoSource.id).desc())\
        .first()
    most_common_type = type_query[0] if type_query else "N/A"
    
    # Speed calculation
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

    # Calculate current queue size (approximate)
    pages_queued = session.pages_queued
    
    return {
        "session": CrawlSessionResponse.from_orm(session),
        "stats": stats,
        "elapsed_time": int(elapsed)
    }

@app.get("/crawl/results", response_model=List[VideoSourceResponse])
def get_crawl_results(crawl_id: Optional[int] = None, db: Session = Depends(get_db)):
    if crawl_id:
        session_id = crawl_id
    else:
        # Latest session
        latest = db.query(CrawlSession).order_by(CrawlSession.id.desc()).first()
        if not latest:
            return []
        session_id = latest.id

    videos = db.query(VideoSource).filter_by(crawl_id=session_id).all()
    return videos

@app.get("/crawl/logs", response_model=List[CrawlLogResponse])
def get_crawl_logs(crawl_id: Optional[int] = None, db: Session = Depends(get_db)):
    if crawl_id:
        session_id = crawl_id
    else:
        # Latest session
        latest = db.query(CrawlSession).order_by(CrawlSession.id.desc()).first()
        if not latest:
            return []
        session_id = latest.id

    logs = db.query(CrawlLog).filter_by(crawl_id=session_id).order_by(CrawlLog.timestamp.desc()).limit(100).all()
    # Reverse to show chronological order
    logs.reverse()
    return logs

@app.get("/crawl/export/json")
def export_json(crawl_id: Optional[int] = None, db: Session = Depends(get_db)):
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
def export_csv(crawl_id: Optional[int] = None, db: Session = Depends(get_db)):
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
    
    # Header
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

@app.websocket("/ws/crawl")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Keep connection open
        while True:
            # We don't expect messages from client, but we block here to detect disconnects
            await websocket.receive_text()
    except (WebSocketDisconnect, Exception):
        manager.disconnect(websocket)
