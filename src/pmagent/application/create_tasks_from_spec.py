import re


def parse_spec_tasks(content: str) -> list[dict]:
    tasks: list[dict] = []
    current_section = ""

    for line in content.splitlines():
        stripped = line.strip()

        if stripped.startswith("##") and not stripped.startswith("###"):
            current_section = stripped.lstrip("#").strip()
            continue

        match = re.match(r"-\s*\[.\]\s+(.+)", stripped)
        if match:
            title = match.group(1).strip()
            task = {"title": title}
            if current_section:
                task["section"] = current_section
            tasks.append(task)

    return tasks


def create_tasks_from_spec(
    clickup_list_id: str,
    tasks: list[dict],
    clickup_client: object,
    priority: str | None = None,
) -> list[str]:
    created_ids: list[str] = []

    for task_data in tasks:
        description = ""
        if task_data.get("section"):
            description = f"Section: {task_data['section']}"

        task = clickup_client.create_task(
            list_id=clickup_list_id,
            title=task_data["title"],
            description=description,
            priority=priority,
        )
        created_ids.append(task.id)

    return created_ids
