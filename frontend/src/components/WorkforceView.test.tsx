import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { WorkforceView } from './WorkforceView';
import { api } from '../services/api';
import {
  WorkforceMember,
  TeamRecommendation,
  TeamCapacitySummary,
  SkillGapAnalysis,
} from '../types/workforce';

vi.mock('../services/api', () => ({
  api: {
    generateRecommendations: vi.fn(),
    approveRecommendation: vi.fn(),
    rejectRecommendation: vi.fn(),
    selectAlternativeCandidate: vi.fn(),
    listWorkforce: vi.fn(),
    getWorkforceCapacity: vi.fn(),
    getSkillGapAnalysis: vi.fn(),
    createWorkforceMember: vi.fn(),
    getWorkforceMember: vi.fn(),
    updateWorkforceMember: vi.fn(),
    activateWorkforceMember: vi.fn(),
    deactivateWorkforceMember: vi.fn(),
    correctMemberScore: vi.fn(),
    getMemberScoreHistory: vi.fn(),
    getMemberEvidence: vi.fn(),
  },
}));

const mockMembers: WorkforceMember[] = [
  {
    id: 'wf-1',
    tenant_id: 'tenant-default',
    full_name: 'Elena Rostova',
    role: 'Senior Full-Stack Engineer',
    hourly_rate: 100.0,
    currency: 'USD',
    skills: ['Python', 'FastAPI', 'React', 'TypeScript'],
    experience_years: 6.0,
    availability_pct: 90.0,
    max_weekly_hours: 40.0,
    active_projects_count: 1,
  },
  {
    id: 'wf-2',
    tenant_id: 'tenant-default',
    full_name: 'David Chen',
    role: 'Solutions Architect',
    hourly_rate: 135.0,
    currency: 'USD',
    skills: ['Architecture', 'System Design', 'Security'],
    experience_years: 9.0,
    availability_pct: 85.0,
    max_weekly_hours: 40.0,
    active_projects_count: 0,
  },
];

const mockRecommendations: TeamRecommendation[] = [
  {
    id: 'rec-1',
    tenant_id: 'tenant-default',
    project_id: 'proj-1',
    task_id: 'task-1',
    task_code: 'TSK-1.1',
    task_title: 'API Architecture Specification',
    role_needed: 'Solutions Architect',
    candidate_id: 'wf-2',
    candidate_name: 'David Chen',
    match_score: 91.5,
    skill_score: 95.0,
    availability_score: 85.0,
    experience_score: 90.0,
    workload_score: 100.0,
    rationale: 'Candidate David Chen exhibits 95% skill alignment (Architecture, System Design, Security), 85% availability, and 9.0 years experience.',
    is_synthetic: false,
    manager_status: 'proposed',
    created_at: '2026-10-24T00:00:00Z',
    alternatives: [
      {
        candidate_id: 'wf-1',
        candidate_name: 'Elena Rostova',
        role: 'Senior Full-Stack Engineer',
        hourly_rate: 100.0,
        match_score: 74.0,
        skill_score: 70.0,
        availability_score: 90.0,
        experience_score: 60.0,
        workload_score: 80.0,
        rationale: 'Candidate Elena Rostova exhibits 70% skill alignment, 90% availability, and 6.0 years experience.',
      },
    ],
  },
  {
    id: 'rec-2',
    tenant_id: 'tenant-default',
    project_id: 'proj-1',
    task_id: 'task-2',
    task_code: 'TSK-2.1',
    task_title: 'Cloud Deployment Pipeline',
    role_needed: 'Cloud DevOps Architect',
    candidate_id: 'syn-cloud-devops',
    candidate_name: '[Synthetic Demo] Cloud DevOps Architect Benchmark',
    match_score: 75.0,
    skill_score: 70.0,
    availability_score: 80.0,
    experience_score: 80.0,
    workload_score: 80.0,
    rationale: '[Synthetic Demo Dataset] Real workforce data is not configured for tenant. Generated baseline role specification.',
    is_synthetic: true,
    manager_status: 'proposed',
    created_at: '2026-10-24T00:00:00Z',
  },
];

