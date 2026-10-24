export interface Project {
  id: string;
  tenant_id: string;
  name: string;
  description?: string;
  status: 'intake' | 'planning' | 'in_progress' | 'completed' | 'on_hold';
  target_budget?: number;
  currency: string;
  target_deadline?: string;
  active_baseline_version?: string;
  document_count: number;
  task_count: number;
  total_pert_hours: number;
  total_cost: number;
  created_at: string;
}
