import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import App from './App';

const mockProjects = [
  {
    id: 'proj-001',
    tenant_id: 'tenant-default',
    name: 'Cloud Migration & Core Platform Modernization',
    description: 'Enterprise Kubernetes migration initiative.',
    status: 'planning',
    target_budget: 250000,
    currency: 'USD',
    target_deadline: '2026-12-15',
    active_baseline_version: '1',
    document_count: 5,
    task_count: 12,
    total_pert_hours: 320,
    total_cost: 45000,
    created_at: '2026-10-23T14:48:26Z',
  },
  {
    id: 'proj-002',
    tenant_id: 'tenant-default',
    name: 'OmniChannel Banking Migration',
    description: 'Cloud core ledger modernization with automated compliance.',
    status: 'intake',
    target_budget: 300000,
    currency: 'USD',
    target_deadline: '2026-12-15',
    active_baseline_version: '0',
    document_count: 1,
    task_count: 0,
    total_pert_hours: 0,
    total_cost: 0,
    created_at: '2026-10-23T18:11:54Z',
  },
];

beforeEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

function setupMockFetch(options: {
  projects?: any[];
  projectsFail?: boolean;
  baselines?: Record<string, any>;
} = {}) {
  global.fetch = vi.fn().mockImplementation((url: string) => {
    if (url.includes('/api/health')) {
      return Promise.resolve({
        ok: true,
        json: async () => ({
          status: 'healthy',
          app: 'DevMatrix AI',
          database: 'connected',
        }),
      });
    }

    if (url.includes('/api/auth/login')) {
      return Promise.resolve({
        ok: true,
        json: async () => ({
          access_token: 'mock-jwt-token',
          token_type: 'Bearer',
          user: {
            id: 'usr-manager-01',
            email: 'manager@devmatrix.local',
            full_name: 'Alex Morgan (Delivery Manager)',
            role: 'delivery_manager',
            tenant_id: 'tenant-default',
            tenant_name: 'Acme Enterprise Delivery',
          },
        }),
      });
    }

    if (url.includes('/api/auth/me')) {
      return Promise.resolve({
        ok: true,
        json: async () => ({
          id: 'usr-manager-01',
          email: 'manager@devmatrix.local',
          full_name: 'Alex Morgan (Delivery Manager)',
          role: 'delivery_manager',
          tenant_id: 'tenant-default',
          tenant_name: 'Acme Enterprise Delivery',
        }),
      });
    }

    if (url.includes('/api/projects')) {
      if (options.projectsFail) {
        return Promise.resolve({
          ok: false,
          status: 500,
          json: async () => ({ detail: 'Internal Database Error' }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () => (options.projects !== undefined ? options.projects : mockProjects),
      });
    }

    if (url.includes('/api/requirements/baseline/')) {
      const parts = url.split('/');
      const projId = parts[parts.length - 1];
      if (options.baselines && options.baselines[projId]) {
        return Promise.resolve({
          ok: true,
          json: async () => options.baselines![projId],
        });
      }
      return Promise.resolve({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'No active baseline found' }),
      });
    }

    if (url.includes('/api/wbs/')) {
      return Promise.resolve({
        ok: true,
        json: async () => ({
          project_id: 'any',
          tasks: [],
          dependencies: [],
          total_pert_hours: 0,
          critical_path_hours: 0,
          is_dag_valid: true,
        }),
      });
    }

    if (url.includes('/api/documents')) {
      return Promise.resolve({
        ok: true,
        json: async () => [
          {
            id: 'doc-123',
            original_filename: 'project_charter.pdf',
            file_type: 'pdf',
            file_size_bytes: 1048576,
            extraction_status: 'completed',
            total_pages: 3,
            total_words: 1250,
            has_text: true,
            created_at: new Date().toISOString(),
          },
        ],
      });
    }

    return Promise.resolve({
      ok: true,
      json: async () => [],
    });
  }) as any;
}

describe('DevMatrix AI Module 1 & 2 Frontend', () => {
  beforeEach(() => {
    setupMockFetch();
  });

  it('renders application branding and intake & requirement extraction header', async () => {
    render(<App />);

    expect(screen.getAllByText(/DevMatrix AI/i).length).toBeGreaterThan(0);
    expect(
      screen.getByText(/Project Intake & AI Requirement Extraction/i)
    ).toBeInTheDocument();
  });

  it('renders upload zone with supported formats', async () => {
    render(<App />);

    expect(
      screen.getByText(/Drop project documents here or click to browse/i)
    ).toBeInTheDocument();
    expect(screen.getByText('PDF')).toBeInTheDocument();
    expect(screen.getByText('DOCX')).toBeInTheDocument();
    expect(screen.getByText('XLSX')).toBeInTheDocument();
  });

  it('renders document list with fetched documents, preview trigger, and AI Reqs button', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('project_charter.pdf')).toBeInTheDocument();
      expect(screen.getByText(/1[,.]?250 words/i)).toBeInTheDocument();
      expect(screen.getAllByText(/Extracted/i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getByRole('button', { name: /Preview/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /AI Reqs/i })).toBeInTheDocument();
    });
  });
});

