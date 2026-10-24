export interface WBSTask {
  id: string;
  tenant_id: string;
  project_id: string;
  baseline_version: number;
  task_code: string;
  title: string;
  description?: string;
  epic_name?: string;
  required_role: string;
  optimistic_hours: number;
  most_likely_hours: number;
  pessimistic_hours: number;
  expected_hours: number;
  variance_hours: number;
  assigned_user_id?: string;
  assigned_user_name?: string;
  status: 'not_started' | 'in_progress' | 'blocked' | 'in_review' | 'completed';
  progress_percentage?: number;
  actual_hours: number;
  blocker_notes?: string;
  is_critical_path: boolean;
  source_requirement_ids: string[];
  order_index: number;
  created_at: string;
}

export interface TaskDependency {
  id: string;
  tenant_id: string;
  project_id: string;
  predecessor_task_id: string;
  successor_task_id: string;
  dependency_type: string;
}

export interface WBSOverview {
  tasks: WBSTask[];
  dependencies: TaskDependency[];
  total_pert_hours: number;
  critical_path_task_codes: string[];
  is_dag_valid: boolean;
  cycle_error?: string;
}
