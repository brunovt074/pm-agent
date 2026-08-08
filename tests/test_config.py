from pmagent.config import get_settings


class TestGetSettings:
    def test_prefers_clickup_api_key_over_clickup_api_token(self, monkeypatch):
        monkeypatch.setenv("CLICKUP_API_KEY", "pk_from_key")
        monkeypatch.setenv("CLICKUP_API_TOKEN", "pk_from_token")

        settings = get_settings()

        assert settings.clickup_api_token == "pk_from_key"

    def test_falls_back_to_clickup_api_token_when_key_missing(self, monkeypatch):
        monkeypatch.delenv("CLICKUP_API_KEY", raising=False)
        monkeypatch.setenv("CLICKUP_API_TOKEN", "pk_from_token")

        settings = get_settings()

        assert settings.clickup_api_token == "pk_from_token"

    def test_defaults_to_empty_string_when_neither_set(self, monkeypatch):
        monkeypatch.delenv("CLICKUP_API_KEY", raising=False)
        monkeypatch.delenv("CLICKUP_API_TOKEN", raising=False)

        settings = get_settings()

        assert settings.clickup_api_token == ""

    def test_reads_clickup_team_id(self, monkeypatch):
        monkeypatch.setenv("CLICKUP_TEAM_ID", "90123456")

        settings = get_settings()

        assert settings.clickup_team_id == "90123456"
