# Security Audit — MC (Django REST + server-rendered)

Branch: `v2-django`  ·  Scope: conservative, behavior-preserving hardening
Auth model: TheCarV SSO (password POST backend + signed-JWT callback), custom user `accounts.Employee`.

## Summary

Reviewed authentication, session/JWT handling, SSO backend + callback, cookie/security-header
configuration (dev vs prod), CORS/CSRF, the service-to-service API key, and secret handling.

Overall posture is reasonable: SimpleJWT with rotation + blacklist, timing-safe service-key
comparison, a clean `check --deploy` (0 warnings), and a correct deliberate `SameSite=None+Secure`
cross-site cookie setup for the SSO redirect chain.

Three concrete, low-risk fixes were applied (open-redirect, deprecated `X-XSS-Protection`,
duplicate/conflicting HSTS header). The most important item left for a human is that
**`.env.production` is not covered by `.gitignore`** (out of edit scope), plus the SSRF in the
avatar downloader and the SSO-driven role/account auto-provisioning trust boundary.

Both `manage.py check` (dev) and `check --deploy` (prod) pass with **0 issues** after changes.

---

## Findings

### F1 — Open redirect via `next` in SSO callback — HIGH — FIXED
`apps/accounts/views.py` `SSOCallbackView.get()` (final `redirect`).
`next_url = request.GET.get('next') or '/dashboard'; return redirect(next_url)` redirected to any
attacker-supplied absolute URL after a valid SSO login (e.g. `?next=https://evil.com`), enabling
phishing/credential-relay. The callback executes after authentication, so it is a usable open
redirect.

### F2 — `.env.production` not gitignored — HIGH — RECOMMENDED (out of scope)
`.gitignore` ignores `.env`, `.env.local`, `.env.*.local` but **not** `.env.production`, which
exists untracked in the repo root (git status: `?? .env.production`). One `git add -A` would commit
production secrets (SECRET_KEY, DB URLs, `THECARV_SSO_SECRET`, `SERVICE_API_KEY`, OpenAI key).
`.gitignore` is outside the allowed edit set — fix manually (see Recommended).

### F3 — SSO auto-provisioning assigns role from payload without validation — MEDIUM — RECOMMENDED
`apps/accounts/backends.py` (create + role-sync block) and `apps/accounts/views.py`
`SSOCallbackView` (create + role-sync block). New `Employee`s are auto-created and `user.role` is set
directly from `data/payload.get('role')`, including potentially `admin`, with no check against
`Employee.ROLE_CHOICES`. Within the SSO trust boundary this is intended; if the SSO role field is
ever attacker-influenced it is a privilege-escalation vector. Note: unknown/garbage roles are
fail-safe (they match no permission list → no access; `role_rank` returns lowest), so the real risk
is specifically a wrongly-elevated *known* role coming from the SSO. Not auto-fixed because coercing
roles could silently break legitimate role mapping if the SSO uses different strings — left as a
human decision.

### F4 — Deprecated `X-XSS-Protection` header — LOW — FIXED
`apps/core/middleware.py` `SecurityHeadersMiddleware` set `X-XSS-Protection: 1; mode=block`, and
`config/settings/production.py` set `SECURE_BROWSER_XSS_FILTER = True` (Django's SecurityMiddleware
emitted it a second time). The header is deprecated and can introduce XSS in legacy browsers
(OWASP recommends not sending it / `0`).

### F5 — Duplicate, conflicting HSTS header — LOW — FIXED
`apps/core/middleware.py` emitted `Strict-Transport-Security: max-age=31536000; includeSubDomains`
on every non-DEBUG response (even plain HTTP), while Django's SecurityMiddleware emits HSTS in
production with `preload` + `includeSubDomains` from `SECURE_HSTS_*`. Two HSTS headers, one weaker
(no `preload`). Consolidated onto Django's settings-based header.

### F6 — SSO JWT decode does not require `exp` — LOW — RECOMMENDED
`apps/accounts/views.py` `pyjwt.decode(token, secret, algorithms=['HS256'])`. Algorithm is correctly
pinned (no `alg=none`/confusion) and `ExpiredSignatureError` is handled, but `exp` is not *required*
— a token minted without `exp` would never expire. Not auto-enforced to avoid breaking login if any
issued token lacks `exp`.

### F7 — Redundant ModelBackend fallback in `LoginView` — INFO — verified safe
`apps/accounts/views.py` `LoginView.post()` explicit `ModelBackend().authenticate(username=email,...)`
fallback. Verified there is **no auth bypass**: SSO-provisioned accounts have `set_unusable_password()`,
so `ModelBackend.check_password` always fails for them; only locally-created accounts with a usable
password authenticate, which is intended. The fallback is also effectively dead code (the first
`authenticate()` already routes `email` to `ModelBackend` via `USERNAME_FIELD='email'`), and on the
rare path where it returns a user, `login()` would raise `ValueError` because `user.backend` is unset
— i.e. it fails closed. Left as-is (cleanup suggested) to avoid changing auth behavior.

### F8 — SSRF in document generator (avatar download) — MEDIUM — OUT OF SCOPE (flag only)
`apps/documents/generators.py` `requests.get(avatar, timeout=5)` fetches arbitrary avatar URLs
(SSO/Google/etc.) with no scheme or host allow-list and no private-IP/loopback filtering. A
controllable avatar URL could be used to probe internal services or cloud metadata endpoints. Out of
the allowed edit set — recommend an allow-list + block of private/link-local ranges.

