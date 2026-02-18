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

### Separation of concerns

Whilst this is currently a monolithic backend, we code in such a way as to easily be able
to change that in future.

How:
 - apps/X - databases only
 - services/ - things that could later be taken out into other apps.
       - email/
            handler_interface (should define methods available, params and return types)
            query_interface (defines querying methods available, params and return types)
            django_impl (django-native implementation of the interface)
       - project/
            handler_interface
            query_interface
            django_impl


Someone is responsible for creating the handler and query classes and these can be referred to from django.conf settings
eg. settings.HANDLERS.email and settings.REPO.email resolves to an instantiated email handler and email querier respectively.

email's interface should contain:
 - send_verification_email(recipient, code)
 - send_project_approved_email(project_id)

project interface then has:
 - get_project_with_owner(project_id)
 - create(project)

email's django implementation should ALSO use the settings.REPO.project to peform the queries it needs

Ruels:
 - Each service in services/ cannot use other apps database models to perform queries.
 - Only exception to this is for foreign keys.
 - Each service defines an interface that other apps can use for a) triggering things, b) fetching things.
 - Each service provides an implementation of those interface which uses django models.



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