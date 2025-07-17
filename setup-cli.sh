#!/bin/bash
set -e

echo "🚀 Installing CLI tools for Claude Bridge..."

# Set up npm configuration for user-local installation
echo "📦 Setting up npm configuration..."
mkdir -p ~/.npm-global
npm config set prefix '~/.npm-global'
export PATH="~/.npm-global/bin:$PATH"

# Install Claude Code CLI (if not already available)
if ! command -v claude &> /dev/null; then
    echo "🤖 Installing Claude Code CLI..."
    npm install -g @anthropic-ai/claude-code@latest
else
    echo "🤖 Claude Code CLI is already installed"
fi

# Install Gemini CLI (if not already available)
if ! command -v gemini &> /dev/null; then
    echo "💎 Installing Gemini CLI..."
    npm install -g @google/gemini-cli@latest
else
    echo "💎 Gemini CLI is already installed"
fi

# Initialize Python project if pyproject.toml doesn't exist
if [ ! -f "pyproject.toml" ]; then
    echo "🐍 Initializing Python project..."
    uv init --name claude-bridge --python 3.12
fi

# Install Python dependencies for Claude Bridge
echo "📦 Installing Python dependencies..."
uv add discord.py pexpect asyncio-mqtt python-dotenv

# Install development dependencies
echo "🛠️ Installing development dependencies..."
uv add --dev pytest pytest-cov pytest-mock pytest-asyncio
uv add --dev ruff black mypy vulture safety bandit
uv add --dev pre-commit

# Install additional Python tools (if not already installed)
echo "🔧 Installing additional Python tools..."
if ! command -v pre-commit &> /dev/null; then
    pip install --user pre-commit
fi

echo "✅ CLI tools setup complete!"
echo ""
echo "Available tools:"
echo "  - python $(python --version)"
echo "  - uv $(uv --version)"
echo "  - node $(node --version)"
echo "  - npm $(npm --version)"
if command -v claude &> /dev/null; then
    echo "  - claude (Claude Code CLI)"
fi
if command -v gemini &> /dev/null; then
    echo "  - gemini (Gemini CLI)"
fi
echo ""
echo "📋 Add to your shell profile:"
echo "export PATH=\"~/.npm-global/bin:\$PATH\""
echo ""
echo "🚀 To start development:"
echo "  1. docker compose up -d"
echo "  2. docker compose exec dev bash"
echo "  3. Run tests: pytest"
echo "  4. Run linter: ruff check ."
echo "  5. Format code: ruff format ."