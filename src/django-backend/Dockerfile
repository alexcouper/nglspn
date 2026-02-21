# Use Python 3.12 slim image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Set work directory
WORKDIR /app

# Copy dependency files (uv.lock from workspace root)
COPY pyproject.toml uv.lock ./

# Install Python dependencies for this package only
RUN uv sync --package django-backend --frozen --no-editable --no-dev

# Copy project files
COPY . .

# Collect static files
RUN uv run python manage.py collectstatic --noinput

# Copy and set entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose port
EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uv", "run", "gunicorn", "-c", "gunicorn.conf.py", "project_showcase.wsgi:application"]