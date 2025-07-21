#!/bin/bash
set -e

# Claude Bridge Global Installer
# Installs Claude Bridge for use across multiple projects

echo "🌉 Claude Bridge Global Installer"
echo "=================================="

# Default installation directory
INSTALL_DIR="$HOME/.claude-bridge"
BIN_DIR="$HOME/bin"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --install-dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        --bin-dir)
            BIN_DIR="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --install-dir DIR   Installation directory (default: ~/.claude-bridge)"
            echo "  --bin-dir DIR       Binary directory (default: ~/bin)"
            echo "  --help             Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "📁 Installation directory: $INSTALL_DIR"
echo "🔧 Binary directory: $BIN_DIR"

# Check if git is available
if ! command -v git &> /dev/null; then
    echo "❌ Git is not installed. Please install git first."
    exit 1
fi

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "⚠️ Docker is not installed. Some features may not work."
    echo "   Continue anyway? (y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 0
    fi
fi

# Create directories
echo "📁 Creating directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"
mkdir -p "$INSTALL_DIR/config"
mkdir -p "$INSTALL_DIR/logs"

# Clone or update Claude Bridge
if [ -d "$INSTALL_DIR/claude-bridge" ]; then
    echo "🔄 Updating existing Claude Bridge installation..."
    cd "$INSTALL_DIR/claude-bridge"
    git pull origin main
else
    echo "📥 Cloning Claude Bridge..."
    cd "$INSTALL_DIR"
    git clone https://github.com/NewAITees/Claude-Bridge.git claude-bridge
fi

# Create global launcher script
echo "🚀 Creating global launcher script..."

cat > "$BIN_DIR/claude-bridge" << 'EOF'
#!/bin/bash

# Claude Bridge Global Launcher
# Runs Claude Bridge from any project directory

CLAUDE_BRIDGE_HOME="$HOME/.claude-bridge"
CLAUDE_BRIDGE_REPO="$CLAUDE_BRIDGE_HOME/claude-bridge"
WORK_DIR="$(pwd)"
PROJECT_NAME="$(basename "$WORK_DIR")"

# Check if Claude Bridge is installed
if [ ! -d "$CLAUDE_BRIDGE_REPO" ]; then
    echo "❌ Claude Bridge not found at $CLAUDE_BRIDGE_REPO"
    echo "Please run the global installer first."
    exit 1
fi

# Parse arguments
CONFIG_FILE=""
SHOW_HELP=false
RUN_TESTS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --config|-c)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --test|-t)
            RUN_TESTS=true
            shift
            ;;
        --help|-h)
            SHOW_HELP=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

if [ "$SHOW_HELP" = true ]; then
    echo "Claude Bridge Global Launcher"
    echo ""
    echo "Usage: claude-bridge [options]"
    echo ""
    echo "Options:"
    echo "  --config FILE    Use specific config file"
    echo "  --test          Run system tests"
    echo "  --help          Show this help message"
    echo ""
    echo "Current project: $PROJECT_NAME"
    echo "Working directory: $WORK_DIR"
    echo "Claude Bridge home: $CLAUDE_BRIDGE_HOME"
    exit 0
fi

# Default config file
if [ -z "$CONFIG_FILE" ]; then
    # Check for project-specific config first
    if [ -f ".claude-bridge/config.json" ]; then
        CONFIG_FILE=".claude-bridge/config.json"
        echo "📋 Using project config: $CONFIG_FILE"
    elif [ -f "$CLAUDE_BRIDGE_HOME/config/discord_config.json" ]; then
        CONFIG_FILE="$CLAUDE_BRIDGE_HOME/config/discord_config.json"
        echo "📋 Using global config: $CONFIG_FILE"
    else
        echo "❌ No configuration file found."
        echo "Please create either:"
        echo "  - .claude-bridge/config.json (project-specific)"
        echo "  - $CLAUDE_BRIDGE_HOME/config/discord_config.json (global)"
        echo ""
        echo "See DISCORD_SETUP.md for configuration instructions."
        exit 1
    fi
fi

echo "🌉 Claude Bridge - Project: $PROJECT_NAME"
echo "🔗 Working Directory: $WORK_DIR"
echo "⚙️ Config: $CONFIG_FILE"
echo ""

