import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { RisksView } from './RisksView';
import { api } from '../services/api';
import { FeasibilityOverview } from '../types/risk';

vi.mock('../services/api', () => ({
  api: {
    evaluateFeasibility: vi.fn(),
    getRisks: vi.fn(),
    updateRiskItem: vi.fn(),
  },
}));

const mockOverview: FeasibilityOverview = {
  overall_status: 'caution',
  overall_score: 74.5,
  summary: 'Project feasibility evaluated as CAUTION.',
  limitations: ['Pending SSO integration details', 'Database backup schedule not finalized'],
  dimensions: {
    schedule: { status: 'feasible', score: 88, notes: 'Fits comfortably within deadline.' },
    budget: { status: 'feasible', score: 92, notes: 'Within target budget.' },
    skills_capacity: { status: 'feasible', score: 88, notes: 'Required roles mapped.' },
    technical_dependencies: { status: 'feasible', score: 90, notes: 'DAG validated.' },
    scope_complexity: { status: 'caution', score: 65, notes: '1 unresolved contradiction.' },
    data_completeness: { status: 'caution', score: 68, notes: '2 open questions pending.' },
    operational_security: { status: 'feasible', score: 94, notes: 'Isolation enforced.' },
  },
  risks: [
    {
      id: 'risk-1',
      tenant_id: 'tenant-default',
      project_id: 'proj-1',
      risk_code: 'RSK-01',
      title: 'Third-Party Auth Latency',
      category: 'technical',
      description: 'External identity provider latency may impact login.',
      likelihood: 3,
      impact: 4,
      risk_score: 12,
      risk_level: 'high',
      supporting_evidence: '[AI-Extracted from Section 4] Identity service integration.',
      mitigation_strategy: 'Implement token cache.',
      risk_owner: 'Lead Architect',
      status: 'identified',
      source: 'ai_extracted',
      created_at: '2026-10-24T00:00:00Z',
    },
    {
      id: 'risk-2',
      tenant_id: 'tenant-default',
      project_id: 'proj-1',
      risk_code: 'RSK-SYS-OPS',
      title: 'Cloud Infrastructure Resilience',
      category: 'operational',
      description: 'Variable cloud latency under burst load.',
      likelihood: 2,
      impact: 3,
      risk_score: 6,
      risk_level: 'medium',
      supporting_evidence: '[System Policy] Multi-region retry policy.',
      mitigation_strategy: 'Configure exponential backoff.',
      risk_owner: 'DevOps Architect',
      status: 'mitigated',
      source: 'deterministic',
      created_at: '2026-10-24T00:00:00Z',
    },
  ],
};

