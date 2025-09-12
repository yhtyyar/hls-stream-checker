#!/usr/bin/env python3
"""
Startup script for Arabic TV HLS Stream Checker Web Application
"""
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

def main():
    """Main function to start the web application"""
    try:
        import uvicorn
        from app.main import app
        
        print("🚀 Starting Arabic TV HLS Stream Checker Web Application...")
        print("📡 Monitoring Arabic TV channels with advanced analytics")
        print("🌐 Web interface will be available at: http://localhost:8080")
        print("📚 API documentation at: http://localhost:8080/v1/api/docs")
        print("=" * 60)
        
        # Start the server
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8080,
            reload=True,
            log_level="info",
            access_log=True
        )
        
    except ImportError as e:
        print(f"❌ Error: Missing dependencies - {e}")
        print("💡 Please install requirements: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
