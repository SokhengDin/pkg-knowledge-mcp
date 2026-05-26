FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Copy dependency manifests 
COPY pyproject.toml ./
COPY fastmcp.json ./

# Install dependencies 

# Copy source
COPY src/ ./src/
COPY skills/ ./skills/
COPY main.py ./

# Install the project itself
RUN uv sync --no-dev

# Create non-root user
RUN adduser --disabled-password --gecos "" mcpuser && chown -R mcpuser /app
USER mcpuser

# SSE transport — listen on 0.0.0.0:8000
ENV HOST=0.0.0.0
ENV PORT=8000

EXPOSE 8000

CMD ["uv", "run", "fastmcp", "run", "main.py", "--transport", "sse", "--host", "0.0.0.0", "--port", "8000"]
