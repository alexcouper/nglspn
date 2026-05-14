"""Domain exceptions for the follows service.

ProjectNotFoundError is re-used from services.project.exceptions where the
caller is resolving a project by slug — see services/follows/django_impl
for that import.
"""


class FollowError(Exception):
    """Base class for follows-service-specific errors."""
