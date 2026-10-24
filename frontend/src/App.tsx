import React, { useEffect, useState, useCallback, useRef } from 'react';
import { DocumentDetail, DocumentSummary } from './types/document';
import { RequirementDraftResponse } from './types/requirement';
import { UserProfile } from './types/auth';
import { Project } from './types/project';
import { WBSOverview } from './types/wbs';
import { ProjectEstimate } from './types/estimation';
import { FeasibilityOverview } from './types/risk';
import { WorkforceMember, TeamRecommendation } from './types/workforce';
import { ExecutionSummary } from './types/execution';
import { DeliveryIntelligence, HistoricalSummary } from './types/analytics';
import { ProjectReportSummary } from './types/report';
import { AdminUser, TenantConfig, AuditLogItem, SystemDiagnostics } from './types/admin';

import { api } from './services/api';

import { Sidebar, ActiveTab } from './components/Sidebar';
import { DashboardView } from './components/DashboardView';
import { ProjectsView } from './components/ProjectsView';
import { DocumentUploadZone } from './components/DocumentUploadZone';
import { DocumentList } from './components/DocumentList';
import { DocumentPreviewModal } from './components/DocumentPreviewModal';
import { RequirementDraftModal } from './components/RequirementDraftModal';
import { RequirementsView } from './components/RequirementsView';
import { WBSView } from './components/WBSView';
import { EstimationView } from './components/EstimationView';
import { RisksView } from './components/RisksView';
import { WorkforceView } from './components/WorkforceView';
import { ExecutionView } from './components/ExecutionView';
import { AnalyticsView } from './components/AnalyticsView';
import { ReportsView } from './components/ReportsView';
import { AdminView } from './components/AdminView';
import { LoginModal } from './components/LoginModal';

import {
  FileText,
  Files,
  CheckCircle,
  Sparkles,
  AlertTriangle,
  X,
  FolderKanban,
} from 'lucide-react';

