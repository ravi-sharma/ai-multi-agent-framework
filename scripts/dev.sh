#!/bin/bash

# AI Agent Framework Development Script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/.env"
DEV_COMPOSE_FILE="$PROJECT_DIR/docker-compose.dev.yml"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    log_info "Checking development requirements..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if .env file exists
    if [ ! -f "$ENV_FILE" ]; then
        log_warning ".env file not found. Creating from .env.example..."
        if [ -f "$PROJECT_DIR/.env.example" ]; then
            cp "$PROJECT_DIR/.env.example" "$ENV_FILE"
            log_info "Created .env file from .env.example"
            log_warning "Please edit .env file with your configuration if needed."
        else
            log_error ".env.example file not found. Cannot create .env file."
            exit 1
        fi
    fi
    
    log_success "Development requirements check passed"
}

start_dev() {
    log_info "Starting development environment..."
    
    cd "$PROJECT_DIR"
    
    # Create necessary directories
    mkdir -p logs data
    
    # Start development services
    if docker-compose -f "$DEV_COMPOSE_FILE" up -d; then
        log_success "Development environment started"
        
        # Wait a moment for services to initialize
        sleep 5
        
        log_info "Development server is starting..."
        log_info "API will be available at: http://localhost:8000"
        log_info "API docs will be available at: http://localhost:8000/docs"
        
        # Show logs
        log_info "Showing logs (Ctrl+C to stop following logs):"
        docker-compose -f "$DEV_COMPOSE_FILE" logs -f
    else
        log_error "Failed to start development environment"
        exit 1
    fi
}

stop_dev() {
    log_info "Stopping development environment..."
    
    cd "$PROJECT_DIR"
    
    if docker-compose -f "$DEV_COMPOSE_FILE" down; then
        log_success "Development environment stopped"
    else
        log_error "Failed to stop development environment"
        exit 1
    fi
}

restart_dev() {
    log_info "Restarting development environment..."
    stop_dev
    start_dev
}

build_dev() {
    log_info "Building development Docker image..."
    
    cd "$PROJECT_DIR"
    
    if docker-compose -f "$DEV_COMPOSE_FILE" build; then
        log_success "Development Docker image built successfully"
    else
        log_error "Failed to build development Docker image"
        exit 1
    fi
}

show_logs() {
    log_info "Showing development logs..."
    cd "$PROJECT_DIR"
    docker-compose -f "$DEV_COMPOSE_FILE" logs -f
}

show_status() {
    log_info "Development environment status:"
    cd "$PROJECT_DIR"
    docker-compose -f "$DEV_COMPOSE_FILE" ps
}

run_tests() {
    log_info "Running tests in development environment..."
    cd "$PROJECT_DIR"
    
    # Run tests inside the development container
    if docker-compose -f "$DEV_COMPOSE_FILE" exec ai-agent-framework-dev python -m pytest tests/ -v; then
        log_success "Tests completed successfully"
    else
        log_error "Tests failed"
        exit 1
    fi
}

shell() {
    log_info "Opening shell in development container..."
    cd "$PROJECT_DIR"
    docker-compose -f "$DEV_COMPOSE_FILE" exec ai-agent-framework-dev /bin/bash
}

# Show usage information
show_usage() {
    echo "AI Agent Framework Development Script"
    echo
    echo "Usage: $0 [COMMAND]"
    echo
    echo "Commands:"
    echo "  start     Start development environment with hot reloading"
    echo "  stop      Stop development environment"
    echo "  restart   Restart development environment"
    echo "  build     Build development Docker image"
    echo "  logs      Show and follow logs"
    echo "  status    Show service status"
    echo "  test      Run tests in development environment"
    echo "  shell     Open shell in development container"
    echo "  help      Show this help message"
    echo
    echo "Examples:"
    echo "  $0 start    # Start development environment"
    echo "  $0 logs     # View logs"
    echo "  $0 test     # Run tests"
    echo "  $0 shell    # Open development shell"
}

# Main script logic
case "${1:-start}" in
    "start")
        check_requirements
        start_dev
        ;;
    "stop")
        stop_dev
        ;;
    "restart")
        check_requirements
        restart_dev
        ;;
    "build")
        check_requirements
        build_dev
        ;;
    "logs")
        show_logs
        ;;
    "status")
        show_status
        ;;
    "test")
        run_tests
        ;;
    "shell")
        shell
        ;;
    "help"|"-h"|"--help")
        show_usage
        ;;
    *)
        log_error "Unknown command: $1"
        echo
        show_usage
        exit 1
        ;;
esac