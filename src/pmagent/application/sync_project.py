import re
from dataclasses import dataclass, field

from pmagent.domain.models import Project, Task, TaskStatus


@dataclass(frozen=True)
class SyncResult:
    tasks_synced: int = 0
    branches_linked: int = 0
    status_changes: list[tuple[str, str, str]] = field(default_factory=list)
    comments_added: list[tuple[str, str]] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


def sync_project(
    project: Project,
    clickup: object,
    git: object,
    clickup_tasks: list[Task] | None = None,
) -> SyncResult:
    if clickup_tasks is None:
        list_ids = [lst["clickup_list_id"] for lst in project.mappings.lists]
        clickup_tasks = []
        for lid in list_ids:
            clickup_tasks.extend(clickup.get_tasks(lid))

    task_id_pattern = project.mappings.commit_patterns.get("task_id", "CU-[a-z0-9]+")
    statuses: list[tuple[str, str, str]] = []
    comments: list[tuple[str, str]] = []
    suggestions: list[str] = []
    tasks_synced = 0
    branches_linked = 0

    branches = git.list_branches()
    current_branch = git.current_branch()
    commits = git.recent_commits(current_branch, 20)

    task_by_id = {t.id: t for t in clickup_tasks}
    task_by_branch = _map_branches_to_tasks(branches, task_by_id, task_id_pattern)

    for branch in branches:
        task = task_by_branch.get(branch)
        if task is None:
            continue
        if task.status == TaskStatus.BACKLOG:
            statuses.append((task.id, task.status.value, "in progress"))
            tasks_synced += 1

    for commit in commits:
        task_ids = re.findall(task_id_pattern, commit.get("message", ""))
        for tid in set(task_ids):
            if tid in task_by_id:
                comments.append((tid, commit["message"]))
                tasks_synced += 1

    for task in clickup_tasks:
        if task.status in (TaskStatus.IN_PROGRESS,):
            has_branch = any(task.id in b for b in branches)
            if not has_branch and task.branch_name is None:
                slug = _slugify(task.title)
                task_type = _guess_task_type(task)
                suggested = project.mappings.branch_pattern.format(
                    type=task_type, task_id=task.id, slug=slug
                )
                suggestions.append(
                    f"Task {task.id} is in progress but has no branch. Suggested: {suggested}"
                )
                branches_linked += 1

    return SyncResult(
        tasks_synced=tasks_synced,
        branches_linked=branches_linked,
        status_changes=statuses,
        comments_added=comments,
        suggestions=suggestions,
    )


def _map_branches_to_tasks(
    branches: list[str],
    task_by_id: dict[str, Task],
    task_id_pattern: str,
) -> dict[str, Task]:
    result: dict[str, Task] = {}
    for branch in branches:
        ids = re.findall(task_id_pattern, branch)
        if ids:
            tid = ids[0]
            if tid in task_by_id:
                result[branch] = task_by_id[tid]
    return result


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9\s-]", "", title.lower())
    slug = re.sub(r"\s+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug)
    return slug[:50]


def _guess_task_type(task: Task) -> str:
    title_lower = task.title.lower()
    if "fix" in title_lower or "bug" in title_lower:
        return "fix"
    return "feature"
