from django.template.loader import render_to_string
from mjml import mjml_to_html


def render_email(template_name: str, context: dict) -> tuple[str, str]:
    mjml_content = render_to_string(f"email/{template_name}.mjml", context)
    result = mjml_to_html(mjml_content)
    html = result.html
    text = render_to_string(f"email/{template_name}.txt", context)
    return html, text


# Import after render_email is defined — handler and query depend on it.
from .handler import DjangoEmailHandler  # noqa: E402
from .query import DjangoEmailQuery  # noqa: E402

__all__ = [
    "DjangoEmailHandler",
    "DjangoEmailQuery",
    "render_email",
]