export const App: React.FC = () => {
  // Navigation & Session
  const [activeTab, setActiveTab] = useState<ActiveTab>('documents');
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState<boolean>(false);

  // Projects State
  const [projects, setProjects] = useState<Project[]>([]);
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [projectsLoading, setProjectsLoading] = useState<boolean>(true);
  const [projectsError, setProjectsError] = useState<string | null>(null);

  // Documents State (Module 2)
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<DocumentDetail | null>(null);
  const [activeDraft, setActiveDraft] = useState<RequirementDraftResponse | null>(null);
  const [extractingDocId, setExtractingDocId] = useState<string | null>(null);
  const [extractionError, setExtractionError] = useState<string | null>(null);
  const [docsLoading, setDocsLoading] = useState<boolean>(true);

  // Requirements Baseline State (Module 3)
  const [activeBaseline, setActiveBaseline] = useState<any | null>(null);
  const [baselineLoading, setBaselineLoading] = useState<boolean>(false);
  const activeDeliverablesProjectIdRef = useRef<string>('');

  // WBS State (Module 4)
  const [wbsOverview, setWbsOverview] = useState<WBSOverview | null>(null);

  // Estimation State (Module 5)
  const [estimate, setEstimate] = useState<ProjectEstimate | null>(null);

  // Feasibility & Risks State (Module 6)
  const [feasibility, setFeasibility] = useState<FeasibilityOverview | null>(null);

  // Workforce State (Module 7)
  const [workforce, setWorkforce] = useState<WorkforceMember[]>([]);
  const [recommendations, setRecommendations] = useState<TeamRecommendation[]>([]);

  // Execution State (Module 8)
  const [executionSummary, setExecutionSummary] = useState<ExecutionSummary | null>(null);

  // Analytics & Historical State (Modules 9 & 10)
  const [intelligence, setIntelligence] = useState<DeliveryIntelligence | null>(null);
  const [historical, setHistorical] = useState<HistoricalSummary | null>(null);

  // Reports State (Module 12)
  const [reports, setReports] = useState<ProjectReportSummary[]>([]);

  // Admin State (Module 13)
  const [adminUsers, setAdminUsers] = useState<AdminUser[]>([]);
  const [tenantConfig, setTenantConfig] = useState<TenantConfig | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);
  const [diagnostics, setDiagnostics] = useState<SystemDiagnostics | null>(null);

  // User Profile Initializer
  const initUser = useCallback(async () => {
    try {
      const profile = await api.getProfile();
      setCurrentUser(profile);
    } catch {
      // Default to demo Delivery Manager session
      setCurrentUser({
        id: 'usr-manager-01',
        tenant_id: 'tenant-default',
        tenant_name: 'Acme Enterprise Delivery',
        email: 'manager@devmatrix.local',
        full_name: 'Alex Morgan (Delivery Manager)',
        role: 'delivery_manager',
      });
    }
  }, []);

  // Load Projects
  const loadProjects = useCallback(async () => {
    setProjectsLoading(true);
    setProjectsError(null);
    try {
      const projList = await api.fetchProjects();
      setProjects(projList);
      setCurrentProject((prev) => {
        if (!projList || projList.length === 0) {
          return null;
        }
        if (prev) {
          const match = projList.find((p) => p.id === prev.id);
          if (match) return match;
        }
        return projList[0];
      });
    } catch (err: any) {
      setProjectsError(err.message || 'Failed to load projects');
      setProjects([]);
      setCurrentProject(null);
    } finally {
      setProjectsLoading(false);
    }
  }, []);

  // Load Documents
  const loadDocuments = useCallback(async (projId?: string) => {
    setDocsLoading(true);
    try {
      const targetProjId = projId !== undefined ? projId : currentProject?.id;
      const data = await api.fetchDocuments(targetProjId);
      setDocuments(data);
    } catch {
      // Handled gracefully
    } finally {
      setDocsLoading(false);
    }
  }, [currentProject?.id]);

  // Load Project-Specific Deliverables
  const loadProjectDeliverables = useCallback(async (projId: string) => {
    activeDeliverablesProjectIdRef.current = projId;
    setBaselineLoading(true);
    try {
      // 1. Requirements Baseline
      const bl = await api.getActiveBaseline(projId).catch(() => null);
      if (activeDeliverablesProjectIdRef.current !== projId) return;
      setActiveBaseline(bl);

      // 2. WBS
      const wbs = await api.getWBSOverview(projId).catch(() => null);
      if (activeDeliverablesProjectIdRef.current !== projId) return;
      setWbsOverview(wbs);

      // 3. Estimate
      const est = await api.getEstimate(projId).catch(() => null);
      if (activeDeliverablesProjectIdRef.current !== projId) return;
      setEstimate(est);

      // 4. Feasibility / Risks
      const rsk = await api.getRisks(projId).catch(() => null);
      if (activeDeliverablesProjectIdRef.current !== projId) return;
      setFeasibility(rsk);

      // 5. Execution Summary
      const exec = await api.getExecutionSummary(projId).catch(() => null);
      if (activeDeliverablesProjectIdRef.current !== projId) return;
      setExecutionSummary(exec);

      // 6. Delivery Intelligence
      const intel = await api.getDeliveryIntelligence(projId).catch(() => null);
      if (activeDeliverablesProjectIdRef.current !== projId) return;
      setIntelligence(intel);

      // 7. Reports
      const rep = await api.listReports(projId).catch(() => []);
      if (activeDeliverablesProjectIdRef.current !== projId) return;
      setReports(rep);

      // 8. Workforce Recommendations
      const recs = await api.getRecommendations(projId).catch(() => []);
      if (activeDeliverablesProjectIdRef.current !== projId) return;
      setRecommendations(recs);
    } catch {
      // Error recovery
    } finally {
      if (activeDeliverablesProjectIdRef.current === projId) {
        setBaselineLoading(false);
      }
    }
  }, []);

  // Global Tenant Data (Workforce, History, Admin)
  const loadGlobalTenantData = useCallback(async () => {
    try {
      const wf = await api.listWorkforce().catch(() => []);
      setWorkforce(wf);

      const hist = await api.getHistoricalCalibration().catch(() => null);
      setHistorical(hist);

      const u = await api.listAdminUsers().catch(() => []);
      setAdminUsers(u);

      const tc = await api.getTenantConfig().catch(() => null);
      setTenantConfig(tc);

      const al = await api.getAuditLogs().catch(() => []);
      setAuditLogs(al);

      const diag = await api.getDiagnostics().catch(() => null);
      setDiagnostics(diag);
    } catch {
      // Handled gracefully
    }
  }, []);

  // Initial mount
  useEffect(() => {
    const initialize = async () => {
      await initUser();
      await loadProjects();
      await loadGlobalTenantData();
    };
    initialize();
  }, [initUser, loadProjects, loadGlobalTenantData]);

  // When current project changes, load project deliverables and documents
  useEffect(() => {
    if (currentProject) {
      // Clear previous project's deliverables and set baselineLoading to true immediately
      setActiveBaseline(null);
      setBaselineLoading(true);
      setWbsOverview(null);
      setEstimate(null);
      setFeasibility(null);
      setExecutionSummary(null);
      setIntelligence(null);
      setReports([]);
      setRecommendations([]);

      loadProjectDeliverables(currentProject.id);
      loadDocuments(currentProject.id);
    } else {
      activeDeliverablesProjectIdRef.current = '';
      setActiveBaseline(null);
      setBaselineLoading(false);
      setWbsOverview(null);
      setEstimate(null);
      setFeasibility(null);
      setExecutionSummary(null);
      setIntelligence(null);
      setReports([]);
      setRecommendations([]);
      loadDocuments(undefined);
    }
  }, [currentProject, loadProjectDeliverables, loadDocuments]);

  // Handlers for Document & Requirements Intake
  const handleUploadSuccess = (_newDoc: DocumentDetail) => {
    loadDocuments();
  };

  const handleSelectDocument = async (docId: string) => {
    try {
      const detail = await api.getDocument(docId);
      setSelectedDoc(detail);
    } catch (err: any) {
      alert(`Could not load document preview: ${err.message}`);
    }
  };

  const handleExtractRequirements = async (doc: DocumentSummary) => {
    setExtractionError(null);
    setExtractingDocId(doc.id);
    try {
      // First check if a validated requirement draft already exists for this document
      const existingDrafts = await api.getDocumentDrafts(doc.id).catch(() => []);
      if (existingDrafts && existingDrafts.length > 0) {
        setActiveDraft(existingDrafts[0]);
        return;
      }
      const draft = await api.extractRequirements(doc.id);
      setActiveDraft(draft);
    } catch (err: any) {
      setExtractionError(err.message || 'AI extraction failed across all configured providers.');
    } finally {
      setExtractingDocId(null);
    }
  };

  const handleDeleteDocument = async (docId: string) => {
    if (!window.confirm('Are you sure you want to delete this document and its extracted content?')) {
      return;
    }
    try {
      await api.deleteDocument(docId);
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
      if (selectedDoc?.id === docId) setSelectedDoc(null);
      if (activeDraft?.document_id === docId) setActiveDraft(null);
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  const handleLogout = () => {
    api.logout();
    setCurrentUser(null);
    setCurrentProject(null);
    setProjects([]);
    setIsLoginModalOpen(true);
  };

  const handleLoginSuccess = async (user: UserProfile) => {
    setCurrentUser(user);
    setIsLoginModalOpen(false);
    await loadProjects();
    await loadGlobalTenantData();
  };

  // Metrics calculations for Document Intake
  const totalWords = documents.reduce((sum, d) => sum + (d.total_words || 0), 0);
  const completedDocs = documents.filter((d) => d.extraction_status === 'completed').length;
  const warningDocs = documents.filter((d) => d.extraction_status === 'warning').length;

  const currentProjectId = currentProject?.id || '';

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans selection:bg-indigo-500 selection:text-white">
      {/* Module Navigation Sidebar */}
      <Sidebar
        activeTab={activeTab}
        onTabChange={(tab) => setActiveTab(tab)}
        currentUser={currentUser}
        onLogout={handleLogout}
      />

      {/* Main Workspace Area */}
      <div className="flex-1 flex flex-col h-screen overflow-y-auto">
        {/* Top Header Bar */}
        <header className="border-b border-slate-800 bg-slate-900/40 backdrop-blur-md sticky top-0 z-30 px-8 py-3.5 flex items-center justify-between">
          <div className="flex items-center gap-4">
            {/* Active Project Dropdown */}
            <div className="flex items-center gap-2 bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200">
              <FolderKanban className="h-4 w-4 text-indigo-400" />
              <span className="text-slate-500">Project:</span>
              <select
                aria-label="Active Project"
                data-testid="project-selector-dropdown"
                value={currentProject?.id || ''}
                onChange={(e) => {
                  const selectedId = e.target.value;
                  if (!selectedId) {
                    setCurrentProject(null);
                  } else {
                    const p = projects.find((x) => x.id === selectedId);
                    if (p) setCurrentProject(p);
                  }
                }}
                disabled={projectsLoading}
                className="bg-transparent font-semibold text-white focus:outline-none cursor-pointer pr-1"
              >
                {projectsLoading ? (
                  <option value="" disabled className="bg-slate-900 text-slate-400">
                    Loading projects...
                  </option>
                ) : projectsError ? (
                  <option value="" disabled className="bg-slate-900 text-rose-400">
                    Error loading projects
                  </option>
                ) : projects.length === 0 ? (
                  <option value="" disabled className="bg-slate-900 text-slate-400">
                    No Projects Available
                  </option>
                ) : (
                  <>
                    <option value="" className="bg-slate-900 text-slate-400">
                      No Project Selected
                    </option>
                    {projects.map((p) => (
                      <option key={p.id} value={p.id} className="bg-slate-900 text-white">
                        {p.name}
                      </option>
                    ))}
                  </>
                )}
              </select>
            </div>

            <span className="hidden sm:inline-block text-[11px] text-slate-500 font-mono">
              Deterministic PERT &bull; CPM Engine &bull; Zero AI Hallucinations
            </span>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsLoginModalOpen(true)}
              className="text-xs text-indigo-400 hover:text-indigo-300 hover:underline font-medium cursor-pointer"
            >
              Switch User
            </button>
            <span className="text-xs bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 px-2.5 py-1 rounded-full font-semibold">
              {currentUser?.role === 'tenant_admin'
                ? 'Tenant Admin'
                : currentUser?.role === 'delivery_manager'
                ? 'Delivery Manager'
                : currentUser?.role === 'contributor'
                ? 'Contributor'
                : 'Project Lead'}
            </span>
          </div>
        </header>

        {/* Tab View Content */}
        <main className="p-8 max-w-7xl w-full mx-auto space-y-6">
          {/* TAB 1: EXECUTIVE DASHBOARD */}
          {activeTab === 'dashboard' && (
            <DashboardView
              currentProject={currentProject}
              estimate={estimate}
              feasibility={feasibility}
              execution={executionSummary}
              onNavigate={(tab) => setActiveTab(tab)}
            />
          )}

          {/* TAB 2: PROJECTS & INTAKE PORTFOLIO */}
          {activeTab === 'projects' && (
            <ProjectsView
              projects={projects}
              currentProjectId={currentProjectId}
              onSelectProject={(p) => setCurrentProject(p)}
              onRefresh={loadProjects}
              isLoading={projectsLoading}
              error={projectsError}
            />
          )}

          {/* TAB 3: DOCUMENT VAULT & INTAKE (DEFAULT) */}
          {activeTab === 'documents' && (
            <div className="space-y-8">
              {/* Module Header Banner */}
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-800/60">
                <div>
                  <div className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 mb-2">
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>Module 2 &bull; AI Requirement Extraction with Multi-Provider Fallback</span>
                  </div>
                  <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
                    Project Intake & AI Requirement Extraction
                  </h1>
                  <p className="text-sm text-slate-400 mt-1 max-w-2xl">
                    Upload project documents and trigger AI extraction. Sequential fallback executes across Google Gemini 2.5 Flash, xAI Grok, and NVIDIA NIM with strict Pydantic validation and human review.
                  </p>
                </div>

                {/* Quick Metrics Cards */}
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-left">
                    <div className="flex items-center space-x-1.5 text-xs text-slate-400 mb-1">
                      <Files className="w-3.5 h-3.5 text-indigo-400" />
                      <span>Documents</span>
                    </div>
                    <p className="text-xl font-bold text-white">{documents.length}</p>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-left">
                    <div className="flex items-center space-x-1.5 text-xs text-slate-400 mb-1">
                      <FileText className="w-3.5 h-3.5 text-emerald-400" />
                      <span>Total Words</span>
                    </div>
                    <p className="text-xl font-bold text-white">{totalWords.toLocaleString()}</p>
                  </div>

                  <div className="hidden sm:block p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-left">
                    <div className="flex items-center space-x-1.5 text-xs text-slate-400 mb-1">
                      <CheckCircle className="w-3.5 h-3.5 text-teal-400" />
                      <span>Status</span>
                    </div>
                    <p className="text-xs font-medium text-slate-300 mt-1">
                      <span className="text-emerald-400">{completedDocs} ready</span>
                      {warningDocs > 0 && <span className="text-amber-400">, {warningDocs} warn</span>}
                    </p>
                  </div>
                </div>
              </div>

              {/* Extraction Error Notice */}
              {extractionError && (
                <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start justify-between text-rose-300 text-sm">
                  <div className="flex items-start space-x-3">
                    <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-semibold text-rose-200">AI Requirement Extraction Failed</p>
                      <p className="text-xs text-rose-300/90 mt-1">{extractionError}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => setExtractionError(null)}
                    className="p-1 rounded text-rose-400 hover:text-white hover:bg-rose-500/20 transition"
                    title="Dismiss error"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              )}

              {/* Upload Zone */}
              <section aria-label="Document Upload Area">
                <DocumentUploadZone
                  onUploadSuccess={handleUploadSuccess}
                  projectId={currentProject?.id}
                />
              </section>

              {/* Document Repository List */}
              <section aria-label="Extracted Documents List">
                {docsLoading ? (
                  <div className="p-8 text-center text-slate-500">Loading cataloged documents...</div>
                ) : (
                  <DocumentList
                    documents={documents}
                    onSelect={handleSelectDocument}
                    onDelete={handleDeleteDocument}
                    onExtractRequirements={handleExtractRequirements}
                    extractingDocId={extractingDocId}
                  />
                )}
              </section>
            </div>
          )}

          {/* TAB 4: REQUIREMENTS BASELINE & APPROVAL */}
          {activeTab === 'requirements' && (
            <RequirementsView
              draft={activeDraft}
              baseline={activeBaseline}
              projectId={currentProjectId}
              onBaselineApproved={() => loadProjectDeliverables(currentProjectId)}
            />
          )}

          {/* TAB 5: WBS & PLANNING */}
          {activeTab === 'wbs' && (
            <WBSView
              overview={wbsOverview}
              projectId={currentProjectId}
              hasApprovedBaseline={Boolean(activeBaseline)}
              isBaselineLoading={baselineLoading}
              onRefresh={() => loadProjectDeliverables(currentProjectId)}
            />
          )}

          {/* TAB 6: ESTIMATION & SCHEDULE */}
          {activeTab === 'estimation' && (
            <EstimationView
              estimate={estimate}
              projectId={currentProjectId}
              onRefresh={() => loadProjectDeliverables(currentProjectId)}
            />
          )}

          {/* TAB 7: RISKS & FEASIBILITY */}
          {activeTab === 'risks' && (
            <RisksView
              overview={feasibility}
              projectId={currentProjectId}
              hasApprovedBaseline={Boolean(activeBaseline)}
              isBaselineLoading={baselineLoading}
              onRefresh={() => loadProjectDeliverables(currentProjectId)}
            />
          )}

          {/* TAB 8: WORKFORCE & TEAM RECOMMENDATIONS */}
          {activeTab === 'workforce' && (
            <WorkforceView
              workforce={workforce}
              recommendations={recommendations}
              projectId={currentProjectId}
              userRole={currentUser?.role}
              onRefresh={async () => {
                const [recs, wf] = await Promise.all([
                  api.getRecommendations(currentProjectId).catch(() => []),
                  api.listWorkforce().catch(() => []),
                ]);
                setRecommendations(recs);
                setWorkforce(wf);
              }}
            />
          )}

          {/* TAB 9: EXECUTION & PROGRESS */}
          {activeTab === 'execution' && (
            <ExecutionView
              summary={executionSummary}
              tasks={wbsOverview?.tasks || []}
              projectId={currentProjectId}
              onRefresh={() => loadProjectDeliverables(currentProjectId)}
            />
          )}

          {/* TAB 10: ANALYTICS & CALIBRATION */}
          {activeTab === 'analytics' && (
            <AnalyticsView
              intelligence={intelligence}
              historical={historical}
              projectId={currentProjectId}
            />
          )}

          {/* TAB 11: PDF REPORTS */}
          {activeTab === 'reports' && (
            <ReportsView
              reports={reports}
              projectId={currentProjectId}
              onRefresh={() => loadProjectDeliverables(currentProjectId)}
            />
          )}

          {/* TAB 12: ADMINISTRATION & AUDIT */}
          {activeTab === 'admin' && (
            <AdminView
              users={adminUsers}
              tenantConfig={tenantConfig}
              auditLogs={auditLogs}
              diagnostics={diagnostics}
            />
          )}
        </main>

        {/* Extracted Document Preview Modal */}
        <DocumentPreviewModal
          document={selectedDoc}
          onClose={() => setSelectedDoc(null)}
        />

        {/* AI Requirement Draft Review Modal */}
        <RequirementDraftModal
          draft={activeDraft}
          onClose={() => setActiveDraft(null)}
          onUpdateDraft={(updated) => setActiveDraft(updated)}
        />

        {/* Authentication & User Switching Modal */}
        <LoginModal
          isOpen={isLoginModalOpen || !currentUser}
          onClose={currentUser ? () => setIsLoginModalOpen(false) : undefined}
          onLoginSuccess={handleLoginSuccess}
        />
      </div>
    </div>
  );
};

export default App;