const mockCapacityData: TeamCapacitySummary = {
  project_id: 'proj-1',
  total_members: 2,
  total_nominal_capacity_hours: 70.0,
  total_planned_effort_hours: 88.0,
  total_actual_effort_hours: 12.0,
  team_utilization_pct: 125.7,
  overallocated_members_count: 1,
  overallocated_members: ['Elena Rostova'],
  optimal_count: 1,
  underutilized_count: 0,
  members: [
    {
      member_id: 'wf-1',
      full_name: 'Elena Rostova',
      role: 'Senior Full-Stack Engineer',
      hourly_rate: 100.0,
      skills: ['Python', 'FastAPI'],
      experience_years: 6.0,
      max_weekly_hours: 40.0,
      availability_pct: 90.0,
      nominal_weekly_hours: 36.0,
      assigned_tasks_count: 3,
      total_planned_hours: 52.0,
      total_actual_effort_hours: 8.0,
      global_planned_hours: 52.0,
      utilization_pct: 144.4,
      is_overallocated: true,
      overallocated_hours: 16.0,
      remaining_capacity_hours: 0.0,
      status_level: 'overallocated',
      assigned_tasks: [
        {
          task_id: 't-1',
          task_code: 'TSK-1.1',
          title: 'Database Schema Design',
          status: 'in_progress',
          expected_hours: 24.0,
          actual_hours: 8.0,
          progress_percentage: 33.0,
        },
      ],
    } as any,
    {
      member_id: 'wf-2',
      full_name: 'David Chen',
      role: 'Solutions Architect',
      hourly_rate: 135.0,
      skills: ['Architecture'],
      experience_years: 9.0,
      max_weekly_hours: 40.0,
      availability_pct: 85.0,
      nominal_weekly_hours: 34.0,
      assigned_tasks_count: 1,
      total_planned_hours: 26.0,
      total_actual_effort_hours: 4.0,
      global_planned_hours: 26.0,
      utilization_pct: 76.5,
      is_overallocated: false,
      overallocated_hours: 0.0,
      remaining_capacity_hours: 8.0,
      status_level: 'optimal',
      assigned_tasks: [],
    } as any,
  ],
};

const mockSkillGapData: SkillGapAnalysis = {
  project_id: 'proj-1',
  total_skills_required: 5,
  covered_skills_count: 3,
  scarce_skills_count: 1,
  missing_skills_count: 1,
  skill_coverage_score: 70.0,
  health_status: 'moderate',
  skills: [
    {
      skill: 'Kubernetes',
      tasks_count: 2,
      tasks: [
        { task_id: 't-1', task_code: 'TSK-2.1', title: 'Cluster Setup', required_role: 'DevOps' },
      ],
      qualified_count: 0,
      qualified_members: [],
      coverage_status: 'missing',
    },
    {
      skill: 'Architecture',
      tasks_count: 1,
      tasks: [
        { task_id: 't-2', task_code: 'TSK-1.1', title: 'Architecture Review', required_role: 'Architect' },
      ],
      qualified_count: 1,
      qualified_members: [
        { id: 'wf-2', name: 'David Chen', role: 'Solutions Architect', experience_years: 9.0, availability_pct: 85.0 },
      ],
      coverage_status: 'scarce',
    },
    {
      skill: 'Python',
      tasks_count: 3,
      tasks: [],
      qualified_count: 2,
      qualified_members: [
        { id: 'wf-1', name: 'Elena Rostova', role: 'Senior Full-Stack Engineer', experience_years: 6.0, availability_pct: 90.0 },
      ],
      coverage_status: 'covered',
    },
  ],
  upskilling_signals: [
    'Critical Competency Gaps: 1 skill(s) (Kubernetes) have 0 qualified in-house profiles.',
    'Single Point of Failure: 1 skill(s) (Architecture) are covered by only a single contributor.',
  ],
};

