"""
linkedin_router.py
=========================================================================
FastAPI router that adds 3 endpoints to the LumaCore gateway:

    GET  /auth/linkedin/login      -> redirect to LinkedIn OAuth
    GET  /auth/linkedin/callback   -> exchange code, persist token
    GET  /auth/linkedin/status     -> JSON: {connected, name, email, ...}

Mount in luma_experience_gateway.py with:

    from linkedin_router import router as linkedin_router
    app.include_router(linkedin_router)

Safe to mount even before keys are configured: endpoints return 503 with a
clear "configure keys first" message when LINKEDIN_CLIENT_ID is missing.
"""
from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

import linkedin_oauth as li

router = APIRouter()

_PENDING_STATES: dict[str, float] = {}  # state -> created_ts; pruned periodically
_STATE_TTL = 600  # seconds


def _prune_states() -> None:
    import time
    now = time.time()
    dead = [s for s, t in _PENDING_STATES.items() if now - t > _STATE_TTL]
    for s in dead:
        _PENDING_STATES.pop(s, None)


@router.get("/auth/linkedin/login")
def linkedin_login() -> RedirectResponse:
    try:
        url, state = li.auth_url()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    import time
    _PENDING_STATES[state] = time.time()
    _prune_states()
    return RedirectResponse(url=url, status_code=302)


@router.get("/auth/linkedin/callback")
def linkedin_callback(request: Request) -> HTMLResponse:
    qp = dict(request.query_params)
    err = qp.get("error")
    if err:
        return HTMLResponse(
            f"<h2>LinkedIn auth error</h2><p>{err}: {qp.get('error_description','')}</p>",
            status_code=400,
        )
    code = qp.get("code")
    state = qp.get("state")
    if not code or not state:
        raise HTTPException(status_code=400, detail="missing code or state")
    if state not in _PENDING_STATES:
        raise HTTPException(status_code=400, detail="state mismatch / expired")
    _PENDING_STATES.pop(state, None)
    try:
        tok = li.exchange_code(code)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"token exchange failed: {e}")
    li.save_token(tok)
    profile: dict = {}
    try:
        profile = li.me()
    except Exception as e:
        profile = {"warning": f"saved token but profile fetch failed: {e}"}
    name = profile.get("name", "—")
    email = profile.get("email", "—")
    expires = tok.get("expires_in", 0)
    return HTMLResponse(f"""
<!doctype html>
<html><head><meta charset='utf-8'><title>LinkedIn connected</title>
<style>body{{font-family:-apple-system,Segoe UI,Roboto;background:#0b1020;color:#e9e9ff;
padding:48px;max-width:640px;margin:0 auto}} a{{color:#7c3aed}} code{{background:#111827;padding:2px 6px;border-radius:4px}}</style>
</head><body>
<h1>✓ LinkedIn connected</h1>
<p><b>Name:</b> {name}</p>
<p><b>Email:</b> {email}</p>
<p><b>Token TTL:</b> {expires} seconds (~{expires // 86400} days)</p>
<p>Token persisted to <code>config/linkedin_token.json</code>.</p>
<p>You can close this tab. Auto-posts will fire from
<code>code/linkedin_publish_evidence.py</code>.</p>
<p><a href='/'>back to gateway</a> · <a href='/evidence/'>evidence</a></p>
</body></html>""")


@router.get("/auth/linkedin/status")
def linkedin_status() -> JSONResponse:
    try:
        keys = li.load_keys()
        configured = bool(keys.get("LINKEDIN_CLIENT_ID")
                          and keys.get("LINKEDIN_CLIENT_SECRET")
                          and keys.get("LINKEDIN_REDIRECT_URI"))
    except Exception:
        configured = False
    tok = li.load_token()
    out = {"configured": configured, "connected": bool(tok)}
    if tok:
        try:
            p = li.me()
            out["name"] = p.get("name")
            out["email"] = p.get("email")
            out["sub"] = p.get("sub")
        except Exception as e:
            out["warning"] = str(e)
    return JSONResponse(out)
