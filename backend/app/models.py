from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from .database import Base

class CrawlSession(Base):
    __tablename__ = "crawl_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    start_url = Column(String, nullable=False)
    status = Column(String, default="running")  # running, completed, failed, stopped
    max_depth = Column(Integer, default=3)
    max_pages = Column(Integer, default=100)
    concurrent_workers = Column(Integer, default=5)
    
    pages_crawled = Column(Integer, default=0)
    pages_queued = Column(Integer, default=0)
    videos_found = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    pages = relationship("CrawledPage", back_populates="session", cascade="all, delete-orphan")
    videos = relationship("VideoSource", back_populates="session", cascade="all, delete-orphan")
    logs = relationship("CrawlLog", back_populates="session", cascade="all, delete-orphan")


class CrawledPage(Base):
    __tablename__ = "crawled_pages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    crawl_id = Column(Integer, ForeignKey("crawl_sessions.id"), nullable=False)
    url = Column(String, nullable=False)
    depth = Column(Integer, nullable=False)
    status_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    crawled_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("CrawlSession", back_populates="pages")


class VideoSource(Base):
    __tablename__ = "video_sources"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    crawl_id = Column(Integer, ForeignKey("crawl_sessions.id"), nullable=False)
    page_url = Column(String, nullable=False)
    video_url = Column(String, nullable=False)
    type = Column(String, nullable=False)  # MP4, HLS, DASH, WEBM, MOV, M4V, etc.
    thumbnail_url = Column(String, nullable=True)
    discovered_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("CrawlSession", back_populates="videos")


class CrawlLog(Base):
    __tablename__ = "crawl_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    crawl_id = Column(Integer, ForeignKey("crawl_sessions.id"), nullable=False)
    level = Column(String, nullable=False)  # VISIT, VIDEO_FOUND, SKIP_EXTERNAL, SKIP_DUPLICATE, ERROR
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    session = relationship("CrawlSession", back_populates="logs")
