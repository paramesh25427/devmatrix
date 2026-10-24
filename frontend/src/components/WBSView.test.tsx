import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { WBSView } from './WBSView';
import { api } from '../services/api';

vi.mock('../services/api', () => ({
  api: {
    generateWBS: vi.fn(),
    createTask: vi.fn(),
    addDependency: vi.fn(),
  },
}));

describe('WBSView Component - Baseline Guard & Guidance', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('disables "Generate WBS from Baseline" and shows guidance when hasApprovedBaseline is false', () => {
    render(
      <WBSView
        overview={null}
        projectId="proj-unapproved"
        hasApprovedBaseline={false}
        isBaselineLoading={false}
        onRefresh={vi.fn()}
      />
    );

    const generateBtn = screen.getByRole('button', { name: /Generate WBS from Baseline/i });
    expect(generateBtn).toBeDisabled();
    expect(generateBtn).toHaveClass('cursor-not-allowed');

    // Verify explanation banner is visible
    expect(screen.getByTestId('wbs-baseline-guidance-banner')).toBeInTheDocument();
    expect(
      screen.getAllByText(/An approved requirements baseline is required\. Review and approve the requirements draft first\./i).length
    ).toBeGreaterThanOrEqual(1);

    // Clicking disabled button does not trigger api.generateWBS
    fireEvent.click(generateBtn);
    expect(api.generateWBS).not.toHaveBeenCalled();
  });

  it('enables "Generate WBS from Baseline" and hides guidance when hasApprovedBaseline is true', async () => {
    const onRefresh = vi.fn();
    (api.generateWBS as any).mockResolvedValueOnce([]);

    render(
      <WBSView
        overview={null}
        projectId="proj-approved"
        hasApprovedBaseline={true}
        isBaselineLoading={false}
        onRefresh={onRefresh}
      />
    );

    const generateBtn = screen.getByRole('button', { name: /Generate WBS from Baseline/i });
    expect(generateBtn).toBeEnabled();
    expect(generateBtn).not.toHaveClass('cursor-not-allowed');

    // Guidance banner should NOT be rendered
    expect(screen.queryByTestId('wbs-baseline-guidance-banner')).not.toBeInTheDocument();

    // Table empty state indicates user can generate
    expect(
      screen.getByText(/No WBS tasks generated yet\. Click "Generate WBS from Baseline" to begin planning\./i)
    ).toBeInTheDocument();

    // Click button to generate
    fireEvent.click(generateBtn);
    expect(api.generateWBS).toHaveBeenCalledWith('proj-approved');
    await waitFor(() => {
      expect(onRefresh).toHaveBeenCalled();
    });
  });

  it('disables button and displays loading indicator while baseline status is loading', () => {
    render(
      <WBSView
        overview={null}
        projectId="proj-loading"
        hasApprovedBaseline={false}
        isBaselineLoading={true}
        onRefresh={vi.fn()}
      />
    );

    const generateBtn = screen.getByRole('button', { name: /Checking Baseline\.\.\./i });
    expect(generateBtn).toBeDisabled();

    // Guidance banner should not flash prematurely while still loading
    expect(screen.queryByTestId('wbs-baseline-guidance-banner')).not.toBeInTheDocument();
    expect(screen.getByText(/Checking requirements baseline status\.\.\./i)).toBeInTheDocument();
  });

  it('correctly transitions from active baseline to disabled when props update (simulating project switch)', () => {
    const { rerender } = render(
      <WBSView
        overview={null}
        projectId="proj-1-approved"
        hasApprovedBaseline={true}
        isBaselineLoading={false}
        onRefresh={vi.fn()}
      />
    );

    // Initial state: approved project 1
    const initialBtn = screen.getByRole('button', { name: /Generate WBS from Baseline/i });
    expect(initialBtn).toBeEnabled();
    expect(screen.queryByTestId('wbs-baseline-guidance-banner')).not.toBeInTheDocument();

    // Simulate switching to unapproved project 2
    rerender(
      <WBSView
        overview={null}
        projectId="proj-2-unapproved"
        hasApprovedBaseline={false}
        isBaselineLoading={false}
        onRefresh={vi.fn()}
      />
    );

    const updatedBtn = screen.getByRole('button', { name: /Generate WBS from Baseline/i });
    expect(updatedBtn).toBeDisabled();
    expect(screen.getByTestId('wbs-baseline-guidance-banner')).toBeInTheDocument();
    expect(
      screen.getAllByText(/An approved requirements baseline is required\. Review and approve the requirements draft first\./i).length
    ).toBeGreaterThanOrEqual(1);
  });
});
