import React, { useEffect } from 'react';
import { CheckCircle2, X, BookOpen, ExternalLink } from 'lucide-react';

export default function CitationModal({ citation, onClose }) {
  if (!citation) return null;

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs transition-opacity animate-fadeIn"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="citation-modal-title"
    >
      <div 
        className="w-full max-w-md bg-white border border-slate-200 rounded-2xl shadow-xl p-6 space-y-4 relative"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition"
          aria-label="Close citation details"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-teal-50 text-teal-700 flex items-center justify-center shrink-0 border border-teal-100">
            <BookOpen className="w-4 h-4" />
          </div>
          <div>
            <h3 id="citation-modal-title" className="text-sm font-semibold text-slate-900">
              Verified Source Citation
            </h3>
            <p className="text-xs text-slate-500">Knowledge base grounding reference</p>
          </div>
        </div>

        {/* Citation Details Card */}
        <div className="p-4 rounded-xl border border-slate-100 bg-slate-50/80 space-y-2.5">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400">
                Source Document
              </span>
              <p className="text-sm font-medium text-slate-800 truncate mt-0.5" title={citation.filename}>
                {citation.filename}
              </p>
            </div>
            <span className="shrink-0 px-2.5 py-1 text-xs font-mono font-medium rounded-md bg-teal-50 text-teal-800 border border-teal-200">
              Page {citation.page_number}
            </span>
          </div>

          <div className="pt-2 border-t border-slate-200/60 flex items-center gap-2 text-xs text-teal-700">
            <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
            <span>Retrieved chunk verified in ChromaDB vector store</span>
          </div>
        </div>

        {/* Explanation */}
        <p className="text-xs text-slate-500 leading-relaxed">
          This citation references 1-based page {citation.page_number} of your uploaded PDF. 
          The assistant’s answer is strictly grounded in the excerpt extracted from this page.
        </p>

        {/* Actions */}
        <div className="pt-2 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-xs font-medium transition shadow-xs"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
