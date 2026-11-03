import React from 'react';
import { 
  Sparkles, 
  RefreshCw, 
  BookOpen, 
  PanelLeftClose, 
  PanelLeft, 
  Bot,
  Scale
} from 'lucide-react';

export default function Header({ 
  healthData, 
  loadingHealth, 
  onRefreshHealth, 
  documentCount = 0,
  sidebarOpen = true,
  onToggleSidebar,
  floatingBotVisible = true,
  onToggleFloatingBot,
  onOpenComparison
}) {
  const isHealthy = healthData?.status === 'healthy';

  return (
    <header className="border-b border-slate-200/80 bg-white/90 backdrop-blur-xs sticky top-0 z-30 transition-colors">
      <div className="max-w-7xl mx-auto px-3 sm:px-4 h-14 flex items-center justify-between gap-2 sm:gap-3">
        {/* Left: Sidebar Toggle & Claude-style Model Selector Pill */}
        <div className="flex items-center gap-2 sm:gap-3 min-w-0">
          {onToggleSidebar && (
            <button
              onClick={onToggleSidebar}
              className="p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-xl transition"
              title={sidebarOpen ? "Close sidebar" : "Open sidebar"}
              aria-label={sidebarOpen ? "Close sidebar" : "Open sidebar"}
            >
              {sidebarOpen ? (
                <PanelLeftClose className="w-4 h-4" />
              ) : (
                <PanelLeft className="w-4 h-4" />
              )}
            </button>
          )}

          {/* Model Pill */}
          <div className="inline-flex items-center gap-1.5 px-2.5 sm:px-3 py-1 rounded-full border border-slate-200 bg-slate-50/70 hover:bg-slate-100/70 transition text-xs font-medium text-slate-800 shadow-2xs truncate">
            <span className="w-2 h-2 rounded-full bg-teal-500 shrink-0" />
            <span className="font-semibold text-slate-900 truncate">Study Assistant</span>
          </div>
        </div>

        {/* Right: Compare Shortcut, Mascot Toggle, Document Counter, Status Dot & Refresh */}
        <div className="flex items-center gap-1.5 sm:gap-2.5 shrink-0">
          {/* Compare Documents Pill (when >= 2 docs exist) */}
          {onOpenComparison && documentCount >= 2 && (
            <button
              onClick={onOpenComparison}
              className="inline-flex items-center gap-1 sm:gap-1.5 px-2 sm:px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-800 border border-indigo-200/90 hover:bg-indigo-100 transition shadow-2xs"
              title="Compare 2 indexed documents side-by-side"
            >
              <Scale className="w-3.5 h-3.5 text-indigo-600" />
              <span className="hidden xs:inline">Compare</span>
            </button>
          )}

          {/* Sparky Mascot Toggle Pill */}
          {onToggleFloatingBot && (
            <button
              onClick={onToggleFloatingBot}
              className={`inline-flex items-center gap-1.5 px-2 sm:px-2.5 py-1 rounded-full text-xs font-medium border transition shadow-2xs ${
                floatingBotVisible
                  ? 'border-teal-300 bg-teal-50 text-teal-800 hover:bg-teal-100'
                  : 'border-slate-200 bg-white text-slate-500 hover:bg-slate-50'
              }`}
              title={floatingBotVisible ? "Hide Sparky Droid" : "Show Sparky Droid"}
            >
              <Bot className="w-3.5 h-3.5 text-teal-600" />
              <span className="hidden sm:inline">Sparky</span>
            </button>
          )}

          {/* Active Docs Pill */}
          {documentCount > 0 && (
            <div className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-teal-50 text-teal-800 border border-teal-200/80">
              <BookOpen className="w-3.5 h-3.5 text-teal-600" />
              <span>{documentCount} {documentCount === 1 ? 'doc' : 'docs'}</span>
            </div>
          )}

          {/* Status Dot */}
          <div 
            className="inline-flex items-center gap-1.5 px-2 sm:px-2.5 py-1 rounded-full text-xs font-medium border border-slate-200 bg-white text-slate-700"
            title={isHealthy ? 'FastAPI Backend Online' : 'Cannot reach backend server'}
          >
            <div className={`w-2 h-2 rounded-full shrink-0 ${isHealthy ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
            <span className="hidden md:inline text-[11px] font-medium">
              {isHealthy ? 'Connected' : 'Offline'}
            </span>
          </div>

          {/* Refresh Connection Button */}
          <button
            onClick={onRefreshHealth}
            disabled={loadingHealth}
            title="Refresh backend status"
            className="p-1.5 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition disabled:opacity-40"
            aria-label="Refresh connection"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingHealth ? 'animate-spin text-teal-600' : ''}`} />
          </button>
        </div>
      </div>
    </header>
  );
}
