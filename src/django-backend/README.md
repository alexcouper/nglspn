# Project Showcase Django Backend

A Django backend implementation using Django Ninja that provides the same functionality as the FastAPI backend for the developer project showcasing platform.

## Features

This Django backend provides identical API endpoints to the FastAPI version:

- **Authentication**: User registration, login, JWT tokens, profile management
- **Projects**: CRUD operations, filtering, search, featured/trending projects
- **Tags**: Tag management for categorizing projects
- **Admin**: Project approval workflow, user management, analytics
- **My Projects**: Personal project management for authenticated users

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL database
- `uv` package manager

### Installation

1. Clone the repository and navigate to the django-backend directory:
```bash
cd django-backend
```

2. Copy the environment file and configure it:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

3. Install dependencies:
```bash
uv sync
```

4. Run migrations:
```bash
uv run python manage.py migrate
```

5. Create a superuser (optional):
```bash
uv run python manage.py createsuperuser
```

6. Run the development server:
```bash
uv run python manage.py runserver
```

The API will be available at `http://localhost:8000/`

## API Documentation

Django Ninja automatically generates OpenAPI documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Environment Variables

Create a `.env` file based on `.env.example`:

```bash
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=project_showcase
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

# JWT
JWT_SECRET_KEY=your-jwt-secret-key-here
```

## Project Structure

```
django-backend/
├── apps/
│   ├── users/          # User model and management
│   ├── projects/       # Project models and logic
│   └── tags/           # Tag models
├── api/
│   ├── auth/           # JWT authentication utilities
│   ├── routers/        # API endpoint definitions
│   └── schemas/        # Pydantic-style schemas for Django Ninja
├── project_showcase/   # Django project settings
└── manage.py
```

## API Endpoints

The Django backend provides identical endpoints to the FastAPI version:

### Authentication
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `GET /auth/me` - Get current user info
- `PUT /auth/me` - Update current user

### Projects
- `GET /projects` - List approved projects (with filtering)
- `GET /projects/featured` - Get featured projects
- `GET /projects/trending` - Get trending projects
- `GET /projects/{id}` - Get specific project

### My Projects (Authenticated)
- `GET /my/projects` - List user's projects
- `POST /my/projects` - Create new project
- `GET /my/projects/{id}` - Get user's project
- `PUT /my/projects/{id}` - Update user's project
- `DELETE /my/projects/{id}` - Delete user's project
- `POST /my/projects/{id}/resubmit` - Resubmit rejected project

### Tags
- `GET /tags` - List all tags

### Admin (Superuser only)
- `GET /admin/projects` - List all projects for review
- `GET /admin/projects/{id}` - Get project for review
- `PUT /admin/projects/{id}/approve` - Approve/reject project
- `PUT /admin/projects/{id}/feature` - Toggle featured status
- `GET /admin/users` - List users
- `PUT /admin/users/{id}/ban` - Ban/unban user
- `POST /admin/tags` - Create tag
- `PUT /admin/tags/{id}` - Update tag
- `DELETE /admin/tags/{id}` - Delete tag
- `GET /admin/analytics` - Get platform analytics

## Comparison with FastAPI Backend

This Django implementation provides the same functionality as the FastAPI backend but uses:

- **Django ORM** instead of SQLAlchemy
- **Django Ninja** instead of FastAPI for API framework
- **Django's built-in user system** (extended) instead of custom user models
- **Django migrations** instead of Alembic
- **Django's settings system** instead of Pydantic settings

Both backends offer identical API interfaces and can be used interchangeably.

## Development

### Common Commands

You can use the provided Makefile for common tasks:

```bash
make install-deps      # Install dependencies
make dev               # Run development server
make migrate           # Run database migrations
make makemigrations    # Create new migrations
make shell             # Open Django shell
make test              # Run tests
make createsuperuser   # Create superuser
make extract-openapi   # Extract OpenAPI spec to openapi.json
make clean             # Clean cache files
```

### Manual Commands

To run in development mode:

```bash
uv run python manage.py runserver 0.0.0.0:8000
```

To run migrations:

```bash
uv run python manage.py makemigrations
uv run python manage.py migrate
```

To create a superuser:

```bash
uv run python manage.py createsuperuser
```

To extract OpenAPI specification:

```bash
make extract-openapi
# or manually:
uv run python scripts/extract_openapi.py
```