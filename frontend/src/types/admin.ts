export interface AdminUser {
  id: string;
  tenant_id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface TenantConfig {
  id: string;
  name: string;
  slug: string;
  currency: string;
  default_contingency_pct: number;
  retention_days: number;
  created_at: string;
}

export interface AuditLogItem {
  id: string;
  tenant_id: string;
  user_email?: string;
  action: string;
  entity_type: string;
  entity_id: string;
  details?: Record<string, any>;
  created_at: string;
}

export interface SystemDiagnostics {
  app_env: string;
  database: {
    status: string;
    type: string;
  };
  storage: {
    storage_dir_exists: boolean;
    uploads_dir_exists: boolean;
    reports_dir_exists: boolean;
  };
  ai_providers: {
    gemini: { enabled: boolean; configured: boolean; model: string };
    nvidia_nim: { enabled: boolean; configured: boolean; model: string };
    grok: { enabled: boolean; configured: boolean; model: string };
    offline_deterministic_mock: { enabled: boolean; status: string };
  };
}
