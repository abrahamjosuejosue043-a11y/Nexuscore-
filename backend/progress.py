"""Pure calculation engine for hybrid project progress.

This module has no database or API dependencies. It can be tested in isolation
before its results are connected to persistent project/task records.
"""

from collections import defaultdict
from math import isfinite


TASK_WEIGHT_BY_PRIORITY = {
    "alta": 3.0,
    "media": 2.0,
    "baixa": 1.0,
}
CANCELLED_STATUSES = {"cancelada"}
COMPLETED_STATUS = "concluida"
KNOWN_TASK_STATUSES = {
    "pendente",
    "em_andamento",
    "em_revisao",
    "bloqueada",
    "concluida",
    "cancelada",
}


def _positive_weight(value, field_name):
    """Return a finite positive weight or reject ambiguous configuration."""
    if isinstance(value, bool):
        raise ValueError(f"{field_name} deve ser um número positivo.")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} deve ser um número positivo.") from exc
    if not isfinite(number) or number <= 0:
        raise ValueError(f"{field_name} deve ser um número positivo.")
    return number


def _task_weight(task):
    explicit = task.get("weight")
    if explicit is not None:
        return _positive_weight(explicit, "O peso da tarefa")
    priority = str(task.get("priority") or "media").strip().lower()
    return TASK_WEIGHT_BY_PRIORITY.get(priority, TASK_WEIGHT_BY_PRIORITY["media"])


def calculate_project_progress(tasks, department_weights=None):
    """Calculate weighted progress by department and for the whole project.

    Only tasks in the `concluida` state count as completed. In particular,
    `em_revisao` does not count until the Directorate accepts the delivery.
    Cancelled tasks are excluded from task denominators.

    `department_weights` may include departments with no tasks yet. Such
    departments remain in the project denominator at 0%, representing planned
    work that has not started. Departments found in tasks but omitted from the
    mapping receive a neutral weight of 1.

    Task records use the existing storage field names:
    `assigned_department`, `status`, `priority`; an optional `weight`
    field is supported for future persisted task weights.
    """
    if tasks is None:
        tasks = []
    if isinstance(tasks, (str, bytes)):
        raise ValueError("A lista de tarefas é inválida.")

    grouped = defaultdict(list)
    total_tasks = 0
    cancelled_tasks = 0

    for task in tasks:
        if not isinstance(task, dict):
            task = dict(task)
        department = str(task.get("assigned_department") or "").strip()
        status = str(task.get("status") or "").strip().lower()
        if not department:
            raise ValueError("Toda tarefa precisa informar assigned_department.")
        if status not in KNOWN_TASK_STATUSES:
            raise ValueError(f"Status de tarefa inválido: {status or 'vazio'}.")
        total_tasks += 1
        if status in CANCELLED_STATUSES:
            cancelled_tasks += 1
            continue
        grouped[department].append({
            "status": status,
            "weight": _task_weight(task),
        })

    configured_weights = {}
    if department_weights is not None:
        if not hasattr(department_weights, "items"):
            raise ValueError("department_weights deve ser um mapa de pesos.")
        for department, weight in department_weights.items():
            name = str(department).strip()
            if not name:
                raise ValueError("O nome do departamento não pode ficar vazio.")
            configured_weights[name] = _positive_weight(
                weight, f"O peso do departamento {name}"
            )

    department_names = set(grouped) | set(configured_weights)
    active_names = {
        name for name, items in grouped.items() if items
    }
    if department_weights is None:
        department_names = active_names

    department_results = []
    weighted_project_total = 0.0
    project_weight_total = 0.0
    active_tasks = 0
    completed_tasks = 0

    for name in sorted(department_names):
        items = grouped.get(name, [])
        task_weight_total = sum(item["weight"] for item in items)
        completed_weight = sum(
            item["weight"] for item in items
            if item["status"] == COMPLETED_STATUS
        )
        department_progress = (
            completed_weight / task_weight_total * 100.0
            if task_weight_total else 0.0
        )
        department_weight = configured_weights.get(name, 1.0)
        weighted_project_total += department_progress * department_weight
        project_weight_total += department_weight
        active_tasks += len(items)
        completed_tasks += sum(
            1 for item in items if item["status"] == COMPLETED_STATUS
        )
        department_results.append({
            "department": name,
            "weight": round(department_weight, 4),
            "progress_percent": round(department_progress, 2),
            "total_tasks": len(items),
            "completed_tasks": sum(
                1 for item in items if item["status"] == COMPLETED_STATUS
            ),
            "cancelled_tasks": sum(
                1 for task in tasks
                if str(task.get("assigned_department") or "").strip() == name
                and str(task.get("status") or "").strip().lower() in CANCELLED_STATUSES
            ),
        })

    project_progress = (
        weighted_project_total / project_weight_total
        if project_weight_total else 0.0
    )

    return {
        "progress_percent": round(project_progress, 2),
        "total_tasks": total_tasks,
        "active_tasks": active_tasks,
        "completed_tasks": completed_tasks,
        "cancelled_tasks": cancelled_tasks,
        "departments": department_results,
        "calculation": "hybrid_weighted_v1",
    }
