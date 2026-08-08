from pmagent.config import get_settings, Settings
from pmagent.domain.models import Project
from pmagent.domain.errors import PmAgentError
from pmagent.infrastructure.yaml_config_loader import YamlConfigLoader
from pmagent.infrastructure.clickup_adapter import ClickUpAdapter
from pmagent.infrastructure.git_adapter import GitAdapter


class Container:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._config_loader = YamlConfigLoader()
        self._project: Project | None = None
        self._clickup: ClickUpAdapter | None = None
        self._git: GitAdapter | None = None

    @property
    def project(self) -> Project:
        if self._project is None:
            config_path = self._config_loader.find_config(None)
            if config_path is None:
                raise PmAgentError("No .pm-agent.yaml found. Run configure_project first.")
            self._project = self._config_loader.load(config_path)
        return self._project

    @property
    def clickup(self) -> ClickUpAdapter:
        if self._clickup is None:
            token = self.settings.clickup_api_token
            if not token:
                raise PmAgentError("CLICKUP_API_TOKEN not set")
            self._clickup = ClickUpAdapter(api_token=token)
        return self._clickup

    @property
    def git(self) -> GitAdapter:
        if self._git is None:
            self._git = GitAdapter()
        return self._git
