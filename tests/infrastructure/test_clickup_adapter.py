import pytest

from pmagent.domain.errors import ClickUpApiError
from pmagent.domain.models import TaskStatus
from pmagent.infrastructure.clickup_adapter import ClickUpAdapter


class TestClickUpAdapter:
    def test_get_tasks_parses_response(self, httpx_mock):
        httpx_mock.add_response(
            url="https://api.clickup.com/api/v2/list/123/task",
            json={
                "tasks": [
                    {
                        "id": "abc123",
                        "name": "Add login page",
                        "status": {"status": "in progress"},
                        "list": {"id": "123"},
                    }
                ]
            },
        )

        adapter = ClickUpAdapter(api_token="pk_test")
        tasks = adapter.get_tasks("123")

        assert len(tasks) == 1
        assert tasks[0].id == "CU-abc123"
        assert tasks[0].title == "Add login page"
        assert tasks[0].status == TaskStatus.IN_PROGRESS
        assert tasks[0].clickup_list_id == "123"

    def test_get_tasks_empty_list(self, httpx_mock):
        httpx_mock.add_response(
            url="https://api.clickup.com/api/v2/list/456/task",
            json={"tasks": []},
        )

        adapter = ClickUpAdapter(api_token="pk_test")
        tasks = adapter.get_tasks("456")

        assert tasks == []

    def test_get_task_by_id(self, httpx_mock):
        httpx_mock.add_response(
            url="https://api.clickup.com/api/v2/task/abc123",
            json={
                "id": "abc123",
                "name": "Fix login bug",
                "status": {"status": "in review"},
                "list": {"id": "123"},
            },
        )

        adapter = ClickUpAdapter(api_token="pk_test")
        task = adapter.get_task("CU-abc123")

        assert task.id == "CU-abc123"
        assert task.title == "Fix login bug"
        assert task.status == TaskStatus.IN_REVIEW

    def test_get_task_strips_cu_prefix(self, httpx_mock):
        httpx_mock.add_response(
            url="https://api.clickup.com/api/v2/task/abc123",
            json={
                "id": "abc123",
                "name": "Fix login bug",
                "status": {"status": "backlog"},
                "list": {"id": "123"},
            },
        )

        adapter = ClickUpAdapter(api_token="pk_test")
        task = adapter.get_task("CU-abc123")
        assert task.id == "CU-abc123"

    def test_create_task(self, httpx_mock):
        httpx_mock.add_response(
            url="https://api.clickup.com/api/v2/list/123/task",
            json={
                "id": "def456",
                "name": "New feature",
                "status": {"status": "backlog"},
                "list": {"id": "123"},
            },
        )

        adapter = ClickUpAdapter(api_token="pk_test")
        task = adapter.create_task("123", "New feature", "Implement the thing")

        assert task.id == "CU-def456"
        assert task.title == "New feature"
        assert task.status == TaskStatus.BACKLOG
        assert task.clickup_list_id == "123"

    def test_create_task_without_priority_omits_key_from_payload(self, httpx_mock):
        httpx_mock.add_response(
            url="https://api.clickup.com/api/v2/list/123/task",
            json={
                "id": "def456",
                "name": "New feature",
                "status": {"status": "backlog"},
                "list": {"id": "123"},
            },
        )

        adapter = ClickUpAdapter(api_token="pk_test")
        adapter.create_task("123", "New feature", "Implement the thing")

        sent_request = httpx_mock.get_requests()[0]
        assert "priority" not in sent_request.read().decode()

    def test_create_task_converts_priority_name_to_level(self, httpx_mock):
        httpx_mock.add_response(
            url="https://api.clickup.com/api/v2/list/123/task",
            json={
                "id": "def456",
                "name": "New feature",
                "status": {"status": "backlog"},
                "list": {"id": "123"},
            },
        )

        adapter = ClickUpAdapter(api_token="pk_test")
        adapter.create_task("123", "New feature", "Implement the thing", priority="urgent")

        sent_request = httpx_mock.get_requests()[0]
        assert b'"priority":1' in sent_request.read()

    @pytest.mark.parametrize(
        "priority_name,expected_level",
        [("urgent", 1), ("high", 2), ("normal", 3), ("low", 4), ("HIGH", 2)],
    )
    def test_create_task_priority_levels(self, httpx_mock, priority_name, expected_level):
        httpx_mock.add_response(
            url="https://api.clickup.com/api/v2/list/123/task",
            json={
                "id": "def456",
                "name": "New feature",
                "status": {"status": "backlog"},
                "list": {"id": "123"},
            },
        )

        adapter = ClickUpAdapter(api_token="pk_test")
        adapter.create_task("123", "New feature", "Implement the thing", priority=priority_name)

        sent_request = httpx_mock.get_requests()[0]
        assert f'"priority":{expected_level}'.encode() in sent_request.read()

    def test_create_task_raises_on_invalid_priority(self):
        adapter = ClickUpAdapter(api_token="pk_test")
        with pytest.raises(ValueError):
            adapter.create_task("123", "New feature", "Implement the thing", priority="asap")

    def test_get_spaces_parses_response(self, httpx_mock):
        httpx_mock.add_response(
            url="https://api.clickup.com/api/v2/team/90123456/space?archived=false",
            json={"spaces": [{"id": "space1", "name": "Engineering"}]},
        )

        adapter = ClickUpAdapter(api_token="pk_test")
        spaces = adapter.get_spaces("90123456")

        assert spaces == [{"id": "space1", "name": "Engineering"}]

    def test_get_lists_parses_response(self, httpx_mock):
        httpx_mock.add_response(
            url="https://api.clickup.com/api/v2/space/space1/list?archived=false",
            json={"lists": [{"id": "123", "name": "Backlog"}]},
        )

        adapter = ClickUpAdapter(api_token="pk_test")
        lists = adapter.get_lists("space1")

        assert lists == [{"id": "123", "name": "Backlog"}]

    def test_update_task_status(self, httpx_mock):
        httpx_mock.add_response(
            url="https://api.clickup.com/api/v2/task/abc123",
            json={},
        )

        adapter = ClickUpAdapter(api_token="pk_test")
        adapter.update_task_status("CU-abc123", "complete")

    def test_add_comment(self, httpx_mock):
        httpx_mock.add_response(
            url="https://api.clickup.com/api/v2/task/abc123/comment",
            json={},
        )

        adapter = ClickUpAdapter(api_token="pk_test")
        adapter.add_comment("CU-abc123", "PR #42 merged")

    def test_search_tasks(self, httpx_mock):
        httpx_mock.add_response(
            url="https://api.clickup.com/api/v2/team/ws123/task",
            json={
                "tasks": [
                    {"id": "abc123", "name": "Add login", "status": {"status": "in progress"}, "list": {"id": "123"}},
                ]
            },
        )

        adapter = ClickUpAdapter(api_token="pk_test")
        tasks = adapter.search_tasks("ws123", "login")

        assert len(tasks) == 1
        assert tasks[0].id == "CU-abc123"

    def test_raises_on_api_error(self, httpx_mock):
        httpx_mock.add_response(
            url="https://api.clickup.com/api/v2/list/123/task",
            status_code=401,
            json={"err": "unauthorized"},
        )

        adapter = ClickUpAdapter(api_token="pk_test")
        with pytest.raises(ClickUpApiError) as exc:
            adapter.get_tasks("123")
        assert exc.value.status_code == 401
