#!/bin/bash

# AI Agent Framework Cleanup Script
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

cleanup_containers() {
    log_info "Stopping and removing containers..."
    
    cd "$PROJECT_DIR"
    
    # Stop and remove production containers
    if docker-compose down --remove-orphans; then
        log_success "Production containers stopped and removed"
    else
        log_warning "Failed to stop production containers (they may not be running)"
    fi
    
    # Stop and remove development containers
    if docker-compose -f docker-compose.dev.yml down --remove-orphans; then
        log_success "Development containers stopped and removed"
    else
        log_warning "Failed to stop development containers (they may not be running)"
    fi
}

cleanup_images() {
    log_info "Removing Docker images..."
    
    # Remove project-specific images
    local images=(
        "ai-agent-framework_ai-agent-framework"
        "ai-agent-framework_ai-agent-framework-dev"
    )
    
    for image in "${images[@]}"; do
        if docker image inspect "$image" &> /dev/null; then
            if docker rmi "$image"; then
                log_success "Removed image: $image"
            else
                log_warning "Failed to remove image: $image"
            fi
        else
            log_info "Image not found: $image"
        fi
    done
}

cleanup_volumes() {
    log_info "Removing Docker volumes..."
    
    cd "$PROJECT_DIR"
    
    # Remove named volumes
    if docker-compose down --volumes; then
        log_success "Named volumes removed"
    else
        log_warning "Failed to remove named volumes"
    fi
    
    # Remove development volumes
    if docker-compose -f docker-compose.dev.yml down --volumes; then
        log_success "Development volumes removed"
    else
        log_warning "Failed to remove development volumes"
    fi
}

cleanup_networks() {
    log_info "Removing Docker networks..."
    
    local networks=(
        "ai-agent-framework_ai-agent-network"
    )
    
    for network in "${networks[@]}"; do
        if docker network inspect "$network" &> /dev/null; then
            if docker network rm "$network"; then
                log_success "Removed network: $network"
            else
                log_warning "Failed to remove network: $network (may be in use)"
            fi
        else
            log_info "Network not found: $network"
        fi
    done
}

cleanup_logs() {
    log_info "Cleaning up log files..."
    
    if [ -d "$PROJECT_DIR/logs" ]; then
        if rm -rf "$PROJECT_DIR/logs"/*; then
            log_success "Log files cleaned up"
        else
            log_warning "Failed to clean up log files"
        fi
    else
        log_info "No logs directory found"
    fi
}

cleanup_data() {
    log_warning "This will remove all persistent data!"
    read -p "Are you sure you want to remove data directory? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Cleaning up data files..."
        
        if [ -d "$PROJECT_DIR/data" ]; then
            if rm -rf "$PROJECT_DIR/data"/*; then
                log_success "Data files cleaned up"
            else
                log_warning "Failed to clean up data files"
            fi
        else
            log_info "No data directory found"
        fi
    else
        log_info "Skipping data cleanup"
    fi
}

cleanup_cache() {
    log_info "Cleaning up Python cache files..."
    
    cd "$PROJECT_DIR"
    
    # Remove Python cache files
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type f -name "*.pyo" -delete 2>/dev/null || true
    
    # Remove pytest cache
    if [ -d ".pytest_cache" ]; then
        rm -rf .pytest_cache
    fi
    
    log_success "Python cache files cleaned up"
}

prune_docker() {
    log_info "Pruning unused Docker resources..."
    
    # Prune unused containers, networks, images, and build cache
    if docker system prune -f; then
        log_success "Docker system pruned"
    else
        log_warning "Failed to prune Docker system"
    fi
}

show_usage() {
    echo "AI Agent Framework Cleanup Script"
    echo
    echo "Usage: $0 [COMMAND]"
    echo
    echo "Commands:"
    echo "  containers  Stop and remove containers only"
    echo "  images      Remove Docker images only"
    echo "  volumes     Remove Docker volumes only"
    echo "  networks    Remove Docker networks only"
    echo "  logs        Clean up log files only"
    echo "  data        Clean up data files only (with confirmation)"
    echo "  cache       Clean up Python cache files only"
    echo "  prune       Prune unused Docker resources"
    echo "  all         Full cleanup (containers, images, volumes, networks, logs, cache)"
    echo "  help        Show this help message"
    echo
    echo "Examples:"
    echo "  $0 containers  # Stop and remove containers"
    echo "  $0 all         # Full cleanup"
    echo "  $0 logs        # Clean up logs only"
}

# Main script logic
case "${1:-all}" in
    "containers")
        cleanup_containers
        ;;
    "images")
        cleanup_images
        ;;
    "volumes")
        cleanup_volumes
        ;;
    "networks")
        cleanup_networks
        ;;
    "logs")
        cleanup_logs
        ;;
    "data")
        cleanup_data
        ;;
    "cache")
        cleanup_cache
        ;;
    "prune")
        prune_docker
        ;;
    "all")
        log_warning "This will perform a full cleanup of the AI Agent Framework Docker environment."
        read -p "Are you sure you want to continue? (y/N): " -n 1 -r
        echo
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cleanup_containers
            cleanup_images
            cleanup_volumes
            cleanup_networks
            cleanup_logs
            cleanup_cache
            prune_docker
            log_success "Full cleanup completed"
        else
            log_info "Cleanup cancelled"
        fi
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