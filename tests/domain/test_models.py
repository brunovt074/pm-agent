from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from pmagent.domain.errors import (
    PmAgentError,
    ConfigNotFoundError,
    ClickUpApiError,
    SyncError,
)
from pmagent.domain.models import (
    CommitRef,
    MappingsConfig,
    Project,
    StatusMapping,
    SyncDirection,
    SyncEvent,
    SyncRule,
    Task,
    TaskStatus,
)
from pmagent.domain.ports import ClickUpPort, GitPort, ConfigPort


class TestPmAgentError:
    def test_base_error_is_exception(self):
        assert issubclass(PmAgentError, Exception)

    def test_base_error_stores_message(self):
        error = PmAgentError("something went wrong")
        assert str(error) == "something went wrong"


class TestConfigNotFoundError:
    def test_is_pm_agent_error(self):
        assert issubclass(ConfigNotFoundError, PmAgentError)

    def test_default_message(self):
        error = ConfigNotFoundError()
        assert "config" in str(error).lower()

    def test_custom_path(self):
        error = ConfigNotFoundError("/custom/.pm-agent.yaml")
        assert "/custom/.pm-agent.yaml" in str(error)


class TestClickUpApiError:
    def test_is_pm_agent_error(self):
        assert issubclass(ClickUpApiError, PmAgentError)

    def test_stores_status_and_body(self):
        error = ClickUpApiError(404, '{"err":"not found"}')
        assert error.status_code == 404
        assert error.response_body == '{"err":"not found"}'
        assert "404" in str(error)


class TestSyncError:
    def test_is_pm_agent_error(self):
        assert issubclass(SyncError, PmAgentError)

    def test_stores_project_and_detail(self):
        error = SyncError("therapy", "branch not found")
        assert error.project_name == "therapy"
        assert error.detail == "branch not found"


class TestTaskStatus:
    def test_valid_statuses(self):
        assert TaskStatus.BACKLOG == "backlog"
        assert TaskStatus.IN_PROGRESS == "in progress"
        assert TaskStatus.IN_REVIEW == "in review"
        assert TaskStatus.COMPLETE == "complete"


class TestCommitRef:
    def test_minimal_commit(self):
        commit = CommitRef(sha="abc123", message="feat: add login", timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc))
        assert commit.sha == "abc123"
        assert commit.message == "feat: add login"
        assert commit.conventional_type == "feat"

    def test_non_conventional_commit(self):
        commit = CommitRef(sha="def456", message="random fix", timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc))
        assert commit.conventional_type is None

    def test_fix_conventional_commit(self):
        commit = CommitRef(sha="ghi789", message="fix: crash on null", timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc))
        assert commit.conventional_type == "fix"


class TestTask:
    def test_minimal_task(self):
        task = Task(
            id="CU-abc123",
            title="Add login page",
            status=TaskStatus.BACKLOG,
            clickup_list_id="123",
        )
        assert task.id == "CU-abc123"
        assert task.title == "Add login page"
        assert task.status == TaskStatus.BACKLOG
        assert task.branch_name is None
        assert task.pr_url is None
        assert task.commits == []

    def test_task_with_branch(self):
        task = Task(
            id="CU-abc123",
            title="Add login page",
            status=TaskStatus.IN_PROGRESS,
            clickup_list_id="123",
            branch_name="feature/CU-abc123-add-login",
        )
        assert task.branch_name == "feature/CU-abc123-add-login"

    def test_task_serialization(self):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        commit = CommitRef(sha="abc", message="feat: done", timestamp=now)
        task = Task(
            id="CU-abc123",
            title="Add login",
            status=TaskStatus.COMPLETE,
            clickup_list_id="123",
            branch_name="feature/CU-abc123-login",
            pr_url="https://github.com/user/repo/pull/42",
            commits=[commit],
        )
        data = task.model_dump()
        assert data["id"] == "CU-abc123"
        assert len(data["commits"]) == 1


class TestProject:
    def test_minimal_project(self):
        mappings = MappingsConfig(
            lists=[],
            statuses={},
            commit_patterns={"task_id": "CU-[a-z0-9]+", "conventional": []},
            branch_pattern="{type}/{task_id}-{slug}",
        )
        project = Project(
            name="test-project",
            clickup_workspace_id="123",
            git_root=Path("/tmp"),
            mappings=mappings,
        )
        assert project.name == "test-project"
        assert project.clickup_workspace_id == "123"

    def test_project_with_webhooks(self):
        mappings = MappingsConfig(
            lists=[],
            statuses={},
            commit_patterns={"task_id": "CU-[a-z0-9]+", "conventional": []},
            branch_pattern="{type}/{task_id}-{slug}",
            webhooks={"github_secret": "abc", "clickup_secret": "xyz"},
        )
        project = Project(
            name="test-project",
            clickup_workspace_id="123",
            git_root=Path("/tmp"),
            mappings=mappings,
        )
        assert project.mappings.webhooks == {"github_secret": "abc", "clickup_secret": "xyz"}


class TestSyncRule:
    def test_bidirectional_rule(self):
        rule = SyncRule(
            direction=SyncDirection.BIDIRECTIONAL,
            trigger="manual",
            status_mapping={"in progress": "active", "complete": "merged"},
        )
        assert rule.direction == SyncDirection.BIDIRECTIONAL
        assert rule.status_mapping["in progress"] == "active"


class TestSyncEvent:
    def test_branch_created_event(self):
        event = SyncEvent(
            type="branch_created",
            source="github",
            project_name="test-project",
            task_id="CU-abc123",
            payload={"branch": "feature/CU-abc123-login"},
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        assert event.type == "branch_created"
        assert event.source == "github"
        assert event.task_id == "CU-abc123"
        assert event.payload["branch"] == "feature/CU-abc123-login"


class TestStatusMapping:
    def test_status_mapping_from_dict(self):
        mapping = StatusMapping(branch_state="active", action="create_branch")
        assert mapping.branch_state == "active"
        assert mapping.action == "create_branch"


class TestPortsAreProtocols:
    def test_clickup_port_is_protocol(self):
        assert isinstance(ClickUpPort, type)
        assert issubclass(ClickUpPort, Protocol)

    def test_git_port_is_protocol(self):
        assert isinstance(GitPort, type)
        assert issubclass(GitPort, Protocol)

    def test_config_port_is_protocol(self):
        assert isinstance(ConfigPort, type)
        assert issubclass(ConfigPort, Protocol)
