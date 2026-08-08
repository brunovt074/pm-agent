from pmagent.application.create_tasks_from_spec import (
    create_tasks_from_spec,
    parse_spec_tasks,
)
from fakes.fake_clickup import FakeClickUpClient


_SPEC_CONTENT = """
# Feature: User Authentication

## Tasks
- [ ] Create login form UI
- [ ] Implement JWT token generation
- [ ] Add password reset flow
"""

_SPEC_WITH_SECTIONS = """
# Feature: User Dashboard

## Backend Tasks
- [ ] Create dashboard API endpoint
- [ ] Add metrics aggregation service

## Frontend Tasks
- [ ] Build dashboard component
- [ ] Add chart library integration
"""


class TestParseSpecTasks:
    def test_parses_checkbox_items(self):
        tasks = parse_spec_tasks(_SPEC_CONTENT)
        assert len(tasks) == 3
        assert tasks[0]["title"] == "Create login form UI"
        assert tasks[1]["title"] == "Implement JWT token generation"
        assert tasks[2]["title"] == "Add password reset flow"

    def test_empty_spec_returns_empty_list(self):
        tasks = parse_spec_tasks("# No tasks here\n\nJust some text.")
        assert tasks == []

    def test_parses_from_sections(self):
        tasks = parse_spec_tasks(_SPEC_WITH_SECTIONS)
        assert len(tasks) == 4
        assert "dashboard API endpoint" in tasks[0]["title"]
        assert "dashboard component" in tasks[2]["title"]


class TestCreateTasksFromSpec:
    def test_creates_tasks_in_clickup(self):
        fake_clickup = FakeClickUpClient()
        tasks = parse_spec_tasks(_SPEC_CONTENT)

        results = create_tasks_from_spec(
            clickup_list_id="123",
            tasks=tasks,
            clickup_client=fake_clickup,
        )

        assert len(results) == 3
        all_tasks = fake_clickup.get_tasks("123")
        assert len(all_tasks) == 3
        assert all_tasks[0].title == "Create login form UI"

    def test_returns_created_task_ids(self):
        fake_clickup = FakeClickUpClient()
        tasks = parse_spec_tasks(_SPEC_WITH_SECTIONS)

        results = create_tasks_from_spec(
            clickup_list_id="123",
            tasks=tasks,
            clickup_client=fake_clickup,
        )

        assert len(results) == 4
        assert all(r.startswith("CU-") for r in results)

    def test_propagates_priority_to_every_created_task(self):
        fake_clickup = FakeClickUpClient()
        tasks = parse_spec_tasks(_SPEC_CONTENT)

        results = create_tasks_from_spec(
            clickup_list_id="123",
            tasks=tasks,
            clickup_client=fake_clickup,
            priority="high",
        )

        assert all(fake_clickup.priorities[task_id] == "high" for task_id in results)

    def test_defaults_to_no_priority(self):
        fake_clickup = FakeClickUpClient()
        tasks = parse_spec_tasks(_SPEC_CONTENT)

        results = create_tasks_from_spec(
            clickup_list_id="123",
            tasks=tasks,
            clickup_client=fake_clickup,
        )

        assert all(fake_clickup.priorities[task_id] is None for task_id in results)
