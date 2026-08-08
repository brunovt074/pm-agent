import json
from pathlib import Path

from pmagent.application.generate_status_report import generate_status_report
from pmagent.domain.models import (
    MappingsConfig,
    Project,
    Task,
    TaskStatus,
)
from fakes.fake_clickup import FakeClickUpClient
from fakes.fake_git import FakeGitRunner
from pmagent.infrastructure.git_adapter import GitAdapter


def _project() -> Project:
    return Project(
        name="test-project",
        clickup_workspace_id="ws123",
        git_root=Path("/tmp"),
        mappings=MappingsConfig(
            lists=[
                {"clickup_list_id": "123", "clickup_list_name": "Backlog", "convention": "feature,fix"},
            ],
            statuses={},
            commit_patterns={"task_id": "CU-[a-z0-9]+", "conventional": ["feat", "fix"]},
            branch_pattern="{type}/{task_id}-{slug}",
        ),
    )


class TestGenerateStatusReport:
    def test_text_report_includes_project_name(self):
        project = _project()
        fake_clickup = FakeClickUpClient(tasks=[
            Task(id="CU-abc123", title="Add login", status=TaskStatus.IN_PROGRESS, clickup_list_id="123"),
        ])
        fake_git = FakeGitRunner(
            current_branch="feature/CU-abc123-login",
            branches=["main", "feature/CU-abc123-login"],
            commits=[
                {"sha": "abc", "message": "CU-abc123 feat: add login form", "date": "2026-01-01T00:00:00Z"},
            ],
        )

        report = generate_status_report(
            project=project,
            clickup=FakeClickUpClient,
            git=GitAdapter(runner=fake_git.run),
            clickup_tasks=fake_clickup.get_tasks("123"),
            format="text",
        )

        assert "test-project" in report
        assert "Add login" in report
        assert "abc" in report

    def test_json_report_has_tasks_and_branches(self):
        project = _project()
        fake_clickup = FakeClickUpClient(tasks=[
            Task(id="CU-abc123", title="Add login", status=TaskStatus.IN_PROGRESS, clickup_list_id="123"),
            Task(id="CU-def456", title="Fix crash", status=TaskStatus.BACKLOG, clickup_list_id="124"),
        ])
        fake_git = FakeGitRunner(
            current_branch="feature/CU-abc123-login",
            branches=["main", "feature/CU-abc123-login"],
        )

        report = generate_status_report(
            project=project,
            clickup=FakeClickUpClient,
            git=GitAdapter(runner=fake_git.run),
            clickup_tasks=fake_clickup.get_tasks("123") + fake_clickup.get_tasks("124"),
            format="json",
        )

        data = json.loads(report)
        assert data["project"] == "test-project"
        assert len(data["tasks"]) == 2
        assert len(data["branches"]) == 2

    def test_text_report_with_no_tasks(self):
        project = _project()
        fake_git = FakeGitRunner(current_branch="main", branches=["main"])

        report = generate_status_report(
            project=project,
            clickup=FakeClickUpClient,
            git=GitAdapter(runner=fake_git.run),
            clickup_tasks=[],
            format="text",
        )

        assert "test-project" in report
