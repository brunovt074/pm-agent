from pathlib import Path
import yaml

from pmagent.interfaces.mcp_server import (
    _sync_project,
    _link_branch,
    _status_report,
    _comment_on_task,
    _configure_project,
    _listen_status,
    _create_task,
    _get_spaces,
    _get_lists,
)
from pmagent.container import Container
from pmagent.domain.models import Task, TaskStatus
from fakes.fake_clickup import FakeClickUpClient
from fakes.fake_git import FakeGitRunner
from pmagent.infrastructure.git_adapter import GitAdapter


_VALID_CONFIG = {
    "project": {
        "name": "test-project",
        "clickup_workspace_id": "90123456",
        "git_root": ".",
    },
    "mappings": {
        "lists": [
            {"clickup_list_id": "123", "clickup_list_name": "Backlog", "convention": "feature,fix"}
        ],
        "statuses": {
            "in progress": {"branch_state": "active", "action": "create_branch"},
            "in review": {"branch_state": "pr_open", "action": "create_pr"},
            "complete": {"branch_state": "merged", "action": "none"},
        },
        "commit_patterns": {
            "task_id": "CU-[a-z0-9]+",
            "conventional": ["feat", "fix"],
        },
        "branch_pattern": "{type}/{task_id}-{slug}",
    },
}


class TestSyncProjectTool:
    def test_sync_returns_summary(self, tmp_path: Path, monkeypatch):
        config_file = tmp_path / ".pm-agent.yaml"
        config_file.write_text(yaml.dump(_VALID_CONFIG))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("CLICKUP_API_TOKEN", "pk_test")

        container = Container()
        container._project = container._config_loader.load(config_file)

        fake_clickup = FakeClickUpClient(tasks=[
            Task(id="CU-abc123", title="Add login", status=TaskStatus.BACKLOG, clickup_list_id="123"),
        ])
        fake_git = FakeGitRunner(
            current_branch="feature/CU-abc123-login",
            branches=["main", "feature/CU-abc123-login"],
        )

        from pmagent.infrastructure.clickup_adapter import ClickUpAdapter
        container._clickup = ClickUpAdapter.__new__(ClickUpAdapter)
        container._clickup.get_tasks = fake_clickup.get_tasks
        container._clickup.get_task = fake_clickup.get_task
        container._clickup.add_comment = fake_clickup.add_comment
        container._clickup.update_task_status = fake_clickup.update_task_status
        container._git = GitAdapter(runner=fake_git.run)

        result = _sync_project(container, "full")

        assert "sync" in result.lower() or "Sync" in result

    def test_sync_directional(self, tmp_path: Path, monkeypatch):
        config_file = tmp_path / ".pm-agent.yaml"
        config_file.write_text(yaml.dump(_VALID_CONFIG))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("CLICKUP_API_TOKEN", "pk_test")

        container = Container()
        container._project = container._config_loader.load(config_file)

        fake_clickup = FakeClickUpClient(tasks=[
            Task(id="CU-abc123", title="Add login", status=TaskStatus.IN_PROGRESS, clickup_list_id="123"),
        ])
        fake_git = FakeGitRunner(current_branch="main", branches=["main"])

        from pmagent.infrastructure.clickup_adapter import ClickUpAdapter
        container._clickup = ClickUpAdapter.__new__(ClickUpAdapter)
        container._clickup.get_tasks = fake_clickup.get_tasks
        container._git = GitAdapter(runner=fake_git.run)

        result = _sync_project(container, "clickup_to_git")
        assert "sugerencia" in result.lower() or "suggestion" in result.lower() or "branch" in result.lower()