### F9 — Dev CORS reflects Origin with credentials — INFO (dev only)
`config/settings/development.py` `CORS_ALLOW_ALL_ORIGINS = True` together with
`config/settings/base.py` `CORS_ALLOW_CREDENTIALS = True` causes django-cors-headers to echo the
request Origin and allow credentials. Development-only; production uses an explicit
`CORS_ALLOWED_ORIGINS` allow-list (good). Keep dev and prod settings distinct.

### F10 — SERVICE_API_KEY handling — INFO — GOOD (no change)
`apps/accounts/permissions.py` `IsServiceClient` uses `hmac.compare_digest` (timing-safe) and returns
`False` when either the request key or `SERVICE_API_KEY` is empty (fails closed). No change needed.

### F11 — JWT signing key — INFO — acceptable
`config/settings/base.py` `SIMPLE_JWT['SIGNING_KEY'] = os.getenv('JWT_SECRET_KEY') or None` → falls
back to `SECRET_KEY` (standard SimpleJWT behavior). Acceptable provided `SECRET_KEY` is strong/secret;
`config/settings/production.py` already raises `ImproperlyConfigured` if `SECRET_KEY`/`ALLOWED_HOSTS`
are missing, and the deploy check flags weak keys (currently clean).

### F12 — Minor info-leak / IP trust — INFO
`apps/core/utils.py` `custom_exception_handler` returns `str(exc)` as the `error` field (DRF-handled
exceptions only; the 500 fallback is generic) — low risk. `get_client_ip` trusts
`X-Forwarded-For`; used only for activity logging, not authorization, so spoofing impact is low
(behind nginx the left-most value is client-controlled — fine for audit logs).

---

## Fixes Applied (all in-scope, behavior-preserving)

1. **F1 / `apps/accounts/views.py`** — `SSOCallbackView` now validates `next` with
   `django.utils.http.url_has_allowed_host_and_scheme(allowed_hosts={request.get_host()},
   require_https=request.is_secure())` and falls back to `/dashboard` for any external/unsafe target.
   Internal relative paths (the normal case) still work unchanged. Added the import.
2. **F4+F5 / `apps/core/middleware.py`** — removed `X-XSS-Protection` and the manual
   `Strict-Transport-Security` header from `SecurityHeadersMiddleware`; HSTS now comes solely from
   Django's `SECURE_HSTS_*` (with `preload`). Other headers (`X-Content-Type-Options`,
   `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`) unchanged.
3. **F4 / `config/settings/production.py`** — `SECURE_BROWSER_XSS_FILTER = True → False` so Django's
   SecurityMiddleware no longer re-emits the deprecated header. (Django 4.2 removed deploy check
   W007, so this adds no new warning.)

No changes were made to the deliberate `SameSite=None + Secure` cross-site SSO cookie configuration,
to the SSO login flow, or to `TEMPLATES`/templates/static/context_processors.

---

## Recommended (manual / out-of-scope)

- **F2 (do first):** add `.env.production` (or `.env.*` except `.env.example`) to `.gitignore`; run
  `git status` to confirm it is no longer untracked-and-committable. Verify no secret file was ever
  committed (`git log --all -- .env.production`). Rotate `THECARV_SSO_SECRET` / `SERVICE_API_KEY` /
  `SECRET_KEY` if there is any doubt.
- **F3:** validate the SSO-supplied `role` against `Employee.ROLE_CHOICES` before assigning, and treat
  unknown values as `employee`; confirm the SSO cannot be coerced into emitting an elevated role for
  the wrong user. Consider not letting SSO *downgrade/upgrade* an existing local admin silently.
- **F6:** add `options={'require': ['exp']}` (and optionally `leeway`) to the `pyjwt.decode` call once
  it is confirmed every SSO token carries `exp`; consider validating `aud`/`iss`.
- **F7:** delete the redundant `ModelBackend` fallback in `LoginView.post` (the primary
  `authenticate()` already covers it), or set `user.backend` before `login()` if it is kept.
- **F8 (SSRF):** in `apps/documents/generators.py`, restrict avatar fetches to an https host
  allow-list and reject private/loopback/link-local/metadata IPs; keep the short timeout.
- **F9:** keep `CORS_ALLOW_ALL_ORIGINS` out of any non-dev settings; it is already prod-safe today.

---

## Check Output

Baseline (before changes) and after changes are identical — no new errors or warnings.

```
$ DJANGO_SETTINGS_MODULE=config.settings.development  .venv/Scripts/python.exe manage.py check
System check identified no issues (0 silenced).

$ DJANGO_SETTINGS_MODULE=config.settings.production   .venv/Scripts/python.exe manage.py check --deploy
System check identified no issues (0 silenced).
```

Deploy-check warnings: **none** (0). Production already sets `SECURE_SSL_REDIRECT`,
`SECURE_HSTS_SECONDS`/`INCLUDE_SUBDOMAINS`/`PRELOAD`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`,
`SECURE_CONTENT_TYPE_NOSNIFF`, `SECURE_PROXY_SSL_HEADER`, and enforces `SECRET_KEY`/`ALLOWED_HOSTS`.
