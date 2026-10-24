import json
import uuid
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session

from app.models.workforce import WorkforceMember, TeamRecommendation
from app.models.wbs import WBSTask

STANDARD_ROLE_SKILLS: Dict[str, List[str]] = {
    "Solutions Architect": ["Architecture", "System Design", "Security", "Risk Management", "API Design"],
    "Senior Full-Stack Engineer": ["Python", "FastAPI", "React", "TypeScript", "PostgreSQL"],
    "Full-Stack Engineer": ["Python", "FastAPI", "React", "TypeScript", "SQL"],
    "Cloud DevOps Architect": ["Kubernetes", "AWS", "Terraform", "Docker", "CI/CD", "Helm"],
    "DevOps Engineer": ["Docker", "Kubernetes", "CI/CD", "Linux", "Cloud"],
    "QA Automation Specialist": ["Playwright", "Pytest", "Jest", "Performance Testing", "API Testing"],
    "Data & AI Systems Engineer": ["PyTorch", "FastAPI", "Vector DBs", "Data Pipelines", "Python"],
    "Frontend UI/UX Specialist": ["React", "TypeScript", "Tailwind CSS", "Design Systems", "Accessibility"],
}


class WorkforceRecommendationService:
    """
    Deterministic workforce intelligence and explainable candidate ranking.
    Computes composite match score based on 4 transparent factors:
    1. Skill Fit Score (40% weight): Match between required task skills and candidate skills.
    2. Availability Score (30% weight): Candidate's active available capacity percentage.
    3. Experience Score (20% weight): Relevant industry experience years (normalized to 10 yrs).
    4. Workload Balance Score (10% weight): Inverse of currently active assigned projects.

    Principles:
    - Never uses keystroke, mouse, webcam, or idle-time surveillance.
    - Requires authorized manager approval; never automatically commits staff.
    - Clearly labels synthetic demo datasets when real employee data is unconfigured.
    """

    @classmethod
    def generate_recommendations_for_project(
        cls,
        db: Session,
        tenant_id: str,
        project_id: str,
    ) -> List[TeamRecommendation]:
        """Generates ranked candidate recommendations for all WBS tasks and required roles in the project."""
        tasks = (
            db.query(WBSTask)
            .filter(WBSTask.tenant_id == tenant_id, WBSTask.project_id == project_id)
            .order_by(WBSTask.order_index.asc())
            .all()
        )
        if not tasks:
            raise ValueError("No WBS tasks found. Please generate and approve WBS tasks first.")

        members = (
            db.query(WorkforceMember)
            .filter(WorkforceMember.tenant_id == tenant_id)
            .all()
        )

        recommendations: List[TeamRecommendation] = []

        # Iterate over project WBS tasks
        for task in tasks:
            role = task.required_role or "Full-Stack Engineer"

            # Check if recommendation already exists for this specific task
            existing = (
                db.query(TeamRecommendation)
                .filter(
                    TeamRecommendation.tenant_id == tenant_id,
                    TeamRecommendation.project_id == project_id,
                    TeamRecommendation.task_id == task.id,
                )
                .first()
            )

            if existing:
                if not getattr(existing, "alternatives_json", None) and members:
                    ranked_candidates = cls._rank_candidates_for_role(members, role, task_title=task.title)
                    alts = []
                    for alt_m, alt_scores, alt_rat in ranked_candidates[1:4]:
                        alts.append({
                            "candidate_id": alt_m.id,
                            "candidate_name": alt_m.full_name,
                            "role": alt_m.role,
                            "hourly_rate": alt_m.hourly_rate,
                            "match_score": alt_scores["match_score"],
                            "skill_score": alt_scores["skill_score"],
                            "availability_score": alt_scores["availability_score"],
                            "experience_score": alt_scores["experience_score"],
                            "workload_score": alt_scores["workload_score"],
                            "rationale": alt_rat,
                        })
                    existing.alternatives_json = json.dumps(alts)
                recommendations.append(existing)
                continue

            # If real members exist, rank deterministically
            if members:
                ranked_candidates = cls._rank_candidates_for_role(members, role, task_title=task.title)
                top_candidate, scores, rationale = ranked_candidates[0]

                # Runner-up / alternative candidates (v2 extension)
                alternatives = []
                for alt_m, alt_scores, alt_rat in ranked_candidates[1:4]:
                    alternatives.append({
                        "candidate_id": alt_m.id,
                        "candidate_name": alt_m.full_name,
                        "role": alt_m.role,
                        "hourly_rate": alt_m.hourly_rate,
                        "match_score": alt_scores["match_score"],
                        "skill_score": alt_scores["skill_score"],
                        "availability_score": alt_scores["availability_score"],
                        "experience_score": alt_scores["experience_score"],
                        "workload_score": alt_scores["workload_score"],
                        "rationale": alt_rat,
                    })

                rec = TeamRecommendation(
                    id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    project_id=project_id,
                    task_id=task.id,
                    role_needed=role,
                    candidate_id=top_candidate.id,
                    candidate_name=top_candidate.full_name,
                    match_score=scores["match_score"],
                    skill_score=scores["skill_score"],
                    availability_score=scores["availability_score"],
                    experience_score=scores["experience_score"],
                    workload_score=scores["workload_score"],
                    performance_score=scores.get("performance_score"),
                    rationale=rationale,
                    alternatives_json=json.dumps(alternatives),
                    manager_status="proposed",
                )
                db.add(rec)
                recommendations.append(rec)
            else:
                # Synthetic Demo Profile Fallback (Requirement 4)
                # When real employee data is unavailable, provide clearly labeled synthetic demo benchmark
                syn_id = f"syn-{role.lower().replace(' ', '-')}"
                syn_name = f"[Synthetic Demo] {role} Benchmark"
                syn_rationale = (
                    f"[Synthetic Demo Dataset] Real workforce data is not registered for tenant. "
                    f"Generated benchmark role profile for task {task.task_code} ('{task.title}') "
                    f"with 75% nominal qualification alignment and 80% baseline availability. "
                    f"Real employee qualifications were not invented."
                )
                syn_alternatives = [
                    {
                        "candidate_id": f"syn-{role.lower().replace(' ', '-')}-alt",
                        "candidate_name": f"[Synthetic Demo] {role} Secondary Benchmark",
                        "role": role,
                        "hourly_rate": 95.0,
                        "match_score": 68.0,
                        "skill_score": 65.0,
                        "availability_score": 75.0,
                        "experience_score": 70.0,
                        "workload_score": 70.0,
                        "rationale": f"[Synthetic Demo Dataset] Secondary role benchmark for task {task.task_code}.",
                    }
                ]
                rec = TeamRecommendation(
                    id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    project_id=project_id,
                    task_id=task.id,
                    role_needed=role,
                    candidate_id=syn_id,
                    candidate_name=syn_name,
                    match_score=75.0,
                    skill_score=70.0,
                    availability_score=80.0,
                    experience_score=80.0,
                    workload_score=80.0,
                    rationale=syn_rationale,
                    alternatives_json=json.dumps(syn_alternatives),
                    manager_status="proposed",
                )
                db.add(rec)
                recommendations.append(rec)

        db.commit()
        return recommendations

    @classmethod
    def _rank_candidates_for_role(
        cls,
        members: List[WorkforceMember],
        role: str,
        task_title: Optional[str] = None,
    ) -> List[Tuple[WorkforceMember, Dict[str, float], str]]:
        """
        Ranks candidates for a role deterministically with full factor explanations.
        Incorporates verified historical performance when available, while ensuring new members
        with insufficient history receive fair baseline evaluation without penalty.
        Returns List of (member, scores_dict, rationale).
        """
        ranked = []
        active_members = [m for m in members if getattr(m, "is_active", True) is not False]
        target_members = active_members if active_members else members

        for m in target_members:
            # 1. Skill Score (35-40% weight)
            candidate_skills = json.loads(m.skills_json) if m.skills_json else []
            role_lower = role.lower()
            role_keywords = role_lower.split()

            target_skills = STANDARD_ROLE_SKILLS.get(role, role_keywords)
            matched_skills = [
                s for s in target_skills
                if any(s.lower() in cs.lower() or cs.lower() in s.lower() for cs in candidate_skills)
            ]
            missing_skills = [s for s in target_skills if s not in matched_skills]

            # Role match component: 20 points for exact/partial role match
            role_points = 20.0 if any(kw in m.role.lower() for kw in role_keywords) else 0.0

            # Verified skill overlap component: up to 80 points based on documented skills
            if candidate_skills and target_skills:
                skill_points = (len(matched_skills) / len(target_skills)) * 80.0
            else:
                skill_points = 0.0

            skill_score = min(round(role_points + skill_points, 1), 100.0)

            # 2. Availability Score (25-30% weight)
            if m.availability_pct is not None and m.availability_pct >= 0:
                availability_score = min(round(float(m.availability_pct), 1), 100.0)
            else:
                availability_score = 0.0

            # 3. Experience Score (10-20% weight): Normalized up to 10 years
            if m.experience_years is not None and m.experience_years >= 0:
                experience_score = min(round((float(m.experience_years) / 10.0) * 100.0, 1), 100.0)
            else:
                experience_score = 0.0

            # 4. Workload Balance Score (10% weight): Fewer active projects = higher score
            act_proj = m.active_projects_count if m.active_projects_count is not None else 0
            workload_score = max(round(100.0 - (act_proj * 25.0), 1), 20.0)

            # 5. Verified Historical Performance Score (v2 Extension)
            has_perf = bool(getattr(m, "has_sufficient_evidence", False) and getattr(m, "performance_score", None) is not None)
            if has_perf:
                perf_score = round(float(m.performance_score), 1)
                # 5-Factor Weighted Formula: Skill 35%, Verified Performance 20%, Availability 25%, Experience 10%, Workload 10%
                composite = (
                    0.35 * skill_score +
                    0.20 * perf_score +
                    0.25 * availability_score +
                    0.10 * experience_score +
                    0.10 * workload_score
                )
                composite = round(composite, 1)
                perf_text = f" Verified delivery performance: {perf_score:.1f}% (Confidence: High)."
            else:
                perf_score = None
                # 4-Factor Baseline Formula for new members without past history
                composite = (
                    0.40 * skill_score +
                    0.30 * availability_score +
                    0.20 * experience_score +
                    0.10 * workload_score
                )
                composite = round(composite, 1)
                perf_text = " Performance history: Insufficient performance history (baseline onboarding assessment)."

            scores = {
                "match_score": composite,
                "skill_score": skill_score,
                "availability_score": availability_score,
                "experience_score": experience_score,
                "workload_score": workload_score,
                "performance_score": perf_score,
            }

            # Transparent, explainable rationale
            weekly_cap = m.max_weekly_hours if m.max_weekly_hours else 40.0
            missing_text = f" Missing key role skills: {', '.join(missing_skills)}." if missing_skills else " Fully satisfies core skill requirements."
            avail_text = f"current availability: {availability_score:.0f}% ({weekly_cap * availability_score / 100:.0f}h/wk)" if availability_score > 0 else "current availability: 0% (capacity exhausted or missing)"
            exp_text = f"{m.experience_years:.1f} years verified experience" if m.experience_years else "experience data not documented"

            task_context = f" for '{task_title}'" if task_title else ""
            synthetic_label = " [Synthetic Demo Benchmark]" if getattr(m, "is_synthetic", False) else ""
            rationale = (
                f"Candidate {m.full_name}{synthetic_label} exhibits {skill_score:.0f}% skill alignment ({', '.join(matched_skills[:3]) if matched_skills else 'role match'}){task_context}, "
                f"{avail_text}, {exp_text}, and manages {act_proj} active project(s)."
                f"{missing_text}"
                f"{perf_text}"
            )

            ranked.append((m, scores, rationale))

        # Deterministic sort descending by match score, secondary by availability, tertiary by candidate ID
        ranked.sort(key=lambda x: (x[1]["match_score"], x[1]["availability_score"], x[0].id), reverse=True)
        return ranked

    @classmethod
    def calculate_team_workload_and_capacity(
        cls,
        db: Session,
        tenant_id: str,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calculates dynamic workload, planned effort, and capacity utilization per workforce member.
        Tracks over-allocation (>100% weekly capacity) and provides actionable workload distribution metrics.
        """
        members = (
            db.query(WorkforceMember)
            .filter(WorkforceMember.tenant_id == tenant_id)
            .order_by(WorkforceMember.full_name.asc())
            .all()
        )

        tenant_tasks = (
            db.query(WBSTask)
            .filter(WBSTask.tenant_id == tenant_id)
            .all()
        )

        project_tasks = [t for t in tenant_tasks if t.project_id == project_id] if project_id else tenant_tasks

        approved_recs = (
            db.query(TeamRecommendation)
            .filter(
                TeamRecommendation.tenant_id == tenant_id,
                TeamRecommendation.manager_status == "approved",
            )
            .all()
        )
        task_rec_map = {r.task_id: r for r in approved_recs if r.task_id}

        member_cards = []
        total_nominal_capacity = 0.0
        total_planned_effort = 0.0
        total_actual_effort = 0.0
        overallocated_count = 0
        overallocated_names = []

        for m in members:
            assigned_all = [
                t for t in tenant_tasks
                if t.assigned_user_id == m.id
                or t.assigned_user_name == m.full_name
                or (t.id in task_rec_map and task_rec_map[t.id].candidate_id == m.id)
            ]
            assigned_proj = [
                t for t in project_tasks
                if t.assigned_user_id == m.id
                or t.assigned_user_name == m.full_name
                or (t.id in task_rec_map and task_rec_map[t.id].candidate_id == m.id)
            ]

            max_weekly = float(m.max_weekly_hours or 40.0)
            avail_pct = float(m.availability_pct if m.availability_pct is not None else 100.0)
            nominal_weekly = round((max_weekly * avail_pct) / 100.0, 1)

            planned_hours = round(sum(t.expected_hours for t in assigned_proj), 1)
            actual_hours = round(sum(t.actual_hours for t in assigned_proj), 1)
            global_planned_hours = round(sum(t.expected_hours for t in assigned_all), 1)

            effective_hours = global_planned_hours if global_planned_hours > 0 else planned_hours
            util_pct = round((effective_hours / nominal_weekly) * 100.0, 1) if nominal_weekly > 0 else 0.0

            is_overallocated = bool(effective_hours > nominal_weekly)
            overallocated_hrs = round(max(0.0, effective_hours - nominal_weekly), 1)
            remaining_capacity = round(max(0.0, nominal_weekly - effective_hours), 1)

            if is_overallocated:
                status_level = "overallocated"
                overallocated_count += 1
                overallocated_names.append(m.full_name)
            elif util_pct >= 50.0:
                status_level = "optimal"
            else:
                status_level = "underutilized"

            total_nominal_capacity += nominal_weekly
            total_planned_effort += planned_hours
            total_actual_effort += actual_hours

            member_cards.append({
                "member_id": m.id,
                "full_name": m.full_name,
                "role": m.role,
                "hourly_rate": m.hourly_rate,
                "skills": json.loads(m.skills_json) if m.skills_json else [],
                "experience_years": m.experience_years,
                "max_weekly_hours": max_weekly,
                "availability_pct": avail_pct,
                "nominal_weekly_hours": nominal_weekly,
                "assigned_tasks_count": len(assigned_proj),
                "total_planned_hours": planned_hours,
                "total_actual_hours": actual_hours,
                "global_planned_hours": global_planned_hours,
                "utilization_pct": util_pct,
                "is_overallocated": is_overallocated,
                "overallocated_hours": overallocated_hrs,
                "remaining_capacity_hours": remaining_capacity,
                "status_level": status_level,
                "assigned_tasks": [
                    {
                        "task_id": t.id,
                        "task_code": t.task_code,
                        "title": t.title,
                        "status": t.status,
                        "expected_hours": t.expected_hours,
                        "actual_hours": t.actual_hours,
                        "progress_percentage": getattr(t, "progress_percentage", 0.0) or 0.0,
                    }
                    for t in assigned_proj
                ],
            })

        team_utilization = (
            round((total_planned_effort / total_nominal_capacity) * 100.0, 1)
            if total_nominal_capacity > 0
            else 0.0
        )

        return {
            "project_id": project_id,
            "total_members": len(members),
            "total_nominal_capacity_hours": round(total_nominal_capacity, 1),
            "total_planned_effort_hours": round(total_planned_effort, 1),
            "total_actual_effort_hours": round(total_actual_effort, 1),
            "team_utilization_pct": team_utilization,
            "overallocated_members_count": overallocated_count,
            "overallocated_members": overallocated_names,
            "optimal_count": sum(1 for c in member_cards if c["status_level"] == "optimal"),
            "underutilized_count": sum(1 for c in member_cards if c["status_level"] == "underutilized"),
            "members": member_cards,
        }

    @classmethod
    def analyze_project_skill_gaps(
        cls,
        db: Session,
        tenant_id: str,
        project_id: str,
    ) -> Dict[str, Any]:
        """
        Conducts forensic skill gap analysis for a project's Work Breakdown Structure.
        Compares skills required by task roles against verified talent directory skills,
        identifying covered, scarce (single-point-of-failure), and missing competencies.
        """
        tasks = (
            db.query(WBSTask)
            .filter(WBSTask.tenant_id == tenant_id, WBSTask.project_id == project_id)
            .order_by(WBSTask.order_index.asc())
            .all()
        )
        if not tasks:
            raise ValueError("No WBS tasks found for skill gap analysis.")

        members = (
            db.query(WorkforceMember)
            .filter(WorkforceMember.tenant_id == tenant_id)
            .all()
        )

        member_skills_map: Dict[str, List[str]] = {}
        for m in members:
            try:
                s_list = json.loads(m.skills_json) if m.skills_json else []
            except Exception:
                s_list = []
            member_skills_map[m.id] = [s.strip() for s in s_list]

        skill_task_map: Dict[str, List[Dict[str, Any]]] = {}
        role_counts: Dict[str, int] = {}

        for t in tasks:
            role = t.required_role or "Full-Stack Engineer"
            role_counts[role] = role_counts.get(role, 0) + 1
            target_skills = STANDARD_ROLE_SKILLS.get(role, [role])

            for skill in target_skills:
                skill_clean = skill.strip()
                if skill_clean not in skill_task_map:
                    skill_task_map[skill_clean] = []
                skill_task_map[skill_clean].append({
                    "task_id": t.id,
                    "task_code": t.task_code,
                    "title": t.title,
                    "required_role": role,
                })

        skills_analysis = []
        covered_count = 0
        scarce_count = 0
        missing_count = 0
        missing_skills_list = []
        scarce_skills_list = []

        for skill, req_tasks in skill_task_map.items():
            skill_lower = skill.lower()
            qualified_members = []
            for m in members:
                m_skills = member_skills_map.get(m.id, [])
                if any(skill_lower in s.lower() or s.lower() in skill_lower for s in m_skills):
                    qualified_members.append({
                        "id": m.id,
                        "name": m.full_name,
                        "role": m.role,
                        "experience_years": m.experience_years,
                        "availability_pct": m.availability_pct,
                    })

            qualified_count = len(qualified_members)
            if qualified_count >= 2:
                status = "covered"
                covered_count += 1
            elif qualified_count == 1:
                status = "scarce"
                scarce_count += 1
                scarce_skills_list.append(skill)
            else:
                status = "missing"
                missing_count += 1
                missing_skills_list.append(skill)

            skills_analysis.append({
                "skill": skill,
                "tasks_count": len(req_tasks),
                "tasks": req_tasks,
                "qualified_count": qualified_count,
                "qualified_members": qualified_members,
                "coverage_status": status,
            })

        status_priority = {"missing": 0, "scarce": 1, "covered": 2}
        skills_analysis.sort(key=lambda x: (status_priority.get(x["coverage_status"], 3), -x["tasks_count"], x["skill"]))

        total_skills = len(skill_task_map)
        if total_skills > 0:
            coverage_score = round(((covered_count * 100.0) + (scarce_count * 50.0)) / total_skills, 1)
        else:
            coverage_score = 100.0

        if coverage_score >= 80.0 and missing_count == 0:
            health_status = "healthy"
        elif coverage_score >= 50.0 or missing_count <= 2:
            health_status = "moderate"
        else:
            health_status = "critical"

        recommendations = []
        if missing_skills_list:
            recommendations.append(
                f"Critical Competency Gaps: {len(missing_skills_list)} skill(s) ({', '.join(missing_skills_list[:4])}) have 0 qualified in-house profiles. External contractor engagement or immediate upskilling required."
            )
        if scarce_skills_list:
            recommendations.append(
                f"Single Point of Failure: {len(scarce_skills_list)} skill(s) ({', '.join(scarce_skills_list[:4])}) are covered by only a single contributor. Establish pairing sessions or cross-training."
            )
        if not missing_skills_list and not scarce_skills_list:
            recommendations.append(
                "Optimal Competency Matrix: All required project competencies are satisfied with multiple verified talent profiles in the directory."
            )

        return {
            "project_id": project_id,
            "total_skills_required": total_skills,
            "covered_skills_count": covered_count,
            "scarce_skills_count": scarce_count,
            "missing_skills_count": missing_count,
            "skill_coverage_score": coverage_score,
            "health_status": health_status,
            "skills": skills_analysis,
            "upskilling_signals": recommendations,
        }
