export interface TableData {
  headers: string[];
  rows: (string | number | boolean | null)[][];
}

export interface SectionContent {
  type: 'page' | 'sheet' | 'text' | 'table';
  index: number;
  title: string;
  content?: string | null;
  table?: TableData | null;
}

export interface ExtractionResult {
  document_id: string;
  filename: string;
  file_type: string;
  status: 'completed' | 'warning' | 'failed';
  has_text: boolean;
  total_pages: number;
  total_sheets: number;
  total_words: number;
  warnings: string[];
  sections: SectionContent[];
  raw_preview: string;
}

export interface DocumentSummary {
  id: string;
  original_filename: string;
  file_type: string;
  file_size_bytes: number;
  extraction_status: 'completed' | 'warning' | 'failed';
  error_message?: string | null;
  warning_message?: string | null;
  total_pages?: number | null;
  total_sheets?: number | null;
  total_words?: number | null;
  has_text: boolean;
  created_at: string;
}

export interface DocumentDetail extends DocumentSummary {
  extraction?: ExtractionResult | null;
}

export interface HealthStatus {
  status: string;
  app: string;
  database: string;
}
