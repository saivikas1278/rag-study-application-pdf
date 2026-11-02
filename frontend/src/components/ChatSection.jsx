import React, { useState, useRef, useEffect } from 'react';
import { 
  Sparkles, 
  User, 
  Bot, 
  AlertCircle, 
  BookOpen, 
  Trash2, 
  RefreshCw, 
  AlertTriangle, 
  Lightbulb, 
  ArrowUp, 
  Paperclip, 
  CheckCircle2, 
  Volume2, 
  VolumeX, 
  FileSpreadsheet,
  Scale
} from 'lucide-react';
import CompanionBot from './CompanionBot';
import { speechService } from '../services/speechService';

function FormattedMessage({ content }) {
  if (!content) return null;

  const lines = content.split('\n');
  const renderedElements = [];
  let inSuggestionBlock = false;
  let suggestionLines = [];

  const flushSuggestionBlock = () => {
    if (suggestionLines.length > 0) {
      renderedElements.push(
        <div 
          key={`sugg-${renderedElements.length}`} 
          className="my-3.5 p-4 rounded-xl border border-teal-200/90 bg-teal-50/60 space-y-2.5 shadow-2xs"
        >
          <div className="flex items-center gap-2 text-xs font-semibold text-teal-900 border-b border-teal-200/70 pb-2">
            <span className="text-sm">💡</span>
            <span className="tracking-wide">Proactive Suggestions & Next Steps</span>
          </div>
          <div className="space-y-1.5 text-xs text-slate-700 leading-relaxed">
            {suggestionLines.map((sLine, sIdx) => renderLine(sLine, `s-${sIdx}`))}
          </div>
        </div>
      );
      suggestionLines = [];
    }
  };

  const renderInline = (text) => {
    const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i} className="text-slate-900 font-semibold">{part.slice(2, -2)}</strong>;
      }
      if (part.startsWith('`') && part.endsWith('`')) {
        return (
          <code key={i} className="px-1.5 py-0.5 rounded-md border border-slate-200 bg-slate-100 font-mono text-[11.5px] text-teal-800">
            {part.slice(1, -1)}
          </code>
        );
      }
      return part;
    });
  };

  const renderLine = (line, idx) => {
    const trimmed = line.trim();
    if (!trimmed) return <div key={idx} className="h-1.5" />;

    // Markdown Headers
    if (trimmed.startsWith('### ')) {
      return (
        <h4 key={idx} className="text-xs sm:text-sm font-semibold tracking-tight text-slate-900 mt-3 mb-1">
          {renderInline(trimmed.replace(/^###\s*/, ''))}
        </h4>
      );
    }
    if (trimmed.startsWith('## ')) {
      return (
        <h3 key={idx} className="text-sm sm:text-base font-semibold tracking-tight text-slate-900 mt-4 mb-1.5 border-b border-slate-100 pb-1">
          {renderInline(trimmed.replace(/^##\s*/, ''))}
        </h3>
      );
    }

    // Bullet points
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      return (
        <div key={idx} className="flex items-start gap-2.5 pl-1 text-slate-700">
          <span className="w-1.5 h-1.5 rounded-full bg-teal-600 mt-2 shrink-0" />
          <span className="flex-1 text-xs sm:text-sm leading-relaxed">{renderInline(trimmed.slice(2))}</span>
        </div>
      );
    }

    // Numbered lists
    const numMatch = trimmed.match(/^(\d+)\.\s+(.*)$/);
    if (numMatch) {
      return (
        <div key={idx} className="flex items-start gap-2.5 pl-1 text-slate-700">
          <span className="font-mono text-xs font-semibold text-teal-700 min-w-[18px] shrink-0">{numMatch[1]}.</span>
          <span className="flex-1 text-xs sm:text-sm leading-relaxed">{renderInline(numMatch[2])}</span>
        </div>
      );
    }

    return (
      <p key={idx} className="text-xs sm:text-sm text-slate-800 leading-relaxed">
        {renderInline(line)}
      </p>
    );
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    if (trimmed.toLowerCase().includes('proactive suggestions') || trimmed.toLowerCase().includes('💡 proactive suggestions')) {
      inSuggestionBlock = true;
      continue;
    }

    if (inSuggestionBlock) {
      if ((trimmed.startsWith('## ') || trimmed.startsWith('### ')) && !trimmed.toLowerCase().includes('suggestions')) {
        inSuggestionBlock = false;
        flushSuggestionBlock();
        renderedElements.push(renderLine(line, i));
      } else {
        suggestionLines.push(line);
      }
    } else {
      renderedElements.push(renderLine(line, i));
    }
  }

  if (inSuggestionBlock) {
    flushSuggestionBlock();
  }

  return <div className="space-y-2">{renderedElements}</div>;
}

export default function ChatSection({ 
  apiBase, 
  messages, 
  onSendMessage, 
  onClearChat, 
  onCitationClick, 
  documentCount = 0,
  onAttachClick,
  onBotMoodChange,
  onOpenCheatSheet,
  onOpenComparison
}) {
  const [inputQuestion, setInputQuestion] = useState('');
  const [querying, setQuerying] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [currentlySpeakingId, setCurrentlySpeakingId] = useState(null);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  // Auto-scroll to latest message
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, querying]);

  // Clean up speech on unmount
  useEffect(() => {
    return () => speechService.stop();
  }, []);

  // Auto-resize textarea
  const adjustTextareaHeight = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  };

  const handleInputChange = (e) => {
    setInputQuestion(e.target.value);
    adjustTextareaHeight();
  };

  const handleToggleSpeak = (msg) => {
    if (currentlySpeakingId === msg.id) {
      speechService.stop();
      setCurrentlySpeakingId(null);
      if (onBotMoodChange) onBotMoodChange('idle');
    } else {
      if (onBotMoodChange) onBotMoodChange('speaking');
      setCurrentlySpeakingId(msg.id);
      speechService.speak(msg.content, {
        onStart: () => {
          setCurrentlySpeakingId(msg.id);
          if (onBotMoodChange) onBotMoodChange('speaking');
        },
        onEnd: () => {
          setCurrentlySpeakingId(null);
          if (onBotMoodChange) onBotMoodChange('idle');
        },
        onError: () => {
          setCurrentlySpeakingId(null);
          if (onBotMoodChange) onBotMoodChange('idle');
        }
      });
    }
  };

  const handleSubmit = async (e, directQuery = null) => {
    if (e && e.preventDefault) e.preventDefault();
    setErrorMessage('');

    const targetQuery = directQuery || inputQuestion;
    const trimmed = targetQuery.trim();
    if (!trimmed || querying) return;

    if (trimmed.length > 1000) {
      setErrorMessage('Question is too long (maximum 1000 characters).');
      return;
    }

    // Determine bot reaction mood from question intent
    const lower = trimmed.toLowerCase();
    if (lower.includes('what more') || lower.includes('suggest') || lower.includes('next steps') || lower.includes('idea')) {
      if (onBotMoodChange) onBotMoodChange('eureka');
    } else {
      if (onBotMoodChange) onBotMoodChange('thinking');
    }

    // Add user message to parent history
    const userMessageId = Date.now().toString();
    const userMsg = {
      id: userMessageId,
      role: 'user',
      content: trimmed,
      timestamp: new Date(),
    };

    onSendMessage(userMsg);
    if (!directQuery) {
      setInputQuestion('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
    setQuerying(true);

    try {
      const res = await fetch(`${apiBase}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: trimmed,
          top_k: 6,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        let errDetail = 'Failed to generate answer.';
        if (typeof data.detail === 'string') {
          errDetail = data.detail;
        } else if (Array.isArray(data.detail)) {
          errDetail = data.detail.map((d) => d.msg).join('; ');
        }
        throw new Error(errDetail);
      }

      // Add assistant response to chat
      const assistantMsg = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.answer,
        citations: data.citations || [],
        hasSufficientContext: data.has_sufficient_context,
        modelUsed: data.model_used,
        timestamp: new Date(),
      };

      onSendMessage(assistantMsg);

      // Trigger celebration on successful retrieval
      if (data.has_sufficient_context === false) {
        if (onBotMoodChange) onBotMoodChange('puzzled');
      } else {
        if (onBotMoodChange) {
          onBotMoodChange('celebrating');
          setTimeout(() => onBotMoodChange('idle'), 2400);
        }
      }

    } catch (err) {
      console.error('Query execution error:', err);
      setErrorMessage(err.message || 'An error occurred while generating the answer.');
      if (onBotMoodChange) onBotMoodChange('puzzled');

      // Add error card into chat stream
      const errorMsg = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Error: ${err.message || 'Unable to process query.'}`,
        isError: true,
        timestamp: new Date(),
      };
      onSendMessage(errorMsg);
    } finally {
      setQuerying(false);
      setTimeout(() => textareaRef.current?.focus(), 50);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const starterQuestions = [
    {
      title: "Core Concepts",
      desc: "Main takeaways and definitions",
      prompt: "What are the main concepts and key takeaways in this document?"
    },
    {
      title: "Intuitive Analogy",
      desc: "Simplify difficult mechanisms",
      prompt: "Explain the most complex concept in these notes using a simple, real-world analogy."
    },
    {
      title: "💡 Next Steps & Ideas",
      desc: "What more can we do?",
      prompt: "What more can we do with this material? Suggest next steps and practical extensions."
    },
    documentCount >= 2 ? {
      title: "⚖️ Compare Documents",
      desc: "Analyze differences and common ground",
      prompt: "Compare and contrast our uploaded study materials, highlighting key differences, shared theories, and unique insights."
    } : {
      title: "🎯 Practice Quiz",
      desc: "Test active recall",
      prompt: "Quiz me on this material with 3 conceptual practice questions to test my understanding."
    }
  ];

  const getMsgBotMood = (msg) => {
    if (currentlySpeakingId === msg.id) return 'speaking';
    if (msg.isError) return 'puzzled';
    if (msg.hasSufficientContext === false) return 'puzzled';
    if (msg.content && msg.content.includes('💡')) return 'eureka';
    return 'idle';
  };

  return (
    <div className="flex flex-col h-full bg-[#F8FAFC] relative">
      {/* Messages Stream Container */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 space-y-6">
        <div className="max-w-3xl mx-auto w-full space-y-6">
          {messages.length === 0 ? (
            /* Claude-style Centered Empty State */
            <div className="min-h-[60vh] flex flex-col items-center justify-center text-center px-4 py-8 space-y-8 animate-fadeIn">
              {/* Sparky Animated Droid Hero */}
              <div className="flex flex-col items-center space-y-3">
                <CompanionBot 
                  size="lg" 
                  mood="idle" 
                  showBubble={true} 
                  bubbleText="Hi! I'm Sparky, your study buddy!"
                  className="mb-1"
                />
                <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight text-slate-900 font-sans">
                  How can I help you study today?
                </h2>
                <p className="text-sm text-slate-500 max-w-md leading-relaxed">
                  {documentCount > 0 
                    ? `I've indexed ${documentCount} study ${documentCount === 1 ? 'document' : 'documents'}. Ask anything, compare materials, or pick a study mode below.`
                    : "Upload lecture slides or textbook PDFs in the sidebar, or ask a question to get started."
                  }
                </p>
              </div>

              {/* 2x2 Starter Question Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-xl text-left">
                {starterQuestions.map((item, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setInputQuestion(item.prompt);
                      textareaRef.current?.focus();
                      adjustTextareaHeight();
                    }}
                    disabled={querying}
                    className="p-3.5 rounded-xl border border-slate-200/90 bg-white hover:bg-slate-50 hover:border-teal-300 text-left transition-all duration-200 shadow-2xs group flex flex-col justify-between"
                  >
                    <div>
                      <div className="text-xs font-semibold text-slate-800 group-hover:text-teal-700 transition-colors">
                        {item.title}
                      </div>
                      <div className="text-[11.5px] text-slate-500 mt-0.5 line-clamp-1">
                        {item.desc}
                      </div>
                    </div>
                    <div className="text-[11px] text-teal-600 font-medium mt-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <span>Use prompt</span>
                      <span>→</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            /* Active Conversation Flow */
            messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3.5 animate-fadeIn ${
                  msg.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                {/* Assistant Vector Droid Avatar */}
                {msg.role === 'assistant' && (
                  <div className="shrink-0 mt-0.5">
                    <CompanionBot 
                      size="sm" 
                      mood={getMsgBotMood(msg)}
                      interactive={true}
                    />
                  </div>
                )}

                {/* Message Bubble */}
                <div
                  className={`relative ${
                    msg.role === 'user'
                      ? 'max-w-xl bg-slate-100 border border-slate-200/80 text-slate-900 rounded-2xl rounded-br-xs px-4 py-3 shadow-2xs'
                      : msg.isError
                      ? 'max-w-2xl bg-white border border-red-200 rounded-2xl p-4 text-red-700 shadow-2xs'
                      : 'flex-1 max-w-2xl text-slate-800 space-y-3 pt-0.5'
                  }`}
                >
                  {/* Message Content */}
                  {msg.role === 'assistant' && !msg.isError ? (
                    <FormattedMessage content={msg.content} />
                  ) : (
                    <p className="text-xs sm:text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                  )}

                  {/* Insufficient Context Warning */}
                  {msg.role === 'assistant' && msg.hasSufficientContext === false && (
                    <div className="p-3 rounded-xl border border-amber-200 bg-amber-50/80 text-xs text-amber-900 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 shrink-0 text-amber-600" />
                      <span>Document context lacked definitive evidence for this query. The answer is guided by general principles.</span>
                    </div>
                  )}

                  {/* Verified Citations Chips */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="pt-2 border-t border-slate-100 space-y-1.5">
                      <span className="text-[11px] font-medium text-slate-500 block">
                        Grounded Sources & Citations:
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {msg.citations.map((cite, idx) => (
                          <button
                            key={`${cite.filename}-${cite.page_number}-${idx}`}
                            onClick={() => onCitationClick && onCitationClick(cite)}
                            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border border-slate-200 bg-white hover:bg-teal-50 hover:border-teal-300 text-slate-700 transition shadow-2xs group"
                            title={`Inspect page ${cite.page_number}`}
                          >
                            <BookOpen className="w-3.5 h-3.5 text-slate-400 group-hover:text-teal-600 transition-colors" />
                            <span className="truncate max-w-[140px] text-slate-800">{cite.filename}</span>
                            <span className="text-[10.5px] px-1 py-0.2 rounded bg-slate-100 text-slate-600 font-mono">
                              p.{cite.page_number}
                            </span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Action Bar: Text-to-Speech + Tools + Follow-up Quick Prompts */}
                  {msg.role === 'assistant' && !msg.isError && (
                    <div className="pt-2 flex flex-wrap items-center gap-1.5 border-t border-slate-100/80">
                      {/* Text to Speech Button */}
                      <button
                        onClick={() => handleToggleSpeak(msg)}
                        className={`px-2.5 py-1 rounded-full text-xs font-medium border transition shadow-2xs flex items-center gap-1.5 ${
                          currentlySpeakingId === msg.id
                            ? 'border-teal-500 bg-teal-50 text-teal-700 animate-pulse'
                            : 'border-slate-200 bg-white hover:bg-slate-50 hover:border-teal-300 text-slate-600 hover:text-teal-700'
                        }`}
                        title={currentlySpeakingId === msg.id ? "Stop reading" : "Read explanation aloud"}
                      >
                        {currentlySpeakingId === msg.id ? (
                          <>
                            <VolumeX className="w-3.5 h-3.5 text-teal-600" />
                            <span>Stop</span>
                          </>
                        ) : (
                          <>
                            <Volume2 className="w-3.5 h-3.5 text-slate-500" />
                            <span>Listen</span>
                          </>
                        )}
                      </button>

                      {/* Compare Shortcut (when >= 2 docs exist) */}
                      {onOpenComparison && documentCount >= 2 && (
                        <button
                          onClick={onOpenComparison}
                          className="px-2.5 py-1 rounded-full text-xs font-medium border border-indigo-200 bg-indigo-50/70 hover:bg-indigo-100 text-indigo-800 transition shadow-2xs flex items-center gap-1"
                          title="Compare 2 documents side-by-side"
                        >
                          <Scale className="w-3 h-3 text-indigo-600" />
                          <span>Compare</span>
                        </button>
                      )}

                      {/* Cheat-Sheet shortcut */}
                      {onOpenCheatSheet && (
                        <button
                          onClick={onOpenCheatSheet}
                          className="px-2.5 py-1 rounded-full text-xs font-medium border border-slate-200 bg-white hover:bg-slate-50 hover:border-teal-300 text-slate-600 hover:text-teal-700 transition shadow-2xs flex items-center gap-1"
                          title="Generate instant 1-page study cheatsheet"
                        >
                          <span>📑 Cheat-Sheet</span>
                        </button>
                      )}

                      {/* Quick follow-ups */}
                      <button
                        onClick={() => handleSubmit(null, "What more can we do with this topic? Suggest next steps and practical ideas.")}
                        disabled={querying}
                        className="px-2.5 py-1 rounded-full text-xs font-medium border border-slate-200 bg-white hover:bg-slate-50 hover:border-teal-300 text-slate-600 hover:text-teal-700 transition shadow-2xs flex items-center gap-1 disabled:opacity-40"
                      >
                        <span>💡 Next Steps</span>
                      </button>
                      <button
                        onClick={() => handleSubmit(null, "Quiz me on this with 3 practice questions to test my recall.")}
                        disabled={querying}
                        className="px-2.5 py-1 rounded-full text-xs font-medium border border-slate-200 bg-white hover:bg-slate-50 hover:border-teal-300 text-slate-600 hover:text-teal-700 transition shadow-2xs flex items-center gap-1 disabled:opacity-40"
                      >
                        <span>🎯 Quiz Me</span>
                      </button>
                      <button
                        onClick={() => handleSubmit(null, "Can you explain this in even simpler terms with a real-world analogy?")}
                        disabled={querying}
                        className="px-2.5 py-1 rounded-full text-xs font-medium border border-slate-200 bg-white hover:bg-slate-50 hover:border-teal-300 text-slate-600 hover:text-teal-700 transition shadow-2xs flex items-center gap-1 disabled:opacity-40"
                      >
                        <span>🔍 Analogy</span>
                      </button>
                    </div>
                  )}

                  {/* Timestamp */}
                  <div className={`text-[10px] text-slate-400 font-mono flex items-center gap-1.5 pt-0.5 ${
                    msg.role === 'user' ? 'justify-end' : 'justify-start'
                  }`}>
                    <span>{new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  </div>
                </div>
              </div>
            ))
          )}

          {/* Assistant Synthesizing Indicator with Animated Droid */}
          {querying && (
            <div className="flex gap-3.5 items-start max-w-xl mr-auto animate-fadeIn">
              <div className="shrink-0 mt-0.5">
                <CompanionBot size="sm" mood="thinking" />
              </div>
              <div className="p-3.5 rounded-2xl bg-white border border-slate-200 text-xs text-slate-600 flex items-center gap-2.5 shadow-2xs">
                <RefreshCw className="w-3.5 h-3.5 text-teal-600 animate-spin" />
                <span>Reading indexed passages & synthesizing answer...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Claude Signature Floating Bottom Input Dock */}
      <div className="sticky bottom-0 w-full px-4 sm:px-6 pb-4 pt-2 bg-gradient-to-t from-[#F8FAFC] via-[#F8FAFC]/90 to-transparent pointer-events-auto">
        <div className="max-w-3xl mx-auto w-full">
          {errorMessage && (
            <div className="mb-2 p-2.5 rounded-xl border border-red-200 bg-red-50 text-xs text-red-700 flex items-center gap-2 shadow-2xs animate-fadeIn">
              <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
              <span className="truncate">{errorMessage}</span>
            </div>
          )}

          <form 
            onSubmit={handleSubmit}
            className="bg-white rounded-2xl border border-slate-200/90 shadow-md hover:border-slate-300 focus-within:border-teal-500 focus-within:ring-2 focus-within:ring-teal-500/15 transition-all p-3"
          >
            {/* Resizing Textarea */}
            <textarea
              ref={textareaRef}
              rows={1}
              value={inputQuestion}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              disabled={querying}
              placeholder="Ask a question about your study notes..."
              className="w-full resize-none bg-transparent border-0 focus:outline-none focus:ring-0 p-1 text-sm text-slate-900 placeholder:text-slate-400 leading-relaxed max-h-40"
              maxLength={1000}
            />

            {/* Bottom Controls inside dock */}
            <div className="flex items-center justify-between pt-2 border-t border-slate-100 mt-1">
              {/* Left action: Attach PDF or toggle note */}
              <div className="flex items-center gap-2">
                {onAttachClick && (
                  <button
                    type="button"
                    onClick={onAttachClick}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
                    title="Upload or manage study PDFs"
                  >
                    <Paperclip className="w-4 h-4" />
                  </button>
                )}

                {/* Compare Button (when >= 2 docs exist) */}
                {onOpenComparison && documentCount >= 2 && (
                  <button
                    type="button"
                    onClick={onOpenComparison}
                    className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[11px] font-semibold text-indigo-800 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200/60 transition"
                    title="Compare two indexed documents side-by-side"
                  >
                    <Scale className="w-3 h-3 text-indigo-600" />
                    <span>Compare</span>
                  </button>
                )}

                {/* Cheat-Sheet Button */}
                {onOpenCheatSheet && documentCount > 0 && (
                  <button
                    type="button"
                    onClick={onOpenCheatSheet}
                    className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[11px] font-medium text-teal-700 bg-teal-50 hover:bg-teal-100 border border-teal-200/60 transition"
                    title="Generate 1-page Study Cheat-Sheet"
                  >
                    <FileSpreadsheet className="w-3 h-3 text-teal-600" />
                    <span>Cheat-Sheet</span>
                  </button>
                )}

                <span className="text-[11px] text-slate-400 hidden sm:inline">
                  {documentCount > 0 ? `${documentCount} active docs` : 'No docs attached yet'}
                </span>
              </div>

              {/* Right action: Character count & Circular Send Button */}
              <div className="flex items-center gap-2.5">
                <span className="text-[11px] text-slate-400 font-mono">
                  {inputQuestion.length}/1000
                </span>

                <button
                  type="submit"
                  disabled={querying || !inputQuestion.trim()}
                  className="w-8 h-8 rounded-full flex items-center justify-center bg-teal-600 hover:bg-teal-700 text-white transition-all shadow-2xs disabled:bg-slate-200 disabled:text-slate-400 disabled:cursor-not-allowed"
                  aria-label="Send query"
                >
                  {querying ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <ArrowUp className="w-4 h-4 stroke-[2.5]" />
                  )}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
