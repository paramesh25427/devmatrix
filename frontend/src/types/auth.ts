export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role: 'tenant_admin' | 'delivery_manager' | 'project_lead' | 'contributor';
  tenant_id: string;
  tenant_name: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}
