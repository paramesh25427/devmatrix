export interface DeliveryIntelligence {
  project_id: string;
  total_planned_hours: number;
  total_actual_hours: number;
  effort_variance_pct: number;
  completed_tasks_count: number;
  open_blockers_count: number;
  fair_metrics_policy: string;
  surveillance_statement: string;
}

export interface HistoricalProject {
  id: string;
  project_name: string;
  category: string;
  estimated_hours: number;
  actual_hours: number;
  effort_variance_pct: number;
  cost_variance_pct: number;
  calibration_factor: number;
  recorded_at: string;
}

export interface HistoricalSummary {
  total_completed_projects: number;
  average_effort_variance_pct: number;
  average_cost_variance_pct: number;
  composite_calibration_factor: number;
  has_minimum_sample: boolean;
  sample_size_policy_message: string;
  projects: HistoricalProject[];
}
