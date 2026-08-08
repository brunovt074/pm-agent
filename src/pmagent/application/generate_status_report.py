import json
from datetime import datetime, timezone

from pmagent.domain.models import Project, Task


def generate_status_report(
    project: Project,
    clickup: object,
    git: object,
    clickup_tasks: list[Task] | None = None,
    format: str = "text",
) -> str:
    if clickup_tasks is None:
        list_ids = [lst["clickup_list_id"] for lst in project.mappings.lists]
        clickup_tasks = []
        for lid in list_ids:
            clickup_tasks.extend(clickup.get_tasks(lid))

    branches = git.list_branches()

    if format == "json":
        return _json_report(project, clickup_tasks, branches)
    return _text_report(project, clickup_tasks, branches)


def _text_report(project: Project, tasks: list[Task], branches: list[str]) -> str:
    lines = [
        f"=== Reporte de Estado: {project.name} ===",
        f"Generado: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        f"--- Tareas ({len(tasks)}) ---",
    ]

    status_order = {"in progress": 0, "in review": 1, "backlog": 2, "complete": 3}
    sorted_tasks = sorted(tasks, key=lambda t: status_order.get(t.status.value, 99))

    for task in sorted_tasks:
        branch_info = f" [{task.branch_name}]" if task.branch_name else ""
        lines.append(f"  [{task.status.value.upper()}] {task.title}{branch_info}")

    lines.append("")
    lines.append(f"--- Branches ({len(branches)}) ---")
    for branch in branches:
        lines.append(f"  {branch}")

    return "\n".join(lines)


def _json_report(project: Project, tasks: list[Task], branches: list[str]) -> str:
    data = {
        "project": project.name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "status": t.status.value,
                "branch": t.branch_name,
                "pr_url": t.pr_url,
                "commits": len(t.commits),
            }
            for t in tasks
        ],
        "branches": branches,
    }
    return json.dumps(data, indent=2, ensure_ascii=False)
