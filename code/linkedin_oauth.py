"""
linkedin_oauth.py
=========================================================================
Self-contained LinkedIn OAuth + Share helpers for LumenCore.

Reads creds from config/luma_live_keys.env or config/luma_outreach_keys.env:
    LINKEDIN_CLIENT_ID
    LINKEDIN_CLIENT_SECRET
    LINKEDIN_REDIRECT_URI    (e.g. http://127.0.0.1:8787/auth/linkedin/callback)

Produces a token store at:
    config/linkedin_token.json

Public functions (called by the gateway router and the publish hook):
    load_keys() -> dict
    auth_url(state: str) -> str
    exchange_code(code: str) -> dict     # {access_token, expires_in, ...}
    save_token(token: dict) -> Path
    load_token() -> dict | None
    me() -> dict                         # current member profile
    share_text(text: str, link: str | None = None,
               link_title: str | None = None,
               link_desc: str | None = None) -> dict   # returns the post id

If creds are missing, every function raises RuntimeError with a clear message
so callers can fall back gracefully (e.g. publish_evidence_bundle.py just
skips the post step instead of crashing).
"""
from __future__ import annotations

import json
import secrets
import time
import urllib.parse
from pathlib import Path
from typing import Optional

import requests

ROOT = Path(__file__).resolve().parent.parent
ENV_FILES = [
    ROOT / "config" / "luma_outreach_keys.env",
    ROOT / "config" / "luma_live_keys.env",
    ROOT / "code" / "execution" / "config" / "luma_live_keys.env",
    ROOT / ".deploy_stage" / "code" / "execution" / "config" / "luma_live_keys.env",
    ROOT / ".env",
]
TOKEN_PATH = ROOT / "config" / "linkedin_token.json"

LI_AUTH = "https://www.linkedin.com/oauth/v2/authorization"
LI_TOKEN = "https://www.linkedin.com/oauth/v2/accessToken"
LI_USERINFO = "https://api.linkedin.com/v2/userinfo"
LI_POSTS = "https://api.linkedin.com/v2/ugcPosts"

# OpenID Connect for sign-in + email + profile, plus w_member_social for posting
DEFAULT_SCOPES = "openid profile email w_member_social"


def load_keys() -> dict:
    out: dict = {}
    for p in ENV_FILES:
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            if k not in out or len(v) > len(out[k]):
                out[k] = v
    return out


def _required(keys: dict, name: str) -> str:
    v = keys.get(name)
    if not v:
        raise RuntimeError(
            f"{name} not set. Add it to config/luma_outreach_keys.env "
            f"(see https://www.linkedin.com/developers/apps Auth tab)."
        )
    return v


def auth_url(state: Optional[str] = None,
             scope: str = DEFAULT_SCOPES) -> tuple[str, str]:
    """Return (url, state). Caller stores state in a session cookie and
    verifies it on the callback."""
    keys = load_keys()
    cid = _required(keys, "LINKEDIN_CLIENT_ID")
    redirect = _required(keys, "LINKEDIN_REDIRECT_URI")
    state = state or secrets.token_urlsafe(24)
    qs = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": cid,
        "redirect_uri": redirect,
        "scope": scope,
        "state": state,
    })
    return f"{LI_AUTH}?{qs}", state


def exchange_code(code: str) -> dict:
    keys = load_keys()
    cid = _required(keys, "LINKEDIN_CLIENT_ID")
    secret = _required(keys, "LINKEDIN_CLIENT_SECRET")
    redirect = _required(keys, "LINKEDIN_REDIRECT_URI")
    r = requests.post(LI_TOKEN, data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect,
        "client_id": cid,
        "client_secret": secret,
    }, timeout=30)
    r.raise_for_status()
    tok = r.json()
    tok["obtained_at"] = int(time.time())
    return tok


def save_token(token: dict) -> Path:
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(json.dumps(token, indent=2), encoding="utf-8")
    try:
        # Best-effort permission tighten on POSIX; harmless on Windows.
        TOKEN_PATH.chmod(0o600)
    except Exception:
        pass
    return TOKEN_PATH


def load_token() -> Optional[dict]:
    if not TOKEN_PATH.exists():
        return None
    try:
        tok = json.loads(TOKEN_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
    obtained = int(tok.get("obtained_at", 0))
    expires_in = int(tok.get("expires_in", 0))
    if obtained and expires_in and (obtained + expires_in) < int(time.time()) + 300:
        # within 5 min of expiry -> treat as gone
        return None
    return tok


def _bearer() -> str:
    tok = load_token()
    if not tok:
        raise RuntimeError(
            "No LinkedIn access token. Visit /auth/linkedin/login on the "
            "FastAPI gateway to grant access first."
        )
    return tok["access_token"]


def me() -> dict:
    r = requests.get(LI_USERINFO, headers={"Authorization": f"Bearer {_bearer()}"},
                     timeout=15)
    r.raise_for_status()
    return r.json()


def share_text(text: str,
               link: Optional[str] = None,
               link_title: Optional[str] = None,
               link_desc: Optional[str] = None) -> dict:
    """Post to the authenticated member's feed.

    Uses the legacy ugcPosts endpoint which is accepted under the
    `w_member_social` scope. Returns the parsed response dict.
    """
    profile = me()
    sub = profile.get("sub")
    if not sub:
        raise RuntimeError(f"LinkedIn /userinfo missing 'sub': {profile}")
    author = f"urn:li:person:{sub}"

    media_category = "NONE"
    media_block: list[dict] = []
    if link:
        media_category = "ARTICLE"
        m: dict = {"status": "READY", "originalUrl": link}
        if link_title:
            m["title"] = {"text": link_title}
        if link_desc:
            m["description"] = {"text": link_desc}
        media_block = [m]

    body = {
        "author": author,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": media_category,
                **({"media": media_block} if media_block else {}),
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC",
        },
    }
    r = requests.post(
        LI_POSTS,
        headers={
            "Authorization": f"Bearer {_bearer()}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        data=json.dumps(body),
        timeout=30,
    )
    if r.status_code >= 300:
        raise RuntimeError(f"LinkedIn share failed [{r.status_code}]: {r.text}")
    out = {"status": r.status_code, "post_id": r.headers.get("x-restli-id")}
    try:
        out["body"] = r.json()
    except Exception:
        out["body"] = r.text
    return out


if __name__ == "__main__":
    # Quick CLI: python linkedin_oauth.py [authurl|whoami|test-share]
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "authurl"
    if cmd == "authurl":
        url, state = auth_url()
        print(f"state: {state}")
        print(url)
    elif cmd == "whoami":
        print(json.dumps(me(), indent=2))
    elif cmd == "test-share":
        print(json.dumps(share_text(
            "LumenCore self-test post — please ignore.",
            link="https://lumen-core.ai/evidence/",
            link_title="LumenCore evidence",
            link_desc="Hash-chained 673-dataset benchmark.",
        ), indent=2))
    else:
        print(f"unknown cmd: {cmd}")
