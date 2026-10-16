from django.template import Context
from django.template.loader import get_template, render_to_string
from mjml import mjml_to_html


def render_email(template_name: str, context: dict) -> tuple[str, str]:
    mjml_content = render_to_string(f"email/{template_name}.mjml", context)
    result = mjml_to_html(mjml_content)
    html = result.html
    text = _render_plain_text(f"email/{template_name}.txt", context)
    return html, text


def _render_plain_text(template_name: str, context: dict) -> str:
    # Autoescape off: the text part is never parsed as HTML, so escaping turns
    # an apostrophe in a name into `&#x27;` and a markdown quote into `&gt;`.
    # `{% include %}` inherits the setting from the context.
    template = get_template(template_name).template
    return template.render(Context(context, autoescape=False))


# Import after render_email is defined — handler and query depend on it.
from .handler import DjangoEmailHandler  # noqa: E402
from .query import DjangoEmailQuery  # noqa: E402

__all__ = [
    "DjangoEmailHandler",
    "DjangoEmailQuery",
    "render_email",
]
