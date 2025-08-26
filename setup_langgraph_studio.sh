#!/bin/bash

echo "🎨 Setting up LangGraph Studio for Visual Debugging"
echo "=================================================="

# Check Python and pip
echo ""
echo "🟢 Checking Python and pip..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.11+ from https://python.org/"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ Python: $PYTHON_VERSION"

# Check for Python 3.11+
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
    if [[ $(echo "$PYTHON_VERSION < 3.11" | bc -l) -eq 1 ]]; then
        echo "⚠️  Python 3.11+ required for LangGraph CLI. Current: $PYTHON_VERSION"
        echo "Please install Python 3.11+ from https://python.org/"
        exit 1
    fi
fi

# Install LangGraph CLI
echo ""
echo "🎨 Installing LangGraph CLI..."
$PYTHON_CMD -m pip install -U "langgraph-cli[inmem]"

if [ $? -eq 0 ]; then
    echo "✅ LangGraph CLI installed successfully"
else
    echo "❌ Failed to install LangGraph CLI"
    echo "Please try manually:"
    echo "$PYTHON_CMD -m pip install -U \"langgraph-cli[inmem]\""
    exit 1
fi

# Check if LangSmith API key is set
echo ""
echo "🔑 Checking LangSmith configuration..."
if [ -z "$LANGSMITH_API_KEY" ]; then
    echo "⚠️  LANGSMITH_API_KEY not set"
    echo ""
    echo "To enable tracing and visualization:"
    echo "1. Sign up at https://smith.langchain.com/"
    echo "2. Create a new project"
    echo "3. Get your API key"
    echo "4. Set environment variable:"
    echo "   export LANGSMITH_API_KEY='your-api-key-here'"
    echo ""
    echo "Or add to your .env file:"
    echo "   LANGSMITH_API_KEY=your-api-key-here"
else
    echo "✅ LANGSMITH_API_KEY is set"
fi

echo ""
echo "🚀 Setup Complete!"
echo "=================="
echo ""
echo "To run the demo and see LangGraph visualization:"
echo ""
echo "1. Start LangGraph development server:"
echo "   langgraph dev --port 3005"
echo ""
echo "2. In another terminal, run the demo:"
echo "   python run_langgraph_demo.py"
echo ""
echo "3. Open LangGraph Studio in your browser:"
echo "   http://localhost:3005"
echo ""
echo "4. Connect with your LangSmith API key and view workflows!"
echo ""

# Instructions for running
echo "🚀 Next Steps:"
echo "=============="
echo ""
echo "1. Start LangGraph dev server: langgraph dev --port 3005"
echo "2. Run the demo: python run_langgraph_demo.py"
echo "3. Open browser: http://localhost:3005"
echo "4. Connect with your LangSmith API key"
echo "5. Watch your workflows execute in real-time!"
echo ""
echo "📖 For detailed instructions, see: LANGGRAPH_VISUALIZATION_GUIDE.md"
