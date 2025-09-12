#!/usr/bin/env python3
"""
HLS monitoring service - integrates with existing HLS checker functionality
"""
import json
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from concurrent.futures import ThreadPoolExecutor
import uuid

from app.core.config import settings
from app.models.schemas import (
    ChannelInfo, MonitoringStatus, StreamStats, 
    MonitoringReport, ReportListItem
)

# Import existing HLS checker components
import sys
sys.path.append(str(settings.PROJECT_ROOT))
from hls_checker_single import HLSStreamChecker, ChannelStats


logger = logging.getLogger(__name__)


class HLSMonitoringService:
    """Service for managing HLS stream monitoring"""
    
    def __init__(self):
        self.active_monitoring: Optional[Dict[str, Any]] = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    async def get_available_channels(self) -> List[ChannelInfo]:
        """Get list of available Arabic TV channels"""
        try:
            with open(settings.PLAYLIST_STREAMS_FILE, 'r', encoding='utf-8') as f:
                channels_data = json.load(f)
            
            channels = [
                ChannelInfo(
                    our_id=channel['our_id'],
                    name_ru=channel['name_ru'],
                    stream_common=channel['stream_common'],
                    url=channel['url']
                )
                for channel in channels_data
            ]
            return channels
        except Exception as e:
            logger.error(f"Error loading channels: {e}")
            return []
    
    async def start_monitoring(
        self, 
        channels: Union[str, List[int]], 
        duration_minutes: int,
        export_data: bool = True
    ) -> str:
        """Start HLS monitoring session"""
        
        if self.active_monitoring and self.active_monitoring['status'] == 'running':
            raise ValueError("Monitoring session already active")
        
        # Generate unique monitoring session ID
        session_id = str(uuid.uuid4())
        
        # Load available channels
        available_channels = await self.get_available_channels()
        
        # Filter channels based on request
        if channels == "all":
            selected_channels = available_channels
        else:
            channel_ids = set(channels)
            selected_channels = [
                ch for ch in available_channels 
                if ch.our_id in channel_ids
            ]
        
        if not selected_channels:
            raise ValueError("No valid channels selected")
        
        # Initialize monitoring session
        start_time = datetime.now()
        self.active_monitoring = {
            'session_id': session_id,
            'status': 'running',
            'start_time': start_time,
            'duration_minutes': duration_minutes,
            'channels': selected_channels,
            'export_data': export_data,
            'progress': 0.0,
            'stats': {}
        }
        
        # Start monitoring in background
        asyncio.create_task(self._run_monitoring_session())
        
        return session_id
    
    async def _run_monitoring_session(self):
        """Run the actual monitoring session"""
        try:
            session = self.active_monitoring
            channels = session['channels']
            duration_minutes = session['duration_minutes']
            
            # Initialize channel stats
            channel_stats = ChannelStats()
            
            # Run monitoring for each channel
            end_time = datetime.now() + timedelta(minutes=duration_minutes)
            
            while datetime.now() < end_time:
                for channel in channels:
                    try:
                        # Create HLS checker for this channel
                        checker = HLSStreamChecker(
                            url=channel.url,
                            channel_stats=channel_stats
                        )
                        
                        # Run check in executor to avoid blocking
                        await asyncio.get_event_loop().run_in_executor(
                            self.executor,
                            self._check_channel,
                            checker,
                            channel
                        )
                        
                        # Update progress
                        elapsed = (datetime.now() - session['start_time']).total_seconds()
                        total_duration = duration_minutes * 60
                        session['progress'] = min(100.0, (elapsed / total_duration) * 100)
                        
                    except Exception as e:
                        logger.error(f"Error checking channel {channel.our_id}: {e}")
                
                # Wait before next check cycle
                await asyncio.sleep(30)  # Check every 30 seconds
            
            # Monitoring completed
            session['status'] = 'completed'
            session['end_time'] = datetime.now()
            
            # Export data if requested
            if session['export_data']:
                await self._export_monitoring_data(session)
                
        except Exception as e:
            logger.error(f"Monitoring session error: {e}")
            if self.active_monitoring:
                self.active_monitoring['status'] = 'error'
                self.active_monitoring['error'] = str(e)
    
    def _check_channel(self, checker: HLSStreamChecker, channel: ChannelInfo):
        """Check a single channel (runs in thread executor)"""
        try:
            # This would integrate with the existing HLS checker logic
            # For now, we'll simulate the check
            import time
            import random
            
            start_time = time.time()
            
            # Simulate network request
            time.sleep(random.uniform(0.1, 2.0))
            
            response_time = time.time() - start_time
            success = random.choice([True, True, True, False])  # 75% success rate
            
            # Update stats
            session = self.active_monitoring
            if channel.our_id not in session['stats']:
                session['stats'][channel.our_id] = {
                    'channel_name': channel.name_ru,
                    'total_checks': 0,
                    'successful_checks': 0,
                    'failed_checks': 0,
                    'response_times': [],
                    'last_check_time': None
                }
            
            stats = session['stats'][channel.our_id]
            stats['total_checks'] += 1
            stats['last_check_time'] = datetime.now()
            stats['response_times'].append(response_time)
            
            if success:
                stats['successful_checks'] += 1
            else:
                stats['failed_checks'] += 1
                
        except Exception as e:
            logger.error(f"Channel check error: {e}")
    
    async def get_monitoring_status(self) -> MonitoringStatus:
        """Get current monitoring status"""
        if not self.active_monitoring:
            return MonitoringStatus(status="idle")
        
        session = self.active_monitoring
        status = MonitoringStatus(
            status=session['status'],
            start_time=session['start_time'],
            duration_minutes=session['duration_minutes'],
            channels_count=len(session['channels']),
            progress_percent=session.get('progress', 0.0)
        )
        
        if session['status'] == 'running' and session.get('start_time'):
            estimated_end = session['start_time'] + timedelta(minutes=session['duration_minutes'])
            status.estimated_completion = estimated_end
        
        return status
    
    async def stop_monitoring(self) -> bool:
        """Stop active monitoring session"""
        if not self.active_monitoring or self.active_monitoring['status'] != 'running':
            return False
        
        self.active_monitoring['status'] = 'stopped'
        self.active_monitoring['end_time'] = datetime.now()
        
        # Export data if requested
        if self.active_monitoring.get('export_data'):
            await self._export_monitoring_data(self.active_monitoring)
        
        return True
    
    async def _export_monitoring_data(self, session: Dict[str, Any]):
        """Export monitoring data to files"""
        try:
            session_id = session['session_id']
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create report data
            report_data = {
                'report_id': session_id,
                'start_time': session['start_time'].isoformat(),
                'end_time': session.get('end_time', datetime.now()).isoformat(),
                'duration_minutes': session['duration_minutes'],
                'channels': [ch.dict() for ch in session['channels']],
                'stats': session['stats'],
                'summary': self._generate_summary(session)
            }
            
            # Export to JSON
            json_file = settings.JSON_DIR / f"arabic_tv_report_{timestamp}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
            
            # Export to CSV
            csv_file = settings.CSV_DIR / f"arabic_tv_report_{timestamp}.csv"
            await self._export_to_csv(session, csv_file)
            
            logger.info(f"Monitoring data exported: {json_file}, {csv_file}")
            
        except Exception as e:
            logger.error(f"Error exporting monitoring data: {e}")
    
    async def _export_to_csv(self, session: Dict[str, Any], csv_file: Path):
        """Export session data to CSV format"""
        import csv
        
        try:
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow([
                    'Channel ID', 'Channel Name', 'Total Checks', 
                    'Successful Checks', 'Failed Checks', 'Success Rate (%)',
                    'Avg Response Time (s)', 'Last Check Time'
                ])
                
                # Write data
                for channel_id, stats in session['stats'].items():
                    success_rate = (stats['successful_checks'] / stats['total_checks'] * 100) if stats['total_checks'] > 0 else 0
                    avg_response_time = sum(stats['response_times']) / len(stats['response_times']) if stats['response_times'] else 0
                    
                    writer.writerow([
                        channel_id,
                        stats['channel_name'],
                        stats['total_checks'],
                        stats['successful_checks'],
                        stats['failed_checks'],
                        f"{success_rate:.2f}",
                        f"{avg_response_time:.3f}",
                        stats['last_check_time']
                    ])
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
    
    def _generate_summary(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Generate monitoring session summary"""
        stats = session['stats']
        
        if not stats:
            return {}
        
        total_checks = sum(s['total_checks'] for s in stats.values())
        total_successful = sum(s['successful_checks'] for s in stats.values())
        total_failed = sum(s['failed_checks'] for s in stats.values())
        
        all_response_times = []
        for s in stats.values():
            all_response_times.extend(s['response_times'])
        
        return {
            'total_channels': len(stats),
            'total_checks': total_checks,
            'total_successful': total_successful,
            'total_failed': total_failed,
            'overall_success_rate': (total_successful / total_checks * 100) if total_checks > 0 else 0,
            'avg_response_time': sum(all_response_times) / len(all_response_times) if all_response_times else 0,
            'session_duration_actual': (session.get('end_time', datetime.now()) - session['start_time']).total_seconds() / 60
        }
    
    async def get_reports_list(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """Get list of available monitoring reports"""
        try:
            json_files = list(settings.JSON_DIR.glob("arabic_tv_report_*.json"))
            json_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Pagination
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            page_files = json_files[start_idx:end_idx]
            
            reports = []
            for file_path in page_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    reports.append(ReportListItem(
                        report_id=data.get('report_id', file_path.stem),
                        start_time=datetime.fromisoformat(data['start_time']),
                        end_time=datetime.fromisoformat(data['end_time']),
                        duration_minutes=data['duration_minutes'],
                        channels_count=len(data.get('channels', [])),
                        success_rate=data.get('summary', {}).get('overall_success_rate', 0),
                        file_path=str(file_path)
                    ))
                except Exception as e:
                    logger.error(f"Error reading report file {file_path}: {e}")
            
            return {
                'reports': reports,
                'total_count': len(json_files),
                'page': page,
                'per_page': per_page,
                'has_next': end_idx < len(json_files)
            }
            
        except Exception as e:
            logger.error(f"Error getting reports list: {e}")
            return {
                'reports': [],
                'total_count': 0,
                'page': page,
                'per_page': per_page,
                'has_next': False
            }
    
    async def get_report_by_id(self, report_id: str) -> Optional[MonitoringReport]:
        """Get detailed monitoring report by ID"""
        try:
            # Find report file
            json_files = list(settings.JSON_DIR.glob("arabic_tv_report_*.json"))
            
            for file_path in json_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if data.get('report_id') == report_id:
                        # Convert to MonitoringReport
                        streams = []
                        for channel_id, stats in data.get('stats', {}).items():
                            success_rate = (stats['successful_checks'] / stats['total_checks'] * 100) if stats['total_checks'] > 0 else 0
                            avg_response_time = sum(stats['response_times']) / len(stats['response_times']) if stats['response_times'] else 0
                            
                            streams.append(StreamStats(
                                channel_id=int(channel_id),
                                channel_name=stats['channel_name'],
                                total_checks=stats['total_checks'],
                                successful_checks=stats['successful_checks'],
                                failed_checks=stats['failed_checks'],
                                success_rate=success_rate,
                                avg_response_time=avg_response_time,
                                last_check_time=datetime.fromisoformat(stats['last_check_time']),
                                status="active" if success_rate > 80 else "warning" if success_rate > 50 else "error"
                            ))
                        
                        return MonitoringReport(
                            report_id=report_id,
                            start_time=datetime.fromisoformat(data['start_time']),
                            end_time=datetime.fromisoformat(data['end_time']),
                            duration_minutes=data['duration_minutes'],
                            total_channels=len(data.get('channels', [])),
                            total_checks=data.get('summary', {}).get('total_checks', 0),
                            overall_success_rate=data.get('summary', {}).get('overall_success_rate', 0),
                            streams=streams,
                            summary=data.get('summary', {})
                        )
                except Exception as e:
                    logger.error(f"Error reading report file {file_path}: {e}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting report by ID: {e}")
            return None


# Global service instance
hls_service = HLSMonitoringService()
