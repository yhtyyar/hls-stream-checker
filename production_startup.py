#!/usr/bin/env python3
"""
Production startup script for Arabic TV HLS Stream Checker
This script provides multiple startup modes for different environments
"""
import os
import sys
import platform
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

def check_dependencies():
    """Check if all required dependencies are installed"""
    try:
        import fastapi
        import uvicorn
        import pydantic
        print("✅ All dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("💡 Run: pip install -r requirements.txt")
        return False

def get_environment_info():
    """Get environment information"""
    print("🔍 Environment Information:")
    print(f"   OS: {platform.system()} {platform.release()}")
    print(f"   Python: {sys.version}")
    print(f"   Working Directory: {os.getcwd()}")
    print(f"   Project Root: {project_root}")
    print()

def create_env_file():
    """Create .env file if it doesn't exist"""
    env_file = project_root / ".env"
    if not env_file.exists():
        env_content = """# Arabic TV HLS Stream Checker Environment Configuration

# Server Configuration
HOST=0.0.0.0
PORT=8080
RELOAD=true
LOG_LEVEL=info

# Application Configuration
PROJECT_NAME="Arabic TV HLS Stream Checker"
VERSION=1.0.0
API_V1_STR=/v1/api

# CORS Settings (comma-separated)
BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:8080,http://127.0.0.1:8080

# Monitoring Configuration
DEFAULT_DURATION_MINUTES=5
MAX_DURATION_MINUTES=1440
DEFAULT_PAGE_SIZE=50
MAX_PAGE_SIZE=1000

# Data Configuration
EXPORT_TIMESTAMP_FORMAT=%Y%m%d_%H%M%S
REQUEST_TIMEOUT=20
MAX_RETRIES=3
"""
        env_file.write_text(env_content)
        print("📝 Created .env configuration file")

def setup_virtual_environment():
    """Setup Python virtual environment"""
    venv_path = project_root / "venv"

    if not venv_path.exists():
        print("🐍 Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)

    # Determine activation script based on OS
    if platform.system() == "Windows":
        activate_script = venv_path / "Scripts" / "activate"
        pip_path = venv_path / "Scripts" / "pip"
        python_path = venv_path / "Scripts" / "python"
    else:
        activate_script = venv_path / "bin" / "activate"
        pip_path = venv_path / "bin" / "pip"
        python_path = venv_path / "bin" / "python"

    print(f"🔧 Virtual Environment: {venv_path}")
    print(f"   Activate: {activate_script}")
    print(f"   Python: {python_path}")
    print(f"   Pip: {pip_path}")
    print()

    return python_path, pip_path

def install_dependencies(pip_path):
    """Install project dependencies"""
    requirements_file = project_root / "requirements.txt"
    if requirements_file.exists():
        print("📦 Installing dependencies...")
        subprocess.run([str(pip_path), "install", "-r", "requirements.txt"], check=True)
        print("✅ Dependencies installed")
    else:
        print("⚠️  requirements.txt not found")

def start_development_server(python_path):
    """Start the development server"""
    print("🚀 Starting Arabic TV HLS Stream Checker (Development Mode)")
    print("=" * 60)
    print("🌐 Web Interface: http://localhost:8080")
    print("📚 API Documentation: http://localhost:8080/v1/api/docs")
    print("🔄 OpenAPI Schema: http://localhost:8080/v1/api/openapi.json")
    print("🛑 Press Ctrl+C to stop the server")
    print("=" * 60)

    try:
        subprocess.run([
            str(python_path), "start_web_app.py"
        ], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Server failed to start: {e}")

def start_production_server(python_path):
    """Start the production server using uvicorn directly"""
    print("🚀 Starting Arabic TV HLS Stream Checker (Production Mode)")
    print("=" * 60)
    print("🌐 Web Interface: http://localhost:8080")
    print("📚 API Documentation: http://localhost:8080/v1/api/docs")
    print("⚡ Production optimizations enabled")
    print("🛑 Press Ctrl+C to stop the server")
    print("=" * 60)

    try:
        subprocess.run([
            str(python_path), "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8080",
            "--workers", "4",
            "--log-level", "info",
            "--access-log"
        ], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Server failed to start: {e}")

def show_startup_options():
    """Show available startup options"""
    print("🎯 Startup Options:")
    print("1. Development Mode (with auto-reload)")
    print("2. Production Mode (multiple workers)")
    print("3. Test API Endpoints")
    print("4. Show System Status")
    print("5. Exit")
    print()

def test_api_endpoints():
    """Test key API endpoints"""
    import time
    import requests

    print("🧪 Testing API Endpoints...")
    print("=" * 40)

    base_url = "http://localhost:8080"

    # Wait for server to start
    time.sleep(3)

    # Test endpoints
    endpoints = [
        ("/", "Main page"),
        ("/v1/api/arabic_tv/channels", "Channels API"),
        ("/v1/api/health", "Health check"),
        ("/v1/api/arabic_tv/monitoring/status", "Monitoring status"),
    ]

    for endpoint, description in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            status = "✅" if response.status_code == 200 else f"❌ ({response.status_code})"
            print(f"{status} {description}: {endpoint}")
        except requests.exceptions.RequestException as e:
            print(f"❌ {description}: {endpoint} - {e}")

    print("=" * 40)
    print("💡 Open http://localhost:8080 in your browser to test the web interface")

def show_system_status():
    """Show system and application status"""
    print("📊 System Status")
    print("=" * 40)

    # Check if server is running
    import requests
    try:
        response = requests.get("http://localhost:8080/v1/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ Web Server: Running")
        else:
            print(f"⚠️  Web Server: Running (status: {response.status_code})")
    except:
        print("❌ Web Server: Not running")

    # Check directories
    dirs_to_check = ["data", "data/csv", "data/json", "logs"]
    for dir_name in dirs_to_check:
        dir_path = project_root / dir_name
        if dir_path.exists():
            file_count = len(list(dir_path.glob("*")))
            print(f"✅ {dir_name}: {file_count} files")
        else:
            print(f"❌ {dir_name}: Directory missing")

    # Check configuration files
    config_files = ["requirements.txt", "playlist_streams.json", "config.py"]
    for config_file in config_files:
        file_path = project_root / config_file
        status = "✅" if file_path.exists() else "❌"
        print(f"{status} {config_file}")

    print("=" * 40)

def main():
    """Main function"""
    print("🎬 Arabic TV HLS Stream Checker - Production Startup")
    print("=" * 60)

    get_environment_info()

    # Check dependencies first
    if not check_dependencies():
        return

    # Setup environment
    create_env_file()
    python_path, pip_path = setup_virtual_environment()
    install_dependencies(pip_path)

    while True:
        show_startup_options()
        try:
            choice = input("Select option (1-5): ").strip()

            if choice == "1":
                start_development_server(python_path)
            elif choice == "2":
                start_production_server(python_path)
            elif choice == "3":
                test_api_endpoints()
            elif choice == "4":
                show_system_status()
            elif choice == "5":
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid option. Please select 1-5.")

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