# Change to Claude Bridge directory
cd "$CLAUDE_BRIDGE_REPO"

# Create dynamic config if using global config
if [[ "$CONFIG_FILE" == "$CLAUDE_BRIDGE_HOME/config/discord_config.json" ]]; then
    DYNAMIC_CONFIG="$CLAUDE_BRIDGE_HOME/config/dynamic_${PROJECT_NAME}.json"
    
    # Check if jq is available
    if command -v jq &> /dev/null; then
        echo "🔧 Creating dynamic config for $PROJECT_NAME..."
        jq --arg work_dir "$WORK_DIR" \
           --arg project "$PROJECT_NAME" \
           '.claude_code.working_directory = $work_dir | 
            .logging.file = "logs/claude_bridge_" + $project + ".log"' \
           "$CONFIG_FILE" > "$DYNAMIC_CONFIG"
        CONFIG_FILE="$DYNAMIC_CONFIG"
    else
        echo "⚠️ jq not found. Using static config with current directory."
        # Create simple dynamic config without jq
        python3 -c "
import json
import sys
import os

try:
    with open('$CONFIG_FILE', 'r') as f:
        config = json.load(f)
    
    config['claude_code']['working_directory'] = '$WORK_DIR'
    config['logging']['file'] = 'logs/claude_bridge_${PROJECT_NAME}.log'
    
    with open('$DYNAMIC_CONFIG', 'w') as f:
        json.dump(config, f, indent=2)
    
    print('✅ Dynamic config created')
except Exception as e:
    print(f'❌ Failed to create dynamic config: {e}')
    sys.exit(1)
"
        CONFIG_FILE="$DYNAMIC_CONFIG"
    fi
fi

# Run tests if requested
if [ "$RUN_TESTS" = true ]; then
    echo "🧪 Running system tests..."
    python comprehensive_test.py
    if [ $? -ne 0 ]; then
        echo "❌ Tests failed. Aborting."
        exit 1
    fi
fi

# Run Claude Bridge
echo "🚀 Starting Claude Bridge..."
python -m claude_bridge.main --config "$CONFIG_FILE"
EOF

# Make launcher executable
chmod +x "$BIN_DIR/claude-bridge"

# Create config template if it doesn't exist
if [ ! -f "$INSTALL_DIR/config/discord_config.json" ]; then
    echo "📝 Creating config template..."
    cat > "$INSTALL_DIR/config/discord_config.json" << 'EOF'
{
  "discord": {
    "token": "YOUR_BOT_TOKEN_HERE",
    "guild_id": "YOUR_GUILD_ID_HERE",  
    "channel_id": "YOUR_CHANNEL_ID_HERE"
  },
  "claude_code": {
    "command": "claude-code",
    "working_directory": "/tmp",
    "timeout": 30
  },
  "session": {
    "timeout": 3600,
    "max_output_length": 1900,
    "max_history": 100,
    "cleanup_interval": 60
  },
  "logging": {
    "level": "INFO",
    "file": "logs/claude_bridge.log",
    "max_size": "10MB",
    "backup_count": 3
  }
}
EOF
fi

# Check if bin directory is in PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo ""
    echo "⚠️ $BIN_DIR is not in your PATH"
    echo "Add the following to your shell configuration file (~/.bashrc, ~/.zshrc, etc.):"
    echo ""
    echo "    export PATH=\"$BIN_DIR:\$PATH\""
    echo ""
    echo "Then restart your shell or run: source ~/.bashrc"
fi

echo ""
echo "✅ Installation completed!"
echo ""
echo "📋 Next steps:"
echo "1. Edit the config file: $INSTALL_DIR/config/discord_config.json"
echo "2. Set your Discord bot token, guild_id, and channel_id"
echo "3. Run 'claude-bridge' from any project directory"
echo ""
echo "📖 For detailed setup instructions, see:"
echo "   $INSTALL_DIR/claude-bridge/DISCORD_SETUP.md"
echo ""
echo "🚀 Quick test:"
echo "   cd /path/to/your/project"
echo "   claude-bridge --test"