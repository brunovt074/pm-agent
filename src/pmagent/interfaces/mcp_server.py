from pathlib import Path

from fastmcp import FastMCP
from dotenv import load_dotenv

from pmagent.container import Container
from pmagent.config import get_settings
from pmagent.application.sync_project import sync_project as _app_sync_project
from pmagent.application.create_tasks_from_spec import parse_spec_tasks as _parse_spec_tasks, create_tasks_from_spec as _app_create_tasks_from_spec
from pmagent.application.generate_status_report import generate_status_report as _app_generate_status_report

mcp = FastMCP("pm-agent")


def _container() -> Container:
    return Container(get_settings())


@mcp.tool()
def sync_project(direction: str = "full") -> str:
    """Sincroniza tareas entre ClickUp y git. Usa 'full', 'clickup_to_git', o 'git_to_clickup'."""
    return _sync_project(_container(), direction)


def _sync_project(container: Container, direction: str) -> str:
    project = container.project
    list_ids = [lst["clickup_list_id"] for lst in project.mappings.lists]
    all_tasks = []
    for lid in list_ids:
        all_tasks.extend(container.clickup.get_tasks(lid))

    result = _app_sync_project(project, container.clickup, container.git, all_tasks)

    lines = [f"Sync completo para {project.name}:"]
    lines.append(f"  Tareas sincronizadas: {result.tasks_synced}")
    lines.append(f"  Branches vinculados: {result.branches_linked}")

    if result.status_changes:
        lines.append("  Cambios de estado:")
        for task_id, old, new in result.status_changes:
            lines.append(f"    {task_id}: {old} -> {new}")

    if result.comments_added:
        lines.append("  Comentarios agregados:")
        for task_id, msg in result.comments_added[:10]:
            lines.append(f"    {task_id}: {msg[:60]}...")

    if result.suggestions:
        lines.append("  Sugerencias:")
        for s in result.suggestions[:5]:
            lines.append(f"    {s}")

    return "\n".join(lines)


@mcp.tool()
def link_branch(task_id: str, branch_name: str) -> str:
    """Vincula un branch de git a una tarea de ClickUp."""
    return _link_branch(_container(), task_id, branch_name)


def _link_branch(container: Container, task_id: str, branch_name: str) -> str:
    container.clickup.update_task_status(task_id, "in progress")
    container.clickup.add_comment(task_id, f"Branch linked: {branch_name}")
    return f"Branch '{branch_name}' vinculado a la tarea {task_id}."


@mcp.tool()
def create_tasks_from_spec(spec_path: str, clickup_list_id: str) -> str:
    """Crea tareas en ClickUp a partir de un documento de spec markdown."""
    return _create_tasks_from_spec(_container(), spec_path, clickup_list_id)


def _create_tasks_from_spec(container: Container, spec_path: str, clickup_list_id: str) -> str:
    path = Path(spec_path)
    if not path.exists():
        return f"Error: archivo no encontrado: {spec_path}"

    content = path.read_text()
    tasks = _parse_spec_tasks(content)

    if not tasks:
        return "No se encontraron tareas (checkbox items) en el spec."

    created = _app_create_tasks_from_spec(clickup_list_id, tasks, container.clickup)

    lines = [f"Se crearon {len(created)} tareas en la lista {clickup_list_id}:"]
    for i, task_data in enumerate(tasks):
        lines.append(f"  {i + 1}. {task_data['title']} -> {created[i]}")

    return "\n".join(lines)


@mcp.tool()
def create_task(list_id: str, title: str, description: str = "", priority: str | None = None) -> str:
    """Crea una tarea suelta en una lista de ClickUp. La prioridad acepta 'urgent', 'high', 'normal' o 'low'."""
    return _create_task(_container(), list_id, title, description, priority)


def _create_task(
    container: Container, list_id: str, title: str, description: str, priority: str | None = None
) -> str:
    task = container.clickup.create_task(
        list_id=list_id, title=title, description=description, priority=priority
    )
    return f"Tarea '{task.title}' creada con id {task.id} en la lista {list_id}."


@mcp.tool()
def get_spaces(team_id: str | None = None) -> str:
    """Lista los spaces disponibles en un workspace de ClickUp. Si no se pasa team_id, usa el configurado en CLICKUP_TEAM_ID."""
    return _get_spaces(_container(), team_id)


def _get_spaces(container: Container, team_id: str | None = None) -> str:
    resolved_team_id = team_id or container.settings.clickup_team_id
    if not resolved_team_id:
        return "Error: team_id es requerido (o configurá CLICKUP_TEAM_ID)."

    spaces = container.clickup.get_spaces(resolved_team_id)
    if not spaces:
        return f"No se encontraron spaces para el team {resolved_team_id}."

    lines = [f"Spaces en el team {resolved_team_id}:"]
    for space in spaces:
        lines.append(f"  {space['id']}: {space['name']}")
    return "\n".join(lines)


