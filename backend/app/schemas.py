from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, HttpUrl, Field

class CrawlStartRequest(BaseModel):
    url: str = Field(..., description="The starting URL for the crawl")
    depth: int = Field(3, ge=0, le=10, description="Max crawl depth")
    max_pages: int = Field(100, ge=1, le=1000, description="Max pages to crawl")
    concurrent_workers: int = Field(5, ge=1, le=10, description="Number of concurrent workers")

class CrawlSessionResponse(BaseModel):
    id: int
    start_url: str
    status: str
    max_depth: int
    max_pages: int
    concurrent_workers: int
    pages_crawled: int
    pages_queued: int
    videos_found: int
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class VideoSourceResponse(BaseModel):
    id: int
    crawl_id: int
    page_url: str
    video_url: str
    type: str
    discovered_at: datetime

    class Config:
        from_attributes = True

class CrawlLogResponse(BaseModel):
    id: int
    crawl_id: int
    level: str
    message: str
    timestamp: datetime

    class Config:
        from_attributes = True

class CrawlStats(BaseModel):
    total_pages: int
    total_videos: int
    most_common_type: str
    avg_speed: float  # pages crawled per second
