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

# Copy workspace root files for uv workspace resolution
COPY pyproject.toml uv.lock ./
COPY src/django-backend/pyproject.toml ./src/django-backend/pyproject.toml

# Install Python dependencies for this package only
RUN uv sync --package django-backend --frozen --no-editable --no-dev

# Copy backend project files
COPY src/django-backend/ ./src/django-backend/

WORKDIR /app/src/django-backend

# Collect static files
RUN uv run python manage.py collectstatic --noinput

# Copy and set entrypoint
COPY src/django-backend/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose port
EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uv", "run", "gunicorn", "-c", "gunicorn.conf.py", "project_showcase.wsgi:application"]
