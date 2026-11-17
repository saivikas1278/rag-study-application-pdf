import React from 'react';
import { Download, X, Smartphone, Share2, MoreVertical, PlusSquare, CheckCircle2 } from 'lucide-react';

export default function InstallModal({ isOpen, onClose, onInstallDirectly, canInstallDirectly }) {
  if (!isOpen) return null;

  const isIOS = typeof navigator !== 'undefined' && /iPad|iPhone|iPod/.test(navigator.userAgent);

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-fadeIn"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      <div 
        className="w-full max-w-md bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col animate-fadeIn"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/80">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-teal-50 border border-teal-200 text-teal-600 flex items-center justify-center shadow-2xs">
              <Smartphone className="w-5 h-5 text-teal-600" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-900">Install Mobile App</h3>
              <p className="text-[11px] text-slate-500">Run Study Assistant as a standalone mobile app</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 space-y-4 text-xs text-slate-700">
          {/* Direct Install Button if browser supports it */}
          {canInstallDirectly && (
            <div className="p-4 rounded-xl bg-teal-50/80 border border-teal-200/80 text-center space-y-2.5">
              <p className="text-xs font-medium text-teal-900">
                Your browser is ready to install the app directly:
              </p>
              <button
                onClick={onInstallDirectly}
                className="w-full py-2.5 px-4 rounded-xl bg-teal-600 hover:bg-teal-700 text-white font-semibold flex items-center justify-center gap-2 shadow-sm transition active:scale-95"
              >
                <Download className="w-4 h-4" />
                <span>Install Study Assistant Now</span>
              </button>
            </div>
          )}

          {/* Step-by-step instructions */}
          <div className="space-y-3">
            <h4 className="font-semibold text-slate-800 text-xs flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-teal-600" />
              <span>How to install in your browser:</span>
            </h4>

            {isIOS ? (
              /* iOS Safari instructions */
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 space-y-2">
                <p className="font-medium text-slate-900">iPhone / iPad (Safari):</p>
                <div className="flex items-center gap-2 text-slate-600">
                  <span className="w-5 h-5 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center text-[10px] font-bold">1</span>
                  <span>Tap the <strong>Share</strong> button <Share2 className="w-3.5 h-3.5 inline mx-0.5 text-teal-600" /> at the bottom.</span>
                </div>
                <div className="flex items-center gap-2 text-slate-600">
                  <span className="w-5 h-5 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center text-[10px] font-bold">2</span>
                  <span>Scroll down and tap <strong>Add to Home Screen</strong> <PlusSquare className="w-3.5 h-3.5 inline mx-0.5 text-teal-600" />.</span>
                </div>
              </div>
            ) : (
              /* Android Chrome instructions */
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 space-y-2">
                <p className="font-medium text-slate-900">Android (Chrome / Edge):</p>
                <div className="flex items-center gap-2 text-slate-600">
                  <span className="w-5 h-5 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center text-[10px] font-bold">1</span>
                  <span>Tap the three dots menu <MoreVertical className="w-3.5 h-3.5 inline mx-0.5 text-slate-700" /> in the top right.</span>
                </div>
                <div className="flex items-center gap-2 text-slate-600">
                  <span className="w-5 h-5 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center text-[10px] font-bold">2</span>
                  <span>Tap <strong>Install app</strong> or <strong>Add to Home screen</strong>.</span>
                </div>
              </div>
            )}
          </div>

          <p className="text-[11px] text-slate-400 text-center">
            Once installed, Study Assistant opens fullscreen like a native mobile app without any browser URL bar.
          </p>
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-slate-100 bg-slate-50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-100 text-slate-700 text-xs font-medium transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
