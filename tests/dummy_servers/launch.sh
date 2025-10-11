#!/bin/bash
# Quick launcher for dummy test servers
# Usage: ./launch.sh

cd "$(dirname "$0")"

echo "========================================"
echo "Dummy Test Servers Quick Launcher"
echo "========================================"
echo ""
echo "Choose an option:"
echo "  1) Start all servers"
echo "  2) Start API server only"
echo "  3) Start WebSocket servers only"
echo "  4) Run demo"
echo "  5) Run tests"
echo "  0) Exit"
echo ""
read -p "Enter your choice: " choice

case $choice in
    1)
        echo "Starting all servers..."
        python run_servers.py
        ;;
    2)
        echo "Starting API server only..."
        python run_servers.py --api-only
        ;;
    3)
        echo "Starting WebSocket servers only..."
        python run_servers.py --websocket-only
        ;;
    4)
        echo "Running demo..."
        python demo.py
        ;;
    5)
        echo "Running tests..."
        python test_servers.py --quick
        ;;
    0)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo "Invalid choice!"
        exit 1
        ;;
esac
