"""Diff parsing helpers.

GitHub inline review comments can only target lines that are part of the diff —
either `+` lines (additions) or context lines in the same hunk. We track which
(file, new_line) pairs are commentable so we can drop any LLM finding that
points at an invalid line.
"""
from unidiff import PatchSet


def commentable_lines(unified_diff: str) -> dict[str, set[int]]:
    """Return {file_path: {new_line_numbers}} for every line GitHub will accept.

    Includes both added lines and context lines. Skips removed-only hunks and
    files that are pure deletions.
    """
    patch = PatchSet(unified_diff)
    result: dict[str, set[int]] = {}
    for patched_file in patch:
        if patched_file.is_removed_file:
            continue
        lines: set[int] = set()
        for hunk in patched_file:
            for line in hunk:
                if line.is_added or line.is_context:
                    if line.target_line_no is not None:
                        lines.add(line.target_line_no)
        if lines:
            result[patched_file.path] = lines
    return result


def truncate_diff(diff: str, max_chars: int = 60_000) -> str:
    """Cheap safeguard against huge PRs blowing the context window.

    ~60k chars ≈ ~15k tokens. Real fix is multi-call review for big PRs; for MVP
    we just clip and note it.
    """
    if len(diff) <= max_chars:
        return diff
    return diff[:max_chars] + "\n\n...[diff truncated at {} chars]\n".format(max_chars)
