import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { DocumentPreviewModal } from './DocumentPreviewModal';
import { DocumentDetail } from '../types/document';

describe('DocumentPreviewModal Component', () => {
  const mockDoc: DocumentDetail = {
    id: 'test-1',
    original_filename: 'sprint_plan.xlsx',
    file_type: 'xlsx',
    file_size_bytes: 4096,
    extraction_status: 'warning',
    has_text: false,
    total_sheets: 1,
    total_words: 0,
    created_at: new Date().toISOString(),
    extraction: {
      document_id: 'test-1',
      filename: 'sprint_plan.xlsx',
      file_type: 'xlsx',
      status: 'warning',
      has_text: false,
      total_pages: 0,
      total_sheets: 1,
      total_words: 0,
      warnings: ['No extractable text found in file. (Note: OCR is not supported in this version).'],
      sections: [
        {
          type: 'sheet',
          index: 1,
          title: 'Sheet: Tasks',
          table: {
            headers: ['Task ID', 'Description'],
            rows: [['DM-101', 'Setup Database']],
          },
        },
      ],
      raw_preview: '',
    },
  };

  it('renders filename, warning banner, and extracted sheet table', () => {
    render(<DocumentPreviewModal document={mockDoc} onClose={vi.fn()} />);

    expect(screen.getByText('sprint_plan.xlsx')).toBeInTheDocument();
    expect(screen.getByText(/OCR is not supported in this version/i)).toBeInTheDocument();
    expect(screen.getByText('Sheet: Tasks')).toBeInTheDocument();
    expect(screen.getByText('Task ID')).toBeInTheDocument();
    expect(screen.getByText('Setup Database')).toBeInTheDocument();
  });
});
