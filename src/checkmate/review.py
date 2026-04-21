"""Core review engine: diff + PR metadata -> Review object."""
import json
import logging
import re

from anthropic import Anthropic
from pydantic import ValidationError

from checkmate.config import settings
from checkmate.prompts import SYSTEM_PROMPT, build_user_prompt
from checkmate.schemas import Review

logger = logging.getLogger(__name__)

_client = Anthropic(api_key=settings.anthropic_api_key)

MAX_OUTPUT_TOKENS = 4096


def _extract_json(text: str) -> dict:
    """Pull the JSON object out of Claude's response.

    Claude usually returns clean JSON when the prompt demands it, but we guard
    against stray prose by grabbing the first `{...}` block.
    """
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"no JSON object found in model output: {text[:200]}")
    return json.loads(match.group(0))


def review_diff(
    repo: str,
    pr_number: int,
    pr_title: str,
    pr_body: str,
    diff: str,
    repo_context: str = "",
) -> Review:
    """Call Claude to review a diff and return a parsed Review."""
    user_prompt = build_user_prompt(
        repo=repo,
        pr_number=pr_number,
        pr_title=pr_title,
        pr_body=pr_body or "",
        diff=diff,
        repo_context=repo_context,
    )

    logger.info("calling Claude for %s#%s (diff %d chars)", repo, pr_number, len(diff))

    response = _client.messages.create(
        model=settings.claude_model,
        max_tokens=MAX_OUTPUT_TOKENS,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_prompt}],
    )

    text = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    )

    logger.info(
        "claude usage: in=%d out=%d cached=%s",
        response.usage.input_tokens,
        response.usage.output_tokens,
        getattr(response.usage, "cache_read_input_tokens", 0),
    )

    raw = _extract_json(text)

    try:
        return Review.model_validate(raw)
    except ValidationError as e:
        logger.warning("review failed schema validation: %s", e)
        # Salvage what we can so a bad model output doesn't kill the whole review
        return Review(
            summary=str(raw.get("summary", "Review parsing error — see logs."))[:300],
            findings=[],
        )