describe('Project List and Selection State Integration', () => {
  it('loads project options from backend and populates the project selector', async () => {
    setupMockFetch({ projects: mockProjects });
    render(<App />);

    const select = await screen.findByTestId('project-selector-dropdown');
    await waitFor(() => {
      expect(select).not.toBeDisabled();
    });

    expect(screen.getByRole('option', { name: 'Cloud Migration & Core Platform Modernization' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'OmniChannel Banking Migration' })).toBeInTheDocument();
    expect((select as HTMLSelectElement).value).toBe('proj-001');
  });

  it('synchronizes selection when choosing a project in the dropdown', async () => {
    setupMockFetch({ projects: mockProjects });
    render(<App />);

    const select = await screen.findByTestId('project-selector-dropdown');
    await waitFor(() => {
      expect(select).not.toBeDisabled();
    });

    // Select second project
    fireEvent.change(select, { target: { value: 'proj-002' } });
    expect((select as HTMLSelectElement).value).toBe('proj-002');

    // Switch to Dashboard and verify project title is synchronized
    const dashboardNavBtn = screen.getByRole('button', { name: /Dashboard/i });
    fireEvent.click(dashboardNavBtn);

    expect(screen.getByRole('heading', { name: 'OmniChannel Banking Migration' })).toBeInTheDocument();
  });

  it('handles empty project list by displaying No Projects Available and No Project Selected', async () => {
    setupMockFetch({ projects: [] });
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('No Projects Available')).toBeInTheDocument();
    });

    // Switch to Dashboard and verify "No Project Selected" banner
    const dashboardNavBtn = screen.getByRole('button', { name: /Dashboard/i });
    fireEvent.click(dashboardNavBtn);

    expect(screen.getByText('No Project Selected')).toBeInTheDocument();
  });

  it('handles API failure by showing Error loading projects without fake project data', async () => {
    setupMockFetch({ projectsFail: true });
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Error loading projects')).toBeInTheDocument();
    });

    // Verify fake project text is NOT rendered
    expect(screen.queryByText('Cloud Modernization Core')).not.toBeInTheDocument();

    // Switch to Dashboard and verify "No Project Selected" is shown
    const dashboardNavBtn = screen.getByRole('button', { name: /Dashboard/i });
    fireEvent.click(dashboardNavBtn);

    expect(screen.getByText('No Project Selected')).toBeInTheDocument();
  });

  it('updates WBS baseline guidance on project switch and never reuses previous project approval state', async () => {
    // proj-001 has an approved baseline; proj-002 has NO approved baseline
    const mockBaseline = {
      id: 'bl-001',
      tenant_id: 'tenant-default',
      project_id: 'proj-001',
      version: 1,
      is_active: true,
      requirements_data_json: JSON.stringify({ functional_requirements: [] }),
    };

    setupMockFetch({
      projects: mockProjects,
      baselines: {
        'proj-001': mockBaseline,
      },
    });

    render(<App />);

    // Switch to WBS tab on proj-001 (which has active baseline)
    const wbsNavBtn = screen.getByRole('button', { name: /WBS & Planning/i });
    fireEvent.click(wbsNavBtn);

    const generateBtn = await screen.findByRole('button', { name: /Generate WBS from Baseline/i });
    await waitFor(() => {
      expect(generateBtn).toBeEnabled();
    });
    expect(screen.queryByTestId('wbs-baseline-guidance-banner')).not.toBeInTheDocument();

    // Now switch project to proj-002 (OmniChannel / unapproved baseline)
    const select = screen.getByTestId('project-selector-dropdown');
    fireEvent.change(select, { target: { value: 'proj-002' } });

    // Verify button becomes disabled and guidance banner appears
    await waitFor(() => {
      expect(generateBtn).toBeDisabled();
      expect(screen.getByTestId('wbs-baseline-guidance-banner')).toBeInTheDocument();
    });
    expect(
      screen.getAllByText(/An approved requirements baseline is required\. Review and approve the requirements draft first\./i).length
    ).toBeGreaterThanOrEqual(1);

    // Switch back to proj-001
    fireEvent.change(select, { target: { value: 'proj-001' } });
    await waitFor(() => {
      expect(generateBtn).toBeEnabled();
      expect(screen.queryByTestId('wbs-baseline-guidance-banner')).not.toBeInTheDocument();
    });
  });
});
