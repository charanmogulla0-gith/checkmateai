"""Background review worker.

RQ calls `review_pr` with a job_data dict. This function is synchronous — RQ
runs it in its own process and we need stable serialization for the enqueue.
We use asyncio.run for the few async GitHub calls.
"""
import asyncio
import logging

from checkmate.diff_utils import commentable_lines, truncate_diff
from checkmate.github_auth import installation_token
from checkmate.github_client import GitHubClient
from checkmate.observability import flush as lf_flush
from checkmate.observability import observe, update_trace
from checkmate.rag import ensure_indexed, retrieve_context
from checkmate.review import review_diff
from checkmate.schemas import Finding, Review, ReviewJob

logger = logging.getLogger(__name__)

SUMMARY_HEADER = "## 🔍 Checkmate review\n\n"


def _filter_findings(findings: list[Finding], valid_lines: dict[str, set[int]]) -> list[Finding]:
    """Drop findings pointing at lines GitHub won't accept inline comments on."""
    kept = []
    for f in findings:
        if f.line in valid_lines.get(f.file, set()):
            kept.append(f)
        else:
            logger.info("dropping finding on %s:%d (line not in diff)", f.file, f.line)
    return kept


def _format_summary(review: Review, kept: int, dropped: int) -> str:
    body = SUMMARY_HEADER + review.summary
    if dropped:
        body += f"\n\n_Note: {dropped} additional finding(s) were dropped because they referenced lines not in the diff._"
    if kept == 0 and review.findings == []:
        body += "\n\nNo issues found. ✅"
    return body


def _finding_to_comment(f: Finding) -> dict:
    severity_icon = {"high": "🔴", "medium": "🟡", "low": "🔵"}[f.severity]
    body = f"**{severity_icon} {f.severity.upper()} · {f.category}**\n\n{f.comment}"
    return {"path": f.file, "line": f.line, "body": body, "side": "RIGHT"}


@observe(name="pr-review")
async def _run_review(job: ReviewJob) -> dict:
    update_trace(
        name=f"{job.repo_full_name}#{job.pr_number}",
        metadata={"repo": job.repo_full_name, "pr_number": job.pr_number, "head_sha": job.head_sha},
    )
    token = await installation_token(job.installation_id)
    gh = GitHubClient(token)

    pr = await gh.get_pr(job.repo_full_name, job.pr_number)
    diff = await gh.get_pr_diff(job.repo_full_name, job.pr_number)
    diff = truncate_diff(diff)

    # RAG: index the repo on first encounter, then retrieve diff-relevant chunks.
    try:
        await ensure_indexed(job.repo_full_name, job.base_sha, token)
        repo_context = retrieve_context(job.repo_full_name, diff)
    except Exception:
        logger.exception("rag step failed — proceeding without repo context")
        repo_context = ""

    review = review_diff(
        repo=job.repo_full_name,
        pr_number=job.pr_number,
        pr_title=pr["title"],
        pr_body=pr.get("body") or "",
        diff=diff,
        repo_context=repo_context,
    )

    valid = commentable_lines(diff)
    kept = _filter_findings(review.findings, valid)
    dropped = len(review.findings) - len(kept)

    await gh.post_review(
        repo=job.repo_full_name,
        number=job.pr_number,
        commit_sha=job.head_sha,
        body=_format_summary(review, len(kept), dropped),
        comments=[_finding_to_comment(f) for f in kept],
    )

    result = {
        "status": "posted",
        "findings_total": len(review.findings),
        "findings_posted": len(kept),
        "findings_dropped": dropped,
    }
    update_trace(output=result)
    return result


def review_pr(job_data: dict) -> dict:
    """Entry point for RQ worker."""
    job = ReviewJob.model_validate(job_data)
    logger.info("starting review for %s#%s", job.repo_full_name, job.pr_number)
    try:
        result = asyncio.run(_run_review(job))
        logger.info("review complete: %s", result)
        return result
    except Exception:
        logger.exception("review failed for %s#%s", job.repo_full_name, job.pr_number)
        raise
    finally:
        lf_flush()
