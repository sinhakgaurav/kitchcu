"""OAuth provider configuration and token exchange for customer social login."""

from __future__ import annotations

import base64
import hashlib
import secrets
import urllib.parse
from dataclasses import dataclass
from typing import Any

import httpx

from ckac_common.config import get_settings

settings = get_settings()

SUPPORTED_OAUTH_PROVIDERS = frozenset({"google", "facebook", "instagram", "twitter", "whatsapp"})
DEV_OAUTH_CODE = "dev"

# Dev-only simulated profiles when OAuth client credentials are not configured.
DEV_OAUTH_PROFILES: dict[str, dict[str, str]] = {
    "google": {
        "provider_user_id": "dev-google-user",
        "name": "Google Customer",
        "email": "google.customer@kitchcu.dev",
        "avatar_url": "",
    },
    "facebook": {
        "provider_user_id": "dev-facebook-user",
        "name": "Facebook Customer",
        "email": "facebook.customer@kitchcu.dev",
        "avatar_url": "",
    },
    "instagram": {
        "provider_user_id": "dev-instagram-user",
        "name": "Instagram Customer",
        "email": "instagram.customer@kitchcu.dev",
        "avatar_url": "",
    },
    "twitter": {
        "provider_user_id": "dev-twitter-user",
        "name": "Twitter Customer",
        "email": "twitter.customer@kitchcu.dev",
        "avatar_url": "",
    },
}


@dataclass(frozen=True)
class OAuthProfile:
    provider_user_id: str
    name: str
    email: str | None
    avatar_url: str | None
    raw: dict[str, Any]


@dataclass(frozen=True)
class OAuthStartResult:
    provider: str
    state: str
    authorization_url: str | None
    dev_mode: bool
    code_verifier: str | None = None


def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def _provider_client(provider: str) -> tuple[str | None, str | None]:
    if provider == "google":
        return settings.oauth_google_client_id, settings.oauth_google_client_secret
    if provider == "facebook":
        return settings.oauth_facebook_client_id, settings.oauth_facebook_client_secret
    if provider == "instagram":
        cid = settings.oauth_instagram_client_id or settings.oauth_facebook_client_id
        secret = settings.oauth_instagram_client_secret or settings.oauth_facebook_client_secret
        return cid, secret
    if provider == "twitter":
        return settings.oauth_twitter_client_id, settings.oauth_twitter_client_secret
    return None, None


def provider_configured(provider: str) -> bool:
    client_id, _ = _provider_client(provider)
    return bool(client_id)


def dev_oauth_allowed() -> bool:
    return settings.app_env in {"development", "test"}


def build_authorization_url(
    provider: str,
    *,
    redirect_uri: str,
    state: str,
    code_challenge: str | None = None,
) -> str:
    client_id, _ = _provider_client(provider)
    if not client_id:
        raise ValueError(f"OAuth client not configured for {provider}")

    if provider == "google":
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "online",
            "prompt": "select_account",
        }
        return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)

    if provider == "facebook":
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "email,public_profile",
            "state": state,
        }
        return "https://www.facebook.com/v19.0/dialog/oauth?" + urllib.parse.urlencode(params)

    if provider == "instagram":
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "user_profile,user_media",
            "state": state,
        }
        return "https://api.instagram.com/oauth/authorize?" + urllib.parse.urlencode(params)

    if provider == "twitter":
        if not code_challenge:
            raise ValueError("Twitter OAuth requires PKCE code_challenge")
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "tweet.read users.read offline.access",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return "https://twitter.com/i/oauth2/authorize?" + urllib.parse.urlencode(params)

    raise ValueError(f"Unsupported OAuth provider: {provider}")


