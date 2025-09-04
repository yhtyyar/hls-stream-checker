#!/bin/bash

# HLS Stream Checker - Ubuntu Setup Script
# This script installs all dependencies and sets up the environment for HLS Stream Checker

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 HLS Stream Checker - Ubuntu Setup${NC}"
echo "======================================"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
  echo -e "${YELLOW}⚠️  It's recommended to run this script as a regular user, not root${NC}"
  echo "   The script will use sudo when necessary"
  echo ""
fi

# Update package list
echo -e "${YELLOW}🔄 Updating package list...${NC}"
sudo apt update

# Install Python 3 and pip if not already installed
echo -e "${YELLOW}🐍 Checking Python installation...${NC}"
if ! command -v python3 &> /dev/null; then
    echo "Installing Python 3..."
    sudo apt install -y python3
else
    echo "Python 3 is already installed"
fi

if ! command -v pip3 &> /dev/null; then
    echo "Installing pip..."
    sudo apt install -y python3-pip
else
    echo "pip is already installed"
fi

# Install required system packages
echo -e "${YELLOW}📦 Installing system dependencies...${NC}"
sudo apt install -y python3-venv python3-dev build-essential

# Create virtual environment
echo -e "${YELLOW}🔧 Creating virtual environment...${NC}"
python3 -m venv hls_venv
source hls_venv/bin/activate

# Upgrade pip
echo -e "${YELLOW}⬆️  Upgrading pip...${NC}"
pip install --upgrade pip

# Install Python dependencies
echo -e "${YELLOW}🐍 Installing Python dependencies...${NC}"
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo -e "${GREEN}✅ Python dependencies installed successfully${NC}"
else
    echo -e "${RED}❌ requirements.txt not found!${NC}"
    echo "Installing requests directly..."
    pip install requests>=2.25.0
fi

# Create necessary directories
echo -e "${YELLOW}📁 Creating data directories...${NC}"
mkdir -p data/csv data/json

# Create a log directory
mkdir -p logs

echo ""
echo -e "${GREEN}✅ Setup completed successfully!${NC}"
echo ""
echo "To run the HLS Stream Checker:"
echo "1. Activate the virtual environment: source hls_venv/bin/activate"
echo "2. Run the checker: python hls_checker_single.py --help"
echo ""
echo "For example:"
echo "  python hls_checker_single.py --count 5 --minutes 2"
echo ""
echo "To deactivate the virtual environment later: deactivate"