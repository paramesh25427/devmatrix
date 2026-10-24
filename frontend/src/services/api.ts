import { DocumentDetail, DocumentSummary, HealthStatus } from '../types/document';
import { RequirementDraftResponse } from '../types/requirement';
import { UserProfile, LoginResponse } from '../types/auth';
import { Project } from '../types/project';
import { WBSTask, WBSOverview, TaskDependency } from '../types/wbs';
import { ProjectEstimate } from '../types/estimation';
import { FeasibilityOverview, ProjectRisk } from '../types/risk';
import {
  WorkforceMember,
  TeamRecommendation,
  TeamCapacitySummary,
  SkillGapAnalysis,
  OnboardMemberRequest,
  MemberPerformanceEvidence,
  MemberPerformanceScoreHistory,
  ScoreCorrectionRequest,
} from '../types/workforce';
import { ExecutionSummary } from '../types/execution';
import { DeliveryIntelligence, HistoricalSummary } from '../types/analytics';
import { ProjectReportSummary } from '../types/report';
import { AdminUser, TenantConfig, AuditLogItem, SystemDiagnostics } from '../types/admin';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export class ApiError extends Error {
  status: number;
  attempts?: any[];
  constructor(message: string, status: number, attempts?: any[]) {
    super(message);
    this.status = status;
    this.attempts = attempts;
    this.name = 'ApiError';
  }
}

export function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem('devmatrix_token');
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export async function getOrEnsureToken(): Promise<string | null> {
  let token = localStorage.getItem('devmatrix_token');
  if (token) {
    return token;
  }
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: 'manager@devmatrix.local', password: 'DevMatrix2026!' }),
    });
    if (response.ok) {
      const data: LoginResponse = await response.json();
      localStorage.setItem('devmatrix_token', data.access_token);
      return data.access_token;
    }
  } catch {
    // Offline or test mock fallback
  }
  return null;
}

export async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const token = await getOrEnsureToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let response = await fetch(url, { ...options, headers });

  // If 401 Unauthorized, token might be expired; retry once after re-authenticating
  if (response.status === 401 && token) {
    localStorage.removeItem('devmatrix_token');
    const freshToken = await getOrEnsureToken();
    if (freshToken) {
      headers['Authorization'] = `Bearer ${freshToken}`;
      response = await fetch(url, { ...options, headers });
    }
  }
  return response;
}

