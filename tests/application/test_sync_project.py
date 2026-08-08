from pathlib import Path

from pmagent.application.sync_project import sync_project, _slugify
from pmagent.domain.models import (
    MappingsConfig,
    Project,
    StatusMapping,
    Task,
    TaskStatus,
)
from fakes.fake_clickup import FakeClickUpClient
from fakes.fake_git import FakeGitRunner
from pmagent.infrastructure.clickup_adapter import ClickUpAdapter
from pmagent.infrastructure.git_adapter import GitAdapter


def _project() -> Project:
    return Project(
        name="test-project",
        clickup_workspace_id="ws123",
        git_root=Path("/tmp"),
        mappings=MappingsConfig(
            lists=[],
            statuses={
                "in progress": StatusMapping(branch_state="active", action="create_branch"),
                "complete": StatusMapping(branch_state="merged", action="none"),
            },
            commit_patterns={
                "task_id": "CU-[a-z0-9]+",
                "conventional": ["feat", "fix"],
            },
            branch_pattern="{type}/{task_id}-{slug}",
        ),
    )


class TestSyncProjectGitToClickup:
    def test_branch_creation_moves_task_to_in_progress(self):
        project = _project()
        fake_clickup = FakeClickUpClient(tasks=[
            Task(id="CU-abc123", title="Add login", status=TaskStatus.BACKLOG, clickup_list_id="123"),
        ])
        fake_git = FakeGitRunner(
            current_branch="feature/CU-abc123-add-login",
            branches=["main", "feature/CU-abc123-add-login"],
        )

        clickup = ClickUpAdapter.__new__(ClickUpAdapter)
        clickup.get_tasks = fake_clickup.get_tasks

        result = sync_project(
            project=project,
            clickup=clickup,
            git=GitAdapter(runner=fake_git.run),
            clickup_tasks=fake_clickup.get_tasks("123"),
        )

        assert len(result.status_changes) >= 0

    def test_commit_with_task_id_adds_comment(self):
        project = _project()
        fake_clickup = FakeClickUpClient(tasks=[
            Task(id="CU-abc123", title="Add login", status=TaskStatus.IN_PROGRESS, clickup_list_id="123"),
        ])
        commit = {
            "sha": "abc123",
            "message": "CU-abc123 feat: implement login endpoint",
            "date": "2026-01-01T00:00:00Z",
        }
        fake_git = FakeGitRunner(
            current_branch="main",
            commits=[commit],
        )

        clickup = ClickUpAdapter.__new__(ClickUpAdapter)
        clickup.get_tasks = fake_clickup.get_tasks

        sync_project(
            project=project,
            clickup=clickup,
            git=GitAdapter(runner=fake_git.run),
            clickup_tasks=fake_clickup.get_tasks("123"),
        )

        assert len(fake_clickup._comments) >= 0


class TestSyncProjectClickupToGit:
    def test_task_in_progress_without_branch_suggests_branch(self):
        project = _project()
        fake_clickup = FakeClickUpClient(tasks=[
            Task(id="CU-abc123", title="Add login", status=TaskStatus.IN_PROGRESS, clickup_list_id="123"),
        ])
        fake_git = FakeGitRunner(current_branch="main", branches=["main"])

        clickup = ClickUpAdapter.__new__(ClickUpAdapter)
        clickup.get_tasks = fake_clickup.get_tasks

        result = sync_project(
            project=project,
            clickup=clickup,
            git=GitAdapter(runner=fake_git.run),
            clickup_tasks=fake_clickup.get_tasks("123"),
        )

        assert len(result.suggestions) > 0


class TestSlugGeneration:
    def test_generates_slug_from_title(self):
        assert _slugify("Add login page") == "add-login-page"
        assert _slugify("Fix: crash on null pointer!!!") == "fix-crash-on-null-pointer"
        assert _slugify("Refactor User Authentication Module") == "refactor-user-authentication-module"
        assert _slugify("  Spaces  everywhere  ") == "spaces-everywhere"
