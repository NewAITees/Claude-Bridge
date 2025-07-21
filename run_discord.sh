#!/bin/bash
set -e

echo "🚀 Claude Bridge Discord Launcher"
echo "=================================="

# Check if config file exists
if [ ! -f "config/discord_config.json" ]; then
    echo "❌ Configuration file not found: config/discord_config.json"
    echo "📖 Please follow DISCORD_SETUP.md to create the configuration file."
    echo ""
    echo "Quick setup:"
    echo "1. Create config/discord_config.json"
    echo "2. Add your Discord bot token, guild_id, and channel_id"
    echo "3. Run this script again"
    exit 1
fi

echo "✅ Configuration file found"

# Check if we're in the project directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Please run this script from the Claude Bridge project root directory"
    exit 1
fi

# Function to run in container
run_in_container() {
    echo "🐳 Starting Claude Bridge in Docker container..."
    docker run -it --rm \
        -v "$(pwd)":/workspace \
        -w /workspace \
        modern-python-base:latest \
        bash -c "
            echo '🔧 Setting up environment...' && \
            uv sync --dev && \
            source .venv/bin/activate && \
            echo '🧪 Running system tests...' && \
            python comprehensive_test.py && \
            echo '🚀 Starting Claude Bridge...' && \
            python -m claude_bridge.main --config config/discord_config.json
        "
}

# Function to run locally
run_locally() {
    echo "🐍 Starting Claude Bridge locally..."
    
    # Check if virtual environment exists
    if [ ! -d ".venv" ]; then
        echo "🔧 Creating virtual environment..."
        uv sync --dev
    fi
    
    echo "🔧 Activating virtual environment..."
    source .venv/bin/activate
    
    echo "🧪 Running system tests..."
    python comprehensive_test.py
    
    if [ $? -eq 0 ]; then
        echo "✅ Tests passed. Starting Claude Bridge..."
        python -m claude_bridge.main --config config/discord_config.json
    else
        echo "❌ Tests failed. Please check your setup."
        exit 1
    fi
}

# Parse command line arguments
USE_CONTAINER=true
for arg in "$@"; do
    case $arg in
        --local)
            USE_CONTAINER=false
            shift
            ;;
        --container)
            USE_CONTAINER=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--local|--container]"
            echo ""
            echo "Options:"
            echo "  --local      Run locally (requires Python 3.12+ and dependencies)"
            echo "  --container  Run in Docker container (default)"
            echo "  --help       Show this help message"
            exit 0
            ;;
    esac
done

# Check Docker availability if using container
if [ "$USE_CONTAINER" = true ]; then
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker not found. Please install Docker or use --local flag"
        exit 1
    fi
    
    if ! docker images | grep -q "modern-python-base"; then
        echo "❌ modern-python-base image not found"
        echo "🔧 Please build the image or use --local flag"
        exit 1
    fi
fi

# Show configuration info
echo ""
echo "📋 Configuration:"
echo "  - Config file: config/discord_config.json"
echo "  - Execution mode: $([ "$USE_CONTAINER" = true ] && echo "Docker container" || echo "Local")"
echo ""

# Run the application
if [ "$USE_CONTAINER" = true ]; then
    run_in_container
else
    run_locally
fi