from datetime import datetime
from typing import Literal
from uuid import UUID

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from ninja import Field, Schema
from pydantic import field_validator

# Mirrors apps.projects.models.ProjectReportReason. Spelled out so the OpenAPI
# spec, and the web-ui types generated from it, carry the set of values.
ProjectReportReasonValue = Literal[
    "site_down", "something_broken", "wrong_link", "other"
]


class ProjectReportCreate(Schema):
    reason: ProjectReportReasonValue
    details: str = Field(default="", max_length=2000)
    contact_email: str = Field(default="", max_length=254)

    @field_validator("details", "contact_email")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()

    @field_validator("contact_email")
    @classmethod
    def _valid_email(cls, value: str) -> str:
        if value:
            try:
                validate_email(value)
            except ValidationError as e:
                msg = "Enter a valid email address"
                raise ValueError(msg) from e
        return value


class ProjectReportResponse(Schema):
    id: UUID
    reason: ProjectReportReasonValue
    created_at: datetime
