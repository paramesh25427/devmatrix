import json
import math
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.models.wbs import WBSTask, TaskDependency
from app.models.estimation import ProjectEstimate
from app.services.planning.wbs_service import WBSService

# Approved Standard Enterprise Role Rate Card ($/hour)
STANDARD_RATE_CARD: Dict[str, float] = {
    "Solutions Architect": 135.0,
    "Project Lead & Solutions Architect": 135.0,
    "Senior Full-Stack Engineer": 115.0,
    "Full-Stack Engineer": 105.0,
    "Cloud DevOps Architect": 140.0,
    "Data & AI Systems Engineer": 150.0,
    "QA Automation Specialist": 90.0,
    "Frontend UI/UX Specialist": 95.0,
}
DEFAULT_HOURLY_RATE = 105.0
HOURS_PER_WORK_DAY = 7.0  # Fair capacity: 7 productive hours per work day (never assume 8 or 24/7)


class EstimationEngine:
    """Deterministic PERT effort, rate-card cost, and CPM schedule calculation engine."""

    @classmethod
    def calculate_project_estimates(
        cls,
        db: Session,
        tenant_id: str,
        project_id: str,
        contingency_pct: float = 15.0,
    ) -> ProjectEstimate:
        """
        Executes deterministic calculations:
        1. PERT expected hours and variance sum.
        2. Role-card labor cost aggregation.
        3. Contingency calculation.
        4. CPM schedule forward & backward pass to identify Critical Path and project duration.
        """
        if contingency_pct is None or not (0.0 <= contingency_pct <= 100.0):
            raise ValueError(
                f"Invalid contingency percentage: {contingency_pct}. Must be between 0.0 and 100.0 inclusive."
            )

        tasks = (
            db.query(WBSTask)
            .filter(WBSTask.tenant_id == tenant_id, WBSTask.project_id == project_id)
            .all()
        )
        if not tasks:
            raise ValueError("Cannot calculate estimate: No WBS tasks found for this project.")

        dependencies = (
            db.query(TaskDependency)
            .filter(TaskDependency.tenant_id == tenant_id, TaskDependency.project_id == project_id)
            .all()
        )

        # 1. Validate DAG and get topological order
        topo_order = WBSService.validate_dependencies(tasks, dependencies)

        # 2. Effort and Labor Cost Aggregation
        total_pert_hours = 0.0
        total_labor_cost = 0.0
        role_breakdown: Dict[str, Dict[str, float]] = {}

        for task in tasks:
            total_pert_hours += task.expected_hours
            role = task.required_role or "Full-Stack Engineer"
            rate = STANDARD_RATE_CARD.get(role, DEFAULT_HOURLY_RATE)
            task_cost = task.expected_hours * rate
            total_labor_cost += task_cost

            if role not in role_breakdown:
                role_breakdown[role] = {"hours": 0.0, "cost": 0.0, "rate": rate}
            role_breakdown[role]["hours"] += task.expected_hours
            role_breakdown[role]["cost"] += task_cost

        # Round totals
        total_pert_hours = round(total_pert_hours, 2)
        total_labor_cost = round(total_labor_cost, 2)
        contingency_cost = round(total_labor_cost * (contingency_pct / 100.0), 2)
        total_cost = round(total_labor_cost + contingency_cost, 2)

        # 3. Critical Path Method (CPM) Schedule Calculation
        critical_path_task_ids, total_duration_days = cls._calculate_cpm(tasks, dependencies, topo_order)

        # Mark tasks that are on the critical path
        for task in tasks:
            task.is_critical_path = task.id in critical_path_task_ids

        # 4. Persist or Update ProjectEstimate
        estimate = (
            db.query(ProjectEstimate)
            .filter(ProjectEstimate.tenant_id == tenant_id, ProjectEstimate.project_id == project_id)
            .first()
        )
        if not estimate:
            import uuid
            estimate = ProjectEstimate(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                project_id=project_id,
                baseline_version=tasks[0].baseline_version,
            )
            db.add(estimate)

        task_id_to_code = {t.id: t.task_code for t in tasks}
        critical_path_task_codes = [task_id_to_code.get(tid, tid) for tid in critical_path_task_ids]

        estimate.total_pert_hours = total_pert_hours
        estimate.total_labor_cost = total_labor_cost
        estimate.contingency_pct = contingency_pct
        estimate.contingency_cost = contingency_cost
        estimate.total_cost = total_cost
        estimate.currency = "USD"
        estimate.estimated_duration_days = total_duration_days
        estimate.critical_path_tasks_json = json.dumps(critical_path_task_codes)
        estimate.role_breakdown_json = json.dumps(role_breakdown)
        estimate.rate_card_version = "Enterprise Standard 2026.1"

        db.commit()
        db.refresh(estimate)
        return estimate

    @classmethod
    def _calculate_cpm(
        cls,
        tasks: List[WBSTask],
        dependencies: List[TaskDependency],
        topo_order: List[str],
    ) -> Tuple[List[str], float]:
        """
        Calculates CPM schedule:
        Forward pass (Early Start, Early Finish).
        Backward pass (Late Start, Late Finish).
        Identifies tasks where Total Float == 0 (Critical Path).
        """
        task_map: Dict[str, WBSTask] = {t.id: t for t in tasks}
        duration_days_map: Dict[str, float] = {
            t.id: max(round(t.expected_hours / HOURS_PER_WORK_DAY, 2), 0.5) for t in tasks
        }

        # Build adjacency graph
        succ_map: Dict[str, List[str]] = {t.id: [] for t in tasks}
        pred_map: Dict[str, List[str]] = {t.id: [] for t in tasks}
        for dep in dependencies:
            succ_map[dep.predecessor_task_id].append(dep.successor_task_id)
            pred_map[dep.successor_task_id].append(dep.predecessor_task_id)

        # Forward Pass: Early Start (ES) and Early Finish (EF)
        es: Dict[str, float] = {}
        ef: Dict[str, float] = {}

        for t_id in topo_order:
            preds = pred_map.get(t_id, [])
            if not preds:
                es[t_id] = 0.0
            else:
                es[t_id] = max(ef[p] for p in preds)
            ef[t_id] = round(es[t_id] + duration_days_map[t_id], 2)

        # Total project duration is max EF
        project_duration = max(ef.values()) if ef else 0.0

        # Backward Pass: Late Start (LS) and Late Finish (LF)
        ls: Dict[str, float] = {}
        lf: Dict[str, float] = {}

        for t_id in reversed(topo_order):
            succs = succ_map.get(t_id, [])
            if not succs:
                lf[t_id] = project_duration
            else:
                lf[t_id] = min(ls[s] for s in succs)
            ls[t_id] = round(lf[t_id] - duration_days_map[t_id], 2)

        # Total float / slack = LF - EF (or LS - ES)
        critical_path_tasks: List[str] = []
        for t_id in topo_order:
            float_days = round(lf[t_id] - ef[t_id], 2)
            if abs(float_days) < 0.01:
                critical_path_tasks.append(t_id)

        return critical_path_tasks, project_duration
