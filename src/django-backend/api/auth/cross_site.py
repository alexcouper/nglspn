from django.http import HttpRequest, JsonResponse

# What the browser puts in `Sec-Fetch-Site` for a request from another site.
# `same-site` covers naglasupan.is -> api.naglasupan.is; a request with no
# header (curl, the Next.js server, older browsers) is let through, so this is
# a second layer behind api/parser.py, not the only one.
CROSS_SITE = "cross-site"


def reject_cross_site(request: HttpRequest) -> JsonResponse | None:
    """403 for a request the browser says came from another site, else None.

    For the endpoints that set or clear the refresh cookie. `SameSite=Lax`
    only governs when the cookie is *sent*; any response may *store* one, so
    a forged cross-site login would otherwise log the victim into the
    attacker's account.
    """
    if request.headers.get("Sec-Fetch-Site") == CROSS_SITE:
        return JsonResponse({"detail": "Cross-site request refused"}, status=403)
    return None
