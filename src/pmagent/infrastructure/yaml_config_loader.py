import os
import re
from pathlib import Path

import yaml

from pmagent.domain.errors import ConfigNotFoundError
from pmagent.domain.models import MappingsConfig, Project, StatusMapping


class YamlConfigLoader:
    _CONFIG_FILE = ".pm-agent.yaml"

    def load(self, path: Path | None) -> Project:
        if path is None:
            path = self.find_config(None)
            if path is None:
                raise ConfigNotFoundError()
        if not path.exists():
            raise ConfigNotFoundError(str(path))
        raw = yaml.safe_load(path.read_text())
        return self._parse(raw, path)

    def find_config(self, start_dir: Path | None) -> Path | None:
        current = start_dir or Path.cwd()
        current = current.resolve()
        while True:
            candidate = current / self._CONFIG_FILE
            if candidate.exists():
                return candidate
            parent = current.parent
            if parent == current:
                return None
            current = parent

    def _parse(self, raw: dict, path: Path) -> Project:
        proj = raw["project"]
        mappings_raw = raw.get("mappings", {})
        statuses_raw = mappings_raw.get("statuses", {})
        statuses = {k: StatusMapping(**v) for k, v in statuses_raw.items()}

        webhooks_raw = mappings_raw.get("webhooks", {})
        webhooks_resolved = {
            k: self._resolve_env(v) for k, v in webhooks_raw.items()
        }

        mappings = MappingsConfig(
            lists=mappings_raw.get("lists", []),
            statuses=statuses,
            commit_patterns=mappings_raw.get("commit_patterns", {}),
            branch_pattern=mappings_raw.get("branch_pattern", "{type}/{task_id}-{slug}"),
            webhooks=webhooks_resolved,
        )

        git_root = path.parent if proj.get("git_root", ".") == "." else Path(proj["git_root"])

        return Project(
            name=proj["name"],
            clickup_workspace_id=proj["clickup_workspace_id"],
            git_root=git_root,
            mappings=mappings,
        )

    def _resolve_env(self, value: str) -> str:
        pattern = re.compile(r"\$\{(\w+)\}")

        def _replace(match: re.Match) -> str:
            return os.environ.get(match.group(1), "")

        return pattern.sub(_replace, value)
