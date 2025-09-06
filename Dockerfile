# Use Python 3.12 slim image as base
FROM python:3.12-slim as base

# Declare volume for database persistence
VOLUME ["/data"]

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_SETTINGS_MODULE=llteacher.production \
    DATABASE_PATH=/data/llteacher.sqlite

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster dependency management
RUN pip install uv

# Set work directory
WORKDIR /app

# Copy UV configuration files and README.md (required by pyproject.toml)
COPY pyproject.toml uv.lock README.md ./

# Copy workspace structure - apps and core components
COPY apps/ ./apps/
COPY core/ ./core/
COPY services/ ./services/
COPY src/ ./src/

# Install dependencies using uv (workspace-aware)
RUN uv sync --frozen

# Copy remaining project files
COPY manage.py run_tests.py docker-entrypoint.sh ./
COPY templates/ ./templates/
COPY static/ ./static/

# Make entrypoint script executable
RUN chmod +x docker-entrypoint.sh

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app && \
    mkdir -p /app/staticfiles /data && \
    chown -R app:app /app/staticfiles /data

USER app

# Collect static files
RUN uv run python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Set entrypoint and default command
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["uv", "run", "gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "llteacher.wsgi:application"]
