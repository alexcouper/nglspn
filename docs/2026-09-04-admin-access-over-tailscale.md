# Putting the Django admin behind Tailscale

Investigation, 2026-09-04. Nothing implemented yet — this records what has been
tried, why it kept failing, and which option to reach for next.

## The goal

`/admin/` should not be reachable from the public internet. Access should be
limited to devices on the tailnet.

## What we tried: an IP allowlist in Django

`project_showcase/middleware.py:11` — `AdminIPMiddleware` intercepts any path
starting with `/admin`, derives the client IP from `X-Forwarded-For` counting
`NUM_TRUSTED_PROXIES` hops back from the right, and raises `Http404` when that IP
is not in `ADMIN_ALLOWED_IPS`. Settings at `project_showcase/settings.py:36-42`.

Two attempts, both abandoned:

| When | Change |
|------|--------|
| 2026-02 | Ported in with the rest of the Scaleway setup |
| 2026-03-01 `0b208cce` | Use `NUM_TRUSTED_PROXIES` instead of taking `X-Forwarded-For[0]` |
| 2026-03-02 `31dfbe30` | Log the denial — i.e. debugging a self-lockout |
| 2026-04-06 `a9411370` | Add `ADMIN_IP_RESTRICTION_ENABLED` so it can be switched off |
| 2026-04-06 (infra) | Enabled in prod, `NUM_TRUSTED_PROXIES` 1 → 2 |
| 2026-09-04 (infra) | Disabled in prod again |

Current state: `ADMIN_IP_RESTRICTION_ENABLED: "False"` in the backend ConfigMap
in the `naglasupan-hq` infra repo. The middleware is dead code in production.

The dev Terraform still carries the allowlist that shows the problem in one
comment:

```hcl
admin_allowed_ips = "157.97.17.17,86.151.8.57" # 86.151.8.57 = Burford Airbnb
```

### Why it failed

- **The allowlist tracks where you are sitting.** Dynamic home IPs and travel
  mean a redeploy per location.
- **It fails closed with no way back in.** A denial is a 404 and the only fix is
  a deploy, so a wrong `NUM_TRUSTED_PROXIES` locks admin out from everywhere.
- **The XFF depth is coupled to the fronting layer.** It was 1 on Scaleway and 2
  behind the current setup; any change to what sits in front of Traefik silently
  moves the check onto the wrong hop. This is the repo's usual IP-trust foot-gun.
- **It answers the wrong question.** Admin access is an identity question, and
  this is a network-shaped approximation of it.

## What already exists

The tailnet already covers the cluster — `k3s-server`, `k3s-agent-1` and
`k3s-agent-2-1` are all nodes on it, and the kubeconfig points at the control
plane's tailnet address (`https://100.101.252.82:6443`). Cluster admin is
therefore already tailnet-gated today.

There is no Tailscale *inside* the cluster: `kube-system` runs Traefik and its
svclb pods only. Neither repo mentions Tailscale anywhere else.

## Proposed direction

**Stop serving admin publicly, then reach it over the tailnet.** Both previous
attempts filtered a route that still existed on every public replica. Make it not
exist:

```python
# project_showcase/urls.py (currently mounts admin unconditionally at :29)
if settings.ADMIN_ENABLED:
    urlpatterns.append(path("admin/", admin.site.urls))
```

The public Deployment sets `ADMIN_ENABLED=False`. A second single-replica
`backend-admin` Deployment (same image) sets it True and is left out of the
public Ingress. A misconfiguration then fails to "no admin", not "open admin".

Then pick how to reach it:

### Option A — `kubectl port-forward`

`kubectl port-forward svc/backend-admin 8000:8000`. No new infrastructure, works
today, and inherits the tailnet gating of the API server. `ALLOWED_HOSTS`
already includes `localhost`, and neither `SESSION_COOKIE_SECURE` nor
`CSRF_COOKIE_SECURE` is set, so logging in over plain http works unchanged.

Cost: a command every time.

### Option B — Tailscale Kubernetes operator

Install the operator, add a second Ingress with `ingressClassName: tailscale` and
`tailscale.com/hostname: nglspn-admin` pointing at the admin Service. Gives
`https://nglspn-admin.<tailnet>.ts.net` with MagicDNS, a Tailscale-issued cert,
and per-device/per-user ACLs.

Needs, in the app:

- the ts.net hostname in `ALLOWED_HOSTS`;
- the ts.net origin in `CSRF_TRUSTED_ORIGINS`. The operator terminates TLS and
  proxies plain http, and there is no `SECURE_PROXY_SSL_HEADER` in settings, so
  Django will not infer the origin itself.

Needs, in infra: an OAuth client secret sealed into the cluster.

### Option C — Tailscale sidecar

`tailscale serve` in the admin pod, same end result as B without the operator
CRDs, but auth keys and node state become hand-managed. Only worth it if the
operator is unwanted.

### Not on its own: IP filtering at Traefik

Allowing `100.64.0.0/10` via a Traefik `IPAllowList` middleware is only
meaningful once traffic actually arrives over the tailnet — a complement to the
above, never a replacement.

## Recommendation

Do the `ADMIN_ENABLED` split plus **Option A** first: a two-line `urls.py` change
and a Deployment, and the public surface is gone immediately. Add **Option B**
later if port-forwarding grates.

Delete `AdminIPMiddleware` and its settings once either is in place. Leaving a
disabled half-measure in the tree invites a third run at the same dead end.
