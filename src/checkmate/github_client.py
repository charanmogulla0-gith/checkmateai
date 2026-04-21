"""Thin async GitHub API client — just the endpoints we need.

Using httpx directly instead of PyGithub because PyGithub is sync and we want
async for the FastAPI app. Keeps the dependency surface small.
"""
import logging

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api.github.com"


class GitHubClient:
    def __init__(self, token: str):
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def _get(self, url: str, **kwargs) -> httpx.Response:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self._headers, **kwargs)
        resp.raise_for_status()
        return resp

    async def _post(self, url: str, json: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=self._headers, json=json)
        resp.raise_for_status()
        return resp

    async def get_pr(self, repo: str, number: int) -> dict:
        r = await self._get(f"{BASE_URL}/repos/{repo}/pulls/{number}")
        return r.json()

    async def get_pr_diff(self, repo: str, number: int) -> str:
        """Unified diff for a PR. Uses the diff media type."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{BASE_URL}/repos/{repo}/pulls/{number}",
                headers={**self._headers, "Accept": "application/vnd.github.v3.diff"},
            )
        resp.raise_for_status()
        return resp.text

    async def post_review(
        self, repo: str, number: int, commit_sha: str, body: str, comments: list[dict]
    ) -> dict:
        """Create a PR review with inline comments in a single call.

        `comments` items must be {"path", "line", "body"} (line is in the new file).
        """
        payload = {
            "commit_id": commit_sha,
            "event": "COMMENT",
            "body": body,
            "comments": comments,
        }
        r = await self._post(
            f"{BASE_URL}/repos/{repo}/pulls/{number}/reviews", json=payload
        )
        return r.json()