describe('RisksView Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders empty state and guidance when no baseline is approved', () => {
    render(
      <RisksView
        overview={null}
        projectId="proj-unapproved"
        hasApprovedBaseline={false}
        isBaselineLoading={false}
        onRefresh={vi.fn()}
      />
    );

    // Baseline required notice must be visible
    expect(
      screen.getByText(/An approved requirements baseline is required\. Review and approve the requirements draft first\./i)
    ).toBeInTheDocument();

    // Evaluation button must be disabled
    const evalButtons = screen.getAllByRole('button', { name: /Run Feasibility Audit/i });
    expect(evalButtons[0]).toBeDisabled();
  });

  it('enables audit button when baseline is approved and triggers evaluateFeasibility', async () => {
    const onRefresh = vi.fn();
    (api.evaluateFeasibility as any).mockResolvedValueOnce(mockOverview);

    render(
      <RisksView
        overview={null}
        projectId="proj-approved"
        hasApprovedBaseline={true}
        isBaselineLoading={false}
        onRefresh={onRefresh}
      />
    );

    const evalButtons = screen.getAllByRole('button', { name: /Run Feasibility Audit/i });
    expect(evalButtons[0]).toBeEnabled();

    fireEvent.click(evalButtons[0]);
    await waitFor(() => {
      expect(api.evaluateFeasibility).toHaveBeenCalledWith('proj-approved');
      expect(onRefresh).toHaveBeenCalled();
    });
  });

  it('renders executive summary, 7 dimensions, and limitations when overview exists', () => {
    render(
      <RisksView
        overview={mockOverview}
        projectId="proj-1"
        hasApprovedBaseline={true}
        isBaselineLoading={false}
        onRefresh={vi.fn()}
      />
    );

    // Overall score
    expect(screen.getByText('74.5')).toBeInTheDocument();
    expect(screen.getByText(/Overall Project Feasibility/i)).toBeInTheDocument();

    // Limitations
    expect(screen.getByText('Pending SSO integration details')).toBeInTheDocument();
    expect(screen.getByText('Database backup schedule not finalized')).toBeInTheDocument();

    // 7 Dimensions rendered
    expect(screen.getByText('Schedule Feasibility')).toBeInTheDocument();
    expect(screen.getByText('Budget & Cost Feasibility')).toBeInTheDocument();
    expect(screen.getByText('Skills & Capacity')).toBeInTheDocument();
    expect(screen.getByText('Technical Dependencies')).toBeInTheDocument();
    expect(screen.getByText('Scope Complexity')).toBeInTheDocument();
    expect(screen.getByText('Data Completeness')).toBeInTheDocument();
    expect(screen.getByText('Operational & Security Risks')).toBeInTheDocument();
  });

  it('renders risk register table with AI vs Deterministic tags, evidence, and allows status updating', async () => {
    const onRefresh = vi.fn();
    (api.updateRiskItem as any).mockResolvedValueOnce({ ...mockOverview.risks[0], status: 'mitigated' });

    render(
      <RisksView
        overview={mockOverview}
        projectId="proj-1"
        hasApprovedBaseline={true}
        isBaselineLoading={false}
        onRefresh={onRefresh}
      />
    );

    // Risk items
    expect(screen.getByText('RSK-01')).toBeInTheDocument();
    expect(screen.getByText('Third-Party Auth Latency')).toBeInTheDocument();
    expect(screen.getByText('AI Suggestion')).toBeInTheDocument();

    expect(screen.getByText('RSK-SYS-OPS')).toBeInTheDocument();
    expect(screen.getByText('Cloud Infrastructure Resilience')).toBeInTheDocument();
    expect(screen.getByText('Deterministic')).toBeInTheDocument();

    // Evidence / Rationale block
    expect(screen.getByText(/\[AI-Extracted from Section 4\] Identity service integration\./i)).toBeInTheDocument();
    expect(screen.getByText(/\[System Policy\] Multi-region retry policy\./i)).toBeInTheDocument();

    // Status select interaction
    const statusSelects = screen.getAllByRole('combobox');
    // First combobox is filter, subsequent are row status dropdowns
    const rowSelect = statusSelects[1];
    fireEvent.change(rowSelect, { target: { value: 'mitigated' } });

    await waitFor(() => {
      expect(api.updateRiskItem).toHaveBeenCalledWith('risk-1', { status: 'mitigated' });
      expect(onRefresh).toHaveBeenCalled();
    });
  });

  it('filters risks by category correctly', () => {
    render(
      <RisksView
        overview={mockOverview}
        projectId="proj-1"
        hasApprovedBaseline={true}
        isBaselineLoading={false}
        onRefresh={vi.fn()}
      />
    );

    // Initial table shows both
    expect(screen.getByText('RSK-01')).toBeInTheDocument();
    expect(screen.getByText('RSK-SYS-OPS')).toBeInTheDocument();

    // Filter by 'operational'
    const filterSelect = screen.getByTestId('risk-category-filter');
    fireEvent.change(filterSelect, { target: { value: 'operational' } });

    // Only operational risk is displayed
    expect(screen.queryByText('RSK-01')).not.toBeInTheDocument();
    expect(screen.getByText('RSK-SYS-OPS')).toBeInTheDocument();
  });
});
