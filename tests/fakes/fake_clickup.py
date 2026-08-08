from pmagent.domain.models import Task, TaskStatus


class FakeClickUpClient:
    def __init__(
        self,
        tasks: list[Task] | None = None,
        spaces: dict[str, list[dict]] | None = None,
        lists: dict[str, list[dict]] | None = None,
    ) -> None:
        self._tasks: dict[str, Task] = {}
        self._comments: dict[str, list[str]] = {}
        self._status_changes: list[tuple[str, str]] = []
        self._priorities: dict[str, str | None] = {}
        self._spaces = spaces or {}
        self._lists = lists or {}
        if tasks:
            for task in tasks:
                self._tasks[task.id] = task

    def get_tasks(self, list_id: str) -> list[Task]:
        return [t for t in self._tasks.values() if t.clickup_list_id == list_id]

    def get_task(self, task_id: str) -> Task:
        if task_id not in self._tasks:
            raise RuntimeError(f"Task {task_id} not found")
        return self._tasks[task_id]

    def create_task(
        self, list_id: str, title: str, description: str, priority: str | None = None
    ) -> Task:
        import uuid
        task_id = f"CU-{uuid.uuid4().hex[:8]}"
        task = Task(id=task_id, title=title, status=TaskStatus.BACKLOG, clickup_list_id=list_id)
        self._tasks[task_id] = task
        self._priorities[task_id] = priority
        return task

    def get_spaces(self, team_id: str) -> list[dict]:
        return list(self._spaces.get(team_id, []))

    def get_lists(self, space_id: str) -> list[dict]:
        return list(self._lists.get(space_id, []))

    def update_task_status(self, task_id: str, status: str) -> None:
        if task_id not in self._tasks:
            raise RuntimeError(f"Task {task_id} not found")
        self._status_changes.append((task_id, status))
        self._tasks[task_id].status = TaskStatus(status)

    def add_comment(self, task_id: str, comment: str) -> None:
        if task_id not in self._comments:
            self._comments[task_id] = []
        self._comments[task_id].append(comment)

    def search_tasks(self, workspace_id: str, query: str) -> list[Task]:
        return [t for t in self._tasks.values() if query.lower() in t.title.lower()]

    @property
    def comments(self) -> dict[str, list[str]]:
        return self._comments

    @property
    def status_changes(self) -> list[tuple[str, str]]:
        return self._status_changes

    @property
    def priorities(self) -> dict[str, str | None]:
        return self._priorities
