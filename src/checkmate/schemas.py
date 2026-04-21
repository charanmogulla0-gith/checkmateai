from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["high", "medium", "low"]
Category = Literal[
    "bug", "security", "performance", "concurrency", "error-handling", "api", "maintainability"
]


class Finding(BaseModel):
    file: str
    line: int = Field(ge=1)
    severity: Severity
    category: Category
    comment: str


class Review(BaseModel):
    summary: str
    findings: list[Finding] = Field(default_factory=list)


class ReviewJob(BaseModel):
    installation_id: int
    repo_full_name: str
    pr_number: int
    head_sha: str
    base_sha: str
