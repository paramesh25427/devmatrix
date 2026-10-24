import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ExecutionView } from './ExecutionView';
import { ExecutionSummary } from '../types/execution';
import { WBSTask } from '../types/wbs';
import { api } from '../services/api';

vi.mock('../services/api', () => ({
  api: {
    updateTaskProgress: vi.fn(),
  },
}));

describe('ExecutionView Component', () => {
  const mockTasks: WBSTask[] = [
    {
      id: 'task-1',
      tenant_id: 'tenant-default',
      project_id: 'proj-1',
      baseline_version: 1,
      task_code: 'TSK-1.1',
      title: 'Architectural Blueprint Design',
      required_role: 'Solutions Architect',
      assigned_user_id: 'user-1',
      assigned_user_name: 'David Chen',
      status: 'in_progress',
      progress_percentage: 60,
      optimistic_hours: 10,
      most_likely_hours: 20,
      pessimistic_hours: 30,
      expected_hours: 20,
      variance_hours: 4,
      actual_hours: 12,
      is_critical_path: true,
      source_requirement_ids: ['req-1'],
      order_index: 0,
      created_at: new Date().toISOString(),
    },
    {
      id: 'task-2',
      tenant_id: 'tenant-default',
      project_id: 'proj-1',
      baseline_version: 1,
      task_code: 'TSK-1.2',
      title: 'API Gateway Implementation',
      required_role: 'Backend Engineer',
      status: 'blocked',
      progress_percentage: 20,
      optimistic_hours: 8,
      most_likely_hours: 16,
      pessimistic_hours: 24,
      expected_hours: 16,
      variance_hours: 4,
      actual_hours: 4,
      blocker_notes: 'Missing OAuth2 client credentials from IdP team',
      is_critical_path: false,
      source_requirement_ids: ['req-2'],
      order_index: 1,
      created_at: new Date().toISOString(),
    },
  ];

  const mockSummary: ExecutionSummary = {
    project_id: 'proj-1',
    total_tasks: 2,
    completed_tasks: 0,
    in_progress_tasks: 1,
    blocked_tasks: 1,
    overdue_milestones_count: 0,
    total_planned_hours: 36,
    total_actual_hours: 16,
    completion_percentage: 40,
    milestones: [
      {
        id: 'ms-1',
        tenant_id: 'tenant-default',
        project_id: 'proj-1',
        title: 'Sprint 1 Core Foundation',
        due_date: '2026-11-01',
        status: 'pending',
        created_at: new Date().toISOString(),
      },
    ],
    active_blockers: [
      {
        task_code: 'TSK-1.2',
        title: 'API Gateway Implementation',
        notes: 'Missing OAuth2 client credentials from IdP team',
      },
    ],
    recent_updates: [
      {
        id: 'rec-1',
        task_id: 'task-1',
        user_name: 'manager@devmatrix.ai',
        hours_logged: 4,
        previous_status: 'not_started',
        new_status: 'in_progress',
        progress_percentage: 60,
        progress_notes: 'Service definitions mapped and schemas created',
        blocker_flag: 'false',
        created_at: new Date().toISOString(),
      },
    ],
  };

  const mockOnRefresh = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders guard empty state when project has no WBS tasks', () => {
    render(
      <ExecutionView
        summary={null}
        tasks={[]}
        projectId="proj-empty"
        onRefresh={mockOnRefresh}
      />
    );

    expect(screen.getByText(/no wbs tasks generated yet/i)).toBeInTheDocument();
    expect(screen.getByText(/approve the requirements baseline/i)).toBeInTheDocument();
  });

  it('renders metric cards with planned vs actual hours and completion percentage', () => {
    render(
      <ExecutionView
        summary={mockSummary}
        tasks={mockTasks}
        projectId="proj-1"
        onRefresh={mockOnRefresh}
      />
    );

    expect(screen.getByText('40%')).toBeInTheDocument();
    expect(screen.getByText(/overall project/i)).toBeInTheDocument();
    expect(screen.getAllByText(/16\.0/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/\/ 36 hrs/i)).toBeInTheDocument();
    expect(screen.getByText('Active Impediments')).toBeInTheDocument();
  });

  it('displays WBS tasks table with task code, title, assignee, status, planned and actual effort, and progress', () => {
    render(
      <ExecutionView
        summary={mockSummary}
        tasks={mockTasks}
        projectId="proj-1"
        onRefresh={mockOnRefresh}
      />
    );

    expect(screen.getByText('TSK-1.1')).toBeInTheDocument();
    expect(screen.getByText('Architectural Blueprint Design')).toBeInTheDocument();
    expect(screen.getByText('David Chen')).toBeInTheDocument();
    expect(screen.getByText('in progress')).toBeInTheDocument();
    expect(screen.getByText('20.0h')).toBeInTheDocument();
    expect(screen.getByText('12.0h')).toBeInTheDocument();
    expect(screen.getByText('60%')).toBeInTheDocument();

    expect(screen.getByText('TSK-1.2')).toBeInTheDocument();
    expect(screen.getByText('API Gateway Implementation')).toBeInTheDocument();
    expect(screen.getByText('Backend Engineer')).toBeInTheDocument();
    expect(screen.getByText('blocked')).toBeInTheDocument();
    expect(screen.getByText('16.0h')).toBeInTheDocument();
    expect(screen.getByText('4.0h')).toBeInTheDocument();
    expect(screen.getByText('20%')).toBeInTheDocument();
  });

  it('clicking update button selects task and switches to update form', async () => {
    render(
      <ExecutionView
        summary={mockSummary}
        tasks={mockTasks}
        projectId="proj-1"
        onRefresh={mockOnRefresh}
      />
    );

    const updateButtons = screen.getAllByRole('button', { name: /^update$/i });
    fireEvent.click(updateButtons[0]);

    // Should switch to update form
    expect(screen.getByText(/record verified task progress/i)).toBeInTheDocument();
    expect(screen.getAllByText(/60%/i).length).toBeGreaterThanOrEqual(1);
  });

  it('submits progress update and triggers onRefresh', async () => {
    (api.updateTaskProgress as any).mockResolvedValueOnce({
      message: 'Task updated successfully',
      task_id: 'task-1',
      new_status: 'completed',
    });

    render(
      <ExecutionView
        summary={mockSummary}
        tasks={mockTasks}
        projectId="proj-1"
        onRefresh={mockOnRefresh}
      />
    );

    // Click Update on task-1
    const updateButtons = screen.getAllByRole('button', { name: /^update$/i });
    fireEvent.click(updateButtons[0]);

    // Change status to completed via 100% preset button
    const preset100 = screen.getByRole('button', { name: '100%' });
    fireEvent.click(preset100);

    // Enter progress notes
    const notesInput = screen.getByPlaceholderText(/detail deliverables completed/i);
    fireEvent.change(notesInput, { target: { value: 'Production verification passed' } });

    // Submit form
    const submitBtn = screen.getByRole('button', { name: /submit progress update/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.updateTaskProgress).toHaveBeenCalledWith(
        'task-1',
        0,
        'completed',
        100,
        'Production verification passed',
        false,
        ''
      );
      expect(mockOnRefresh).toHaveBeenCalled();
    });
  });

  it('renders audit trail subtab with past updates and milestones', () => {
    render(
      <ExecutionView
        summary={mockSummary}
        tasks={mockTasks}
        projectId="proj-1"
        onRefresh={mockOnRefresh}
      />
    );

    const historyTabBtn = screen.getByRole('button', { name: /audit trail & milestones/i });
    fireEvent.click(historyTabBtn);

    expect(screen.getByText(/execution audit trail/i)).toBeInTheDocument();
    expect(screen.getByText(/manager@devmatrix.ai/i)).toBeInTheDocument();
    expect(screen.getByText(/Service definitions mapped and schemas created/i)).toBeInTheDocument();
    expect(screen.getByText('Sprint 1 Core Foundation')).toBeInTheDocument();
  });
});
