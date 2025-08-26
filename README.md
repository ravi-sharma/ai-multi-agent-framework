# AI Agent Framework

A production-ready, intelligent agent framework for building scalable AI-driven automation systems with advanced routing, monitoring, and LangGraph orchestration.

## 🎯 Overview

The AI Agent Framework is a modular Python library that enables organizations to build sophisticated AI agents capable of processing emails, webhooks, and other data sources. It features multi-provider LLM support, intelligent routing, state management, and comprehensive tooling with visual debugging through LangGraph Studio.

## 🏗️ Architecture

```
├── agents/               # Agent implementations (roles, tools, prompts)
├── graphs/               # LangGraph orchestration workflows
├── prompts/              # Separated prompt templates (YAML + Python)
├── tools/                # Custom tools for agents
├── memory/               # Persistent memory and state management
├── services/             # Integration layers (API, CLI, UI)
├── configs/              # Environment-specific configurations
├── utils/                # Helper utilities (logging, validation)
├── models/               # Data models and structures
└── main.py               # Main entry point
```

### Application Flow with LangGraph Orchestration

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Sources  │───▶│  LangGraph       │───▶│   Agents        │
│  • Email        │    │  Orchestrator    │    │  • Sales        │
│  • Webhooks     │    │  • Route Request │    │  • Support      │
│  • API Calls    │    │  • Process       │    │  • Custom       │
└─────────────────┘    │  • Validate      │    └─────────────────┘
                       │  • Finalize      │             │
┌─────────────────┐    └──────────────────┘             │
│   Monitoring    │◀───────────────────────────────────┘
│  • LangSmith    │    ┌──────────────────┐
│  • Metrics      │    │   Responses      │
│  • Logging      │    │  • Email Reply   │
└─────────────────┘    │  • API Response  │
                       │  • Webhook       │
                       └──────────────────┘
```

## ⚡ Quick Start

### Prerequisites

- Python 3.11+ (required for LangGraph CLI)
- API keys for LLM providers
- LangSmith API key (optional, for tracing)

### Setup

```bash
# Clone and setup
git clone https://github.com/ravi-sharma/ai-agent-framework.git
cd ai-agent-framework

# Install all dependencies (Python + LangGraph CLI)
./install_dependencies.sh

# Configure environment
cp env.example .env
# Edit .env and add your API keys
```

### Run the Demo

```bash
# Start LangGraph development server
langgraph dev --port 3005

# In another terminal, run the demo
python run_langgraph_demo.py

# Open LangGraph Studio in browser
# https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:3005
```

## 🎨 LangGraph Visualization & Debugging

### Browser-Based LangGraph Studio

The framework includes comprehensive visualization and debugging capabilities:

**1. Start the Development Server**
```bash
# Activate virtual environment
source venv/bin/activate

# Start LangGraph dev server
langgraph dev --port 3005
```

**2. Access LangGraph Studio**
- **Studio UI**: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:3005
- **API Docs**: http://localhost:3005/docs
- **Local API**: http://127.0.0.1:3005

**3. Run Workflows**
```bash
# Run automated demo scenarios
echo "1" | python run_langgraph_demo.py

# Or run interactively
python run_langgraph_demo.py
```

### LangSmith Integration

**Setup LangSmith Tracing:**
```bash
# Add to your .env file
LANGSMITH_API_KEY=your-api-key-here
LANGSMITH_PROJECT=ai-agent-framework-demo
LANGCHAIN_TRACING_V2=true
```

**View Traces:**
- Dashboard: https://smith.langchain.com/
- Project traces show complete workflow execution
- Step-by-step debugging with input/output inspection
- Performance metrics and error tracking

### Multi-Agent Workflow

The framework implements a sophisticated multi-agent workflow:

```
┌─────────────────┐
│  route_request  │ ──┐
└─────────────────┘   │
                      ▼
┌─────────────────────────────┐
│  process_with_agent         │
│  • Sales Agent             │
│  • Support Agent           │
│  • Default Agent           │
└─────────────────────────────┘
                      │
                      ▼
┌─────────────────┐   │
│ validate_result │ ◀─┘
└─────────────────┘
                      │
                      ▼
┌─────────────────┐
│finalize_response│
└─────────────────┘
```

### Demo Scenarios

The included demo runs three scenarios:

1. **Sales Inquiry** → Routes to SalesAgent
   - Input: "Interested in pricing for enterprise plan"
   - Shows intelligent routing based on keywords

2. **General Support** → Routes to DefaultAgent
   - Input: "How to reset my password"
   - Demonstrates fallback handling

3. **Product Demo** → Intelligent routing
   - Input: Complex form data with company info
   - Shows advanced routing logic

## 🛠️ CLI Usage

```bash
# List available agents
python main.py cli list-agents

# Process email
python main.py cli process-email --email-file sample.eml

# Process webhook
python main.py cli process-webhook --data '{"type": "support", "message": "Help needed"}'

# Start API server
python main.py api --host 0.0.0.0 --port 8000

# Run with specific config
python main.py --config configs/prod_config.py api
```

## 🔧 Configuration

### Environment Variables

```bash
# LLM Providers
OPENAI_API_KEY=sk-your-key-here
ANTHROPIC_API_KEY=your-key-here

# LangSmith (Optional)
LANGSMITH_API_KEY=your-key-here
LANGSMITH_PROJECT=ai-agent-framework
LANGCHAIN_TRACING_V2=true