def start_oauth(provider: str, *, redirect_uri: str) -> OAuthStartResult:
    if provider not in SUPPORTED_OAUTH_PROVIDERS or provider == "whatsapp":
        raise ValueError(f"Unsupported OAuth provider: {provider}")

    state = secrets.token_urlsafe(32)
    configured = provider_configured(provider)
    code_verifier: str | None = None
    code_challenge: str | None = None

    if provider == "twitter" and configured:
        code_verifier, code_challenge = _pkce_pair()

    authorization_url: str | None = None
    dev_mode = not configured
    if configured:
        authorization_url = build_authorization_url(
            provider,
            redirect_uri=redirect_uri,
            state=state,
            code_challenge=code_challenge,
        )
    elif not dev_oauth_allowed():
        raise ValueError(f"OAuth not configured for {provider}")

    return OAuthStartResult(
        provider=provider,
        state=state,
        authorization_url=authorization_url,
        dev_mode=dev_mode,
        code_verifier=code_verifier,
    )


async def exchange_oauth_code(
    provider: str,
    *,
    code: str,
    redirect_uri: str,
    code_verifier: str | None = None,
) -> OAuthProfile:
    if code == DEV_OAUTH_CODE:
        if not dev_oauth_allowed():
            raise ValueError("Dev OAuth login is not allowed in this environment")
        mock = DEV_OAUTH_PROFILES.get(provider)
        if not mock:
            raise ValueError(f"No dev profile for {provider}")
        return OAuthProfile(
            provider_user_id=mock["provider_user_id"],
            name=mock["name"],
            email=mock.get("email"),
            avatar_url=mock.get("avatar_url") or None,
            raw={"dev": True, "provider": provider},
        )

    client_id, client_secret = _provider_client(provider)
    if not client_id or not client_secret:
        raise ValueError(f"OAuth client not configured for {provider}")

    async with httpx.AsyncClient(timeout=20.0) as client:
        if provider == "google":
            token_resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            token_resp.raise_for_status()
            access_token = token_resp.json()["access_token"]
            user_resp = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            user_resp.raise_for_status()
            data = user_resp.json()
            return OAuthProfile(
                provider_user_id=str(data["sub"]),
                name=data.get("name") or "Google User",
                email=data.get("email"),
                avatar_url=data.get("picture"),
                raw=data,
            )

        if provider == "facebook":
            token_resp = await client.get(
                "https://graph.facebook.com/v19.0/oauth/access_token",
                params={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "code": code,
                },
            )
            token_resp.raise_for_status()
            access_token = token_resp.json()["access_token"]
            user_resp = await client.get(
                "https://graph.facebook.com/me",
                params={"fields": "id,name,email,picture", "access_token": access_token},
            )
            user_resp.raise_for_status()
            data = user_resp.json()
            picture = data.get("picture", {}).get("data", {}).get("url")
            return OAuthProfile(
                provider_user_id=str(data["id"]),
                name=data.get("name") or "Facebook User",
                email=data.get("email"),
                avatar_url=picture,
                raw=data,
            )

        if provider == "instagram":
            token_resp = await client.post(
                "https://api.instagram.com/oauth/access_token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                    "code": code,
                },
            )
            token_resp.raise_for_status()
            data = token_resp.json()
            user_id = str(data.get("user_id", ""))
            return OAuthProfile(
                provider_user_id=user_id,
                name="Instagram User",
                email=None,
                avatar_url=None,
                raw=data,
            )

        if provider == "twitter":
            if not code_verifier:
                raise ValueError("Twitter OAuth requires code_verifier")
            token_resp = await client.post(
                "https://api.twitter.com/2/oauth2/token",
                data={
                    "code": code,
                    "grant_type": "authorization_code",
                    "client_id": client_id,
                    "redirect_uri": redirect_uri,
                    "code_verifier": code_verifier,
                },
                auth=(client_id, client_secret),
            )
            token_resp.raise_for_status()
            access_token = token_resp.json()["access_token"]
            user_resp = await client.get(
                "https://api.twitter.com/2/users/me",
                params={"user.fields": "profile_image_url,name"},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            user_resp.raise_for_status()
            data = user_resp.json()["data"]
            return OAuthProfile(
                provider_user_id=str(data["id"]),
                name=data.get("name") or "Twitter User",
                email=None,
                avatar_url=data.get("profile_image_url"),
                raw=data,
            )

    raise ValueError(f"Unsupported OAuth provider: {provider}")
