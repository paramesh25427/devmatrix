import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ProjectsView } from './ProjectsView';
import { Project } from '../types/project';

const mockProjects: Project[] = [
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

describe('ProjectsView Component', () => {
  it('renders explicit loading state when isLoading is true', () => {
    render(
      <ProjectsView
        projects={[]}
        currentProjectId=""
        onSelectProject={vi.fn()}
        onRefresh={vi.fn()}
        isLoading={true}
      />
    );

    expect(screen.getByTestId('projects-loading-state')).toBeInTheDocument();
    expect(screen.getByText(/Loading enterprise delivery projects/i)).toBeInTheDocument();
  });

  it('renders explicit error state with retry button when error is present', () => {
    const onRefresh = vi.fn();
    render(
      <ProjectsView
        projects={[]}
        currentProjectId=""
        onSelectProject={vi.fn()}
        onRefresh={onRefresh}
        isLoading={false}
        error="Unable to connect to project service"
      />
    );

    expect(screen.getByTestId('projects-error-state')).toBeInTheDocument();
    expect(screen.getByText(/Failed to Load Projects/i)).toBeInTheDocument();
    expect(screen.getByText(/Unable to connect to project service/i)).toBeInTheDocument();

    const retryBtn = screen.getByRole('button', { name: /Retry Connection/i });
    fireEvent.click(retryBtn);
    expect(onRefresh).toHaveBeenCalledTimes(1);
  });

  it('renders explicit empty state when projects array is empty and not loading', () => {
    render(
      <ProjectsView
        projects={[]}
        currentProjectId=""
        onSelectProject={vi.fn()}
        onRefresh={vi.fn()}
        isLoading={false}
        error={null}
      />
    );

    expect(screen.getByTestId('projects-empty-state')).toBeInTheDocument();
    expect(screen.getByText(/No Delivery Projects Available/i)).toBeInTheDocument();
    expect(screen.getByText(/Create your first delivery project/i)).toBeInTheDocument();
  });

  it('renders project cards, marks active project, and handles selection', () => {
    const onSelectProject = vi.fn();
    render(
      <ProjectsView
        projects={mockProjects}
        currentProjectId="proj-001"
        onSelectProject={onSelectProject}
        onRefresh={vi.fn()}
        isLoading={false}
        error={null}
      />
    );

    expect(screen.getByTestId('projects-grid')).toBeInTheDocument();
    expect(screen.getByText('Cloud Migration & Core Platform Modernization')).toBeInTheDocument();
    expect(screen.getByText('OmniChannel Banking Migration')).toBeInTheDocument();

    // proj-001 is active
    expect(screen.getByText('Active')).toBeInTheDocument();

    // Clicking the second project card triggers onSelectProject
    const secondCard = screen.getByTestId('project-card-proj-002');
    fireEvent.click(secondCard);
    expect(onSelectProject).toHaveBeenCalledWith(mockProjects[1]);
  });
});
