import React, { useState, useEffect } from 'react';
import { 
  FileText, 
  Copy, 
  Check, 
  Download, 
  X, 
  RefreshCw, 
  Sparkles, 
  BookOpen,
  Award
} from 'lucide-react';

export default function CheatSheetModal({
  isOpen,
  onClose,
  apiBase,
  documents = [],
  onBotCelebrate
}) {
  const [cheatSheetText, setCheatSheetText] = useState('');
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState('');

  const generateCheatSheet = async () => {
    if (documents.length === 0) {
      setCheatSheetText('');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const prompt = 
        "Generate a comprehensive 1-page Study Cheat-Sheet and Quick Reference from these indexed notes. Structure it clearly into: " +
        "### 1. 📌 Executive Summary\n" +
        "### 2. 🧠 Core Terminology & Definitions (Key concepts with punchy 1-line definitions)\n" +
        "### 3. 📐 Key Principles, Rules & Equations\n" +
        "### 4. ⚡ High-Yield Exam Takeaways & Common Pitfalls to Avoid\n" +
        "Keep it concise, clear, and high-yield.";

      const res = await fetch(`${apiBase}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: prompt,
          top_k: 6,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to synthesize cheat-sheet.');
      }

      setCheatSheetText(data.answer);
      if (onBotCelebrate) onBotCelebrate();
    } catch (err) {
      console.error('Cheat-sheet generation error:', err);
      setError(err.message || 'Unable to generate cheat-sheet.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && documents.length > 0 && !cheatSheetText) {
      generateCheatSheet();
    }
  }, [isOpen, documents.length]);

  if (!isOpen) return null;

  const handleCopy = () => {
    if (!cheatSheetText) return;
    navigator.clipboard.writeText(cheatSheetText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    if (!cheatSheetText) return;
    const blob = new Blob([cheatSheetText], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `Study_CheatSheet_${documents[0]?.filename || 'notes'}.md`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-fadeIn">
      <div 
        className="w-full max-w-2xl bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden flex flex-col max-h-[85vh] animate-fadeIn"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-headline"
      >
        {/* Modal Header */}
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-teal-50 border border-teal-200 text-teal-600 flex items-center justify-center shadow-2xs">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 id="modal-headline" className="text-sm font-semibold text-slate-900">
                Study Cheat-Sheet & Quick Reference
              </h3>
              <p className="text-[11px] text-slate-500">
                {documents.length > 0 
                  ? `Synthesized from ${documents.length} indexed document(s)`
                  : 'Grounded in your uploaded lecture materials'
                }
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
            aria-label="Close dialog"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {documents.length === 0 ? (
            <div className="text-center py-12 space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-teal-50 text-teal-600 mx-auto flex items-center justify-center border border-teal-100">
                <BookOpen className="w-6 h-6" />
              </div>
              <h4 className="text-sm font-semibold text-slate-800">No Study Documents Indexed</h4>
              <p className="text-xs text-slate-500 max-w-sm mx-auto leading-relaxed">
                Upload a lecture PDF or textbook chapter in the left sidebar first. Sparky will then synthesize a high-yield 1-page summary.
              </p>
            </div>
          ) : loading ? (
            <div className="text-center py-14 space-y-3">
              <RefreshCw className="w-8 h-8 text-teal-600 animate-spin mx-auto" />
              <div className="text-sm font-medium text-slate-800">
                Extracting core principles & condensing cheat-sheet...
              </div>
              <p className="text-xs text-slate-400 max-w-xs mx-auto">
                Analyzing embeddings, ranking key concepts, and formatting high-yield takeaways.
              </p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 flex items-center justify-between">
              <span>{error}</span>
              <button
                onClick={generateCheatSheet}
                className="px-2.5 py-1 rounded-lg bg-red-600 text-white font-medium hover:bg-red-700 transition"
              >
                Retry
              </button>
            </div>
          ) : (
            <div className="prose prose-slate max-w-none text-xs sm:text-sm leading-relaxed whitespace-pre-wrap text-slate-800 font-sans p-4 rounded-xl bg-slate-50 border border-slate-200/80">
              {cheatSheetText}
            </div>
          )}
        </div>

        {/* Modal Footer Controls */}
        <div className="px-5 py-3.5 border-t border-slate-100 bg-slate-50 flex items-center justify-between gap-3">
          <button
            onClick={generateCheatSheet}
            disabled={loading || documents.length === 0}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-100 text-xs font-medium text-slate-700 transition disabled:opacity-40 shadow-2xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-teal-600' : ''}`} />
            <span>Regenerate</span>
          </button>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              disabled={!cheatSheetText || loading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-100 text-xs font-medium text-slate-700 transition disabled:opacity-40 shadow-2xs"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-teal-600" />
                  <span className="text-teal-700">Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5 text-slate-500" />
                  <span>Copy Markdown</span>
                </>
              )}
            </button>

            <button
              onClick={handleDownload}
              disabled={!cheatSheetText || loading}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-xs font-medium transition disabled:opacity-40 shadow-2xs"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download File</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
