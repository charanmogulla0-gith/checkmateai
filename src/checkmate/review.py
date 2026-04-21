"""Core review engine: diff + PR metadata -> Review object."""
import json
import logging
import re

from anthropic import Anthropic
from pydantic import ValidationError

from checkmate.config import settings
from checkmate.observability import observe, update_generation
from checkmate.prompts import SYSTEM_PROMPT, build_user_prompt
from checkmate.schemas import Review

logger = logging.getLogger(__name__)

_client = Anthropic(api_key=settings.anthropic_api_key)

MAX_OUTPUT_TOKENS = 4096

# Anthropic Claude Sonnet 4.x pricing per 1M tokens (USD).
PRICE_INPUT_PER_MTOK = 3.00
PRICE_OUTPUT_PER_MTOK = 15.00
PRICE_CACHE_WRITE_PER_MTOK = 3.75
PRICE_CACHE_READ_PER_MTOK = 0.30


def _compute_cost(input_tokens: int, output_tokens: int, cache_read: int, cache_write: int) -> dict:
    input_cost = input_tokens * PRICE_INPUT_PER_MTOK / 1_000_000
    output_cost = output_tokens * PRICE_OUTPUT_PER_MTOK / 1_000_000
    cache_write_cost = cache_write * PRICE_CACHE_WRITE_PER_MTOK / 1_000_000
    cache_read_cost = cache_read * PRICE_CACHE_READ_PER_MTOK / 1_000_000
    return {
        "input": round(input_cost, 6),
        "output": round(output_cost, 6),
        "cache_write": round(cache_write_cost, 6),
        "cache_read": round(cache_read_cost, 6),
        "total": round(input_cost + output_cost + cache_write_cost + cache_read_cost, 6),
    }


def _extract_json(text: str) -> dict:
    """Pull the JSON object out of Claude's response.

    Claude usually returns clean JSON when the prompt demands it, but we guard
    against stray prose by grabbing the first `{...}` block.
    """
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"no JSON object found in model output: {text[:200]}")
    return json.loads(match.group(0))


@observe(as_type="generation", name="claude-review")
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

    usage = response.usage
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
    logger.info(
        "claude usage: in=%d out=%d cache_read=%d cache_write=%d",
        usage.input_tokens, usage.output_tokens, cache_read, cache_write,
    )

    total_input = usage.input_tokens + cache_read + cache_write
    cost = _compute_cost(usage.input_tokens, usage.output_tokens, cache_read, cache_write)
    update_generation(
        model=settings.claude_model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        output=text,
        usage={
            "input": total_input,
            "output": usage.output_tokens,
            "total": total_input + usage.output_tokens,
            "unit": "TOKENS",
            "inputCost": round(
                cost["input"] + cost["cache_write"] + cost["cache_read"], 6
            ),
            "outputCost": cost["output"],
            "totalCost": cost["total"],
        },
        metadata={
            "repo": repo,
            "pr_number": pr_number,
            "has_repo_context": bool(repo_context),
            "cache_read_input_tokens": cache_read,
            "cache_creation_input_tokens": cache_write,
            "uncached_input_tokens": usage.input_tokens,
            "cost_breakdown": cost,
        },
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
