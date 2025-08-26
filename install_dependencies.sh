#!/bin/bash

# AI Agent Framework Dependency Installation Script

echo "🚀 AI Agent Framework - Dependency Installation"
echo "=============================================="

# Check Python version and find best version
echo "🐍 Checking Python version..."
if command -v python3.13 &> /dev/null; then
    PYTHON_CMD="python3.13"
    echo "✅ Using Python 3.13 for LangGraph CLI compatibility"
elif command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
    echo "✅ Using Python 3.12 for LangGraph CLI compatibility"
elif command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
    echo "✅ Using Python 3.11 for LangGraph CLI compatibility"
else
    PYTHON_CMD="python3"
    PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    echo "✅ Python: $PYTHON_VERSION"
    if [[ $(echo "$PYTHON_VERSION < 3.11" | bc -l) -eq 1 ]]; then
        echo "⚠️  Python 3.11+ required for LangGraph CLI. Current: $PYTHON_VERSION"
        echo "Please install Python 3.11+ from https://python.org/"
        exit 1
    fi
fi

# Create virtual environment
echo ""
echo "🌐 Setting up virtual environment..."
$PYTHON_CMD -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
echo ""
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Install LangGraph CLI
echo ""
echo "🎨 Installing LangGraph CLI..."
pip install -U "langgraph-cli[inmem]"

if [ $? -eq 0 ]; then
    echo "✅ LangGraph CLI installed successfully"
else
    echo "❌ Failed to install LangGraph CLI"
    echo "Please try manually:"
    echo "pip install -U \"langgraph-cli[inmem]\""
    exit 1
fi

# Setup environment variables
echo ""
echo "🔐 Setting up environment variables..."
if [ ! -f .env ]; then
    cp env.example .env
    echo "✅ Created .env file from env.example"
    echo "   Please edit .env and add your API keys"
fi

# Verify LangSmith configuration
echo ""
echo "🔍 Checking LangSmith configuration..."
if [ -z "$LANGSMITH_API_KEY" ]; then
    echo "⚠️  LANGSMITH_API_KEY not set"
    echo "   To enable tracing:"
    echo "   1. Sign up at https://smith.langchain.com/"
    echo "   2. Create a new project"
    echo "   3. Get your API key"
    echo "   4. Add to .env or set environment variable"
fi

# Final instructions
echo ""
echo "🎉 Installation Complete!"
echo "======================="
echo ""
echo "Next steps:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Start LangGraph dev server: langgraph dev --port 3005"
echo "3. Run demo: python run_langgraph_demo.py"
echo "4. Open browser: http://localhost:3005"
echo ""
echo "📖 For more details, see LANGGRAPH_VISUALIZATION_GUIDE.md"
