import httpx
from pmagent.domain.errors import ClickUpApiError
from pmagent.domain.models import Task, TaskStatus


class ClickUpAdapter:
    _BASE_URL = "https://api.clickup.com/api/v2"
    _PRIORITY_LEVELS = {"urgent": 1, "high": 2, "normal": 3, "low": 4}

    def __init__(self, api_token: str) -> None:
        self._client = httpx.Client(
            base_url=self._BASE_URL,
            headers={"Authorization": api_token},
            timeout=30,
        )

    def get_tasks(self, list_id: str) -> list[Task]:
        response = self._client.get(f"/list/{list_id}/task")
        self._check_response(response)
        return [self._parse_task(t) for t in response.json().get("tasks", [])]

    def get_task(self, task_id: str) -> Task:
        clean_id = task_id.replace("CU-", "")
        response = self._client.get(f"/task/{clean_id}")
        self._check_response(response)
        return self._parse_task(response.json())

    def create_task(
        self, list_id: str, title: str, description: str, priority: str | None = None
    ) -> Task:
        payload = {"name": title, "description": description}
        if priority is not None:
            payload["priority"] = self._priority_to_level(priority)
        response = self._client.post(f"/list/{list_id}/task", json=payload)
        self._check_response(response)
        return self._parse_task(response.json())

    def get_spaces(self, team_id: str) -> list[dict]:
        response = self._client.get(f"/team/{team_id}/space", params={"archived": "false"})
        self._check_response(response)
        return [{"id": s["id"], "name": s["name"]} for s in response.json().get("spaces", [])]

    def get_lists(self, space_id: str) -> list[dict]:
        response = self._client.get(f"/space/{space_id}/list", params={"archived": "false"})
        self._check_response(response)
        return [{"id": lst["id"], "name": lst["name"]} for lst in response.json().get("lists", [])]

    def _priority_to_level(self, priority: str) -> int:
        try:
            return self._PRIORITY_LEVELS[priority.lower()]
        except KeyError:
            raise ValueError(f"Invalid priority: {priority}") from None

    def update_task_status(self, task_id: str, status: str) -> None:
        clean_id = task_id.replace("CU-", "")
        response = self._client.put(f"/task/{clean_id}", json={"status": status})
        self._check_response(response)

    def add_comment(self, task_id: str, comment: str) -> None:
        clean_id = task_id.replace("CU-", "")
        response = self._client.post(
            f"/task/{clean_id}/comment",
            json={"comment_text": comment},
        )
        self._check_response(response)

    def search_tasks(self, workspace_id: str, query: str) -> list[Task]:
        response = self._client.get(f"/team/{workspace_id}/task")
        self._check_response(response)
        all_tasks = [self._parse_task(t) for t in response.json().get("tasks", [])]
        return [t for t in all_tasks if query.lower() in t.title.lower()]

    def _parse_task(self, raw: dict) -> Task:
        raw_status = raw.get("status", {}).get("status", "backlog")
        try:
            status = TaskStatus(raw_status)
        except ValueError:
            status = TaskStatus.BACKLOG
        return Task(
            id=f"CU-{raw['id']}",
            title=raw.get("name", ""),
            status=status,
            clickup_list_id=raw.get("list", {}).get("id", ""),
        )

    def _check_response(self, response: httpx.Response) -> None:
        if response.status_code >= 400:
            raise ClickUpApiError(response.status_code, response.text)
