class PmAgentError(Exception):
    pass


class ConfigNotFoundError(PmAgentError):
    def __init__(self, path: str = ".pm-agent.yaml") -> None:
        super().__init__(f"Configuration not found at {path}")


class ClickUpApiError(PmAgentError):
    def __init__(self, status_code: int, response_body: str) -> None:
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(f"ClickUp API error {status_code}: {response_body}")


class SyncError(PmAgentError):
    def __init__(self, project_name: str, detail: str) -> None:
        self.project_name = project_name
        self.detail = detail
        super().__init__(f"Sync error in {project_name}: {detail}")
