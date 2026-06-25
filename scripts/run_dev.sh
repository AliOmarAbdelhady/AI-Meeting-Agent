#!/usr/bin/env bash
# ── AI Meeting Agent — Development Setup Script ──────────────────────────────
set -euo pipefail

echo "🤖 AI Meeting Agent — Development Setup"
echo "========================================"

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# 1. Create virtual environment
if [ ! -d ".venv" ]; then
    echo ""
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Install dependencies
echo ""
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -e ".[dev]"

# 4. Create data directories
echo ""
echo "📁 Creating data directories..."
mkdir -p data/audio credentials

# 5. Copy .env if not present
if [ ! -f .env ]; then
    echo ""
    echo "⚙️  Creating .env from .env.example..."
    cp .env.example .env
    echo "   ⚠️  Edit .env with your API keys before running!"
fi

# 6. Install Playwright browsers (optional)
echo ""
read -p "🌐 Install Playwright Chromium for meeting bot? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    playwright install chromium
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your API keys"
echo "  2. Run: source .venv/bin/activate"
echo "  3. Run: make run"
echo "  4. Open: http://localhost:8000/docs"
echo ""
