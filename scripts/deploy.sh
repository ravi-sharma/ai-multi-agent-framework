#!/bin/bash

# AI Agent Framework Deployment Script
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
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"

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
    log_info "Checking requirements..."
    
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
            log_warning "Please edit .env file with your configuration before running again."
            exit 1
        else
            log_error ".env.example file not found. Cannot create .env file."
            exit 1
        fi
    fi
    
    log_success "Requirements check passed"
}

validate_env() {
    log_info "Validating environment configuration..."
    
    # Source the .env file
    set -a
    source "$ENV_FILE"
    set +a
    
    # Check required environment variables
    required_vars=("OPENAI_API_KEY" "ANTHROPIC_API_KEY")
    missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ] || [ "${!var}" = "your_${var,,}_here" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        log_warning "The following environment variables need to be configured:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        log_warning "Please update your .env file with valid values."
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    log_success "Environment validation completed"
}

build_images() {
    log_info "Building Docker images..."
    
    cd "$PROJECT_DIR"
    
    if docker-compose build; then
        log_success "Docker images built successfully"
    else
        log_error "Failed to build Docker images"
        exit 1
    fi
}

deploy_services() {
    log_info "Deploying services..."
    
    cd "$PROJECT_DIR"
    
    # Create necessary directories
    mkdir -p logs data
    
    # Deploy with docker-compose
    if docker-compose up -d; then
        log_success "Services deployed successfully"
    else
        log_error "Failed to deploy services"
        exit 1
    fi
}

check_health() {
    log_info "Checking service health..."
    
    # Wait for services to start
    sleep 10
    
    # Check if the main service is healthy
    max_attempts=30
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:8000/health &> /dev/null; then
            log_success "Service is healthy and responding"
            return 0
        fi
        
        log_info "Attempt $attempt/$max_attempts: Service not ready yet, waiting..."
        sleep 5
        ((attempt++))
    done
    
    log_error "Service health check failed after $max_attempts attempts"
    log_info "Checking service logs..."
    docker-compose logs ai-agent-framework
    return 1
}

show_status() {
    log_info "Service status:"
    docker-compose ps
    
    echo
    log_info "Service endpoints:"
    echo "  - API: http://localhost:8000"
    echo "  - Health: http://localhost:8000/health"
    echo "  - Docs: http://localhost:8000/docs"
    echo "  - Monitoring: http://localhost:8000/api/monitoring/dashboard"
}

# Main deployment process
main() {
    log_info "Starting AI Agent Framework deployment..."
    
    check_requirements
    validate_env
    build_images
    deploy_services
    
    if check_health; then
        show_status
        log_success "Deployment completed successfully!"
        echo
        log_info "To view logs: docker-compose logs -f"
        log_info "To stop services: docker-compose down"
        log_info "To restart services: docker-compose restart"
    else
        log_error "Deployment completed but health check failed"
        exit 1
    fi
}

# Handle script arguments
case "${1:-}" in
    "build")
        check_requirements
        build_images
        ;;
    "deploy")
        check_requirements
        validate_env
        deploy_services
        check_health
        show_status
        ;;
    "health")
        check_health
        ;;
    "status")
        show_status
        ;;
    *)
        main
        ;;
esac