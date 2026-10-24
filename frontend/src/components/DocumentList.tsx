import React, { useState } from 'react';
import { DocumentSummary } from '../types/document';
import { FileText, Eye, Trash2, AlertTriangle, CheckCircle, XCircle, Sparkles, Loader2 } from 'lucide-react';

interface Props {
  documents: DocumentSummary[];
  onSelect: (docId: string) => void;
  onDelete: (docId: string) => void;
  onExtractRequirements?: (doc: DocumentSummary) => void;
  extractingDocId?: string | null;
}

export const DocumentList: React.FC<Props> = ({
  documents,
  onSelect,
  onDelete,
  onExtractRequirements,
  extractingDocId,
}) => {
  const [filter, setFilter] = useState<'all' | 'completed' | 'warning' | 'failed'>('all');

  const filteredDocs = documents.filter((doc) => {
    if (filter === 'all') return true;
    return doc.extraction_status === filter;
  });

  const getFormatBadge = (type: string) => {
    const t = type.toLowerCase();
    switch (t) {
      case 'pdf':
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/20">PDF</span>;
      case 'docx':
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">DOCX</span>;
      case 'xlsx':
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">XLSX</span>;
      case 'csv':
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-teal-500/10 text-teal-400 border border-teal-500/20">CSV</span>;
      case 'md':
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/20">MD</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700">{type.toUpperCase()}</span>;
    }
  };

  const getStatusBadge = (status: string, hasText: boolean) => {
    if (status === 'completed') {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <CheckCircle className="w-3 h-3 mr-1" />
          Extracted
        </span>
      );
    }
    if (status === 'warning') {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
          <AlertTriangle className="w-3 h-3 mr-1" />
          {!hasText ? 'No Text (OCR Unsup.)' : 'Warning'}
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
        <XCircle className="w-3 h-3 mr-1" />
        Failed
      </span>
    );
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="w-full bg-slate-900/40 border border-slate-800/80 rounded-2xl overflow-hidden shadow-xl">
      {/* Header and Filter Tabs */}
      <div className="p-5 border-b border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-white">Intake Document Repository</h2>
          <p className="text-xs text-slate-400">
            {documents.length} {documents.length === 1 ? 'document' : 'documents'} cataloged and processed
          </p>
        </div>

        {/* Filters */}
        <div className="flex items-center space-x-1 bg-slate-950/60 p-1 rounded-xl border border-slate-800 text-xs">
          {(
            [
              { key: 'all', label: `All (${documents.length})` },
              { key: 'completed', label: `Extracted (${documents.filter((d) => d.extraction_status === 'completed').length})` },
              { key: 'warning', label: `Warnings (${documents.filter((d) => d.extraction_status === 'warning').length})` },
              { key: 'failed', label: `Failed (${documents.filter((d) => d.extraction_status === 'failed').length})` },
            ] as const
          ).map((t) => (
            <button
              key={t.key}
              onClick={() => setFilter(t.key)}
              className={`px-3 py-1.5 rounded-lg font-medium transition ${
                filter === t.key
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Document Table or Empty State */}
      {filteredDocs.length === 0 ? (
        <div className="p-12 text-center text-slate-500">
          <FileText className="w-10 h-10 mx-auto mb-3 opacity-30" />
          <p className="text-sm font-medium text-slate-400">No documents found</p>
          <p className="text-xs mt-1">Upload a project document using the dropzone above to begin extraction.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800/80 bg-slate-950/30 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                <th className="py-3.5 px-5">Document Name</th>
                <th className="py-3.5 px-4">Format</th>
                <th className="py-3.5 px-4">File Size</th>
                <th className="py-3.5 px-4">Extracted Stats</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-sm">
              {filteredDocs.map((doc) => (
                <tr
                  key={doc.id}
                  className="hover:bg-slate-800/30 transition-colors group"
                >
                  <td className="py-4 px-5">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center text-slate-400 group-hover:text-indigo-400 transition-colors">
                        <FileText className="w-4 h-4" />
                      </div>
                      <div>
                        <p className="font-medium text-slate-200 group-hover:text-white transition-colors">
                          {doc.original_filename}
                        </p>
                        <p className="text-[11px] text-slate-500">
                          Uploaded {new Date(doc.created_at).toLocaleDateString()} at{' '}
                          {new Date(doc.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </p>
                      </div>
                    </div>
                  </td>

                  <td className="py-4 px-4">{getFormatBadge(doc.file_type)}</td>

                  <td className="py-4 px-4 text-xs font-mono text-slate-400">
                    {formatFileSize(doc.file_size_bytes)}
                  </td>

                  <td className="py-4 px-4 text-xs text-slate-300">
                    <div className="flex flex-col space-y-0.5">
                      <span>{doc.total_words?.toLocaleString() || 0} words</span>
                      <span className="text-[11px] text-slate-500">
                        {doc.total_pages ? `${doc.total_pages} pages` : ''}
                        {doc.total_sheets ? `${doc.total_sheets} sheets` : ''}
                      </span>
                    </div>
                  </td>

                  <td className="py-4 px-4">
                    {getStatusBadge(doc.extraction_status, doc.has_text)}
                  </td>

                  <td className="py-4 px-5 text-right">
                    <div className="flex items-center justify-end space-x-2">
                      {onExtractRequirements && (
                        <button
                          onClick={() => onExtractRequirements(doc)}
                          disabled={
                            extractingDocId === doc.id ||
                            !doc.has_text ||
                            (doc.total_words || 0) === 0
                          }
                          className="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-medium bg-gradient-to-r from-indigo-500/10 to-purple-500/10 text-indigo-300 hover:from-indigo-600 hover:to-purple-600 hover:text-white border border-indigo-500/30 transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
                          title={
                            !doc.has_text || (doc.total_words || 0) === 0
                              ? 'Document has no extractable text'
                              : 'Extract project requirements using AI multi-provider fallback'
                          }
                        >
                          {extractingDocId === doc.id ? (
                            <>
                              <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                              <span>Extracting...</span>
                            </>
                          ) : (
                            <>
                              <Sparkles className="w-3.5 h-3.5 mr-1.5 text-indigo-400 group-hover:text-white" />
                              <span>AI Reqs</span>
                            </>
                          )}
                        </button>
                      )}
                      <button
                        onClick={() => onSelect(doc.id)}
                        className="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white border border-slate-700 transition-all"
                        title="Preview Extracted Content"
                      >
                        <Eye className="w-3.5 h-3.5 mr-1" />
                        Preview
                      </button>
                      <button
                        onClick={() => onDelete(doc.id)}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                        title="Delete Document"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