class TestLinkBranchTool:
    def test_link_branch_returns_confirmation(self, tmp_path: Path, monkeypatch):
        config_file = tmp_path / ".pm-agent.yaml"
        config_file.write_text(yaml.dump(_VALID_CONFIG))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("CLICKUP_API_TOKEN", "pk_test")

        container = Container()
        container._project = container._config_loader.load(config_file)

        fake_clickup = FakeClickUpClient(tasks=[
            Task(id="CU-abc123", title="Add login", status=TaskStatus.BACKLOG, clickup_list_id="123"),
        ])

        from pmagent.infrastructure.clickup_adapter import ClickUpAdapter
        container._clickup = ClickUpAdapter.__new__(ClickUpAdapter)
        container._clickup.update_task_status = fake_clickup.update_task_status
        container._clickup.add_comment = fake_clickup.add_comment

        result = _link_branch(container, "CU-abc123", "feature/CU-abc123-login")
        assert "CU-abc123" in result
        assert "feature/CU-abc123-login" in result


class TestStatusReportTool:
    def test_status_report_text(self, tmp_path: Path, monkeypatch):
        config_file = tmp_path / ".pm-agent.yaml"
        config_file.write_text(yaml.dump(_VALID_CONFIG))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("CLICKUP_API_TOKEN", "pk_test")

        container = Container()
        container._project = container._config_loader.load(config_file)

        fake_clickup = FakeClickUpClient(tasks=[
            Task(id="CU-abc123", title="Add login", status=TaskStatus.IN_PROGRESS, clickup_list_id="123"),
        ])
        fake_git = FakeGitRunner(
            current_branch="feature/CU-abc123-login",
            branches=["main", "feature/CU-abc123-login"],
        )

        from pmagent.infrastructure.clickup_adapter import ClickUpAdapter
        container._clickup = ClickUpAdapter.__new__(ClickUpAdapter)
        container._clickup.get_tasks = fake_clickup.get_tasks
        container._git = GitAdapter(runner=fake_git.run)

        result = _status_report(container, "text")
        assert "test-project" in result


class TestCommentOnTaskTool:
    def test_comment_returns_confirmation(self, tmp_path: Path, monkeypatch):
        config_file = tmp_path / ".pm-agent.yaml"
        config_file.write_text(yaml.dump(_VALID_CONFIG))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("CLICKUP_API_TOKEN", "pk_test")

        container = Container()
        container._project = container._config_loader.load(config_file)

        fake_clickup = FakeClickUpClient(tasks=[
            Task(id="CU-abc123", title="Test", status=TaskStatus.IN_PROGRESS, clickup_list_id="123"),
        ])

        from pmagent.infrastructure.clickup_adapter import ClickUpAdapter
        container._clickup = ClickUpAdapter.__new__(ClickUpAdapter)
        container._clickup.add_comment = fake_clickup.add_comment

        result = _comment_on_task(container, "CU-abc123", "PR #42 merged")
        assert "ment" in result

    def test_comment_requires_task_id(self, tmp_path: Path, monkeypatch):
        config_file = tmp_path / ".pm-agent.yaml"
        config_file.write_text(yaml.dump(_VALID_CONFIG))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("CLICKUP_API_TOKEN", "pk_test")

        container = Container()
        container._project = container._config_loader.load(config_file)

        result = _comment_on_task(container, "", "some comment")
        assert "error" in result.lower() or "task_id" in result.lower()


class TestConfigureProjectTool:
    def test_configure_returns_instructions(self):
        result = _configure_project()
        assert ".pm-agent.yaml" in result
        assert "CLICKUP_API_TOKEN" in result


class TestListenStatusTool:
    def test_listen_status_returns_status(self):
        result = _listen_status("status")
        assert "listener" in result.lower()


