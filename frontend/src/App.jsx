import React, { useState, useEffect, useCallback } from 'react';
import { 
  SquarePen, 
  BookOpen, 
  Trash2, 
  PanelLeftClose, 
  PanelLeft, 
  ShieldCheck, 
  Layers,
  Bot,
  Minus,
  Sparkles,
  Scale
} from 'lucide-react';
import Header from './components/Header';
import UploadSection from './components/UploadSection';
import ChatSection from './components/ChatSection';
import CitationModal from './components/CitationModal';
import CheatSheetModal from './components/CheatSheetModal';
import ComparisonModal from './components/ComparisonModal';
import CompanionBot from './components/CompanionBot';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

export default function App() {
  const [healthData, setHealthData] = useState(null);
  const [loadingHealth, setLoadingHealth] = useState(true);
  const [documents, setDocuments] = useState([]);
  const [messages, setMessages] = useState([]);
  const [selectedCitation, setSelectedCitation] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth >= 768;
    }
    return true;
  });

  // Sparky Droid & Study Utility States
  const [botMood, setBotMood] = useState('idle');
  const [floatingBotVisible, setFloatingBotVisible] = useState(true);
  const [mascotMinimized, setMascotMinimized] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth < 640;
    }
    return false;
  });
  const [cheatSheetOpen, setCheatSheetOpen] = useState(false);
  const [comparisonModalOpen, setComparisonModalOpen] = useState(false);
  const [tipIndex, setTipIndex] = useState(0);

  const studyTips = [
    "Ask me 'Quiz me' to test your active recall!",
    "Click 'Listen' to have me read the explanation!",
    "Upload 2 PDFs and click 'Compare' for a Contrast Matrix!",
    "Try 'What more can we do?' for creative extensions!",
    "Click 'Cheat-Sheet' for an instant 1-page summary!",
    "I ground every answer in your uploaded PDF pages!"
  ];

  // Poll backend health status
  const checkHealth = useCallback(async () => {
    setLoadingHealth(true);
    try {
      const res = await fetch(`${API_BASE}/health`);
      if (res.ok) {
        const data = await res.json();
        setHealthData(data);
      } else {
        setHealthData(null);
      }
    } catch (err) {
      console.warn('Backend health check error:', err);
      setHealthData(null);
    } finally {
      setLoadingHealth(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  // Handle new document uploaded
  const handleDocumentUploaded = (newDoc) => {
    setDocuments((prev) => {
      const filtered = prev.filter((d) => d.filename !== newDoc.filename);
      return [newDoc, ...filtered];
    });
    // Trigger celebration on upload
    triggerBotCelebration();
    // Auto-close drawer on mobile to return focus to chat
    if (typeof window !== 'undefined' && window.innerWidth < 768) {
      setSidebarOpen(false);
    }
  };

  const triggerBotCelebration = () => {
    setBotMood('celebrating');
    setTimeout(() => setBotMood('idle'), 2600);
  };

  // Handle sending new chat message
  const handleSendMessage = (msg) => {
    setMessages((prev) => [...prev, msg]);
  };

  // Handle clearing conversation / starting new chat
  const handleClearChat = () => {
    setMessages([]);
    setBotMood('idle');
    if (typeof window !== 'undefined' && window.innerWidth < 768) {
      setSidebarOpen(false);
    }
  };

  const getBotSpeechBubble = () => {
    if (botMood === 'thinking') return 'Scanning your notes...';
    if (botMood === 'speaking') return 'Reading aloud for you!';
    if (botMood === 'eureka') return 'Eureka! Great idea!';
    if (botMood === 'celebrating') return 'Awesome job! Got it!';
    if (botMood === 'puzzled') return 'Hmm, checking evidence...';
    return studyTips[tipIndex % studyTips.length];
  };

  const cycleMascotTip = () => {
    setTipIndex((prev) => prev + 1);
  };

  return (
    <div className="flex h-screen w-full max-w-full overflow-hidden bg-[#F8FAFC] text-slate-900 font-sans antialiased relative">
      {/* Mobile Drawer Overlay Backdrop */}
      {sidebarOpen && (
        <div 
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs z-40 md:hidden animate-fadeIn"
          aria-hidden="true"
        />
      )}

      {/* Claude-style Left Sidebar / Mobile Slide-Over Drawer */}
      <aside 
        className={`
          fixed inset-y-0 left-0 z-50 md:static md:z-30 h-full
          ${sidebarOpen ? 'w-80 translate-x-0' : 'w-0 -translate-x-full md:w-0'}
          transition-all duration-200 ease-in-out border-r border-slate-200/80 bg-white flex flex-col shrink-0 overflow-hidden shadow-xl md:shadow-xs
        `}
        aria-label="Study Assistant Navigation & Knowledge Base"
      >
        <div className="w-80 flex flex-col h-full">
          {/* Sidebar Top: New Chat & Close Toggle */}
          <div className="p-3.5 border-b border-slate-100 flex items-center justify-between gap-2">
            <button
              onClick={handleClearChat}
              className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200/80 text-xs font-medium text-slate-800 transition shadow-2xs group"
              title="Start a fresh conversation"
            >
              <SquarePen className="w-3.5 h-3.5 text-teal-600 group-hover:scale-110 transition-transform" />
              <span>Start new chat</span>
            </button>

            <button
              onClick={() => setSidebarOpen(false)}
              className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
              title="Collapse sidebar"
              aria-label="Collapse sidebar"
            >
              <PanelLeftClose className="w-4 h-4" />
            </button>
          </div>

          {/* Sidebar Body: Knowledge Base & Upload Section */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            <UploadSection
              apiBase={API_BASE}
              documents={documents}
              onDocumentUploaded={handleDocumentUploaded}
              disabled={healthData?.status !== 'healthy' && !loadingHealth}
              onOpenCheatSheet={() => setCheatSheetOpen(true)}
              onOpenComparison={() => setComparisonModalOpen(true)}
              onBotCelebrate={triggerBotCelebration}
            />
          </div>

          {/* Sidebar Bottom: Session Info & Clear Button */}
          <div className="p-3.5 border-t border-slate-100 bg-slate-50/60 flex items-center justify-between text-xs text-slate-500">
            <div className="flex items-center gap-1.5 font-medium text-[11px] text-slate-600">
              <ShieldCheck className="w-3.5 h-3.5 text-teal-600" />
              <span>Grounded RAG Mode</span>
            </div>

            {messages.length > 0 && (
              <button
                onClick={handleClearChat}
                className="text-[11px] text-slate-400 hover:text-red-600 flex items-center gap-1 transition"
                title="Clear current conversation"
              >
                <Trash2 className="w-3 h-3" />
                <span>Clear</span>
              </button>
            )}
          </div>
        </div>
      </aside>

      {/* Main Area: Top Bar + Centered Chat Canvas */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        {/* Minimalist Top Header */}
        <Header
          healthData={healthData}
          loadingHealth={loadingHealth}
          onRefreshHealth={checkHealth}
          documentCount={documents.length}
          sidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen((prev) => !prev)}
          floatingBotVisible={floatingBotVisible}
          onToggleFloatingBot={() => setFloatingBotVisible((prev) => !prev)}
          onOpenComparison={() => setComparisonModalOpen(true)}
        />

        {/* Chat Canvas */}
        <main className="flex-1 min-h-0 relative flex flex-col overflow-hidden">
          <ChatSection
            apiBase={API_BASE}
            messages={messages}
            onSendMessage={handleSendMessage}
            onClearChat={handleClearChat}
            onCitationClick={(cite) => setSelectedCitation(cite)}
            documentCount={documents.length}
            onAttachClick={() => setSidebarOpen(true)}
            onBotMoodChange={(mood) => setBotMood(mood)}
            onOpenCheatSheet={() => setCheatSheetOpen(true)}
            onOpenComparison={() => setComparisonModalOpen(true)}
          />
        </main>
      </div>

      {/* Roaming Interactive Floating Companion Droid (Bottom-Right) */}
      {floatingBotVisible && (
        <div className="fixed bottom-20 right-3 sm:bottom-24 sm:right-7 z-30 pointer-events-auto flex flex-col items-end animate-fadeIn max-w-[calc(100vw-1.5rem)]">
          {mascotMinimized ? (
            /* Minimized mascot pill */
            <button
              onClick={() => setMascotMinimized(false)}
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/95 border border-slate-200/90 shadow-md hover:border-teal-400 hover:bg-slate-50 transition text-xs font-medium text-slate-700 group backdrop-blur-xs"
              title="Expand Sparky Droid"
            >
              <span className="w-2 h-2 rounded-full bg-teal-500 animate-pulse" />
              <Bot className="w-4 h-4 text-teal-600 group-hover:scale-110 transition-transform" />
              <span>Sparky</span>
            </button>
          ) : (
            /* Full Floating Droid Mascot */
            <div className="relative flex flex-col items-end">
              {/* Controls bar above bot */}
              <div className="flex items-center gap-1 mb-1 mr-1 bg-white/90 backdrop-blur-xs border border-slate-200/80 rounded-full px-2 py-0.5 shadow-2xs">
                <span className="text-[10px] font-mono text-slate-500 font-medium">Sparky</span>
                <button
                  onClick={() => setMascotMinimized(true)}
                  className="p-0.5 text-slate-400 hover:text-slate-700 transition"
                  title="Minimize Sparky"
                >
                  <Minus className="w-3 h-3" />
                </button>
              </div>

              {/* Vector Animated Mascot */}
              <CompanionBot
                size="md"
                mood={botMood}
                showBubble={true}
                bubbleText={getBotSpeechBubble()}
                bubbleAlign="right"
                onClick={cycleMascotTip}
              />
            </div>
          )}
        </div>
      )}

      {/* Citation Inspector Modal */}
      <CitationModal
        citation={selectedCitation}
        onClose={() => setSelectedCitation(null)}
      />

      {/* Automatic Study Cheat-Sheet Modal */}
      <CheatSheetModal
        isOpen={cheatSheetOpen}
        onClose={() => setCheatSheetOpen(false)}
        apiBase={API_BASE}
        documents={documents}
        onBotCelebrate={triggerBotCelebration}
      />

      {/* Multi-Document Comparison Matrix Modal */}
      <ComparisonModal
        isOpen={comparisonModalOpen}
        onClose={() => setComparisonModalOpen(false)}
        apiBase={API_BASE}
        documents={documents}
        onBotCelebrate={triggerBotCelebration}
        onBotMoodChange={(mood) => setBotMood(mood)}
        onCitationClick={(cite) => setSelectedCitation(cite)}
      />
    </div>
  );
}
