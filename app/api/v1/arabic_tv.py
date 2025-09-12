#!/usr/bin/env python3
"""
Arabic TV HLS Stream Checker API endpoints
"""
from datetime import datetime
from typing import List, Optional, Union
import logging

from fastapi import APIRouter, HTTPException, Query, Path
from fastapi.responses import FileResponse, JSONResponse

from app.models.schemas import (
    ChannelInfo, MonitoringRequest, MonitoringStatus, 
    MonitoringReport, ReportListItem, SuccessResponse, ErrorResponse
)
from app.services.hls_service import hls_service
from app.services.logs_service import logs_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/arabic_tv", tags=["Arabic TV Monitoring"])


@router.get("/channels", response_model=List[ChannelInfo])
async def get_channels():
    """Get list of available Arabic TV channels"""
    try:
        channels = await hls_service.get_available_channels()
        return channels
    except Exception as e:
        logger.error(f"Error getting channels: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitoring/start", response_model=SuccessResponse)
async def start_monitoring(request: MonitoringRequest):
    """Start HLS stream monitoring session"""
    try:
        session_id = await hls_service.start_monitoring(
            channels=request.channels,
            duration_minutes=request.duration_minutes,
            export_data=request.export_data
        )
        
        return SuccessResponse(
            message="Monitoring session started successfully",
            data={"session_id": session_id}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitoring/status", response_model=MonitoringStatus)
async def get_monitoring_status():
    """Get current monitoring session status"""
    try:
        status = await hls_service.get_monitoring_status()
        return status
    except Exception as e:
        logger.error(f"Error getting monitoring status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitoring/stop", response_model=SuccessResponse)
async def stop_monitoring():
    """Stop active monitoring session"""
    try:
        stopped = await hls_service.stop_monitoring()
        if stopped:
            return SuccessResponse(message="Monitoring session stopped successfully")
        else:
            raise HTTPException(status_code=400, detail="No active monitoring session")
    except Exception as e:
        logger.error(f"Error stopping monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports", response_model=dict)
async def get_reports(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=1000, description="Items per page")
):
    """Get list of monitoring reports"""
    try:
        reports_data = await hls_service.get_reports_list(page=page, per_page=per_page)
        return reports_data
    except Exception as e:
        logger.error(f"Error getting reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/{report_id}", response_model=MonitoringReport)
async def get_report(report_id: str = Path(..., description="Report ID")):
    """Get detailed monitoring report by ID"""
    try:
        report = await hls_service.get_report_by_id(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: str = Path(..., description="Report ID"),
    format: str = Query("json", regex="^(json|csv)$", description="Download format")
):
    """Download monitoring report in specified format"""
    try:
        # Find the report file
        reports_data = await hls_service.get_reports_list(page=1, per_page=1000)
        report_item = None
        
        for report in reports_data['reports']:
            if report.report_id == report_id:
                report_item = report
                break
        
        if not report_item:
            raise HTTPException(status_code=404, detail="Report not found")
        
        if format == "json":
            file_path = report_item.file_path
        else:  # csv
            # Convert JSON path to CSV path
            json_path = report_item.file_path
            csv_path = json_path.replace('/json/', '/csv/').replace('.json', '.csv')
            file_path = csv_path
        
        # Check if file exists
        from pathlib import Path
        if not Path(file_path).exists():
            raise HTTPException(status_code=404, detail=f"Report file not found in {format} format")
        
        # Determine media type
        media_type = "application/json" if format == "json" else "text/csv"
        filename = f"arabic_tv_report_{report_id}.{format}"
        
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs/files")
async def get_log_files():
    """Get list of available log files"""
    try:
        log_files = await logs_service.get_log_files()
        return {"log_files": log_files}
    except Exception as e:
        logger.error(f"Error getting log files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs")
async def get_logs(
    file_path: Optional[str] = Query(None, description="Specific log file path"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(100, ge=1, le=1000, description="Items per page"),
    level: Optional[str] = Query(None, regex="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$", description="Log level filter"),
    search: Optional[str] = Query(None, description="Search query")
):
    """Get log entries with filtering and pagination"""
    try:
        logs_response = await logs_service.read_logs(
            file_path=file_path,
            page=page,
            per_page=per_page,
            level_filter=level,
            search_query=search
        )
        return logs_response
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs/raw")
async def get_raw_log_content(
    file_path: str = Query(..., description="Log file path")
):
    """Get raw content of a log file"""
    try:
        content = await logs_service.get_log_file_content(file_path)
        if content is None:
            raise HTTPException(status_code=404, detail="Log file not found")
        
        return JSONResponse(
            content={"content": content, "file_path": file_path}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting raw log content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/logs")
async def delete_log_file(
    file_path: str = Query(..., description="Log file path to delete")
):
    """Delete a log file"""
    try:
        deleted = await logs_service.delete_log_file(file_path)
        if deleted:
            return SuccessResponse(message="Log file deleted successfully")
        else:
            raise HTTPException(status_code=404, detail="Log file not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting log file: {e}")
        raise HTTPException(status_code=500, detail=str(e))
