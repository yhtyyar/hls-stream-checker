# Arabic TV HLS Stream Checker - Production Deployment Guide

## 🚀 Quick Start for Testing

### 1. Activate Virtual Environment
```bash
# On Linux/Mac:
source venv/bin/activate

# On Windows (PowerShell):
venv\Scripts\activate

# On Windows (Command Prompt):
venv\Scripts\activate.bat
```

### 2. Start the Server
```bash
# Development mode (recommended for testing):
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload --log-level info

# Production mode (multiple workers):
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 4 --log-level info
```

### 3. Access the Application
- **Web Interface**: http://localhost:8080
- **API Documentation**: http://localhost:8080/v1/api/docs
- **OpenAPI Schema**: http://localhost:8080/v1/api/openapi.json

## 🧪 Testing Scenarios

### Scenario 1: Basic Channel Monitoring
1. Open http://localhost:8080
2. Select "All Channels" or choose specific channels by ID
3. Set duration to 2-5 minutes
4. Click "Start Monitoring"
5. Watch real-time progress
6. View results in Reports tab

### Scenario 2: API Testing with Python
```python
import requests

# Test health endpoint
response = requests.get("http://localhost:8080/v1/api/health")
print(f"Health: {response.json()}")

# Get channels
channels = requests.get("http://localhost:8080/v1/api/arabic_tv/channels").json()
print(f"Found {len(channels)} channels")

# Start monitoring
monitoring_data = {
    "channels": [23388, 27252],  # Al Jazeera channels
    "duration_minutes": 3,
    "export_data": True
}
start = requests.post("http://localhost:8080/v1/api/arabic_tv/monitoring/start", json=monitoring_data)
print(f"Monitoring started: {start.json()}")
```

### Scenario 3: Load Testing
```bash
# Test API endpoints with curl
curl -X GET "http://localhost:8080/v1/api/arabic_tv/channels"
curl -X GET "http://localhost:8080/v1/api/arabic_tv/monitoring/status"
curl -X GET "http://localhost:8080/v1/api/arabic_tv/reports"
```

## 📊 Key Features to Test

### ✅ Channel Management
- [ ] Load all Arabic TV channels
- [ ] Filter by channel IDs
- [ ] Verify channel data structure

### ✅ Monitoring Engine
- [ ] Start monitoring with different channel selections
- [ ] Monitor real-time progress
- [ ] Handle different duration settings (1-1440 minutes)
- [ ] Test stop monitoring functionality

### ✅ Reporting System
- [ ] Generate monitoring reports
- [ ] Download reports in JSON format
- [ ] Download reports in CSV format
- [ ] View report details with metrics

### ✅ Logging System
- [ ] View system logs
- [ ] Filter logs by level (DEBUG, INFO, WARNING, ERROR)
- [ ] Search logs by content
- [ ] Pagination through log entries

### ✅ Web Interface
- [ ] Responsive design on different screen sizes
- [ ] Real-time status updates
- [ ] Interactive channel selection
- [ ] Report visualization

## 🔧 Troubleshooting

### Common Issues:

1. **Port Already in Use**
   ```bash
   # Find process using port 8080
   lsof -i :8080
   # Kill the process
   kill -9 <PID>
   ```

2. **Dependencies Missing**
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Permission Issues**
   ```bash
   # Make scripts executable
   chmod +x start_web_app.py
   chmod +x test_api.py
   ```

4. **Windows-Specific Issues**
   ```cmd
   # Use different port if 8080 is blocked
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8081 --reload
   ```

## 📈 Performance Testing

### Load Testing Commands:
```bash
# Test concurrent requests
ab -n 100 -c 10 http://localhost:8080/v1/api/health

# Test API endpoints
siege -c 10 -t 30s http://localhost:8080/v1/api/arabic_tv/channels
```

## 🔍 Monitoring & Logs

### Check Application Logs:
```bash
# View recent logs
tail -f logs/application.log

# Check uvicorn logs
python -m uvicorn app.main:app --log-level debug
```

### System Monitoring:
```bash
# Check memory usage
ps aux | grep uvicorn

# Check network connections
netstat -tulpn | grep 8080
```

## 🎯 Success Criteria

Your testing is successful when you can:

1. ✅ Start the server without errors
2. ✅ Load the web interface in browser
3. ✅ View all Arabic TV channels
4. ✅ Start monitoring with channel selection
5. ✅ See real-time progress updates
6. ✅ Generate and download reports
7. ✅ View and filter logs
8. ✅ Stop monitoring gracefully

## 🚨 Emergency Stop

If something goes wrong:

```bash
# Stop all uvicorn processes
pkill -f uvicorn

# Stop all Python processes
pkill -f python3

# Clean restart
source venv/bin/activate
python3 start_web_app.py
```

## 📞 Support

If you encounter issues:

1. Check the server logs for error messages
2. Verify all dependencies are installed
3. Test individual API endpoints
4. Check network connectivity
5. Review firewall settings

---

**Happy Testing! 🎉**

*This guide was created for comprehensive testing of the Arabic TV HLS Stream Checker application.*