@mcp.tool()
def get_lists(space_id: str) -> str:
    """Lista las lists disponibles dentro de un space de ClickUp."""
    return _get_lists(_container(), space_id)


def _get_lists(container: Container, space_id: str) -> str:
    lists = container.clickup.get_lists(space_id)
    if not lists:
        return f"No se encontraron lists para el space {space_id}."

    lines = [f"Lists en el space {space_id}:"]
    for lst in lists:
        lines.append(f"  {lst['id']}: {lst['name']}")
    return "\n".join(lines)


@mcp.tool()
def status_report(format: str = "text") -> str:
    """Genera un reporte de estado del proyecto (tareas, branches, commits)."""
    return _status_report(_container(), format)


def _status_report(container: Container, format: str) -> str:
    project = container.project
    list_ids = [lst["clickup_list_id"] for lst in project.mappings.lists]
    all_tasks = []
    for lid in list_ids:
        all_tasks.extend(container.clickup.get_tasks(lid))

    return _app_generate_status_report(project, container.clickup, container.git, all_tasks, format)


@mcp.tool()
def move_task(task_id: str, new_status: str) -> str:
    """Cambia el estado de una tarea en ClickUp."""
    return _move_task(_container(), task_id, new_status)


def _move_task(container: Container, task_id: str, new_status: str) -> str:
    container.clickup.update_task_status(task_id, new_status)
    return f"Tarea {task_id} movida a '{new_status}'."


@mcp.tool()
def comment_on_task(task_id: str, comment: str) -> str:
    """Agrega un comentario a una tarea de ClickUp."""
    return _comment_on_task(_container(), task_id, comment)


def _comment_on_task(container: Container, task_id: str, comment: str) -> str:
    if not task_id:
        return "Error: task_id es requerido."
    if not comment:
        return "Error: comment es requerido."

    container.clickup.add_comment(task_id, comment)
    return f"Comentario agregado a {task_id}."


@mcp.tool()
def create_branch_from_task(task_id: str) -> str:
    """Crea un branch de git a partir de una tarea de ClickUp, siguiendo la convención del proyecto."""
    return _create_branch_from_task(_container(), task_id)


def _create_branch_from_task(container: Container, task_id: str) -> str:
    from pmagent.application.sync_project import _slugify

    project = container.project
    task = container.clickup.get_task(task_id)

    task_type = "feature"
    if "fix" in task.title.lower() or "bug" in task.title.lower():
        task_type = "fix"

    slug = _slugify(task.title)
    branch_name = project.mappings.branch_pattern.format(
        type=task_type, task_id=task.id, slug=slug
    )

    container.git.create_branch(branch_name)
    container.clickup.update_task_status(task.id, "in progress")
    container.clickup.add_comment(task.id, f"Branch created: {branch_name}")

    return f"Branch '{branch_name}' creado y tarea {task.id} movida a 'in progress'."


@mcp.tool()
def configure_project() -> str:
    """Guía para configurar el archivo .pm-agent.yaml del proyecto."""
    return _configure_project()


def _configure_project() -> str:
    return (
        "Para configurar PM Agent en tu proyecto:\n\n"
        "1. Copia el template de configuración:\n"
        "   cp .pm-agent.yaml.example .pm-agent.yaml\n\n"
        "2. Editá .pm-agent.yaml con los datos de tu espacio ClickUp:\n"
        "   - project.name: nombre del proyecto\n"
        "   - project.clickup_workspace_id: ID del workspace en ClickUp\n"
        "   - mappings.lists: mapeo de listas de ClickUp a tipos de branch\n"
        "   - mappings.statuses: mapeo de estados ClickUp ↔ estados git\n\n"
        "3. Configurá las variables de entorno en .env:\n"
        "   CLICKUP_API_TOKEN=pk_...\n\n"
        "4. Ejecutá sync_project para verificar la conexión."
    )


@mcp.tool()
def listen_status(action: str = "status") -> str:
    """Gestiona el listener de webhooks (start/stop/status)."""
    return _listen_status(action)


def _listen_status(action: str) -> str:
    if action == "start":
        return "Webhook listener: funcionalidad disponible en una versión futura. Usá las herramientas MCP manualmente por ahora."
    if action == "stop":
        return "No hay listener activo."
    return "Webhook listener: no activo. Usá 'pm-agent listen start' para iniciarlo (próximamente)."


def main() -> None:
    load_dotenv()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
