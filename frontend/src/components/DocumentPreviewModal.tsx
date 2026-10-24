import React, { useState } from 'react';
import { DocumentDetail, SectionContent } from '../types/document';
import { X, AlertTriangle, FileText, CheckCircle2, Layers, AlignLeft, Table as TableIcon } from 'lucide-react';

interface Props {
  document: DocumentDetail | null;
  onClose: () => void;
}

export const DocumentPreviewModal: React.FC<Props> = ({ document, onClose }) => {
  const [selectedSectionIdx, setSelectedSectionIdx] = useState<number>(0);
  const [viewMode, setViewMode] = useState<'structured' | 'raw'>('structured');

  if (!document) return null;

  const extraction = document.extraction;
  const sections = extraction?.sections || [];
  const activeSection: SectionContent | undefined = sections[selectedSectionIdx];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-5xl h-[88vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800/80 flex items-center justify-between bg-slate-950/40">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600/10 text-indigo-400 flex items-center justify-center border border-indigo-500/20">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-base font-semibold text-white">
                  {document.original_filename}
                </h3>
                <span className="px-2 py-0.5 rounded text-[11px] font-bold uppercase bg-slate-800 text-indigo-300 border border-slate-700">
                  {document.file_type}
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Source Document &bull; {document.total_words?.toLocaleString() || 0} extracted words
                {document.total_pages ? ` &bull; ${document.total_pages} pages` : ''}
                {document.total_sheets ? ` &bull; ${document.total_sheets} sheets` : ''}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {/* View Mode Toggle */}
            <div className="bg-slate-950/80 p-1 rounded-lg border border-slate-800 flex text-xs">
              <button
                onClick={() => setViewMode('structured')}
                className={`px-3 py-1 rounded-md font-medium transition ${
                  viewMode === 'structured' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-white'
                }`}
              >
                Structured View
              </button>
              <button
                onClick={() => setViewMode('raw')}
                className={`px-3 py-1 rounded-md font-medium transition ${
                  viewMode === 'raw' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-white'
                }`}
              >
                Raw Snippet
              </button>
            </div>

            <button
              onClick={onClose}
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Warnings Banner */}
        {extraction && extraction.warnings && extraction.warnings.length > 0 && (
          <div className="px-6 py-3 bg-amber-500/10 border-b border-amber-500/20 text-amber-300 text-xs flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 flex-shrink-0 text-amber-400" />
            <div className="flex-1">
              {extraction.warnings.map((w, i) => (
                <p key={i} className="font-medium">{w}</p>
              ))}
            </div>
          </div>
        )}

        {/* Main Body */}
        <div className="flex-1 flex overflow-hidden">
          {viewMode === 'raw' ? (
            <div className="flex-1 p-6 overflow-y-auto">
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 font-mono text-xs text-slate-300 whitespace-pre-wrap leading-relaxed">
                {extraction?.raw_preview || 'No raw preview available.'}
              </div>
            </div>
          ) : (
            <>
              {/* Sections / Pages / Sheets Sidebar */}
              {sections.length > 1 && (
                <div className="w-64 border-r border-slate-800/80 bg-slate-950/30 overflow-y-auto p-3 space-y-1">
                  <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider px-2 py-1 flex items-center">
                    <Layers className="w-3.5 h-3.5 mr-1.5" />
                    Document Structure ({sections.length})
                  </p>
                  {sections.map((sec, idx) => (
                    <button
                      key={idx}
                      onClick={() => setSelectedSectionIdx(idx)}
                      className={`w-full text-left px-3 py-2 rounded-lg text-xs font-medium flex items-center justify-between transition ${
                        selectedSectionIdx === idx
                          ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                          : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                      }`}
                    >
                      <span className="truncate flex items-center">
                        {sec.type === 'table' || sec.type === 'sheet' ? (
                          <TableIcon className="w-3.5 h-3.5 mr-1.5 flex-shrink-0 text-slate-400" />
                        ) : (
                          <AlignLeft className="w-3.5 h-3.5 mr-1.5 flex-shrink-0 text-slate-400" />
                        )}
                        {sec.title}
                      </span>
                    </button>
                  ))}
                </div>
              )}

              {/* Active Section Content View */}
              <div className="flex-1 p-6 overflow-y-auto bg-slate-900/20">
                {sections.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-slate-500">
                    <FileText className="w-12 h-12 mb-3 opacity-30" />
                    <p className="text-sm font-medium">No structured sections extracted</p>
                    <p className="text-xs mt-1 text-slate-400">
                      {document.warning_message || 'Content could not be parsed into sections.'}
                    </p>
                  </div>
                ) : activeSection ? (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 uppercase">
                          {activeSection.type}
                        </span>
                        <h4 className="text-base font-semibold text-white">
                          {activeSection.title}
                        </h4>
                      </div>
                      <span className="text-xs text-slate-500">
                        Section {selectedSectionIdx + 1} of {sections.length}
                      </span>
                    </div>

                    {/* Render Text Content */}
                    {activeSection.content !== undefined && activeSection.content !== null && (
                      <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 text-sm text-slate-200 leading-relaxed whitespace-pre-wrap font-sans">
                        {activeSection.content.trim() ? (
                          activeSection.content
                        ) : (
                          <span className="text-slate-500 italic">
                            [No text on this page or section]
                          </span>
                        )}
                      </div>
                    )}

                    {/* Render Table Content */}
                    {activeSection.table && (
                      <div className="rounded-xl border border-slate-800 overflow-hidden shadow-sm">
                        <div className="overflow-x-auto max-h-[55vh]">
                          <table className="w-full text-left text-xs border-collapse">
                            {activeSection.table.headers.length > 0 && (
                              <thead className="sticky top-0 bg-slate-950 text-slate-300 border-b border-slate-800 font-semibold uppercase tracking-wider">
                                <tr>
                                  {activeSection.table.headers.map((h, hIdx) => (
                                    <th key={hIdx} className="py-2.5 px-3 border-r border-slate-800 last:border-r-0 whitespace-nowrap">
                                      {h || `Column ${hIdx + 1}`}
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                            )}
                            <tbody className="divide-y divide-slate-800/50 bg-slate-900/40">
                              {activeSection.table.rows.map((row, rIdx) => (
                                <tr key={rIdx} className="hover:bg-slate-800/40 transition-colors">
                                  {row.map((cell, cIdx) => (
                                    <td key={cIdx} className="py-2 px-3 border-r border-slate-800/50 last:border-r-0 text-slate-300 whitespace-nowrap font-mono text-[11px]">
                                      {cell !== null && cell !== undefined ? String(cell) : ''}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </div>
                ) : null}
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-800/80 bg-slate-950/60 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>Extracted locally and stored securely</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
          >
            Close Preview
          </button>
        </div>
      </div>
    </div>
  );
};
