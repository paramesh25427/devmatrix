import React, { useRef, useState } from 'react';
import { UploadCloud, AlertCircle, CheckCircle2, Loader2, FileText } from 'lucide-react';
import { api } from '../services/api';
import { DocumentDetail } from '../types/document';

interface Props {
  onUploadSuccess: (doc: DocumentDetail) => void;
  projectId?: string;
}

const SUPPORTED_EXTENSIONS = ['pdf', 'docx', 'xlsx', 'csv', 'txt', 'md'];
const MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024; // 15MB

export const DocumentUploadZone: React.FC<Props> = ({ onUploadSuccess, projectId }) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [currentFileName, setCurrentFileName] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      processFiles(Array.from(e.target.files));
    }
    // Reset input value so same file can be selected again
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const validateFile = (file: File): string | null => {
    if (file.size === 0) {
      return `File "${file.name}" is empty (0 bytes) and cannot be processed.`;
    }
    if (file.size > MAX_FILE_SIZE_BYTES) {
      return `File "${file.name}" exceeds the maximum allowed size of 15 MB.`;
    }
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!ext || !SUPPORTED_EXTENSIONS.includes(ext)) {
      return `Unsupported format for "${file.name}". Allowed types: ${SUPPORTED_EXTENSIONS.join(', ')}.`;
    }
    return null;
  };

  const processFiles = async (files: File[]) => {
    setErrorMessage(null);
    setSuccessMessage(null);

    for (const file of files) {
      const validationError = validateFile(file);
      if (validationError) {
        setErrorMessage(validationError);
        return;
      }

      setUploading(true);
      setCurrentFileName(file.name);

      try {
        const result = await api.uploadDocument(file, projectId);
        onUploadSuccess(result);
        setSuccessMessage(`Successfully processed "${file.name}"`);
      } catch (err: any) {
        setErrorMessage(err.message || `Failed to process "${file.name}"`);
        break;
      } finally {
        setUploading(false);
        setCurrentFileName('');
      }
    }
  };

  return (
    <div className="w-full">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !uploading && fileInputRef.current?.click()}
        className={`relative rounded-2xl border-2 border-dashed p-8 sm:p-12 text-center cursor-pointer transition-all duration-200 ${
          isDragging
            ? 'border-indigo-500 bg-indigo-500/10 scale-[1.01]'
            : 'border-slate-800 bg-slate-900/40 hover:border-slate-700 hover:bg-slate-900/60'
        } ${uploading ? 'pointer-events-none opacity-80' : ''}`}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileInputChange}
          multiple
          accept=".pdf,.docx,.xlsx,.csv,.txt,.md"
          className="hidden"
          disabled={uploading}
        />

        <div className="flex flex-col items-center justify-center space-y-4">
          <div className="w-14 h-14 rounded-2xl bg-indigo-600/10 text-indigo-400 flex items-center justify-center border border-indigo-500/20 shadow-inner">
            {uploading ? (
              <Loader2 className="w-7 h-7 animate-spin text-indigo-400" />
            ) : (
              <UploadCloud className="w-7 h-7" />
            )}
          </div>

          <div className="space-y-1">
            <h3 className="text-base sm:text-lg font-semibold text-white">
              {uploading ? (
                <span>Parsing & Extracting <span className="text-indigo-400 font-mono text-sm">{currentFileName}</span>...</span>
              ) : (
                'Drop project documents here or click to browse'
              )}
            </h3>
            <p className="text-xs sm:text-sm text-slate-400 max-w-md mx-auto">
              Securely parse project specs, sprint backlogs, sheets, or requirement documents.
            </p>
          </div>

          {/* Supported format tags */}
          <div className="flex flex-wrap items-center justify-center gap-1.5 pt-2">
            {['PDF', 'DOCX', 'XLSX', 'CSV', 'TXT', 'MARKDOWN'].map((fmt) => (
              <span
                key={fmt}
                className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-slate-800/80 text-slate-300 border border-slate-700/60"
              >
                <FileText className="w-2.5 h-2.5 mr-1 text-slate-400" />
                {fmt}
              </span>
            ))}
            <span className="text-[11px] text-slate-500 ml-1">Max 15MB</span>
          </div>
        </div>
      </div>

      {/* Notifications */}
      {errorMessage && (
        <div className="mt-4 p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0 text-rose-400 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold text-rose-200">Upload Issue</p>
            <p className="text-xs text-rose-300/90 mt-0.5">{errorMessage}</p>
          </div>
          <button
            onClick={() => setErrorMessage(null)}
            className="text-xs text-rose-400 hover:text-rose-200 ml-2"
          >
            Dismiss
          </button>
        </div>
      )}

      {successMessage && (
        <div className="mt-4 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-sm flex items-start space-x-3">
          <CheckCircle2 className="w-5 h-5 flex-shrink-0 text-emerald-400 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold text-emerald-200">Processing Complete</p>
            <p className="text-xs text-emerald-300/90 mt-0.5">{successMessage}</p>
          </div>
          <button
            onClick={() => setSuccessMessage(null)}
            className="text-xs text-emerald-400 hover:text-emerald-200 ml-2"
          >
            Dismiss
          </button>
        </div>
      )}
    </div>
  );
};