# Framework Settings
LOG_LEVEL=INFO
ENVIRONMENT=development
```

### Agent Configuration

```python
# configs/custom_config.py
from configs.base_config import BaseConfig

class CustomConfig(BaseConfig):
    def __init__(self):
        super().__init__()
        self.agents = {
            "sales_agent": {
                "enabled": True,
                "llm_provider": "openai",
                "model": "gpt-4",
                "temperature": 0.7
            },
            "support_agent": {
                "enabled": True,
                "llm_provider": "anthropic",
                "model": "claude-3-sonnet"
            }
        }
```

## 🎯 Key Features

### Multi-Agent System
- **Intelligent Routing**: Automatic agent selection based on content analysis
- **Specialized Agents**: Sales, support, and custom agents with specific capabilities
- **Fallback Handling**: Graceful degradation to default agent when routing fails

### LangGraph Orchestration
- **Visual Workflows**: See your agent workflows in LangGraph Studio
- **State Management**: Persistent state across workflow steps
- **Error Handling**: Comprehensive error tracking and recovery
- **Real-time Debugging**: Step-through execution with full context

### Monitoring & Observability
- **LangSmith Integration**: Complete trace visibility and debugging
- **Performance Metrics**: Execution time, success rates, error tracking
- **Structured Logging**: Comprehensive logging with context
- **Health Checks**: Built-in monitoring endpoints

### Production Ready
- **Scalable Architecture**: Modular design for easy scaling
- **Configuration Management**: Environment-specific configurations
- **Error Resilience**: Comprehensive error handling and recovery
- **Testing Suite**: Unit, integration, and performance tests

## 📊 Monitoring & Debugging

### LangSmith Dashboard
- **Trace Analysis**: Complete workflow execution traces
- **Performance Monitoring**: Execution times and bottlenecks
- **Error Tracking**: Failed runs with detailed error context
- **Agent Analytics**: Success rates by agent type

### LangGraph Studio Features
- **Visual Debugging**: Interactive workflow visualization
- **Real-time Execution**: Watch workflows execute live
- **State Inspection**: Examine workflow state at each step
- **Interactive Testing**: Submit custom inputs and see results

### Local Development
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with tracing
export LANGCHAIN_TRACING_V2=true
python run_langgraph_demo.py

# Check server health
curl http://localhost:3005/ok
```

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific test categories
python -m pytest tests/test_agents.py
python -m pytest tests/integration/
python -m pytest tests/performance/

# Run with coverage
python -m pytest --cov=. tests/

# Load testing
python tests/performance/test_load_stress.py
```

## 🚀 Deployment

### Docker Deployment
```bash
# Build image
docker build -t ai-agent-framework .

# Run container
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=your-key \
  -e LANGSMITH_API_KEY=your-key \
  ai-agent-framework
```

### Production Configuration
```python
# configs/prod_config.py
class ProductionConfig(BaseConfig):
    def __init__(self):
        super().__init__()
        self.log_level = "INFO"
        self.enable_metrics = True
        self.rate_limiting = True
        self.max_concurrent_requests = 100
```

## 🔐 Security

- **API Key Management**: Secure handling of LLM provider keys
- **Input Validation**: Comprehensive input sanitization
- **Rate Limiting**: Built-in request rate limiting
- **Audit Logging**: Complete audit trail of all operations

## 📈 Performance

- **Async Processing**: Non-blocking request handling
- **Connection Pooling**: Efficient LLM provider connections
- **Caching**: Intelligent response caching
- **Load Balancing**: Multi-instance deployment support

## 🔧 Development

### Adding Custom Agents
```python
# agents/custom_agent.py
from agents.base_agent import BaseAgent

class CustomAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.name = "custom_agent"
    
    async def process(self, input_data):
        # Your custom logic here
        return AgentResult(
            success=True,
            output={"response": "Custom response"},
            agent_name=self.name
        )
```

### Custom Routing Logic
```python
# Modify graphs/multiagent_graph.py
def _select_agent(self, input_data):
    if "urgent" in str(input_data).lower():
        return "priority_agent"
    elif "technical" in str(input_data).lower():
        return "technical_agent"
    else:
        return "default_agent"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support & Troubleshooting

### Common Issues

**LangGraph Studio won't connect:**
- Ensure the dev server is running: `langgraph dev --port 3005`
- Check the correct URL: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:3005
- Verify Python 3.11+ is being used

**No traces in LangSmith:**
- Verify `LANGSMITH_API_KEY` is set
- Check `LANGCHAIN_TRACING_V2=true`
- Ensure project name matches in LangSmith dashboard

**Module import errors:**
- Activate virtual environment: `source venv/bin/activate`
- Reinstall dependencies: `pip install -r requirements.txt`

### Debug Commands
```bash
# Test LangSmith connection
python -c "from langsmith import Client; print('Connected:', bool(Client().list_runs(limit=1)))"

# Validate environment
python -c "import os; print('Keys set:', bool(os.getenv('LANGSMITH_API_KEY')))"

# Test workflow without tracing
LANGCHAIN_TRACING_V2=false python run_langgraph_demo.py
```

### Getting Help

- **Documentation**: This README covers all major features
- **Issues**: Report bugs via GitHub Issues
- **Discussions**: Join community discussions for questions
- **Examples**: Check the `examples/` directory for usage patterns

---

**Built with ❤️ using LangGraph, LangSmith, and modern Python practices.**