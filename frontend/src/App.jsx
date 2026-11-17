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
  Scale,
  MessageSquare,
  Plus
} from 'lucide-react';
import Header from './components/Header';
import UploadSection from './components/UploadSection';
import ChatSection from './components/ChatSection';
import CitationModal from './components/CitationModal';
import CheatSheetModal from './components/CheatSheetModal';
import ComparisonModal from './components/ComparisonModal';
import CompanionBot from './components/CompanionBot';
import InstallModal from './components/InstallModal';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

const createNewSession = (title = 'New Chat') => ({
  id: `chat_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
  title,
  messages: [],
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString()
});

const formatTime = (isoString) => {
  if (!isoString) return '';
  try {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / (1000 * 60));
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  } catch {
    return '';
  }
};

export default function App() {
  const [healthData, setHealthData] = useState(null);
  const [loadingHealth, setLoadingHealth] = useState(true);
  const [sidebarTab, setSidebarTab] = useState('chats'); // 'chats' | 'docs'

  // Persisted Documents
  const [documents, setDocuments] = useState(() => {
    try {
      const saved = localStorage.getItem('rag_study_documents_v1');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem('rag_study_documents_v1', JSON.stringify(documents));
    } catch (err) {
      console.warn('Failed to save documents to localStorage:', err);
    }
  }, [documents]);

  // Persisted Multi-Chat Sessions
  const [sessions, setSessions] = useState(() => {
    try {
      const saved = localStorage.getItem('rag_study_chat_sessions_v1');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed;
        }
      }
    } catch (e) {
      console.warn('Error loading chat sessions:', e);
    }
    return [createNewSession()];
  });

  const [activeSessionId, setActiveSessionId] = useState(() => {
    try {
      const savedId = localStorage.getItem('rag_study_active_session_id_v1');
      if (savedId) return savedId;
    } catch {}
    return '';
  });

  // Ensure activeSessionId always references a valid session
  useEffect(() => {
    if (!sessions.some(s => s.id === activeSessionId) && sessions.length > 0) {
      setActiveSessionId(sessions[0].id);
    }
  }, [sessions, activeSessionId]);

  // Save sessions to localStorage
  useEffect(() => {
    try {
      localStorage.setItem('rag_study_chat_sessions_v1', JSON.stringify(sessions));
    } catch (err) {
      console.warn('Failed to save sessions:', err);
    }
  }, [sessions]);

  // Save activeSessionId to localStorage
  useEffect(() => {
    try {
      if (activeSessionId) {
        localStorage.setItem('rag_study_active_session_id_v1', activeSessionId);
      }
    } catch (err) {
      console.warn('Failed to save activeSessionId:', err);
    }
  }, [activeSessionId]);

  const activeSession = sessions.find((s) => s.id === activeSessionId) || sessions[0] || createNewSession();

  const [selectedCitation, setSelectedCitation] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth >= 768;
    }
    return true;
  });

  // PWA Install prompt states
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [isInstalled, setIsInstalled] = useState(false);
  const [installModalOpen, setInstallModalOpen] = useState(false);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
      if (isStandalone) {
        setIsInstalled(true);
      }

      const handler = (e) => {
        e.preventDefault();
        setDeferredPrompt(e);
      };
      window.addEventListener('beforeinstallprompt', handler);
      return () => window.removeEventListener('beforeinstallprompt', handler);
    }
  }, []);

  const handleDirectInstall = async () => {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      if (outcome === 'accepted') {
        setDeferredPrompt(null);
        setIsInstalled(true);
        setInstallModalOpen(false);
      }
    }
  };

  const handleInstallClick = () => {
    if (deferredPrompt) {
      handleDirectInstall();
    } else {
      setInstallModalOpen(true);
    }
  };

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

  // Multi-Chat Session Handlers
  const handleNewChat = () => {
    // If current session is already empty, just keep it active and close mobile drawer
    if (activeSession && activeSession.messages && activeSession.messages.length === 0) {
      setSidebarTab('chats');
      if (typeof window !== 'undefined' && window.innerWidth < 768) {
        setSidebarOpen(false);
      }
      return;
    }

    const newSession = createNewSession();
    setSessions((prev) => [newSession, ...prev]);
    setActiveSessionId(newSession.id);
    setBotMood('idle');
    setSidebarTab('chats');
    if (typeof window !== 'undefined' && window.innerWidth < 768) {
      setSidebarOpen(false);
    }
  };

  const handleSelectSession = (sessionId) => {
    setActiveSessionId(sessionId);
    setBotMood('idle');
    if (typeof window !== 'undefined' && window.innerWidth < 768) {
      setSidebarOpen(false);
    }
  };

  const handleDeleteSession = (sessionId, e) => {
    if (e) e.stopPropagation();
    setSessions((prev) => {
      const remaining = prev.filter((s) => s.id !== sessionId);
      if (remaining.length === 0) {
        const fresh = createNewSession();
        setActiveSessionId(fresh.id);
        return [fresh];
      }
      if (activeSessionId === sessionId) {
        setActiveSessionId(remaining[0].id);
      }
      return remaining;
    });
  };

  // Handle sending new chat message (scoped to activeSession only)
  const handleSendMessage = (msg) => {
    const currentId = activeSession?.id || activeSessionId;
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id !== currentId) return s;

        const updatedMessages = [...(s.messages || []), msg];
        let updatedTitle = s.title;

        // Auto-title from the first user question if still default
        if ((!s.title || s.title === 'New Chat') && msg.role === 'user') {
          const clean = msg.content.trim().replace(/\n+/g, ' ');
          updatedTitle = clean.length > 28 ? `${clean.slice(0, 28)}...` : clean;
        }

        return {
          ...s,
          title: updatedTitle,
          messages: updatedMessages,
          updatedAt: new Date().toISOString(),
        };
      })
    );
  };

  // Handle clearing current session's conversation
  const handleClearChat = () => {
    const currentId = activeSession?.id || activeSessionId;
    setSessions((prev) =>
      prev.map((s) =>
        s.id === currentId
          ? { ...s, messages: [], updatedAt: new Date().toISOString() }
          : s
      )
    );
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
    <div className="flex h-[100dvh] h-screen w-full max-w-full overflow-hidden bg-[#F8FAFC] text-slate-900 font-sans antialiased relative">
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
          ${sidebarOpen ? 'w-[85vw] max-w-[320px] sm:w-80 translate-x-0' : 'w-0 -translate-x-full md:w-0'}
          transition-all duration-200 ease-in-out border-r border-slate-200/80 bg-white flex flex-col shrink-0 overflow-hidden shadow-xl md:shadow-xs
        `}
        aria-label="Study Assistant Navigation & Knowledge Base"
      >
        <div className="w-full flex flex-col h-full">
          {/* Sidebar Top: New Chat & Close Toggle */}
          <div className="p-3.5 border-b border-slate-100 flex items-center justify-between gap-2">
            <button
              onClick={handleNewChat}
              className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-xl bg-teal-50/80 hover:bg-teal-100/80 border border-teal-200 text-xs font-semibold text-teal-800 transition shadow-2xs group"
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

          {/* Segmented Tab Switcher: Chats vs Documents */}
          <div className="px-3 pt-2 pb-1.5 flex gap-1 border-b border-slate-100 bg-slate-50/50">
            <button
              onClick={() => setSidebarTab('chats')}
              className={`flex-1 py-1.5 px-2 rounded-lg text-xs font-medium flex items-center justify-center gap-1.5 transition ${
                sidebarTab === 'chats'
                  ? 'bg-white text-teal-900 shadow-2xs font-semibold border border-slate-200/80'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/60'
              }`}
            >
              <MessageSquare className="w-3.5 h-3.5 text-teal-600" />
              <span>Chats ({sessions.length})</span>
            </button>

            <button
              onClick={() => setSidebarTab('docs')}
              className={`flex-1 py-1.5 px-2 rounded-lg text-xs font-medium flex items-center justify-center gap-1.5 transition ${
                sidebarTab === 'docs'
                  ? 'bg-white text-teal-900 shadow-2xs font-semibold border border-slate-200/80'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/60'
              }`}
            >
              <BookOpen className="w-3.5 h-3.5 text-teal-600" />
              <span>Files ({documents.length})</span>
            </button>
          </div>

          {/* Sidebar Body: Dynamic Switcher */}
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {sidebarTab === 'chats' ? (
              /* Chat Sessions History List */
              <div className="space-y-1.5">
                <div className="px-1 text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Recent Conversations
                </div>

                {sessions.map((session) => {
                  const isActive = session.id === (activeSession?.id || activeSessionId);
                  return (
                    <div
                      key={session.id}
                      onClick={() => handleSelectSession(session.id)}
                      className={`group relative flex items-center justify-between gap-2 px-3 py-2.5 rounded-xl cursor-pointer transition border text-left ${
                        isActive
                          ? 'bg-teal-50/80 border-teal-300 text-teal-950 font-medium shadow-2xs'
                          : 'bg-white hover:bg-slate-50 border-slate-200/70 text-slate-700 hover:border-slate-300'
                      }`}
                    >
                      <div className="flex items-center gap-2.5 min-w-0 flex-1">
                        <MessageSquare className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-teal-600' : 'text-slate-400 group-hover:text-slate-600'}`} />
                        <div className="min-w-0 flex-1">
                          <p className="text-xs truncate font-medium">{session.title || 'New Chat'}</p>
                          <p className="text-[10px] text-slate-400 mt-0.5">
                            {session.messages?.length || 0} msgs • {formatTime(session.updatedAt || session.createdAt)}
                          </p>
                        </div>
                      </div>

                      {/* Delete individual chat session */}
                      <button
                        onClick={(e) => handleDeleteSession(session.id, e)}
                        className="p-1 rounded-md text-slate-400 hover:text-red-600 hover:bg-red-50 opacity-80 sm:opacity-0 group-hover:opacity-100 transition shrink-0"
                        title="Delete this chat"
                        aria-label="Delete this chat"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  );
                })}
              </div>
            ) : (
              /* Knowledge Base & PDF Upload Section */
              <UploadSection
                apiBase={API_BASE}
                documents={documents}
                onDocumentUploaded={handleDocumentUploaded}
                disabled={healthData?.status !== 'healthy' && !loadingHealth}
                onOpenCheatSheet={() => setCheatSheetOpen(true)}
                onOpenComparison={() => setComparisonModalOpen(true)}
                onBotCelebrate={triggerBotCelebration}
              />
            )}
          </div>

          {/* Sidebar Bottom: Session Info & Clear Button */}
          <div className="p-3.5 border-t border-slate-100 bg-slate-50/60 flex items-center justify-between text-xs text-slate-500">
            <div className="flex items-center gap-1.5 font-medium text-[11px] text-slate-600">
              <ShieldCheck className="w-3.5 h-3.5 text-teal-600" />
              <span>Grounded RAG Mode</span>
            </div>

            {activeSession?.messages?.length > 0 && (
              <button
                onClick={handleClearChat}
                className="text-[11px] text-slate-400 hover:text-red-600 flex items-center gap-1 transition"
                title="Clear current conversation messages"
              >
                <Trash2 className="w-3 h-3" />
                <span>Clear chat</span>
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
          onInstallClick={handleInstallClick}
          isInstalled={isInstalled}
          onNewChat={handleNewChat}
          activeChatTitle={activeSession?.title}
        />

        {/* Chat Canvas (Displaying ONLY the active session's messages) */}
        <main className="flex-1 min-h-0 relative flex flex-col overflow-hidden">
          <ChatSection
            apiBase={API_BASE}
            messages={activeSession?.messages || []}
            onSendMessage={handleSendMessage}
            onClearChat={handleClearChat}
            onCitationClick={(cite) => setSelectedCitation(cite)}
            documentCount={documents.length}
            onAttachClick={() => {
              setSidebarTab('docs');
              setSidebarOpen(true);
            }}
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
      {/* PWA Mobile Install Modal */}
      <InstallModal
        isOpen={installModalOpen}
        onClose={() => setInstallModalOpen(false)}
        onInstallDirectly={handleDirectInstall}
        canInstallDirectly={!!deferredPrompt}
      />
    </div>
  );
}
