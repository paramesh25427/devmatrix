export interface Milestone {
  id: string;
  tenant_id: string;
  project_id: string;
  title: string;
  description?: string;
  due_date: string;
  status: 'pending' | 'completed' | 'delayed';
  completed_at?: string;
  created_at: string;
}

export interface TaskUpdateRecordItem {
  id: string;
  task_id: string;
  user_name: string;
  hours_logged: number;
  previous_status: string;
  new_status: string;
  progress_percentage: number;
  progress_notes?: string;
  blocker_flag: string;
  blocker_description?: string;
  created_at: string;
}

export interface ExecutionSummary {
  project_id: string;
  total_tasks: number;
  completed_tasks: number;
  in_progress_tasks: number;
  blocked_tasks: number;
  overdue_milestones_count?: number;
  total_planned_hours: number;
  total_actual_hours: number;
  completion_percentage: number;
  milestones: Milestone[];
  active_blockers: Array<{ task_id?: string; task_code: string; title: string; notes: string }>;
  recent_updates?: TaskUpdateRecordItem[];
}
