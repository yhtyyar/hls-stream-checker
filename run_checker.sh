#!/bin/bash

# HLS Stream Checker - Run Script
# This script runs the HLS Stream Checker with common options

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
CHANNEL_COUNT="all"
DURATION_MINUTES="5"
REFRESH_PLAYLIST=false
EXPORT_DATA=true

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -c|--count)
      CHANNEL_COUNT="$2"
      shift 2
      ;;
    -m|--minutes)
      DURATION_MINUTES="$2"
      shift 2
      ;;
    -r|--refresh)
      REFRESH_PLAYLIST=true
      shift
      ;;
    --no-export)
      EXPORT_DATA=false
      shift
      ;;
    -h|--help)
      echo "HLS Stream Checker Runner"
      echo "========================"
      echo ""
      echo "Usage: ./run_checker.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  -c, --count NUM       Number of channels to check (default: all)"
      echo "  -m, --minutes NUM     Duration in minutes (default: 5)"
      echo "  -r, --refresh         Refresh playlist before checking"
      echo "  --no-export           Run without exporting data"
      echo "  -h, --help            Show this help message"
      echo ""
      echo "Examples:"
      echo "  ./run_checker.sh                    # Check all channels for 5 minutes"
      echo "  ./run_checker.sh -c 10 -m 3         # Check 10 channels for 3 minutes"
      echo "  ./run_checker.sh -r -c 5 -m 2       # Refresh and check 5 channels for 2 minutes"
      echo "  ./run_checker.sh --no-export        # Run without data export"
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

echo -e "${GREEN}🚀 HLS Stream Checker${NC}"
echo "====================="

# Build command
CMD="python hls_checker_single.py --count $CHANNEL_COUNT --minutes $DURATION_MINUTES"

if [ "$REFRESH_PLAYLIST" = true ]; then
    CMD="$CMD --refresh"
fi

if [ "$EXPORT_DATA" = false ]; then
    CMD="$CMD --no-export"
fi

echo -e "${BLUE}📋 Running command:${NC}"
echo "  $CMD"
echo ""

# Check if virtual environment exists
if [ -d "hls_venv" ]; then
    echo -e "${YELLOW}🔧 Activating virtual environment...${NC}"
    source hls_venv/bin/activate
else
    echo -e "${YELLOW}⚠️  Virtual environment not found, using system Python${NC}"
fi

# Run the checker
echo -e "${GREEN}▶️  Starting HLS Stream Checker...${NC}"
eval $CMD

echo ""
echo -e "${GREEN}✅ HLS Stream Checker completed!${NC}"

# Show where data was exported
if [ "$EXPORT_DATA" = true ]; then
    echo ""
    echo -e "${BLUE}📁 Data exported to:${NC}"
    echo "  CSV files: data/csv/"
    echo "  JSON files: data/json/"
    ls -la data/csv/ data/json/ 2>/dev/null || echo "  No files found"
fi