describe('WorkforceView Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders empty state when no recommendations are available and triggers generate on click', async () => {
    const onRefresh = vi.fn();
    (api.generateRecommendations as any).mockResolvedValueOnce(mockRecommendations);
    (api.getWorkforceCapacity as any).mockResolvedValue(mockCapacityData);
    (api.getSkillGapAnalysis as any).mockResolvedValue(mockSkillGapData);

    render(
      <WorkforceView
        workforce={mockMembers}
        recommendations={[]}
        projectId="proj-1"
        onRefresh={onRefresh}
      />
    );

    expect(screen.getByText(/No Recommendations Generated Yet/i)).toBeInTheDocument();

    const generateBtn = screen.getByRole('button', { name: /Generate Team Candidates/i });
    fireEvent.click(generateBtn);

    await waitFor(() => {
      expect(api.generateRecommendations).toHaveBeenCalledWith('proj-1');
      expect(onRefresh).toHaveBeenCalled();
    });
  });

  it('renders recommendation cards with task code, title, 4-factor scores, and synthetic demo badge', () => {
    render(
      <WorkforceView
        workforce={mockMembers}
        recommendations={mockRecommendations}
        projectId="proj-1"
        onRefresh={vi.fn()}
      />
    );

    // Card 1: Verified Candidate
    expect(screen.getByText('TSK-1.1')).toBeInTheDocument();
    expect(screen.getByText(/API Architecture Specification/i)).toBeInTheDocument();
    expect(screen.getByText('David Chen')).toBeInTheDocument();
    expect(screen.getByText('91.5%')).toBeInTheDocument();
    expect(screen.getByText('95%')).toBeInTheDocument(); // skill score

    // Card 2: Synthetic Demo Candidate
    expect(screen.getByText('TSK-2.1')).toBeInTheDocument();
    expect(screen.getByText(/Cloud Deployment Pipeline/i)).toBeInTheDocument();
    expect(screen.getByText('[Synthetic Demo] Cloud DevOps Architect Benchmark')).toBeInTheDocument();
    expect(screen.getByText('Synthetic Demo')).toBeInTheDocument();
  });

  it('allows manager to approve a recommendation and calls api.approveRecommendation', async () => {
    const onRefresh = vi.fn();
    (api.approveRecommendation as any).mockResolvedValueOnce({
      ...mockRecommendations[0],
      manager_status: 'approved',
    });
    (api.getWorkforceCapacity as any).mockResolvedValue(mockCapacityData);

    render(
      <WorkforceView
        workforce={mockMembers}
        recommendations={mockRecommendations}
        projectId="proj-1"
        onRefresh={onRefresh}
      />
    );

    const approveButtons = screen.getAllByRole('button', { name: /Accept & Assign/i });
    expect(approveButtons.length).toBe(2);

    fireEvent.click(approveButtons[0]);

    await waitFor(() => {
      expect(api.approveRecommendation).toHaveBeenCalledWith('rec-1');
      expect(onRefresh).toHaveBeenCalled();
    });
  });

  it('allows manager to reject a recommendation and calls api.rejectRecommendation', async () => {
    const onRefresh = vi.fn();
    (api.rejectRecommendation as any).mockResolvedValueOnce({
      ...mockRecommendations[0],
      manager_status: 'rejected',
    });
    (api.getWorkforceCapacity as any).mockResolvedValue(mockCapacityData);

    render(
      <WorkforceView
        workforce={mockMembers}
        recommendations={mockRecommendations}
        projectId="proj-1"
        onRefresh={onRefresh}
      />
    );

    const rejectButtons = screen.getAllByRole('button', { name: /Reject/i });
    expect(rejectButtons.length).toBe(2);

    fireEvent.click(rejectButtons[0]);

    await waitFor(() => {
      expect(api.rejectRecommendation).toHaveBeenCalledWith('rec-1', expect.any(String));
      expect(onRefresh).toHaveBeenCalled();
    });
  });

  it('allows manager to expand runner-up alternatives and select an alternative candidate', async () => {
    const onRefresh = vi.fn();
    (api.selectAlternativeCandidate as any).mockResolvedValueOnce({
      ...mockRecommendations[0],
      candidate_id: 'wf-1',
      candidate_name: 'Elena Rostova',
      match_score: 74.0,
      manager_status: 'approved',
    });
    (api.getWorkforceCapacity as any).mockResolvedValue(mockCapacityData);

    render(
      <WorkforceView
        workforce={mockMembers}
        recommendations={mockRecommendations}
        projectId="proj-1"
        onRefresh={onRefresh}
      />
    );

    const expandAltBtn = screen.getByRole('button', { name: /1 Alternative Candidates Evaluated/i });
    fireEvent.click(expandAltBtn);

    expect(screen.getByText('Elena Rostova')).toBeInTheDocument();
    expect(screen.getByText('74% fit')).toBeInTheDocument();

    const selectAltBtn = screen.getByRole('button', { name: /Select Alternative/i });
    fireEvent.click(selectAltBtn);

    await waitFor(() => {
      expect(api.selectAlternativeCandidate).toHaveBeenCalledWith(
        'rec-1',
        'wf-1',
        expect.stringContaining('Elena Rostova')
      );
      expect(onRefresh).toHaveBeenCalled();
    });
  });

  it('switches to Workload & Capacity subtab and displays capacity metrics and over-allocation alert', async () => {
    (api.getWorkforceCapacity as any).mockResolvedValueOnce(mockCapacityData);

    render(
      <WorkforceView
        workforce={mockMembers}
        recommendations={mockRecommendations}
        projectId="proj-1"
        onRefresh={vi.fn()}
      />
    );

    const capacityTabBtn = screen.getByRole('button', { name: /Workload & Capacity/i });
    fireEvent.click(capacityTabBtn);

    await waitFor(() => {
      expect(api.getWorkforceCapacity).toHaveBeenCalledWith('proj-1');
    });

    expect(await screen.findByText('70h')).toBeInTheDocument(); // total nominal capacity
    expect(screen.getByText('88h')).toBeInTheDocument(); // planned project effort
    expect(screen.getByText('125.7%')).toBeInTheDocument(); // utilization pct
    expect(screen.getByText(/Capacity Warning:/i)).toBeInTheDocument();
    expect(screen.getByText(/144.4%/i)).toBeInTheDocument(); // Elena's utilization
    expect(screen.getByText(/\+16h over/i)).toBeInTheDocument();
  });

  it('switches to Skill Gap Matrix subtab and displays coverage score and upskilling signals', async () => {
    (api.getSkillGapAnalysis as any).mockResolvedValueOnce(mockSkillGapData);

    render(
      <WorkforceView
        workforce={mockMembers}
        recommendations={mockRecommendations}
        projectId="proj-1"
        onRefresh={vi.fn()}
      />
    );

    const skillGapsTabBtn = screen.getByRole('button', { name: /Skill Gap Matrix/i });
    fireEvent.click(skillGapsTabBtn);

    await waitFor(() => {
      expect(api.getSkillGapAnalysis).toHaveBeenCalledWith('proj-1');
    });

    expect(await screen.findByText('moderate coverage')).toBeInTheDocument();
    expect((await screen.findAllByText('70%')).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Kubernetes')).toBeInTheDocument();
    expect(screen.getByText('missing')).toBeInTheDocument();
    expect(screen.getByText('scarce')).toBeInTheDocument();
    expect(screen.getByText(/Critical Competency Gaps: 1 skill\(s\) \(Kubernetes\)/i)).toBeInTheDocument();
  });

  it('toggles to Talent Directory subtab and lists verified contributors', () => {
    render(
      <WorkforceView
        workforce={mockMembers}
        recommendations={mockRecommendations}
        projectId="proj-1"
        onRefresh={vi.fn()}
      />
    );

    const directoryTabBtn = screen.getByRole('button', { name: /Talent Directory \(2\)/i });
    fireEvent.click(directoryTabBtn);

    expect(screen.getByText('Talent Directory & Capacity Registry')).toBeInTheDocument();
    expect(screen.getByText('Elena Rostova')).toBeInTheDocument();
    expect(screen.getByText('Senior Full-Stack Engineer')).toBeInTheDocument();
    expect(screen.getByText('$100.00/hr')).toBeInTheDocument();
    expect(screen.getByText('David Chen')).toBeInTheDocument();
    expect(screen.getByText('$135.00/hr')).toBeInTheDocument();
  });

  it('allows delivery manager to open onboarding modal and onboard a new contributor with skills and proficiencies', async () => {
    const onRefresh = vi.fn();
    (api.createWorkforceMember as any).mockResolvedValueOnce({
      id: 'wf-new',
      tenant_id: 'tenant-default',
      full_name: 'Alex Mercer',
      role: 'Full-Stack Engineer',
      hourly_rate: 95.0,
      currency: 'USD',
      skills: ['Python', 'FastAPI', 'React'],
      skill_proficiencies: { Python: 'Advanced', FastAPI: 'Advanced', React: 'Intermediate' },
      experience_years: 5.0,
      availability_pct: 100.0,
      max_weekly_hours: 40.0,
      initial_assessed_score: 85.0,
      performance_score: null,
      has_sufficient_evidence: false,
      is_active: true,
      is_synthetic: false,
    });

    render(
      <WorkforceView
        workforce={mockMembers}
        recommendations={mockRecommendations}
        projectId="proj-1"
        userRole="delivery_manager"
        onRefresh={onRefresh}
      />
    );

    // Click Top Banner "Onboard Member" button
    const onboardBtn = screen.getByRole('button', { name: /Onboard Member/i });
    fireEvent.click(onboardBtn);

    expect(screen.getByText('Onboard Team Contributor')).toBeInTheDocument();
    expect(screen.getByText(/Insufficient performance history/i)).toBeInTheDocument();

    // Fill in the contributor form
    const nameInput = screen.getByPlaceholderText(/e\.g\. Jordan Blake/i);
    fireEvent.change(nameInput, { target: { value: 'Alex Mercer' } });

    const submitBtn = screen.getByRole('button', { name: /Onboard Contributor/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.createWorkforceMember).toHaveBeenCalledWith(
        expect.objectContaining({
          full_name: 'Alex Mercer',
          role: 'Full-Stack Engineer',
          hourly_rate: 95,
          initial_assessed_score: 85,
        })
      );
      expect(onRefresh).toHaveBeenCalled();
    });
  });

  it('allows delivery manager to toggle member active and deactivate status', async () => {
    const onRefresh = vi.fn();
    (api.deactivateWorkforceMember as any).mockResolvedValueOnce({
      ...mockMembers[0],
      is_active: false,
    });

    render(
      <WorkforceView
        workforce={mockMembers}
        recommendations={mockRecommendations}
        projectId="proj-1"
        userRole="delivery_manager"
        onRefresh={onRefresh}
      />
    );

    // Switch to Talent Directory tab
    const dirTabBtn = screen.getByRole('button', { name: /Talent Directory \(2\)/i });
    fireEvent.click(dirTabBtn);

    const deactivateBtns = screen.getAllByRole('button', { name: /Deactivate/i });
    expect(deactivateBtns.length).toBeGreaterThanOrEqual(1);

    fireEvent.click(deactivateBtns[0]);

    await waitFor(() => {
      expect(api.deactivateWorkforceMember).toHaveBeenCalledWith('wf-1');
      expect(onRefresh).toHaveBeenCalled();
    });
  });

  it('allows manager to view score history, contributing evidence, and submit an authorized correction', async () => {
    const onRefresh = vi.fn();
    (api.getMemberScoreHistory as any).mockResolvedValue([
      {
        id: 'hist-1',
        member_id: 'wf-1',
        score_version: 1,
        performance_score: 92.0,
        has_sufficient_evidence: true,
        delivery_score: 94.0,
        quality_score: 90.0,
        formula_version: 'v2.0-deterministic-outcomes',
        is_manual_correction: false,
        created_at: '2026-10-24T00:00:00Z',
      },
    ]);
    (api.getMemberEvidence as any).mockResolvedValue([
      {
        id: 'ev-1',
        member_id: 'wf-1',
        project_id: 'proj-1',
        task_id: 't-1',
        task_code: 'TSK-1.1',
        event_type: 'task_completed',
        planned_hours: 20.0,
        actual_hours: 18.0,
        effort_variance_ratio: -0.1,
        on_schedule: true,
        was_blocked_externally: false,
        quality_outcome: 'passed',
        evidence_notes: 'Completed ahead of schedule with zero defects',
        created_at: '2026-10-24T00:00:00Z',
      },
    ]);
    (api.correctMemberScore as any).mockResolvedValue({
      id: 'hist-2',
      member_id: 'wf-1',
      score_version: 2,
      performance_score: 97.0,
      has_sufficient_evidence: true,
      delivery_score: 94.0,
      quality_score: 90.0,
      is_manual_correction: true,
      correction_reason: 'Post-launch client retrospective verified exceptional quality.',
      created_at: '2026-10-24T00:00:00Z',
    });

    render(
      <WorkforceView
        workforce={mockMembers}
        recommendations={mockRecommendations}
        projectId="proj-1"
        userRole="delivery_manager"
        onRefresh={onRefresh}
      />
    );

    // Switch to Directory
    const dirTabBtn = screen.getByRole('button', { name: /Talent Directory \(2\)/i });
    fireEvent.click(dirTabBtn);

    // Click History button on first member
    const historyBtns = screen.getAllByRole('button', { name: /History/i });
    fireEvent.click(historyBtns[0]);

    // Check modal displays Elena Rostova
    expect(await screen.findByText('v1')).toBeInTheDocument();
    expect(screen.getByText('92.0% Score')).toBeInTheDocument();

    // Check Contributing Evidence subtab
    const evidenceTabBtn = screen.getByRole('button', { name: /Contributing Evidence/i });
    fireEvent.click(evidenceTabBtn);
    expect(screen.getByText('TSK-1.1')).toBeInTheDocument();
    expect(screen.getByText(/Completed ahead of schedule with zero defects/i)).toBeInTheDocument();

    // Check Authorized Correction subtab
    const correctionTabBtn = screen.getByRole('button', { name: /Authorized Correction/i });
    fireEvent.click(correctionTabBtn);

    const justificationInput = screen.getByPlaceholderText(/Provide formal explanation for this correction/i);
    fireEvent.change(justificationInput, {
      target: { value: 'Post-launch client retrospective verified exceptional quality.' },
    });

    const submitCorrBtn = screen.getByRole('button', { name: /Submit Authorized Correction/i });
    fireEvent.click(submitCorrBtn);

    await waitFor(() => {
      expect(api.correctMemberScore).toHaveBeenCalledWith(
        'wf-1',
        expect.objectContaining({
          reason: 'Post-launch client retrospective verified exceptional quality.',
        })
      );
      expect(onRefresh).toHaveBeenCalled();
    });
  });

  it('distinguishes real profiles from synthetic demo benchmarks and shows performance scores', () => {
    render(
      <WorkforceView
        workforce={mockMembers}
        recommendations={mockRecommendations}
        projectId="proj-1"
        onRefresh={vi.fn()}
      />
    );

    // In recommendations list:
    // rec-1 is not synthetic
    expect(screen.getByText('Real Profile')).toBeInTheDocument();
    // rec-2 is synthetic
    expect(screen.getByText('Synthetic Demo')).toBeInTheDocument();
  });
});
