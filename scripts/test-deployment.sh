#!/bin/bash

# AI Agent Framework Docker Deployment Test Script
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
TEST_ENV_FILE="$PROJECT_DIR/.env.test"

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

create_test_env() {
    log_info "Creating test environment file..."
    
    cat > "$TEST_ENV_FILE" << EOF
# Test environment variables for AI Agent Framework

# LLM Provider API Keys (using dummy values for testing)
OPENAI_API_KEY=test_openai_key_12345
ANTHROPIC_API_KEY=test_anthropic_key_12345

# Email Configuration (disabled for testing)
EMAIL_HOST=
EMAIL_PORT=
EMAIL_USERNAME=
EMAIL_PASSWORD=

# Framework Configuration
LOG_LEVEL=INFO
ENABLE_MONITORING=true
CONFIG_FILE=config/example_config.yaml

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=1

# Development Settings
DEBUG=false
TESTING=true
EOF
    
    log_success "Test environment file created"
}

test_docker_build() {
    log_info "Testing Docker image build..."
    
    cd "$PROJECT_DIR"
    
    if docker build -t ai-agent-framework-test .; then
        log_success "Docker image built successfully"
        return 0
    else
        log_error "Docker image build failed"
        return 1
    fi
}

test_container_start() {
    log_info "Testing container startup..."
    
    cd "$PROJECT_DIR"
    
    # Copy test env file
    cp "$TEST_ENV_FILE" .env
    
    # Start container in detached mode
    if docker-compose up -d; then
        log_success "Container started successfully"
        
        # Wait for container to be ready
        log_info "Waiting for container to be ready..."
        sleep 15
        
        return 0
    else
        log_error "Container startup failed"
        return 1
    fi
}

test_health_endpoint() {
    log_info "Testing health endpoint..."
    
    local max_attempts=10
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s http://localhost:8000/health > /dev/null; then
            log_success "Health endpoint is responding"
            return 0
        fi
        
        log_info "Attempt $attempt/$max_attempts: Health endpoint not ready, waiting..."
        sleep 5
        ((attempt++))
    done
    
    log_error "Health endpoint test failed"
    return 1
}

test_api_endpoints() {
    log_info "Testing API endpoints..."
    
    local endpoints=(
        "/"
        "/health"
        "/docs"
        "/api/monitoring/health"
        "/api/monitoring/status"
    )
    
    local failed_endpoints=()
    
    for endpoint in "${endpoints[@]}"; do
        if curl -f -s "http://localhost:8000$endpoint" > /dev/null; then
            log_success "Endpoint $endpoint is responding"
        else
            log_warning "Endpoint $endpoint is not responding"
            failed_endpoints+=("$endpoint")
        fi
    done
    
    if [ ${#failed_endpoints[@]} -eq 0 ]; then
        log_success "All API endpoints are responding"
        return 0
    else
        log_warning "Some endpoints failed: ${failed_endpoints[*]}"
        return 1
    fi
}

test_container_logs() {
    log_info "Checking container logs for errors..."
    
    cd "$PROJECT_DIR"
    
    # Get logs from the last 2 minutes
    local logs=$(docker-compose logs --since=2m ai-agent-framework 2>&1)
    
    # Check for critical errors
    if echo "$logs" | grep -i "error\|exception\|failed\|traceback" | grep -v "test\|warning" > /dev/null; then
        log_warning "Found potential errors in logs:"
        echo "$logs" | grep -i "error\|exception\|failed\|traceback" | grep -v "test\|warning" | head -5
        return 1
    else
        log_success "No critical errors found in logs"
        return 0
    fi
}

cleanup_test() {
    log_info "Cleaning up test environment..."
    
    cd "$PROJECT_DIR"
    
    # Stop and remove containers
    docker-compose down --remove-orphans > /dev/null 2>&1 || true
    
    # Remove test image
    docker rmi ai-agent-framework-test > /dev/null 2>&1 || true
    
    # Remove test env file
    rm -f "$TEST_ENV_FILE" .env
    
    log_success "Test cleanup completed"
}

run_full_test() {
    log_info "Starting Docker deployment test..."
    
    local test_results=()
    
    # Create test environment
    create_test_env
    
    # Test Docker build
    if test_docker_build; then
        test_results+=("build:PASS")
    else
        test_results+=("build:FAIL")
    fi
    
    # Test container startup
    if test_container_start; then
        test_results+=("startup:PASS")
        
        # Test health endpoint
        if test_health_endpoint; then
            test_results+=("health:PASS")
        else
            test_results+=("health:FAIL")
        fi
        
        # Test API endpoints
        if test_api_endpoints; then
            test_results+=("api:PASS")
        else
            test_results+=("api:PARTIAL")
        fi
        
        # Test container logs
        if test_container_logs; then
            test_results+=("logs:PASS")
        else
            test_results+=("logs:WARNING")
        fi
        
    else
        test_results+=("startup:FAIL")
    fi
    
    # Cleanup
    cleanup_test
    
    # Report results
    echo
    log_info "Test Results Summary:"
    for result in "${test_results[@]}"; do
        local test_name=$(echo "$result" | cut -d: -f1)
        local test_status=$(echo "$result" | cut -d: -f2)
        
        case "$test_status" in
            "PASS")
                log_success "$test_name: $test_status"
                ;;
            "PARTIAL"|"WARNING")
                log_warning "$test_name: $test_status"
                ;;
            "FAIL")
                log_error "$test_name: $test_status"
                ;;
        esac
    done
    
    # Determine overall result
    if echo "${test_results[*]}" | grep -q "FAIL"; then
        echo
        log_error "Docker deployment test FAILED"
        return 1
    elif echo "${test_results[*]}" | grep -q "WARNING\|PARTIAL"; then
        echo
        log_warning "Docker deployment test completed with WARNINGS"
        return 0
    else
        echo
        log_success "Docker deployment test PASSED"
        return 0
    fi
}

# Show usage information
show_usage() {
    echo "AI Agent Framework Docker Deployment Test Script"
    echo
    echo "Usage: $0 [COMMAND]"
    echo
    echo "Commands:"
    echo "  build     Test Docker image build only"
    echo "  start     Test container startup only"
    echo "  health    Test health endpoint only"
    echo "  api       Test API endpoints only"
    echo "  logs      Test container logs only"
    echo "  cleanup   Cleanup test environment"
    echo "  full      Run full deployment test (default)"
    echo "  help      Show this help message"
}

# Main script logic
case "${1:-full}" in
    "build")
        create_test_env
        test_docker_build
        cleanup_test
        ;;
    "start")
        create_test_env
        test_container_start
        cleanup_test
        ;;
    "health")
        test_health_endpoint
        ;;
    "api")
        test_api_endpoints
        ;;
    "logs")
        test_container_logs
        ;;
    "cleanup")
        cleanup_test
        ;;
    "full")
        run_full_test
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