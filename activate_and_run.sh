#!/bin/bash

# Simple script to activate virtual environment and run commands
# Works with both bash and fish shells

echo "🐍 Activating Python virtual environment..."

# Use the virtual environment Python directly
PYTHON_PATH="./venv/bin/python"

if [ ! -f "$PYTHON_PATH" ]; then
    echo "❌ Virtual environment not found at $PYTHON_PATH"
    echo "Please run: python3 -m venv venv && pip install -r requirements.txt"
    exit 1
fi

echo "✅ Using Python: $PYTHON_PATH"

# Check if argument provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <script_name.py> [args...]"
    echo "Example: $0 run_langgraph_demo.py"
    exit 1
fi

# Run the Python script with all arguments
echo "🚀 Running: $@"
echo ""
$PYTHON_PATH "$@"
