# Use a minimal and secure base image
FROM python:3.12-slim-bookworm AS builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Create app directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml README.md ./

# Install dependencies to a virtual environment
RUN uv venv .venv
RUN uv pip install .

# Copy source code
COPY mosmetro/ ./mosmetro/

# Build the application (optional, we can just run from source with uv or the venv)
# But since we are in a container, using the venv created by uv is good.
RUN uv pip install .

# --- Final Stage ---
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /app/.venv ./.venv

# Copy application code (although it's installed in venv as editable or package,
# if we installed it as a package, we might not need source, but typically safer to copy)
# Wait, `uv pip install .` installs the package.
# If it's just the code, we need it?
# If we installed it, the egg-link or whatever mechanism implies the code is there OR copied.
# Standard practice: copy venv.
# But wait, `uv pip install .` installs the current directory.
# If we change files, we need to rebuild? Yes.
# So in the final stage, if we just copy venv, does it contain the code?
# If it was a wheel build, yes. If editable, no.
# Let's assume we want a clean image.
# We should probably build a wheel in builder and install it in runtime?
# Or just copy venv. uv installs in venv site-packages if not editable.
# I did not use -e.

# Create a non-root user
RUN useradd --create-home appuser
USER appuser

# Entrypoint
ENTRYPOINT ["mosmetro"]
CMD ["login"]
