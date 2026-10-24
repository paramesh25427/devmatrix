from typing import List, Dict, Set, Tuple, Optional
import uuid
from sqlalchemy.orm import Session

from app.models.wbs import WBSTask, TaskDependency
from app.models.baseline import RequirementBaseline
from app.models.audit import AuditLog


class CyclicDependencyError(Exception):
    """Raised when a dependency cycle is detected in the WBS graph."""
    def __init__(self, cycle_path: List[str]):
        self.cycle_path = cycle_path
        cycle_str = " -> ".join(cycle_path)
        super().__init__(f"Circular dependency detected: {cycle_str}. Tasks cannot depend on themselves or form cycles.")


class WBSService:
    """Service for WBS task generation, topological sorting, and cycle detection."""

    @staticmethod
    def calculate_pert(optimistic: float, most_likely: float, pessimistic: float) -> Tuple[float, float]:
        """Calculates PERT expected effort and variance."""
        expected = (optimistic + 4.0 * most_likely + pessimistic) / 6.0
        variance = ((pessimistic - optimistic) / 6.0) ** 2
        return round(expected, 2), round(variance, 2)

    @staticmethod
    def validate_dependencies(tasks: List[WBSTask], dependencies: List[TaskDependency]) -> List[str]:
        """
        Validates task references and checks for cyclic dependencies using Kahn's algorithm.
        Returns topological ordering if valid.
        Raises CyclicDependencyError if a cycle exists.
        Raises ValueError if an invalid task reference exists.
        """
        task_ids = {t.id for t in tasks}
        task_code_map = {t.id: t.task_code for t in tasks}

        # Build adjacency and in-degree maps
        adj: Dict[str, List[str]] = {t.id: [] for t in tasks}
        in_degree: Dict[str, int] = {t.id: 0 for t in tasks}

        for dep in dependencies:
            if dep.predecessor_task_id not in task_ids:
                raise ValueError(f"Dependency references nonexistent predecessor task ID: {dep.predecessor_task_id}")
            if dep.successor_task_id not in task_ids:
                raise ValueError(f"Dependency references nonexistent successor task ID: {dep.successor_task_id}")
            if dep.predecessor_task_id == dep.successor_task_id:
                code = task_code_map.get(dep.predecessor_task_id, dep.predecessor_task_id)
                raise CyclicDependencyError([code, code])

            adj[dep.predecessor_task_id].append(dep.successor_task_id)
            in_degree[dep.successor_task_id] += 1

        # Kahn's Algorithm
        queue = [t_id for t_id, deg in in_degree.items() if deg == 0]
        topo_order: List[str] = []

        while queue:
            curr = queue.pop(0)
            topo_order.append(curr)
            for succ in adj[curr]:
                in_degree[succ] -= 1
                if in_degree[succ] == 0:
                    queue.append(succ)

        if len(topo_order) != len(tasks):
            # A cycle exists! Let's find the cycle using DFS
            cycle = WBSService._find_cycle_dfs(tasks, adj)
            readable_cycle = [task_code_map.get(cid, cid) for cid in cycle]
            raise CyclicDependencyError(readable_cycle)

        return topo_order

    @staticmethod
    def _find_cycle_dfs(tasks: List[WBSTask], adj: Dict[str, List[str]]) -> List[str]:
        """Finds cycle nodes using depth-first search."""
        visited: Dict[str, int] = {t.id: 0 for t in tasks}  # 0=unvisited, 1=visiting, 2=visited
        parent: Dict[str, Optional[str]] = {t.id: None for t in tasks}
        cycle_nodes: List[str] = []

        def dfs(node: str) -> bool:
            visited[node] = 1
            for neighbor in adj.get(node, []):
                if visited[neighbor] == 1:
                    # Found cycle! Backtrack
                    curr = node
                    cycle_nodes.append(neighbor)
                    while curr and curr != neighbor:
                        cycle_nodes.append(curr)
                        curr = parent.get(curr)
                    cycle_nodes.append(neighbor)
                    cycle_nodes.reverse()
                    return True
                elif visited[neighbor] == 0:
                    parent[neighbor] = node
                    if dfs(neighbor):
                        return True
            visited[node] = 2
            return False

        for t in tasks:
            if visited[t.id] == 0:
                if dfs(t.id):
                    return cycle_nodes
        return ["Cycle detected in graph"]

    @classmethod
    def generate_wbs_from_baseline(
        cls,
        db: Session,
        tenant_id: str,
        project_id: str,
        baseline: RequirementBaseline,
    ) -> List[WBSTask]:
        """
        Generates candidate WBS tasks and dependencies from approved baseline requirements.
        Preserves existing manager-approved/edited tasks.
        """
        import json

        data = json.loads(baseline.requirements_data_json)
        functional_reqs = data.get("functional_requirements", [])

        # Check existing tasks to avoid clobbering manager modifications
        existing_tasks = db.query(WBSTask).filter(
            WBSTask.tenant_id == tenant_id,
            WBSTask.project_id == project_id,
        ).all()
        if existing_tasks:
            return existing_tasks

        generated_tasks: List[WBSTask] = []
        task_id_by_index: Dict[int, str] = {}

        # Default standard breakdown template linked to requirements
        task_templates = [
            ("TSK-1.1", "Architecture & API Contract Design", "System Architecture", "Solutions Architect", 16.0, 24.0, 40.0, 0),
            ("TSK-1.2", "Database Schema & Canonical Storage Migration", "Data Infrastructure", "Full-Stack Engineer", 20.0, 32.0, 50.0, 1),
            ("TSK-2.1", "Secure Document Upload & Magic Byte Extraction", "Document Ingestion", "Full-Stack Engineer", 24.0, 36.0, 60.0, 2),
            ("TSK-2.2", "Multi-Provider AI Fallback Pipeline & Async Worker", "AI Intelligence", "Data & AI Systems Engineer", 30.0, 48.0, 80.0, 3),
            ("TSK-3.1", "Deterministic PERT Effort & Rate-Card Cost Engine", "Planning & Cost", "Full-Stack Engineer", 16.0, 28.0, 45.0, 4),
            ("TSK-3.2", "Risk Matrix & Feasibility Assessment Service", "Governance & Risk", "Solutions Architect", 12.0, 20.0, 35.0, 5),
            ("TSK-4.1", "Talent Matching & Explainable Workforce Recommendation", "Workforce Intelligence", "Full-Stack Engineer", 20.0, 30.0, 48.0, 6),
            ("TSK-4.2", "Executive ReportLab PDF Report Generation", "Reporting & Audit", "Full-Stack Engineer", 16.0, 24.0, 40.0, 7),
            ("TSK-5.1", "End-to-End Test Suite & Security Verification", "Quality Assurance", "QA Automation Specialist", 24.0, 36.0, 55.0, 8),
        ]

        for code, title, epic, role, opt, ml, pess, idx in task_templates:
            expected, variance = cls.calculate_pert(opt, ml, pess)
            t_id = str(uuid.uuid4())
            task_id_by_index[idx] = t_id

            # Associate with source requirements where available
            req_ids = [r.get("id") for r in functional_reqs[:2]] if functional_reqs else ["REQ-F-01"]

            task = WBSTask(
                id=t_id,
                tenant_id=tenant_id,
                project_id=project_id,
                baseline_version=baseline.version,
                task_code=code,
                title=title,
                epic_name=epic,
                required_role=role,
                optimistic_hours=opt,
                most_likely_hours=ml,
                pessimistic_hours=pess,
                expected_hours=expected,
                variance_hours=variance,
                status="not_started",
                actual_hours=0.0,
                source_requirement_ids_json=json.dumps(req_ids),
                order_index=idx,
            )
            db.add(task)
            generated_tasks.append(task)

        # Create natural dependency chains (e.g. Architecture -> Schema -> Ingestion -> AI)
        default_dependencies = [
            (0, 1), # 1.1 -> 1.2
            (1, 2), # 1.2 -> 2.1
            (2, 3), # 2.1 -> 2.2
            (3, 4), # 2.2 -> 3.1
            (4, 5), # 3.1 -> 3.2
            (5, 6), # 3.2 -> 4.1
            (6, 7), # 4.1 -> 4.2
            (7, 8), # 4.2 -> 5.1
        ]

        for pred_idx, succ_idx in default_dependencies:
            dep = TaskDependency(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                project_id=project_id,
                predecessor_task_id=task_id_by_index[pred_idx],
                successor_task_id=task_id_by_index[succ_idx],
                dependency_type="finish_to_start",
            )
            db.add(dep)

        db.commit()
        return generated_tasks
