#!/usr/bin/env python
"""Bootstrap script to initialize the database with default users.

This script:
1. Runs migrations
2. Creates a superuser (root@root.com)
3. Creates a test user and saves credentials to .env.claude
"""

import os
import secrets
import string
import sys
from pathlib import Path

# Add the django-backend directory to the path
DJANGO_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DJANGO_BACKEND_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_showcase.settings")

import django

django.setup()

from django.core.management import call_command

from apps.users.models import User


def generate_password(length: int = 16) -> str:
    """Generate a secure random password."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_kennitala() -> str:
    """Generate a fake kennitala (Icelandic ID) for testing."""
    # Format: DDMMYY-XXXX (10 digits total, no dash in DB)
    return "".join(secrets.choice(string.digits) for _ in range(10))


def main() -> None:
    print("Running database migrations...")
    call_command("migrate", verbosity=1)
    print()

    # Create superuser
    superuser_email = "root@root.com"
    superuser_password = "root"

    if User.objects.filter(email=superuser_email).exists():
        print(f"Superuser {superuser_email} already exists, skipping...")
    else:
        print(f"Creating superuser: {superuser_email}")
        User.objects.create_superuser(
            email=superuser_email,
            password=superuser_password,
            kennitala=generate_kennitala(),
            first_name="Root",
            last_name="Admin",
        )
        print(f"Superuser created: {superuser_email} (password: {superuser_password})")
    print()

    # Create test user
    test_user_email = "test@example.com"
    test_user_password = generate_password()

    if User.objects.filter(email=test_user_email).exists():
        print(f"Test user {test_user_email} already exists, skipping...")
        # Still need to update .env.claude but we don't know the password
        print("Note: Cannot update .env.claude with existing user's password")
    else:
        print(f"Creating test user: {test_user_email}")
        User.objects.create_user(
            email=test_user_email,
            password=test_user_password,
            kennitala=generate_kennitala(),
            first_name="Test",
            last_name="User",
            is_verified=True,
        )
        print(f"Test user created: {test_user_email}")

        # Write credentials to .env.claude at project root
        project_root = DJANGO_BACKEND_DIR.parent.parent
        env_claude_path = project_root / ".env.claude"

        env_content = f"""# Test user credentials for Playwright browser automation
# Update these with your actual test user credentials

export TEST_USER_EMAIL={test_user_email}
export TEST_USER_PASSWORD={test_user_password}
export TEST_APP_URL=http://localhost:3000
"""
        env_claude_path.write_text(env_content)
        print(f"Credentials written to: {env_claude_path}")

    print()
    print("Bootstrap complete!")


if __name__ == "__main__":
    main()
