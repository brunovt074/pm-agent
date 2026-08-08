from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class TaskStatus(StrEnum):
    BACKLOG = "backlog"
    IN_PROGRESS = "in progress"
    IN_REVIEW = "in review"
    COMPLETE = "complete"


class SyncDirection(StrEnum):
    CLICKUP_TO_GIT = "clickup_to_git"
    GIT_TO_CLICKUP = "git_to_clickup"
    BIDIRECTIONAL = "bidirectional"


class CommitRef(BaseModel):
    sha: str
    message: str
    timestamp: datetime

    @field_validator("timestamp", mode="before")
    @classmethod
    def _default_tz(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

    @property
    def conventional_type(self) -> str | None:
        valid = {"feat", "fix", "chore", "docs", "refactor", "test", "style", "perf", "ci", "build"}
        parts = self.message.split(":", 1)
        if len(parts) >= 2 and parts[0].strip() in valid:
            return parts[0].strip()
        return None


class Task(BaseModel):
    id: str
    title: str
    status: TaskStatus
    clickup_list_id: str
    branch_name: str | None = None
    pr_url: str | None = None
    commits: list[CommitRef] = Field(default_factory=list)
    last_synced: datetime | None = None


class StatusMapping(BaseModel):
    branch_state: str
    action: str


class MappingsConfig(BaseModel):
    lists: list[dict]
    statuses: dict[str, StatusMapping] = Field(default_factory=dict)
    commit_patterns: dict
    branch_pattern: str = "{type}/{task_id}-{slug}"
    webhooks: dict[str, str] = Field(default_factory=dict)


class Project(BaseModel):
    name: str
    clickup_workspace_id: str
    git_root: Path
    mappings: MappingsConfig


class SyncRule(BaseModel):
    direction: SyncDirection
    trigger: str
    status_mapping: dict[str, str] = Field(default_factory=dict)


class SyncEvent(BaseModel):
    type: str
    source: str
    project_name: str
    task_id: str | None = None
    payload: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
