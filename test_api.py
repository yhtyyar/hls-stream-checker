#!/usr/bin/env python3
"""
Comprehensive API Testing Script for Arabic TV HLS Stream Checker
This script demonstrates all API endpoints and functionality
"""
import requests
import json
import time
import sys
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8081"
API_BASE = f"{BASE_URL}/v1/api/arabic_tv"

def test_endpoint(name, url, method="GET", data=None, expected_status=200):
    """Test an API endpoint"""
    print(f"\n🧪 Testing {name}...")
    print(f"   {method} {url}")

    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, timeout=10)

        status_icon = "✅" if response.status_code == expected_status else f"❌ ({response.status_code})"
        print(f"   {status_icon} Status: {response.status_code}")

        if response.status_code == expected_status:
            try:
                result = response.json()
                if isinstance(result, list):
                    print(f"   📊 Returned {len(result)} items")
                elif isinstance(result, dict):
                    print(f"   📊 Response keys: {list(result.keys())}")
                return result
            except:
                print(f"   📄 Response: {response.text[:200]}...")
                return response.text
        else:
            print(f"   ❌ Error: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"   ❌ Connection Error: {e}")
        return None

def wait_for_server(max_attempts=30):
    """Wait for server to be ready"""
    print("⏳ Waiting for server to start...")
    for attempt in range(max_attempts):
        try:
            response = requests.get(f"{BASE_URL}/v1/api/health", timeout=5)
            if response.status_code == 200:
                print("✅ Server is ready!")
                return True
        except:
            pass

        if attempt < max_attempts - 1:
            print(f"   Attempt {attempt + 1}/{max_attempts}... waiting 2 seconds")
            time.sleep(2)

    print("❌ Server failed to start within timeout")
    return False

def main():
    """Main testing function"""
    print("🚀 Arabic TV HLS Stream Checker - API Testing Suite")
    print("=" * 60)

    # Check if server is running
    if not wait_for_server():
        print("💡 Make sure the server is running:")
        print("   source venv/bin/activate")
        print("   python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8081 --reload")
        sys.exit(1)

    print("\n📋 Testing API Endpoints...\n")

    # 1. Health Check
    test_endpoint("Health Check", f"{BASE_URL}/v1/api/health")

    # 2. Get Channels
    channels = test_endpoint("Get Channels", f"{API_BASE}/channels")
    if channels:
        print(f"   📺 Found {len(channels)} Arabic TV channels")
        if len(channels) > 0:
            print(f"   🎯 Sample channel: {channels[0]['name_ru']} (ID: {channels[0]['our_id']})")

    # 3. Get Monitoring Status
    status = test_endpoint("Monitoring Status", f"{API_BASE}/monitoring/status")
    if status:
        print(f"   📊 Monitoring status: {status['status']}")

    # 4. Get Reports
    reports = test_endpoint("Get Reports", f"{API_BASE}/reports")
    if reports:
        print(f"   📄 Found {reports['total_count']} reports")
        if reports['reports']:
            print(f"   📈 Latest report: {reports['reports'][0]['success_rate']:.1f}% success rate")

    # 5. Get Log Files
    log_files = test_endpoint("Get Log Files", f"{API_BASE}/logs/files")
    if log_files:
        print(f"   📁 Found {len(log_files['log_files'])} log files")
        for log_file in log_files['log_files'][:3]:  # Show first 3
            print(f"      📄 {log_file['name']} ({log_file['size']} bytes)")

    # 6. Start Monitoring (if no active monitoring)
    if status and status['status'] == 'idle':
        print("\n🎬 Starting monitoring test...")
        monitoring_data = {
            "channels": [23388, 27252],  # Al Jazeera channels
            "duration_minutes": 2,
            "export_data": True
        }

        start_result = test_endpoint(
            "Start Monitoring",
            f"{API_BASE}/monitoring/start",
            method="POST",
            data=monitoring_data
        )

        if start_result:
            print("   ⏳ Monitoring started, waiting for completion...")
            time.sleep(10)  # Wait 10 seconds

            # Check status again
            status = test_endpoint("Monitoring Status (After Start)", f"{API_BASE}/monitoring/status")
            if status:
                print(f"   📊 Current status: {status['status']}")
                if status.get('progress_percent'):
                    print(f"   📊 Progress: {status['progress_percent']:.1f}%")

    # 7. Get Logs (with filtering)
    print("\n📝 Testing Log API...")
    logs = test_endpoint(
        "Get Logs (INFO level)",
        f"{API_BASE}/logs?level=INFO&page=1&per_page=5"
    )
    if logs:
        print(f"   📄 Found {logs['total_count']} log entries")
        for log in logs['logs'][:3]:  # Show first 3
            print(f"      📋 {log['timestamp'][:19]} [{log['level']}] {log['message'][:80]}...")

    # 8. Test Report Download (if reports exist)
    if reports and reports['reports']:
        print("\n📥 Testing Report Download...")
        report_id = reports['reports'][0]['report_id']
        test_endpoint(
            "Download JSON Report",
            f"{API_BASE}/reports/{report_id}/download?format=json"
        )
        test_endpoint(
            "Download CSV Report",
            f"{API_BASE}/reports/{report_id}/download?format=csv"
        )

    print("\n" + "=" * 60)
    print("🎉 API Testing Complete!")
    print("\n🌐 Web Interface Available:")
    print(f"   📱 Main App: {BASE_URL}")
    print(f"   📚 API Docs: {BASE_URL}/v1/api/docs")
    print(f"   🔧 OpenAPI: {BASE_URL}/v1/api/openapi.json")
    print("\n💡 Pro Tips:")
    print("   • Use the web interface for interactive testing")
    print("   • Check API documentation for detailed endpoint specs")
    print("   • Monitor logs for debugging information")
    print("   • Test with different channel selections and durations")

if __name__ == "__main__":
    main()
