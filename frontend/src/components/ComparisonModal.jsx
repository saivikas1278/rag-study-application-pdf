import React, { useState, useEffect } from 'react';
import { 
  Scale, 
  ArrowLeftRight, 
  Copy, 
  Check, 
  Download, 
  X, 
  RefreshCw, 
  BookOpen, 
  Sparkles, 
  Layers,
  FileCheck2,
  AlertCircle
} from 'lucide-react';

export default function ComparisonModal({
  isOpen,
  onClose,
  apiBase,
  documents = [],
  onBotCelebrate,
  onBotMoodChange,
  onCitationClick
}) {
  const [docA, setDocA] = useState('');
  const [docB, setDocB] = useState('');
  const [comparisonFocus, setComparisonFocus] = useState('');
  const [comparing, setComparing] = useState(false);
  const [result, setResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [copied, setCopied] = useState(false);

  // Initialize selected docs when modal opens or docs change
  useEffect(() => {
    if (documents.length >= 2) {
      if (!docA || !documents.some(d => d.filename === docA)) {
        setDocA(documents[0].filename);
      }
      if (!docB || !documents.some(d => d.filename === docB) || docB === documents[0].filename) {
        setDocB(documents[1].filename);
      }
    }
  }, [isOpen, documents]);

  if (!isOpen) return null;

  const handleSwap = () => {
    const temp = docA;
    setDocA(docB);
    setDocB(temp);
  };

  const handleCompare = async (customPrompt = null) => {
    setErrorMessage('');
    const focus = customPrompt !== null ? customPrompt : comparisonFocus;

    if (!docA || !docB) {
      setErrorMessage('Please select both Document A and Document B to compare.');
      return;
    }

    if (docA === docB) {
      setErrorMessage('Please select two distinct documents. Cannot compare a document with itself.');
      return;
    }

    setComparing(true);
    if (onBotMoodChange) onBotMoodChange('thinking');

    try {
      const res = await fetch(`${apiBase}/documents/compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          doc_a: docA,
          doc_b: docB,
          comparison_focus: focus ? focus.trim() : null,
          top_k_per_doc: 5
        })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to generate comparison matrix.');
      }

      setResult(data);
      if (onBotCelebrate) onBotCelebrate();
    } catch (err) {
      console.error('Comparison error:', err);
      setErrorMessage(err.message || 'Error occurred while comparing documents.');
      if (onBotMoodChange) onBotMoodChange('puzzled');
    } finally {
      setComparing(false);
    }
  };

  const handleCopy = () => {
    if (!result?.matrix_markdown) return;
    navigator.clipboard.writeText(result.matrix_markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    if (!result?.matrix_markdown) return;
    const blob = new Blob([result.matrix_markdown], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `Comparison_${docA}_vs_${docB}.md`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const quickLenses = [
    { label: "⚡ Methodologies & Approaches", prompt: "Focus on comparing research methodologies, experimental techniques, and practical approaches." },
    { label: "📐 Formulas & Definitions", prompt: "Focus on comparing mathematical formulations, theoretical models, and technical definitions." },
    { label: "⚖️ Contradictions & Discrepancies", prompt: "Focus on identifying conflicting conclusions, divergent evidence, and contrasting arguments." },
    { label: "🎯 Key Takeaways & Exam Tips", prompt: "Focus on synthesizing high-yield exam takeaways and unifying knowledge from both texts." }
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-900/50 backdrop-blur-xs animate-fadeIn">
      <div 
        className="w-full max-w-4xl bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh] animate-fadeIn"
        role="dialog"
        aria-modal="true"
        aria-labelledby="comparison-headline"
      >
        {/* Modal Header */}
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-teal-50 border border-teal-200 text-teal-600 flex items-center justify-center shadow-2xs">
              <Scale className="w-4 h-4" />
            </div>
            <div>
              <h3 id="comparison-headline" className="text-sm font-semibold text-slate-900">
                Multi-Document Comparison & Contrast Matrix
              </h3>
              <p className="text-[11px] text-slate-500">
                Balanced side-by-side semantic retrieval and grounded academic synthesis
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

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-5">
          {documents.length < 2 ? (
            <div className="text-center py-14 space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-teal-50 text-teal-600 mx-auto flex items-center justify-center border border-teal-100">
                <Layers className="w-6 h-6" />
              </div>
              <h4 className="text-sm font-semibold text-slate-800">At Least 2 Documents Required</h4>
              <p className="text-xs text-slate-500 max-w-sm mx-auto leading-relaxed">
                You have {documents.length} document indexed. Please upload at least one more study PDF in the left sidebar to unlock comparative matrix generation.
              </p>
            </div>
          ) : (
            <>
              {/* Document Selector Controls */}
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-11 gap-3 items-center">
                  {/* Document A Selector */}
                  <div className="sm:col-span-5 space-y-1">
                    <label className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-teal-500" />
                      <span>Document A (Primary Reference)</span>
                    </label>
                    <select
                      value={docA}
                      onChange={(e) => setDocA(e.target.value)}
                      disabled={comparing}
                      className="w-full text-xs font-medium p-2.5 rounded-xl border border-slate-300 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-teal-500/20"
                    >
                      {documents.map((d) => (
                        <option key={d.filename} value={d.filename} disabled={d.filename === docB}>
                          {d.filename} ({d.totalPages}p)
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Swap Button */}
                  <div className="sm:col-span-1 flex justify-center pt-2 sm:pt-4">
                    <button
                      type="button"
                      onClick={handleSwap}
                      disabled={comparing}
                      className="p-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-100 text-slate-600 transition shadow-2xs"
                      title="Swap Document A and Document B"
                    >
                      <ArrowLeftRight className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  {/* Document B Selector */}
                  <div className="sm:col-span-5 space-y-1">
                    <label className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-indigo-500" />
                      <span>Document B (Comparison Target)</span>
                    </label>
                    <select
                      value={docB}
                      onChange={(e) => setDocB(e.target.value)}
                      disabled={comparing}
                      className="w-full text-xs font-medium p-2.5 rounded-xl border border-slate-300 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-teal-500/20"
                    >
                      {documents.map((d) => (
                        <option key={d.filename} value={d.filename} disabled={d.filename === docA}>
                          {d.filename} ({d.totalPages}p)
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Custom Comparison Focus Input */}
                <div className="space-y-2 pt-1 border-t border-slate-200/60">
                  <label className="text-xs font-semibold text-slate-700 block">
                    Optional Custom Focus Lens
                  </label>
                  <input
                    type="text"
                    value={comparisonFocus}
                    onChange={(e) => setComparisonFocus(e.target.value)}
                    disabled={comparing}
                    placeholder="e.g. Focus on conflicting conclusions, mathematical proofs, or key definitions..."
                    className="w-full p-2.5 rounded-xl border border-slate-300 bg-white text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500/20"
                  />

                  {/* Quick Focus Preset Pills */}
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {quickLenses.map((lens, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => {
                          setComparisonFocus(lens.prompt);
                          handleCompare(lens.prompt);
                        }}
                        disabled={comparing}
                        className="px-2.5 py-1 rounded-full text-[11px] font-medium border border-slate-200 bg-white hover:bg-slate-100 hover:border-teal-300 text-slate-600 transition shadow-2xs"
                      >
                        {lens.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Action Trigger Button */}
              <div className="flex justify-center">
                <button
                  type="button"
                  onClick={() => handleCompare()}
                  disabled={comparing || !docA || !docB}
                  className="px-6 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold flex items-center gap-2 shadow-xs transition disabled:opacity-40"
                >
                  {comparing ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Synthesizing 5-Dimension Matrix...</span>
                    </>
                  ) : (
                    <>
                      <Scale className="w-3.5 h-3.5" />
                      <span>Generate Contrast Matrix</span>
                    </>
                  )}
                </button>
              </div>

              {/* Error Message */}
              {errorMessage && (
                <div className="p-3.5 rounded-xl border border-red-200 bg-red-50 text-xs text-red-700 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
                  <span>{errorMessage}</span>
                </div>
              )}

              {/* Results View */}
              {result && (
                <div className="space-y-4 pt-3 border-t border-slate-200 animate-fadeIn">
                  {/* Sources Badges */}
                  <div className="flex flex-wrap items-center justify-between gap-2 p-3 rounded-xl bg-slate-50 border border-slate-200">
                    <div className="flex flex-wrap items-center gap-2 text-xs">
                      <span className="font-semibold text-slate-700">Verified Evidence:</span>
                      
                      {/* Doc A Citations */}
                      {result.citations_a?.map((cite, idx) => (
                        <button
                          key={`a-${idx}`}
                          onClick={() => onCitationClick && onCitationClick(cite)}
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium bg-teal-50 text-teal-800 border border-teal-200 hover:bg-teal-100 transition"
                          title={`Doc A: ${cite.filename} page ${cite.page_number}`}
                        >
                          <span className="w-1.5 h-1.5 rounded-full bg-teal-500" />
                          <span>{cite.filename} p.{cite.page_number}</span>
                        </button>
                      ))}

                      {/* Doc B Citations */}
                      {result.citations_b?.map((cite, idx) => (
                        <button
                          key={`b-${idx}`}
                          onClick={() => onCitationClick && onCitationClick(cite)}
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium bg-indigo-50 text-indigo-800 border border-indigo-200 hover:bg-indigo-100 transition"
                          title={`Doc B: ${cite.filename} page ${cite.page_number}`}
                        >
                          <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
                          <span>{cite.filename} p.{cite.page_number}</span>
                        </button>
                      ))}
                    </div>

                    <span className="text-[10.5px] font-mono text-slate-400">
                      Grounded Comparative Matrix
                    </span>
                  </div>

                  {/* Contrast Matrix Rendered Body */}
                  <div className="p-5 rounded-2xl bg-white border border-slate-200/90 shadow-2xs space-y-4">
                    <div className="prose prose-slate max-w-none text-xs sm:text-sm leading-relaxed whitespace-pre-wrap text-slate-800">
                      {result.matrix_markdown}
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Modal Footer Controls */}
        <div className="px-5 py-3.5 border-t border-slate-100 bg-slate-50 flex items-center justify-between gap-3">
          <span className="text-[11px] text-slate-400">
            {result ? 'Matrix synthesized with citation grounding' : 'Select any 2 PDFs to start comparing'}
          </span>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              disabled={!result?.matrix_markdown || comparing}
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
              disabled={!result?.matrix_markdown || comparing}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-xs font-medium transition disabled:opacity-40 shadow-2xs"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export Report (.md)</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
