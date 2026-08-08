from pathlib import Path
import yaml

from pmagent.container import Container
from pmagent.interfaces.mcp_server import (
    _sync_project,
    _status_report,
    _comment_on_task,
    _move_task,
    _create_tasks_from_spec,
)
from pmagent.domain.models import Task, TaskStatus
from fakes.fake_clickup import FakeClickUpClient
from fakes.fake_git import FakeGitRunner
from pmagent.infrastructure.clickup_adapter import ClickUpAdapter
from pmagent.infrastructure.git_adapter import GitAdapter


_VALID_CONFIG = {
    "project": {
        "name": "e2e-project",
        "clickup_workspace_id": "90123456",
        "git_root": ".",
    },
    "mappings": {
        "lists": [
            {"clickup_list_id": "123", "clickup_list_name": "Backlog", "convention": "feature,fix"},
            {"clickup_list_id": "124", "clickup_list_name": "Bugs", "convention": "fix,hotfix"},
        ],
        "statuses": {
            "in progress": {"branch_state": "active", "action": "create_branch"},
            "in review": {"branch_state": "pr_open", "action": "create_pr"},
            "complete": {"branch_state": "merged", "action": "none"},
        },
        "commit_patterns": {
            "task_id": "CU-[a-z0-9]+",
            "conventional": ["feat", "fix", "chore", "docs", "refactor", "test"],
        },
        "branch_pattern": "{type}/{task_id}-{slug}",
    },
}


class TestEndToEndFlow:
    def test_full_sync_workflow(self, tmp_path: Path, monkeypatch):
        config_file = tmp_path / ".pm-agent.yaml"
        config_file.write_text(yaml.dump(_VALID_CONFIG))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("CLICKUP_API_TOKEN", "pk_e2e_test")

        container = Container()
        container._project = container._config_loader.load(config_file)

        fake_clickup = FakeClickUpClient(tasks=[
            Task(id="CU-abc123", title="Add login", status=TaskStatus.BACKLOG, clickup_list_id="123"),
            Task(id="CU-def456", title="Fix crash on logout", status=TaskStatus.IN_PROGRESS, clickup_list_id="124"),
        ])
        fake_git = FakeGitRunner(
            current_branch="feature/CU-abc123-add-login",
            branches=["main", "feature/CU-abc123-add-login"],
            commits=[
                {"sha": "abc", "message": "CU-abc123 feat: add login form", "date": "2026-01-01T00:00:00Z"},
                {"sha": "def", "message": "CU-abc123 feat: add auth middleware", "date": "2026-01-02T00:00:00Z"},
            ],
        )

        container._clickup = ClickUpAdapter.__new__(ClickUpAdapter)
        container._clickup.get_tasks = fake_clickup.get_tasks
        container._clickup.get_task = fake_clickup.get_task
        container._clickup.add_comment = fake_clickup.add_comment
        container._clickup.update_task_status = fake_clickup.update_task_status
        container._clickup.create_task = fake_clickup.create_task
        container._git = GitAdapter(runner=fake_git.run)

        sync_result = _sync_project(container, "full")
        assert "e2e-project" in sync_result

        report = _status_report(container, "text")
        assert "e2e-project" in report
        assert "Add login" in report
        assert "Fix crash on logout" in report

        comment_result = _comment_on_task(container, "CU-abc123", "PR #42 merged")
        assert "CU-abc123" in comment_result

        move_result = _move_task(container, "CU-abc123", "complete")
        assert "complete" in move_result

    def test_configure_and_create_tasks_flow(self, tmp_path: Path, monkeypatch):
        config_file = tmp_path / ".pm-agent.yaml"
        config_file.write_text(yaml.dump(_VALID_CONFIG))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("CLICKUP_API_TOKEN", "pk_e2e_test")

        spec_file = tmp_path / "feature-spec.md"
        spec_file.write_text("""
# Feature: User Authentication

## Backend
- [ ] Create POST /login endpoint
- [ ] Implement JWT middleware

## Frontend
- [ ] Build login form component
- [ ] Add auth store (zustand)
        """.strip())

        container = Container()
        container._project = container._config_loader.load(config_file)

        fake_clickup = FakeClickUpClient()
        container._clickup = ClickUpAdapter.__new__(ClickUpAdapter)
        container._clickup.create_task = fake_clickup.create_task
        container._clickup.get_tasks = fake_clickup.get_tasks

        result = _create_tasks_from_spec(container, str(spec_file), "123")
        assert "creadas" in result.lower() or "created" in result.lower() or "crearon" in result.lower()

        all_tasks = fake_clickup.get_tasks("123")
        assert len(all_tasks) == 4

        titles = [t.title for t in all_tasks]
        assert "Create POST /login endpoint" in titles
        assert "Build login form component" in titles
