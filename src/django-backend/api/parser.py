"""Request-body parsing for the API.

Ninja's default parser runs `json.loads` on any body whatever its declared
type. That lets a cross-site HTML form (`enctype="text/plain"`) hand an
endpoint a well-formed JSON body without a CORS preflight, which is how a
forged login could plant a refresh cookie in a victim's browser. Insisting on
`application/json` closes that: a form cannot send the header, and a `fetch`
that does send it from a foreign origin is preflighted and refused by CORS.
Every endpoint in this API takes JSON, so nothing legitimate is lost.
"""

from django.http import HttpRequest
from ninja.parser import Parser
from ninja.types import DictStrAny

JSON_CONTENT_TYPE = "application/json"


class JsonOnlyParser(Parser):
    def parse_body(self, request: HttpRequest) -> DictStrAny:
        if request.content_type != JSON_CONTENT_TYPE:
            msg = f"Request body must be {JSON_CONTENT_TYPE}"
            raise ValueError(msg)
        return super().parse_body(request)
