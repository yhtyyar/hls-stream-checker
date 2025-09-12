#!/usr/bin/env python3
"""
Logs service for viewing and managing log files
"""
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

from app.core.config import settings
from app.models.schemas import LogEntry, LogsResponse


logger = logging.getLogger(__name__)


class LogsService:
    """Service for managing log files and entries"""
    
    def __init__(self):
        self.logs_dir = settings.LOGS_DIR
        self.project_root = settings.PROJECT_ROOT
    
    async def get_log_files(self) -> List[Dict[str, Any]]:
        """Get list of available log files"""
        try:
            log_files = []
            
            # Check logs directory
            if self.logs_dir.exists():
                for log_file in self.logs_dir.glob("*.log*"):
                    if log_file.is_file():
                        stat = log_file.stat()
                        log_files.append({
                            'name': log_file.name,
                            'path': str(log_file),
                            'size': stat.st_size,
                            'modified': datetime.fromtimestamp(stat.st_mtime),
                            'type': 'logs_directory'
                        })
            
            # Check for .logs files in project root
            for logs_file in self.project_root.glob("*.logs"):
                if logs_file.is_file():
                    stat = logs_file.stat()
                    log_files.append({
                        'name': logs_file.name,
                        'path': str(logs_file),
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime),
                        'type': 'dot_logs'
                    })
            
            # Sort by modification time (newest first)
            log_files.sort(key=lambda x: x['modified'], reverse=True)
            
            return log_files
            
        except Exception as e:
            logger.error(f"Error getting log files: {e}")
            return []
    
    async def read_logs(
        self, 
        file_path: Optional[str] = None,
        page: int = 1,
        per_page: int = 100,
        level_filter: Optional[str] = None,
        search_query: Optional[str] = None
    ) -> LogsResponse:
        """Read log entries from specified file or latest log file"""
        try:
            # If no file specified, get the latest log file
            if not file_path:
                log_files = await self.get_log_files()
                if not log_files:
                    return LogsResponse(
                        logs=[],
                        total_count=0,
                        page=page,
                        per_page=per_page,
                        has_next=False
                    )
                file_path = log_files[0]['path']
            
            # Validate file path
            log_path = Path(file_path)
            if not log_path.exists() or not log_path.is_file():
                raise FileNotFoundError(f"Log file not found: {file_path}")
            
            # Read and parse log entries
            log_entries = await self._parse_log_file(log_path)
            
            # Apply filters
            if level_filter:
                log_entries = [
                    entry for entry in log_entries 
                    if entry.level.upper() == level_filter.upper()
                ]
            
            if search_query:
                search_lower = search_query.lower()
                log_entries = [
                    entry for entry in log_entries
                    if search_lower in entry.message.lower()
                ]
            
            # Sort by timestamp (newest first)
            log_entries.sort(key=lambda x: x.timestamp, reverse=True)
            
            # Pagination
            total_count = len(log_entries)
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            page_entries = log_entries[start_idx:end_idx]
            
            return LogsResponse(
                logs=page_entries,
                total_count=total_count,
                page=page,
                per_page=per_page,
                has_next=end_idx < total_count
            )
            
        except Exception as e:
            logger.error(f"Error reading logs: {e}")
            return LogsResponse(
                logs=[],
                total_count=0,
                page=page,
                per_page=per_page,
                has_next=False
            )
    
    async def _parse_log_file(self, log_path: Path) -> List[LogEntry]:
        """Parse log file and extract log entries"""
        entries = []
        
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Common log patterns
            patterns = [
                # Standard Python logging format: 2024-01-15 10:30:45 INFO [module] message
                re.compile(r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(\w+)\s+\[([^\]]*)\]\s+(.*)$'),
                # Alternative format: 2024-01-15 10:30:45,123 - INFO - message
                re.compile(r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}),\d+\s*-\s*(\w+)\s*-\s*(.*)$'),
                # Simple format: INFO: message
                re.compile(r'^(\w+):\s*(.*)$'),
                # Timestamp only: [2024-01-15 10:30:45] message
                re.compile(r'^\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\]\s*(.*)$')
            ]
            
            current_entry = None
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue
                
                parsed = False
                
                # Try each pattern
                for pattern in patterns:
                    match = pattern.match(line)
                    if match:
                        groups = match.groups()
                        
                        if len(groups) >= 3 and groups[0] and groups[1]:
                            # Full format with timestamp, level, and message
                            try:
                                timestamp = datetime.strptime(groups[0], '%Y-%m-%d %H:%M:%S')
                                level = groups[1].upper()
                                source = groups[2] if len(groups) > 3 else None
                                message = groups[3] if len(groups) > 3 else groups[2]
                            except ValueError:
                                continue
                        elif len(groups) == 2:
                            # Level and message only
                            timestamp = datetime.now()  # Use current time as fallback
                            level = groups[0].upper()
                            source = None
                            message = groups[1]
                        else:
                            continue
                        
                        # Save previous entry if exists
                        if current_entry:
                            entries.append(current_entry)
                        
                        # Create new entry
                        current_entry = LogEntry(
                            timestamp=timestamp,
                            level=level,
                            message=message,
                            source=source
                        )
                        parsed = True
                        break
                
                # If line doesn't match any pattern, append to current entry message
                if not parsed and current_entry:
                    current_entry.message += f"\n{line}"
            
            # Add the last entry
            if current_entry:
                entries.append(current_entry)
            
            # If no structured logs found, treat each line as a log entry
            if not entries and lines:
                for line in lines:
                    line = line.strip()
                    if line:
                        entries.append(LogEntry(
                            timestamp=datetime.now(),
                            level="INFO",
                            message=line,
                            source=log_path.name
                        ))
            
        except Exception as e:
            logger.error(f"Error parsing log file {log_path}: {e}")
        
        return entries
    
    async def get_log_file_content(self, file_path: str) -> Optional[str]:
        """Get raw content of a log file"""
        try:
            log_path = Path(file_path)
            if not log_path.exists() or not log_path.is_file():
                return None
            
            # Limit file size to prevent memory issues (max 10MB)
            if log_path.stat().st_size > 10 * 1024 * 1024:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    # Read last 10MB
                    f.seek(-10 * 1024 * 1024, 2)
                    content = f.read()
                    return f"... (showing last 10MB)\n{content}"
            else:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
                    
        except Exception as e:
            logger.error(f"Error reading log file content: {e}")
            return None
    
    async def delete_log_file(self, file_path: str) -> bool:
        """Delete a log file"""
        try:
            log_path = Path(file_path)
            
            # Security check - only allow deletion of files in logs directory or .logs files
            if not (
                log_path.parent == self.logs_dir or 
                (log_path.parent == self.project_root and log_path.suffix == '.logs')
            ):
                raise PermissionError("Can only delete files in logs directory or .logs files")
            
            if log_path.exists() and log_path.is_file():
                log_path.unlink()
                logger.info(f"Deleted log file: {file_path}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error deleting log file: {e}")
            return False


# Global service instance
logs_service = LogsService()
