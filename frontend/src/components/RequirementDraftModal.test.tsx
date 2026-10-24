import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { RequirementDraftModal } from './RequirementDraftModal';
import { RequirementDraftResponse } from '../types/requirement';

describe('RequirementDraftModal Component', () => {
  const mockDraft: RequirementDraftResponse = {
    id: 'draft-999',
    document_id: 'doc-123',
    document_name: 'cloud_spec.pdf',
    provider_used: 'google_gemini',
    model_used: 'gemini-2.5-flash',
    status: 'draft_ready',
    review_status: 'pending_review',
    manager_notes: '',
    attempt_history: [
      {
        provider: 'google_gemini',
        model: 'gemini-2.5-flash',
        status: 'success',
        attempt_count: 1,
        duration_ms: 1240,
      },
    ],
    requirements: {
      project_summary: 'Cloud-native real-time communication platform.',
      objectives: ['Achieve 99.9% uptime', 'Sub-100ms latency globally'],
      scope: {
        deliverables: ['Web Client', 'REST API Service'],
        scope_inclusions: ['User sign-in', 'Real-time messaging'],
        scope_exclusions: ['Hardware biometric scanning'],
      },
      functional_requirements: [
        {
          id: 'FR-01',
          title: 'User Authentication',
          description: 'Users must authenticate via OAuth2 / OIDC providers.',
          category: 'Security',
          confidence: 'high',
          needs_verification: false,
          source_references: [
            {
              source_type: 'page',
              location: 'Page 1 - Auth Architecture',
              excerpt: 'Users authenticate using standard OAuth2',
            },
          ],
        },
        {
          id: 'FR-02',
          title: 'Legacy Export Feature',
          description: 'Export telemetry data to obsolete legacy mainframe.',
          category: 'Integration',
          confidence: 'low',
          needs_verification: true,
          verification_reason: 'Contradicts modern cloud-native objective in Section 1',
          source_references: [
            {
              source_type: 'page',
              location: 'Page 4 - Legacy Systems',
            },
          ],
        },
      ],
      non_functional_requirements: [
        {
          id: 'NFR-01',
          title: 'API Latency',
          description: 'P99 latency must stay under 50ms.',
          category: 'Performance',
          confidence: 'high',
          needs_verification: false,
          source_references: [],
        },
      ],
      constraints: ['Must deploy to AWS us-east-1'],
      dependencies: ['Third-party SMS gateway'],
      assumptions: ['Database read-replicas will scale linearly'],
      risks: [
        {
          id: 'RISK-01',
          description: 'High burst traffic during launch event',
          severity: 'high',
          mitigation_hint: 'Implement auto-scaling and Redis rate-limiting',
        },
      ],
      missing_information: [
        {
          id: 'GAP-01',
          topic: 'Disaster Recovery RTO/RPO',
          question: 'What is the required RTO and RPO for production outages?',
          impact: 'high',
        },
      ],
      overall_confidence: 0.92,
      uncertainty_notes: ['Awaiting RTO SLA sign-off'],
    },
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders project summary, provider attribution, and objectives', () => {
    render(<RequirementDraftModal draft={mockDraft} onClose={vi.fn()} />);

    expect(screen.getByText(/AI Requirement Draft/i)).toBeInTheDocument();
    expect(screen.getByText('gemini-2.5-flash')).toBeInTheDocument();
    expect(screen.getByText('Pending Review')).toBeInTheDocument();
    expect(screen.getByText('Cloud-native real-time communication platform.')).toBeInTheDocument();
    expect(screen.getByText('Achieve 99.9% uptime')).toBeInTheDocument();
  });

  it('renders functional requirements with provenance and uncertainty verification tags', () => {
    render(<RequirementDraftModal draft={mockDraft} onClose={vi.fn()} />);

    // Switch to Functional tab
    fireEvent.click(screen.getByRole('button', { name: /Functional Requirements/i }));

    expect(screen.getByText('FR-01')).toBeInTheDocument();
    expect(screen.getByText('User Authentication')).toBeInTheDocument();
    expect(screen.getByText('High Confidence')).toBeInTheDocument();
    expect(screen.getByText(/Page 1 - Auth Architecture/i)).toBeInTheDocument();

    // Verify FR-02 with uncertainty flag
    expect(screen.getByText('FR-02')).toBeInTheDocument();
    expect(screen.getByText('Needs Verification')).toBeInTheDocument();
    expect(screen.getByText(/Contradicts modern cloud-native objective/i)).toBeInTheDocument();
  });

  it('renders risks and missing information tabs', () => {
    render(<RequirementDraftModal draft={mockDraft} onClose={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: /Risks & Clarifications/i }));

    expect(screen.getByText('High burst traffic during launch event')).toBeInTheDocument();
    expect(screen.getByText(/Disaster Recovery RTO\/RPO/i)).toBeInTheDocument();
    expect(screen.getByText(/What is the required RTO and RPO for production outages\?/i)).toBeInTheDocument();
  });

  it('supports manager review sign-off and calling the review API', async () => {
    const onUpdateMock = vi.fn();
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        ...mockDraft,
        review_status: 'approved',
        manager_notes: 'Scope approved with contingency budget.',
      }),
    });

    render(<RequirementDraftModal draft={mockDraft} onClose={vi.fn()} onUpdateDraft={onUpdateMock} />);

    fireEvent.click(screen.getByRole('button', { name: /Manager Review & Sign-off/i }));

    expect(screen.getByText(/Manager Notes & Feedback/i)).toBeInTheDocument();

    // Click Approved button
    fireEvent.click(screen.getByRole('button', { name: /Approve Draft/i }));

    // Enter notes
    const textarea = screen.getByPlaceholderText(/Enter approval conditions/i);
    fireEvent.change(textarea, { target: { value: 'Scope approved with contingency budget.' } });

    // Submit review
    fireEvent.click(screen.getByRole('button', { name: /Commit Review Decision/i }));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/requirements/draft-999/review'),
        expect.objectContaining({
          method: 'PATCH',
        })
      );
    });

    expect(onUpdateMock).toHaveBeenCalledWith(
      expect.objectContaining({
        review_status: 'approved',
      })
    );
  });
});
