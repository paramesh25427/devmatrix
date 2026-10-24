import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ReportsView } from './ReportsView';
import { api } from '../services/api';
import { ProjectReportSummary } from '../types/report';

vi.mock('../services/api', () => ({
  api: {
    generateReport: vi.fn(),
    downloadReportBlob: vi.fn(),
    getReportDownloadUrl: vi.fn().mockImplementation((id: string) => `http://localhost:8000/api/reports/${id}/download`),
  },
}));

const mockReports: ProjectReportSummary[] = [
  {
    id: 'report-101',
    tenant_id: 'tenant-default',
    project_id: 'proj-demo-1',
    title: 'DevMatrix WBS Demo - Executive Delivery Report v1',
    report_type: 'executive_delivery_book',
    baseline_version: 1,
    file_size_bytes: 48512,
    generated_by: 'manager@devmatrix.local',
    created_at: '2026-10-24T06:30:00Z',
  },
  {
    id: 'report-102',
    tenant_id: 'tenant-default',
    project_id: 'proj-demo-1',
    title: 'DevMatrix WBS Demo - Executive Delivery Report v2',
    report_type: 'executive_delivery_book',
    baseline_version: 2,
    file_size_bytes: 52180,
    generated_by: 'director@devmatrix.local',
    created_at: '2026-10-24T07:15:00Z',
  },
];

describe('ReportsView Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders report specification cards and generated report vault table', () => {
    render(
      <ReportsView
        reports={mockReports}
        projectId="proj-demo-1"
        onRefresh={vi.fn()}
      />
    );

    expect(screen.getByText(/Executive Project Delivery Book & PDF Generation/i)).toBeInTheDocument();
    expect(screen.getByText(/Report Specification & Included Sections/i)).toBeInTheDocument();
    expect(screen.getByText('DevMatrix WBS Demo - Executive Delivery Report v1')).toBeInTheDocument();
    expect(screen.getByText('DevMatrix WBS Demo - Executive Delivery Report v2')).toBeInTheDocument();
    expect(screen.getByText('2 reports archived')).toBeInTheDocument();
  });

  it('renders empty table message when no reports exist', () => {
    render(
      <ReportsView
        reports={[]}
        projectId="proj-demo-1"
        onRefresh={vi.fn()}
      />
    );

    expect(screen.getByText('0 reports archived')).toBeInTheDocument();
    expect(screen.getByText(/No reports generated yet for this project/i)).toBeInTheDocument();
  });

  it('handles "Generate PDF Report" click with loading state and triggers onRefresh', async () => {
    const onRefreshMock = vi.fn();
    const newReport: ProjectReportSummary = {
      id: 'report-new',
      tenant_id: 'tenant-default',
      project_id: 'proj-demo-1',
      title: 'DevMatrix WBS Demo - Executive Delivery Report v3',
      report_type: 'executive_delivery_book',
      baseline_version: 3,
      file_size_bytes: 55000,
      generated_by: 'manager@devmatrix.local',
      created_at: '2026-10-24T07:45:00Z',
    };
    (api.generateReport as any).mockResolvedValueOnce(newReport);

    render(
      <ReportsView
        reports={mockReports}
        projectId="proj-demo-1"
        onRefresh={onRefreshMock}
      />
    );

    const generateBtn = screen.getByRole('button', { name: /Generate PDF Report/i });
    expect(generateBtn).toBeInTheDocument();
    expect(generateBtn).not.toBeDisabled();

    fireEvent.click(generateBtn);

    await waitFor(() => {
      expect(api.generateReport).toHaveBeenCalledWith('proj-demo-1');
      expect(onRefreshMock).toHaveBeenCalledTimes(1);
    });

    expect(screen.getByText(/Executive Project Delivery PDF Report generated successfully/i)).toBeInTheDocument();
  });

  it('displays error banner when PDF report generation fails', async () => {
    (api.generateReport as any).mockRejectedValueOnce(new Error('Cross-tenant unauthorized project access'));

    render(
      <ReportsView
        reports={mockReports}
        projectId="proj-demo-1"
        onRefresh={vi.fn()}
      />
    );

    const generateBtn = screen.getByRole('button', { name: /Generate PDF Report/i });
    fireEvent.click(generateBtn);

    await waitFor(() => {
      expect(screen.getByText('Cross-tenant unauthorized project access')).toBeInTheDocument();
    });
  });

  it('triggers authenticated download when "Download PDF" is clicked in the vault table', async () => {
    (api.downloadReportBlob as any).mockResolvedValueOnce(undefined);

    render(
      <ReportsView
        reports={mockReports}
        projectId="proj-demo-1"
        onRefresh={vi.fn()}
      />
    );

    const downloadButtons = screen.getAllByRole('button', { name: /Download PDF/i });
    expect(downloadButtons.length).toBe(2);

    fireEvent.click(downloadButtons[0]);

    await waitFor(() => {
      expect(api.downloadReportBlob).toHaveBeenCalledWith(
        'report-101',
        'DevMatrix_WBS_Demo_-_Executive_Delivery_Report_v1.pdf'
      );
    });
  });
});
