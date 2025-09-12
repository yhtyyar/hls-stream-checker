#!/usr/bin/env python3
"""
Pydantic models for API request/response schemas
"""
from datetime import datetime
from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field, validator


class ChannelInfo(BaseModel):
    """Channel information model"""
    our_id: int
    name_ru: str
    stream_common: str
    url: str


class MonitoringRequest(BaseModel):
    """Request model for starting monitoring"""
    channels: Union[str, List[int]] = Field(
        default="all", 
        description="Channel selection: 'all' or list of channel IDs"
    )
    duration_minutes: int = Field(
        default=5, 
        ge=1, 
        le=1440, 
        description="Monitoring duration in minutes (1-1440)"
    )
    export_data: bool = Field(
        default=True, 
        description="Whether to export data after monitoring"
    )

    @validator('channels')
    def validate_channels(cls, v):
        if isinstance(v, str) and v != "all":
            raise ValueError("String value must be 'all'")
        if isinstance(v, list):
            for channel_id in v:
                if not isinstance(channel_id, int) or channel_id <= 0:
                    raise ValueError("Channel IDs must be positive integers")
        return v


class MonitoringStatus(BaseModel):
    """Monitoring status response"""
    status: str = Field(description="Current monitoring status")
    start_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    channels_count: Optional[int] = None
    progress_percent: Optional[float] = None
    estimated_completion: Optional[datetime] = None


class StreamStats(BaseModel):
    """Stream statistics model"""
    channel_id: int
    channel_name: str
    total_checks: int
    successful_checks: int
    failed_checks: int
    success_rate: float
    avg_response_time: float
    last_check_time: datetime
    status: str


class MonitoringReport(BaseModel):
    """Monitoring report model"""
    report_id: str
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    total_channels: int
    total_checks: int
    overall_success_rate: float
    streams: List[StreamStats]
    summary: Dict[str, Any]


class LogEntry(BaseModel):
    """Log entry model"""
    timestamp: datetime
    level: str
    message: str
    source: Optional[str] = None


class LogsResponse(BaseModel):
    """Logs response model"""
    logs: List[LogEntry]
    total_count: int
    page: int
    per_page: int
    has_next: bool


class ReportListItem(BaseModel):
    """Report list item model"""
    report_id: str
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    channels_count: int
    success_rate: float
    file_path: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class SuccessResponse(BaseModel):
    """Success response model"""
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)
