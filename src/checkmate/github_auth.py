import time
from functools import lru_cache
from pathlib import Path

import httpx
import jwt

from checkmate.config import settings


@lru_cache(maxsize=1)
def _private_key() -> str:
    return Path(settings.github_app_private_key_path).read_text()


def app_jwt() -> str:
    """Short-lived JWT signed with the App's private key.

    Used to authenticate as the GitHub App itself (not as an installation).
    Valid for 10 minutes per GitHub's max.
    """
    now = int(time.time())
    payload = {"iat": now - 60, "exp": now + 9 * 60, "iss": str(settings.github_app_id)}
    return jwt.encode(payload, _private_key(), algorithm="RS256")


async def installation_token(installation_id: int) -> str:
    """Exchange the App JWT for an installation access token.

    Tokens last 1 hour. Cache by installation_id if you hit rate limits.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {app_jwt()}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
    resp.raise_for_status()
    return resp.json()["token"]
