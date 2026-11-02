import React, { useState, useRef } from 'react';
import { 
  UploadCloud, 
  FileText, 
  CheckCircle2, 
  AlertCircle, 
  RefreshCw, 
  Layers, 
  BookOpen,
  X,
  FileCheck2,
  FileSpreadsheet,
  Scale
} from 'lucide-react';

const MAX_SIZE_MB = 15;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

export default function UploadSection({ 
  apiBase, 
  documents, 
  onDocumentUploaded, 
  disabled = false,
  onOpenCheatSheet,
  onOpenComparison,
  onBotCelebrate
}) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgressText, setUploadProgressText] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const fileInputRef = useRef(null);

  // Validate file constraints before initiating network transfer
  const validateFile = (file) => {
    if (!file) return 'No file selected.';
    
    // Check extension and type
    const isPdfExt = file.name.toLowerCase().endsWith('.pdf');
    const isPdfMime = file.type === 'application/pdf' || file.type === 'application/x-pdf' || !file.type;
    if (!isPdfExt || !isPdfMime) {
      return `"${file.name}" is not a PDF. Only .pdf files are accepted.`;
    }

    // Check size limit (15 MB)
    if (file.size > MAX_SIZE_BYTES) {
      const actualMb = (file.size / (1024 * 1024)).toFixed(1);
      return `File size (${actualMb} MB) exceeds maximum allowed limit of ${MAX_SIZE_MB} MB.`;
    }

    if (file.size === 0) {
      return 'The selected PDF is empty (0 bytes).';
    }

    return null;
  };

  const handleUpload = async (file) => {
    setErrorMessage('');
    setSuccessMessage('');

    const validationError = validateFile(file);
    if (validationError) {
      setErrorMessage(validationError);
      return;
    }

    setUploading(true);
    setUploadProgressText('Uploading document and parsing text...');

    try {
      const formData = new FormData();
      formData.append('file', file);

      // Simulate step feedback while server processes extraction & embeddings
      const progressTimer = setTimeout(() => {
        setUploadProgressText('Chunking pages & generating 384-dim embeddings...');
      }, 900);

      const res = await fetch(`${apiBase}/documents/upload`, {
        method: 'POST',
        body: formData,
      });

      clearTimeout(progressTimer);

      const data = await res.json();

      if (!res.ok) {
        const errorDetail = typeof data.detail === 'string' 
          ? data.detail 
          : Array.isArray(data.detail)
          ? data.detail.map(d => d.msg).join('; ')
          : `Upload failed with HTTP ${res.status}`;
        throw new Error(errorDetail);
      }

      setSuccessMessage(
        `Successfully indexed "${data.filename}" (${data.total_pages} pages, ${data.total_chunks} chunks).`
      );

      // Notify parent component to update session document state
      if (onDocumentUploaded) {
        onDocumentUploaded({
          filename: data.filename,
          totalPages: data.total_pages,
          totalChunks: data.total_chunks,
          embeddingModel: data.embedding_model,
          uploadedAt: new Date(),
        });
      }

      // Trigger bot celebration
      if (onBotCelebrate) {
        onBotCelebrate();
      }

    } catch (err) {
      console.error('Document ingestion error:', err);
      setErrorMessage(err.message || 'Failed to upload and process document.');
    } finally {
      setUploading(false);
      setUploadProgressText('');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const onDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled && !uploading) {
      setIsDragging(true);
    }
  };

  const onDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const onDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (disabled || uploading) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      handleUpload(file);
    }
  };

  const onFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      handleUpload(file);
    }
  };

  return (
    <div className="space-y-4">
      {/* Title & Description */}
      <div>
        <h3 className="text-sm font-semibold tracking-tight text-slate-900 flex items-center gap-2">
          <span>Study Materials</span>
          <span className="text-[10px] font-mono font-normal px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
            PDF only
          </span>
        </h3>
        <p className="text-xs text-slate-500 mt-1 leading-relaxed">
          Upload course notes, textbook chapters, or lecture slides (up to {MAX_SIZE_MB}MB).
        </p>
      </div>

      {/* Hidden native input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,application/pdf"
        onChange={onFileChange}
        className="hidden"
        disabled={disabled || uploading}
      />

      {/* Drag & Drop Upload Zone */}
      <div
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={() => !disabled && !uploading && fileInputRef.current?.click()}
        className={`p-5 rounded-xl border-2 border-dashed transition-all duration-200 flex flex-col items-center justify-center text-center cursor-pointer ${
          disabled
            ? 'border-slate-200 bg-slate-50/60 cursor-not-allowed opacity-60'
            : isDragging
            ? 'border-teal-500 bg-teal-50/60 shadow-inner'
            : uploading
            ? 'border-teal-400 bg-teal-50/20 cursor-wait'
            : 'border-slate-200 hover:border-teal-400 hover:bg-slate-50/80 bg-white shadow-2xs'
        }`}
      >
        {uploading ? (
          <div className="space-y-2 py-2 flex flex-col items-center">
            <RefreshCw className="w-6 h-6 text-teal-600 animate-spin" />
            <p className="text-xs font-medium text-slate-800">
              {uploadProgressText || 'Processing document...'}
            </p>
            <p className="text-[11px] text-slate-400 font-mono">
              Extracting text & computing embeddings
            </p>
          </div>
        ) : (
          <div className="space-y-2 py-1 flex flex-col items-center">
            <div className="w-10 h-10 rounded-xl bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-600 group-hover:bg-teal-50 group-hover:text-teal-600 transition-colors">
              <UploadCloud className="w-5 h-5 text-teal-600" />
            </div>
            <div>
              <p className="text-xs font-medium text-slate-800">
                <span className="text-teal-600 font-semibold underline decoration-teal-300 underline-offset-2">Click to upload</span> or drag & drop
              </p>
              <p className="text-[11px] text-slate-400 mt-0.5">
                PDF textbooks, papers & notes (max {MAX_SIZE_MB}MB)
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Error Notification */}
      {errorMessage && (
        <div className="p-3 rounded-lg border border-red-200 bg-red-50 text-xs text-red-700 flex items-start gap-2 animate-fadeIn">
          <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-red-800 text-[11px]">Upload Failed</p>
            <p className="text-red-600 mt-0.5">{errorMessage}</p>
          </div>
          <button 
            onClick={() => setErrorMessage('')}
            className="text-red-500 hover:text-red-700 p-0.5"
            aria-label="Dismiss error"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Success Notification */}
      {successMessage && (
        <div className="p-3 rounded-lg border border-teal-200 bg-teal-50/80 text-xs text-teal-800 flex items-start gap-2 animate-fadeIn">
          <CheckCircle2 className="w-4 h-4 text-teal-600 shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-teal-900 text-[11px]">Document Indexed</p>
            <p className="text-teal-700 mt-0.5">{successMessage}</p>
          </div>
          <button 
            onClick={() => setSuccessMessage('')}
            className="text-teal-600 hover:text-teal-800 p-0.5"
            aria-label="Dismiss message"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Session Documents List & Tools */}
      {documents.length > 0 && (
        <div className="space-y-2.5 pt-2 border-t border-slate-200/80">
          <div className="flex items-center justify-between text-xs text-slate-500 px-0.5">
            <span className="font-medium text-[11px] uppercase tracking-wider">Active Documents</span>
            <span className="font-mono text-[11px] bg-slate-200/80 text-slate-700 px-1.5 py-0.2 rounded-full">{documents.length}</span>
          </div>

          <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
            {documents.map((doc, idx) => (
              <div 
                key={`${doc.filename}-${idx}`}
                className="p-2.5 rounded-lg border border-slate-200/80 bg-white hover:border-teal-300 transition-colors flex items-center justify-between gap-2.5 text-xs shadow-2xs"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <FileCheck2 className="w-4 h-4 text-teal-600 shrink-0" />
                  <div className="min-w-0">
                    <p className="font-medium text-slate-800 truncate" title={doc.filename}>
                      {doc.filename}
                    </p>
                    <p className="text-[10px] text-slate-400 font-mono flex items-center gap-1.5">
                      <span>{doc.totalPages}p</span>
                      <span>•</span>
                      <span>{doc.totalChunks} chunks</span>
                    </p>
                  </div>
                </div>

                <span className="shrink-0 text-[10px] font-mono px-1.5 py-0.5 rounded bg-teal-50 text-teal-700 border border-teal-200/60">
                  Active
                </span>
              </div>
            ))}
          </div>

          {/* Action Tools Grid */}
          <div className="space-y-1.5 pt-1">
            {/* Multi-Document Compare Trigger (Visible when >= 2 documents exist) */}
            {onOpenComparison && documents.length >= 2 && (
              <button
                onClick={onOpenComparison}
                className="w-full py-2 px-3 rounded-xl border border-indigo-200 bg-indigo-50/80 hover:bg-indigo-100 text-indigo-900 text-xs font-semibold flex items-center justify-center gap-2 transition shadow-2xs group"
                title="Compare two indexed documents side-by-side"
              >
                <Scale className="w-3.5 h-3.5 text-indigo-600 group-hover:scale-110 transition-transform" />
                <span>Compare Documents (Contrast Matrix)</span>
              </button>
            )}

            {/* Quick Study Cheat-Sheet Generator Button */}
            {onOpenCheatSheet && (
              <button
                onClick={onOpenCheatSheet}
                className="w-full py-2 px-3 rounded-xl border border-teal-200 bg-teal-50/70 hover:bg-teal-100/70 text-teal-800 text-xs font-medium flex items-center justify-center gap-2 transition shadow-2xs group"
              >
                <FileSpreadsheet className="w-3.5 h-3.5 text-teal-600 group-hover:scale-110 transition-transform" />
                <span>Generate Study Cheat-Sheet</span>
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
