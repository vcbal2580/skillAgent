#!/usr/bin/env bash
# SkillAgent - macOS/Linux one-time setup script
# Usage: bash scripts/setup.sh
# Run this once after cloning the repository.

set -e

echo ""
echo "=== SkillAgent Setup ==="

# 1. Create virtual environment
if [ ! -d ".venv" ]; then
    echo ""
    echo "[1/4] Creating virtual environment..."
    python3 -m venv .venv
else
    echo ""
    echo "[1/4] Virtual environment already exists, skipping."
fi

# 2. Activate
echo ""
echo "[2/4] Activating virtual environment..."
source .venv/bin/activate

# 3. Install dependencies
echo ""
echo "[3/4] Installing dependencies..."
pip install -r requirements.txt

# 4. Install project in editable mode (generates 'hi' command)
echo ""
echo "[4/4] Installing project (generates 'hi' command)..."
pip install -e .

# 5. Config file
if [ ! -f "config.yaml" ]; then
    echo ""
    echo "[+] Copying config template..."
    cp config.example.yaml config.yaml
    echo "    --> Please edit config.yaml and fill in your API key."
else
    echo ""
    echo "[+] config.yaml already exists, skipping."
fi

echo ""
echo "=== Setup complete! ==="
echo "Next steps:"
echo "  1. Edit config.yaml and set your API key"
echo "  2. Activate venv: source .venv/bin/activate"
echo "  3. Run: hi vcbal"