export const api = {
  // ==========================================
  // Health Check
  // ==========================================
  async checkHealth(): Promise<HealthStatus> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/health`);
      if (!response.ok) {
        throw new ApiError(`Health check failed (${response.status})`, response.status);
      }
      return await response.json();
    } catch (err: any) {
      if (err instanceof ApiError) throw err;
      throw new ApiError(err.message || 'Cannot connect to backend server', 0);
    }
  },

  // ==========================================
  // Module 1: Auth & Profiles
  // ==========================================
  async ensureAuth(): Promise<string | null> {
    return await getOrEnsureToken();
  },

  async login(email: string, password: string): Promise<LoginResponse> {
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Login failed', response.status);
    }
    const data: LoginResponse = await response.json();
    localStorage.setItem('devmatrix_token', data.access_token);
    return data;
  },

  async getProfile(): Promise<UserProfile> {
    const response = await fetchWithAuth(`${API_BASE_URL}/api/auth/me`);
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to fetch user profile', response.status);
    }
    return await response.json();
  },

  logout(): void {
    localStorage.removeItem('devmatrix_token');
  },

  // ==========================================
  // Projects
  // ==========================================
  async fetchProjects(): Promise<Project[]> {
    const response = await fetchWithAuth(`${API_BASE_URL}/api/projects`);
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to fetch projects', response.status);
    }
    return await response.json();
  },

  async createProject(name: string, description?: string, target_budget?: number, target_deadline?: string): Promise<Project> {
    const response = await fetchWithAuth(`${API_BASE_URL}/api/projects`, {
      method: 'POST',
      body: JSON.stringify({ name, description, target_budget, target_deadline }),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to create project', response.status);
    }
    return await response.json();
  },

  async getProject(projectId: string): Promise<Project> {
    const response = await fetchWithAuth(`${API_BASE_URL}/api/projects/${projectId}`);
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to get project', response.status);
    }
    return await response.json();
  },

  // ==========================================
  // Module 2: Document Intake
  // ==========================================
  async fetchDocuments(projectId?: string): Promise<DocumentSummary[]> {
    const url = projectId ? `${API_BASE_URL}/api/documents?project_id=${projectId}` : `${API_BASE_URL}/api/documents`;
    const response = await fetch(url, { headers: getAuthHeaders() });
    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new ApiError(errData.detail || `Failed to fetch documents (${response.status})`, response.status);
    }
    return await response.json();
  },

  async getDocument(docId: string): Promise<DocumentDetail> {
    const response = await fetch(`${API_BASE_URL}/api/documents/${docId}`, { headers: getAuthHeaders() });
    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new ApiError(errData.detail || `Failed to get document (${response.status})`, response.status);
    }
    return await response.json();
  },

  async uploadDocument(file: File, projectId?: string): Promise<DocumentDetail> {
    const formData = new FormData();
    formData.append('file', file);
    if (projectId) {
      formData.append('project_id', projectId);
    }

    const token = localStorage.getItem('devmatrix_token');
    const headers: HeadersInit = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const response = await fetch(`${API_BASE_URL}/api/documents/upload`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new ApiError(errData.detail || `Upload failed with status ${response.status}`, response.status);
    }

    return await response.json();
  },

  async deleteDocument(docId: string): Promise<{ message: string; id: string }> {
    const response = await fetch(`${API_BASE_URL}/api/documents/${docId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new ApiError(errData.detail || `Deletion failed with status ${response.status}`, response.status);
    }

    return await response.json();
  },

  // ==========================================
  // Module 3: Observable Jobs & AI Requirements
  // ==========================================
  async startExtractionJob(documentId: string): Promise<{ id: string; status: string; progress_pct: number }> {
    const response = await fetch(`${API_BASE_URL}/api/jobs/extract/${documentId}`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to start extraction job', response.status);
    }
    return await response.json();
  },

  async getJobStatus(jobId: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/api/jobs/${jobId}`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to get job status', response.status);
    }
    return await response.json();
  },

  async extractRequirements(documentId: string): Promise<RequirementDraftResponse> {
    const response = await fetch(`${API_BASE_URL}/api/requirements/extract/${documentId}`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      const msg = typeof errData.detail === 'object' ? errData.detail.message : errData.detail;
      const attempts = typeof errData.detail === 'object' ? errData.detail.attempts : undefined;
      throw new ApiError(msg || `AI extraction failed with status ${response.status}`, response.status, attempts);
    }
    return await response.json();
  },

  async getDocumentDrafts(documentId: string): Promise<RequirementDraftResponse[]> {
    const response = await fetch(`${API_BASE_URL}/api/requirements/document/${documentId}`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new ApiError(errData.detail || `Failed to fetch drafts (${response.status})`, response.status);
    }
    return await response.json();
  },

  async approveBaseline(draftId: string, managerNotes?: string, changeSummary?: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/api/requirements/draft/${draftId}/approve`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ manager_notes: managerNotes, change_summary: changeSummary }),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to approve requirements baseline', response.status);
    }
    return await response.json();
  },

  async updateManagerReview(draftId: string, reviewStatus: string, managerNotes?: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/api/requirements/${draftId}/review`, {
      method: 'PATCH',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        review_status: reviewStatus,
        manager_notes: managerNotes,
      }),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to update manager review', response.status);
    }
    return await response.json();
  },

  async getActiveBaseline(projectId: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/api/requirements/baseline/${projectId}`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'No active baseline found', response.status);
    }
    return await response.json();
  },

  // ==========================================
  // Module 4: WBS & Planning
  // ==========================================
  async generateWBS(projectId: string): Promise<WBSTask[]> {
    const response = await fetch(`${API_BASE_URL}/api/wbs/generate/${projectId}`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to generate WBS', response.status);
    }
    return await response.json();
  },

  async getWBSOverview(projectId: string): Promise<WBSOverview> {
    const response = await fetch(`${API_BASE_URL}/api/wbs/${projectId}`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to get WBS overview', response.status);
    }
    return await response.json();
  },

  async createTask(taskData: any): Promise<WBSTask> {
    const response = await fetch(`${API_BASE_URL}/api/wbs/task`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(taskData),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to create task', response.status);
    }
    return await response.json();
  },

  async addDependency(projectId: string, predecessorTaskId: string, successorTaskId: string): Promise<TaskDependency> {
    const response = await fetch(`${API_BASE_URL}/api/wbs/dependency`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        project_id: projectId,
        predecessor_task_id: predecessorTaskId,
        successor_task_id: successorTaskId,
      }),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to add dependency', response.status);
    }
    return await response.json();
  },

  // ==========================================
  // Module 5: Estimation & Schedule
  // ==========================================
  async calculateEstimate(projectId: string, contingencyPct: number = 15.0): Promise<ProjectEstimate> {
    const response = await fetch(`${API_BASE_URL}/api/estimation/calculate/${projectId}`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ contingency_pct: contingencyPct }),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to calculate estimate', response.status);
    }
    return await response.json();
  },

  async getEstimate(projectId: string): Promise<ProjectEstimate> {
    const response = await fetch(`${API_BASE_URL}/api/estimation/${projectId}`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to get estimate', response.status);
    }
    return await response.json();
  },

  // ==========================================
  // Module 6: Risks & Feasibility
  // ==========================================
  async evaluateFeasibility(projectId: string): Promise<FeasibilityOverview> {
    const response = await fetch(`${API_BASE_URL}/api/risks/evaluate/${projectId}`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to evaluate feasibility', response.status);
    }
    return await response.json();
  },

  async getRisks(projectId: string): Promise<FeasibilityOverview> {
    const response = await fetch(`${API_BASE_URL}/api/risks/${projectId}`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to get risks', response.status);
    }
    return await response.json();
  },

  async updateRiskItem(riskId: string, payload: Partial<ProjectRisk>): Promise<ProjectRisk> {
    const response = await fetch(`${API_BASE_URL}/api/risks/item/${riskId}`, {
      method: 'PUT',
      headers: {
        ...getAuthHeaders(),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to update risk item', response.status);
    }
    return await response.json();
  },

  // ==========================================
  // Module 7: Workforce Intelligence
  // ==========================================
  async listWorkforce(): Promise<WorkforceMember[]> {
    const response = await fetch(`${API_BASE_URL}/api/workforce`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to list workforce', response.status);
    }
    return await response.json();
  },

  async generateRecommendations(projectId: string): Promise<TeamRecommendation[]> {
    const response = await fetch(`${API_BASE_URL}/api/workforce/recommend/${projectId}`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to generate recommendations', response.status);
    }
    return await response.json();
  },

  async approveRecommendation(recId: string): Promise<TeamRecommendation> {
    const response = await fetch(`${API_BASE_URL}/api/workforce/recommendations/${recId}/approve`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to approve recommendation', response.status);
    }
    return await response.json();
  },

  async rejectRecommendation(recId: string, notes?: string): Promise<TeamRecommendation> {
    const response = await fetch(`${API_BASE_URL}/api/workforce/recommendations/${recId}/reject`, {
      method: 'POST',
      headers: {
        ...getAuthHeaders(),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ manager_notes: notes || '' }),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to reject recommendation', response.status);
    }
    return await response.json();
  },

  async getRecommendations(projectId: string): Promise<TeamRecommendation[]> {
    const response = await fetch(`${API_BASE_URL}/api/workforce/recommendations/${projectId}`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to get recommendations', response.status);
    }
    return await response.json();
  },

  async selectAlternativeCandidate(
    recId: string,
    candidateId: string,
    managerNotes?: string
  ): Promise<TeamRecommendation> {
    const response = await fetch(
      `${API_BASE_URL}/api/workforce/recommendations/${recId}/select-alternative`,
      {
        method: 'POST',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          candidate_id: candidateId,
          manager_notes: managerNotes,
        }),
      }
    );
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to select alternative candidate', response.status);
    }
    return await response.json();
  },

  async overrideRecommendation(
    recId: string,
    candidateId: string,
    candidateName: string,
    managerNotes: string
  ): Promise<TeamRecommendation> {
    const response = await fetch(
      `${API_BASE_URL}/api/workforce/recommendations/${recId}/override`,
      {
        method: 'POST',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          candidate_id: candidateId,
          candidate_name: candidateName,
          manager_notes: managerNotes,
        }),
      }
    );
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to override recommendation', response.status);
    }
    return await response.json();
  },

  async getWorkforceCapacity(projectId: string): Promise<TeamCapacitySummary> {
    const response = await fetch(`${API_BASE_URL}/api/workforce/capacity/${projectId}`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to get workforce capacity', response.status);
    }
    return await response.json();
  },

  async getSkillGapAnalysis(projectId: string): Promise<SkillGapAnalysis> {
    const response = await fetch(`${API_BASE_URL}/api/workforce/skill-gaps/${projectId}`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to get skill gap analysis', response.status);
    }
    return await response.json();
  },

  async createWorkforceMember(member: OnboardMemberRequest): Promise<WorkforceMember> {
    const response = await fetch(`${API_BASE_URL}/api/workforce`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(member),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to onboard team member', response.status);
    }
    return await response.json();
  },

  async getWorkforceMember(memberId: string): Promise<WorkforceMember> {
    const response = await fetch(`${API_BASE_URL}/api/workforce/members/${memberId}`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to fetch workforce member', response.status);
    }
    return await response.json();
  },

  async updateWorkforceMember(memberId: string, member: Partial<OnboardMemberRequest>): Promise<WorkforceMember> {
    const response = await fetch(`${API_BASE_URL}/api/workforce/members/${memberId}`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(member),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to update workforce member', response.status);
    }
    return await response.json();
  },

  async activateWorkforceMember(memberId: string): Promise<WorkforceMember> {
    const response = await fetch(`${API_BASE_URL}/api/workforce/members/${memberId}/activate`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to activate team member', response.status);
    }
    return await response.json();
  },

  async deactivateWorkforceMember(memberId: string): Promise<WorkforceMember> {
    const response = await fetch(`${API_BASE_URL}/api/workforce/members/${memberId}/deactivate`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to deactivate team member', response.status);
    }
    return await response.json();
  },

  async correctMemberScore(memberId: string, payload: ScoreCorrectionRequest): Promise<MemberPerformanceScoreHistory> {
    const response = await fetch(`${API_BASE_URL}/api/workforce/members/${memberId}/correct-score`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to submit score correction', response.status);
    }
    return await response.json();
  },

  async getMemberScoreHistory(memberId: string): Promise<MemberPerformanceScoreHistory[]> {
    const response = await fetch(`${API_BASE_URL}/api/workforce/members/${memberId}/score-history`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to get member score history', response.status);
    }
    return await response.json();
  },

  async getMemberEvidence(memberId: string): Promise<MemberPerformanceEvidence[]> {
    const response = await fetch(`${API_BASE_URL}/api/workforce/members/${memberId}/evidence`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to get member performance evidence', response.status);
    }
    return await response.json();
  },

  // ==========================================
  // Module 8: Execution & Progress
  // ==========================================
  async getExecutionSummary(projectId: string): Promise<ExecutionSummary> {
    const response = await fetch(`${API_BASE_URL}/api/execution/summary/${projectId}`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to get execution summary', response.status);
    }
    return await response.json();
  },

  async updateTaskProgress(
    taskId: string,
    hoursLogged: number,
    newStatus: string,
    progressPercentage?: number,
    notes?: string,
    blockerFlag: boolean = false,
    blockerDesc?: string
  ): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/api/execution/task-update`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        task_id: taskId,
        hours_logged: hoursLogged,
        new_status: newStatus,
        progress_percentage: progressPercentage,
        progress_notes: notes,
        blocker_flag: blockerFlag,
        blocker_description: blockerDesc,
      }),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to update task progress', response.status);
    }
    return await response.json();
  },

  // ==========================================
  // Module 9 & 10: Analytics & Calibration
  // ==========================================
  async getDeliveryIntelligence(projectId: string): Promise<DeliveryIntelligence> {
    const response = await fetch(`${API_BASE_URL}/api/analytics/delivery/${projectId}`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to get delivery intelligence', response.status);
    }
    return await response.json();
  },

  async getHistoricalCalibration(): Promise<HistoricalSummary> {
    const response = await fetch(`${API_BASE_URL}/api/analytics/historical`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to get historical calibration', response.status);
    }
    return await response.json();
  },

  // ==========================================
  // Module 12: PDF Reports
  // ==========================================
  async generateReport(projectId: string): Promise<ProjectReportSummary> {
    const response = await fetch(`${API_BASE_URL}/api/reports/generate/${projectId}`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to generate report', response.status);
    }
    return await response.json();
  },

  async listReports(projectId: string): Promise<ProjectReportSummary[]> {
    const response = await fetch(`${API_BASE_URL}/api/reports/${projectId}`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to list reports', response.status);
    }
    return await response.json();
  },

  getReportDownloadUrl(reportId: string): string {
    const token = localStorage.getItem('devmatrix_token');
    return token
      ? `${API_BASE_URL}/api/reports/${reportId}/download?token=${encodeURIComponent(token)}`
      : `${API_BASE_URL}/api/reports/${reportId}/download`;
  },

  async downloadReportBlob(reportId: string, filename?: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/reports/${reportId}/download`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to download report', response.status);
    }
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename || `project_report_${reportId.substring(0, 8)}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.parentNode?.removeChild(link);
    window.URL.revokeObjectURL(url);
  },

  // ==========================================
  // Module 13: Administration & Governance
  // ==========================================
  async listAdminUsers(): Promise<AdminUser[]> {
    const response = await fetch(`${API_BASE_URL}/api/admin/users`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to list users', response.status);
    }
    return await response.json();
  },

  async getTenantConfig(): Promise<TenantConfig> {
    const response = await fetch(`${API_BASE_URL}/api/admin/tenant`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to get tenant config', response.status);
    }
    return await response.json();
  },

  async getAuditLogs(): Promise<AuditLogItem[]> {
    const response = await fetch(`${API_BASE_URL}/api/admin/audit-logs`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to get audit logs', response.status);
    }
    return await response.json();
  },

  async getDiagnostics(): Promise<SystemDiagnostics> {
    const response = await fetch(`${API_BASE_URL}/api/admin/diagnostics`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(err.detail || 'Failed to get diagnostics', response.status);
    }
    return await response.json();
  },
};
