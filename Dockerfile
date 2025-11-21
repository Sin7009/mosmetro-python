FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

COPY . .

# Set entrypoint
ENTRYPOINT ["uv", "run", "python", "-m", "mosmetro"]
