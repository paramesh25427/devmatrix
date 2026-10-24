export interface ProjectReportSummary {
  id: string;
  tenant_id: string;
  project_id: string;
  title: string;
  report_type: string;
  baseline_version: number;
  file_size_bytes: number;
  generated_by: string;
  created_at: string;
}
