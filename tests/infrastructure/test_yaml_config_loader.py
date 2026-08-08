from pathlib import Path
import yaml

from pmagent.infrastructure.yaml_config_loader import YamlConfigLoader


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
            "conventional": ["feat", "fix", "chore", "docs", "refactor", "test"],
        },
        "branch_pattern": "{type}/{task_id}-{slug}",
    },
}


class TestYamlConfigLoader:
    def test_loads_valid_config(self, tmp_path: Path):
        config_file = tmp_path / ".pm-agent.yaml"
        config_file.write_text(yaml.dump(_VALID_CONFIG))

        loader = YamlConfigLoader()
        project = loader.load(config_file)

        assert project.name == "test-project"
        assert project.clickup_workspace_id == "90123456"
        assert len(project.mappings.lists) == 1
        assert project.mappings.lists[0]["clickup_list_id"] == "123"
        assert len(project.mappings.statuses) == 3
        assert project.mappings.branch_pattern == "{type}/{task_id}-{slug}"

    def test_find_config_in_current_dir(self, tmp_path: Path, monkeypatch):
        config_file = tmp_path / ".pm-agent.yaml"
        config_file.write_text(yaml.dump(_VALID_CONFIG))
        monkeypatch.chdir(tmp_path)

        loader = YamlConfigLoader()
        found = loader.find_config(None)

        assert found == config_file.resolve()

    def test_find_config_walks_up(self, tmp_path: Path):
        config_file = tmp_path / ".pm-agent.yaml"
        config_file.write_text(yaml.dump(_VALID_CONFIG))
        subdir = tmp_path / "sub" / "deep"
        subdir.mkdir(parents=True)

        loader = YamlConfigLoader()
        found = loader.find_config(subdir)

        assert found == config_file.resolve()

    def test_raises_when_config_not_found(self, tmp_path: Path):
        loader = YamlConfigLoader()
        path = tmp_path / "nonexistent.yaml"
        from pmagent.domain.errors import ConfigNotFoundError

        try:
            loader.load(path)
            assert False, "expected ConfigNotFoundError"
        except ConfigNotFoundError as e:
            assert "nonexistent.yaml" in str(e)

    def test_find_config_returns_none_when_not_found(self, tmp_path: Path):
        loader = YamlConfigLoader()
        result = loader.find_config(tmp_path)
        assert result is None

    def test_handles_missing_webhooks_section(self, tmp_path: Path):
        config_without_webhooks = {
            "project": {
                "name": "test-project",
                "clickup_workspace_id": "90123456",
                "git_root": ".",
            },
            "mappings": {
                "lists": [],
                "statuses": {},
                "commit_patterns": {"task_id": "CU-[a-z0-9]+", "conventional": []},
                "branch_pattern": "{type}/{task_id}-{slug}",
            },
        }
        config_file = tmp_path / ".pm-agent.yaml"
        config_file.write_text(yaml.dump(config_without_webhooks))

        loader = YamlConfigLoader()
        project = loader.load(config_file)

        assert project.mappings.webhooks == {}

    def test_resolves_env_vars_in_webhooks(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("GH_SECRET", "my-github-secret")
        config_with_env = dict(_VALID_CONFIG)
        config_with_env["mappings"]["webhooks"] = {"github_secret": "${GH_SECRET}"}

        config_file = tmp_path / ".pm-agent.yaml"
        config_file.write_text(yaml.dump(config_with_env))

        loader = YamlConfigLoader()
        project = loader.load(config_file)

        assert project.mappings.webhooks["github_secret"] == "my-github-secret"
