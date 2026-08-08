import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    clickup_api_token: str = ""
    clickup_team_id: str = ""
    clickup_webhook_secret: str = ""
    github_token: str = ""
    github_webhook_secret: str = ""
    log_level: str = "INFO"


def get_settings() -> Settings:
    return Settings(
        clickup_api_token=os.environ.get("CLICKUP_API_KEY") or os.environ.get("CLICKUP_API_TOKEN", ""),
        clickup_team_id=os.environ.get("CLICKUP_TEAM_ID", ""),
        clickup_webhook_secret=os.environ.get("CLICKUP_WEBHOOK_SECRET", ""),
        github_token=os.environ.get("GITHUB_TOKEN", ""),
        github_webhook_secret=os.environ.get("GITHUB_WEBHOOK_SECRET", ""),
        log_level=os.environ.get("PM_AGENT_LOG_LEVEL", "INFO"),
    )
