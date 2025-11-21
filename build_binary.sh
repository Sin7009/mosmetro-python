#!/bin/bash
set -e

# Install dev dependencies (including pyinstaller)
uv sync

# Build the binary
uv run pyinstaller \
    --onefile \
    --name mosmetro \
    --hidden-import furl \
    --hidden-import pydantic \
    --hidden-import user_agent \
    --hidden-import tenacity \
    --hidden-import bs4 \
    mosmetro/__main__.py

echo "Build complete. Binary located at dist/mosmetro"
