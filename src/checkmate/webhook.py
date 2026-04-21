import hashlib
import hmac
import logging

from fastapi import APIRouter, Header, HTTPException, Request
from redis import Redis
from rq import Queue

from checkmate.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

_redis = Redis.from_url(settings.redis_url)
_queue = Queue("reviews", connection=_redis)


def _verify_signature(body: bytes, signature_header: str | None) -> None:
    if not signature_header or not signature_header.startswith("sha256="):
        raise HTTPException(status_code=401, detail="missing or malformed signature")
    expected = hmac.new(
        settings.github_webhook_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    provided = signature_header.removeprefix("sha256=")
    if not hmac.compare_digest(expected, provided):
        raise HTTPException(status_code=401, detail="signature mismatch")


@router.post("/webhook")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
) -> dict[str, str]:
    body = await request.body()
    _verify_signature(body, x_hub_signature_256)

    if x_github_event != "pull_request":
        return {"status": "ignored", "reason": f"event {x_github_event}"}

    payload = await request.json()
    action = payload.get("action")
    if action not in {"opened", "synchronize", "reopened"}:
        return {"status": "ignored", "reason": f"action {action}"}

    pr = payload["pull_request"]
    job_data = {
        "installation_id": payload["installation"]["id"],
        "repo_full_name": payload["repository"]["full_name"],
        "pr_number": pr["number"],
        "head_sha": pr["head"]["sha"],
        "base_sha": pr["base"]["sha"],
    }

    # Import here to avoid circular imports at module load
    from checkmate.worker import review_pr

    job = _queue.enqueue(review_pr, job_data, job_timeout=300)
    logger.info("enqueued review job %s for %s#%s", job.id, job_data["repo_full_name"], job_data["pr_number"])

    return {"status": "queued", "job_id": job.id}
