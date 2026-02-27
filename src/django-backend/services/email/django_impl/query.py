from __future__ import annotations

from typing import TYPE_CHECKING

import markdown
from django.conf import settings
from django.utils import timezone

from services.email import EMAIL_LOGO_URL
from services.email.query_interface import EmailQueryInterface
from services.users.django_impl import DjangoUserQuery

from . import render_email

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from apps.emails.models import BroadcastEmail


class DjangoEmailQuery(EmailQueryInterface):
    def render_broadcast_email(self, broadcast: BroadcastEmail) -> tuple[str, str]:
        body_html = markdown.markdown(
            broadcast.body_markdown,
            extensions=["extra", "smarty"],
        )
        context = {
            "subject": broadcast.subject,
            "body_html": body_html,
            "body_markdown": broadcast.body_markdown,
            "profile_url": f"{settings.FRONTEND_URL}/profile",
            "logo_url": EMAIL_LOGO_URL,
            "current_year": timezone.now().year,
        }
        return render_email("broadcast", context)

    def resolve_broadcast_recipients(self, broadcast: BroadcastEmail) -> QuerySet:
        if broadcast.email_type in ("platform_updates", "competition_results"):
            return DjangoUserQuery().list_opted_in_for_broadcast_type(
                broadcast.email_type
            )
        return broadcast.individual_recipients.filter(is_active=True)
