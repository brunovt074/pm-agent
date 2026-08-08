from pathlib import Path
import yaml
import pytest

from pmagent.container import Container
from pmagent.domain.errors import PmAgentError


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


class TestContainer:
    def test_loads_project_from_config(self, tmp_path: Path, monkeypatch):
        config_file = tmp_path / ".pm-agent.yaml"
        config_file.write_text(yaml.dump(_VALID_CONFIG))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("CLICKUP_API_TOKEN", "pk_test")

        container = Container()
        project = container.project

        assert project.name == "test-project"
        assert project.clickup_workspace_id == "90123456"

    def test_clickup_adapter_requires_token(self, tmp_path: Path, monkeypatch):
        config_file = tmp_path / ".pm-agent.yaml"
        config_file.write_text(yaml.dump(_VALID_CONFIG))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("CLICKUP_API_TOKEN", "pk_test123")

        container = Container()
        adapter = container.clickup
        assert adapter is not None

    def test_git_adapter_always_available(self, tmp_path: Path, monkeypatch):
        config_file = tmp_path / ".pm-agent.yaml"
        config_file.write_text(yaml.dump(_VALID_CONFIG))
        monkeypatch.chdir(tmp_path)

        container = Container()
        git = container.git
        assert git is not None

    def test_clickup_raises_without_token(self, tmp_path: Path, monkeypatch):
        config_file = tmp_path / ".pm-agent.yaml"
        config_file.write_text(yaml.dump(_VALID_CONFIG))
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("CLICKUP_API_TOKEN", raising=False)

        container = Container()
        with pytest.raises(PmAgentError):
            _ = container.clickup