class TestCreateTaskTool:
    def test_create_task_returns_confirmation(self, tmp_path: Path, monkeypatch):
        config_file = tmp_path / ".pm-agent.yaml"
        config_file.write_text(yaml.dump(_VALID_CONFIG))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("CLICKUP_API_TOKEN", "pk_test")

        container = Container()
        container._project = container._config_loader.load(config_file)

        fake_clickup = FakeClickUpClient()
        from pmagent.infrastructure.clickup_adapter import ClickUpAdapter
        container._clickup = ClickUpAdapter.__new__(ClickUpAdapter)
        container._clickup.create_task = fake_clickup.create_task

        result = _create_task(container, "123", "New task", "Some description", "high")

        assert "123" in result
        created_task_id = next(iter(fake_clickup.priorities))
        assert fake_clickup.priorities[created_task_id] == "high"

    def test_create_task_without_priority(self, tmp_path: Path, monkeypatch):
        config_file = tmp_path / ".pm-agent.yaml"
        config_file.write_text(yaml.dump(_VALID_CONFIG))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("CLICKUP_API_TOKEN", "pk_test")

        container = Container()
        container._project = container._config_loader.load(config_file)

        fake_clickup = FakeClickUpClient()
        from pmagent.infrastructure.clickup_adapter import ClickUpAdapter
        container._clickup = ClickUpAdapter.__new__(ClickUpAdapter)
        container._clickup.create_task = fake_clickup.create_task

        result = _create_task(container, "123", "New task", "Some description")

        assert "New task" in result
        created_task_id = next(iter(fake_clickup.priorities))
        assert fake_clickup.priorities[created_task_id] is None


class TestGetSpacesTool:
    def test_get_spaces_lists_spaces_for_given_team(self, tmp_path: Path, monkeypatch):
        config_file = tmp_path / ".pm-agent.yaml"
        config_file.write_text(yaml.dump(_VALID_CONFIG))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("CLICKUP_API_TOKEN", "pk_test")

        container = Container()
        container._project = container._config_loader.load(config_file)

        fake_clickup = FakeClickUpClient(spaces={"90123456": [{"id": "space1", "name": "Engineering"}]})
        from pmagent.infrastructure.clickup_adapter import ClickUpAdapter
        container._clickup = ClickUpAdapter.__new__(ClickUpAdapter)
        container._clickup.get_spaces = fake_clickup.get_spaces

        result = _get_spaces(container, "90123456")

        assert "space1" in result
        assert "Engineering" in result

    def test_get_spaces_falls_back_to_configured_team_id(self, tmp_path: Path, monkeypatch):
        config_file = tmp_path / ".pm-agent.yaml"
        config_file.write_text(yaml.dump(_VALID_CONFIG))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("CLICKUP_API_TOKEN", "pk_test")
        monkeypatch.setenv("CLICKUP_TEAM_ID", "90123456")

        container = Container()
        container._project = container._config_loader.load(config_file)

        fake_clickup = FakeClickUpClient(spaces={"90123456": [{"id": "space1", "name": "Engineering"}]})
        from pmagent.infrastructure.clickup_adapter import ClickUpAdapter
        container._clickup = ClickUpAdapter.__new__(ClickUpAdapter)
        container._clickup.get_spaces = fake_clickup.get_spaces

        result = _get_spaces(container, None)

        assert "space1" in result

    def test_get_spaces_requires_team_id_when_none_configured(self, tmp_path: Path, monkeypatch):
        config_file = tmp_path / ".pm-agent.yaml"
        config_file.write_text(yaml.dump(_VALID_CONFIG))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("CLICKUP_API_TOKEN", "pk_test")
        monkeypatch.delenv("CLICKUP_TEAM_ID", raising=False)

        container = Container()
        container._project = container._config_loader.load(config_file)

        result = _get_spaces(container, None)

        assert "error" in result.lower() or "team_id" in result.lower()


class TestGetListsTool:
    def test_get_lists_lists_lists_for_given_space(self, tmp_path: Path, monkeypatch):
        config_file = tmp_path / ".pm-agent.yaml"
        config_file.write_text(yaml.dump(_VALID_CONFIG))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("CLICKUP_API_TOKEN", "pk_test")

        container = Container()
        container._project = container._config_loader.load(config_file)

        fake_clickup = FakeClickUpClient(lists={"space1": [{"id": "123", "name": "Backlog"}]})
        from pmagent.infrastructure.clickup_adapter import ClickUpAdapter
        container._clickup = ClickUpAdapter.__new__(ClickUpAdapter)
        container._clickup.get_lists = fake_clickup.get_lists

        result = _get_lists(container, "space1")

        assert "123" in result
        assert "Backlog" in result
