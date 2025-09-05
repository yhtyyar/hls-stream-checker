#!/bin/bash

# HLS Stream Checker - Deployment Script
# This script deploys the HLS Stream Checker to a production environment

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 HLS Stream Checker - Deployment${NC}"
echo "==================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}❌ This deployment script must be run as root${NC}"
  echo "Please run with sudo: sudo ./deploy.sh"
  exit 1
fi

# Default values
INSTALL_DIR="/opt/hls-checker"
SERVICE_NAME="hls_checker"
USER_NAME="hlschecker"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --install-dir)
      INSTALL_DIR="$2"
      shift 2
      ;;
    --service-name)
      SERVICE_NAME="$2"
      shift 2
      ;;
    --user)
      USER_NAME="$2"
      shift 2
      ;;
    --help)
      echo "Usage: sudo ./deploy.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --install-dir DIR     Installation directory (default: /opt/hls-checker)"
      echo "  --service-name NAME   Service name (default: hls_checker)"
      echo "  --user NAME           User to run service as (default: hlschecker)"
      echo "  --help                Show this help message"
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      exit 1
      ;;
  esac
done

echo -e "${BLUE}📋 Configuration:${NC}"
echo "  Install directory: $INSTALL_DIR"
echo "  Service name: $SERVICE_NAME"
echo "  User: $USER_NAME"
echo ""

# Create system user if it doesn't exist
echo -e "${YELLOW}👥 Creating system user...${NC}"
if id "$USER_NAME" &>/dev/null; then
    echo "User $USER_NAME already exists"
else
    useradd --system --no-create-home --shell /usr/sbin/nologin "$USER_NAME"
    echo "Created user $USER_NAME"
fi

# Create installation directory
echo -e "${YELLOW}📁 Creating installation directory...${NC}"
mkdir -p "$INSTALL_DIR"

# Copy files
echo -e "${YELLOW}📦 Copying files...${NC}"
cp -r ./* "$INSTALL_DIR/"
# Exclude deployment script
rm -f "$INSTALL_DIR/deploy.sh"

# Set permissions
echo -e "${YELLOW}🔒 Setting permissions...${NC}"
chown -R "$USER_NAME":"$USER_NAME" "$INSTALL_DIR"
chmod +x "$INSTALL_DIR/hls_checker_single.py"
chmod +x "$INSTALL_DIR/setup_ubuntu.sh"
chmod +x "$INSTALL_DIR/run_checker.sh"

# Create data directories with proper permissions
mkdir -p "$INSTALL_DIR/data/csv" "$INSTALL_DIR/data/json"
chown -R "$USER_NAME":"$USER_NAME" "$INSTALL_DIR/data"

# Create logs directory
mkdir -p "$INSTALL_DIR/logs"
chown -R "$USER_NAME":"$USER_NAME" "$INSTALL_DIR/logs"

# Run setup script
echo -e "${YELLOW}🔧 Running setup...${NC}"
cd "$INSTALL_DIR"

# Create and setup virtual environment
python3 -m venv hls_venv
chown -R "$USER_NAME":"$USER_NAME" hls_venv

# Install dependencies as hlschecker user
sudo -u "$USER_NAME" bash << EOF
source hls_venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
EOF

# Create necessary directories if they don't exist
mkdir -p data/csv data/json logs
chown -R "$USER_NAME":"$USER_NAME" data logs

# Install the service
echo -e "${YELLOW}⚙️  Installing systemd service...${NC}"
# Update service file with correct paths
sed -i "s|/opt/hls-checker|$INSTALL_DIR|g" "$INSTALL_DIR/hls_checker.service"
cp "$INSTALL_DIR/hls_checker.service" "/etc/systemd/system/$SERVICE_NAME.service"

# Reload systemd
systemctl daemon-reload

echo ""
echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo ""
echo -e "${BLUE}📋 Next steps:${NC}"
echo "1. Start the service: sudo systemctl start $SERVICE_NAME"
echo "2. Enable service on boot: sudo systemctl enable $SERVICE_NAME"
echo "3. Check service status: sudo systemctl status $SERVICE_NAME"
echo "4. View logs: sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "To run manually:"
echo "  sudo -u $USER_NAME /opt/hls-checker/hls_venv/bin/python /opt/hls-checker/hls_checker_single.py --count 5 --minutes 2"