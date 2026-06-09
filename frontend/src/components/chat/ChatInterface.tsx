import { useEffect, useRef, useState } from 'react';
import { RotateCcw } from 'lucide-react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import ToolCarousel from './ToolCarousel';
import LoadingSpinner from '../common/LoadingSpinner';
import type { ChatMessage as ChatMessageType, ToolSearchResult, ToolRecommendation } from '../../types';
import { fetchTool } from '../../services/api';

interface ChatInterfaceProps {
  messages: ChatMessageType[];
  isLoading: boolean;
  error: string | null;
  recommendedTools: ToolRecommendation[];
  onSend: (message: string) => void;
  onReset: () => void;
  onToolSelect: (tool: ToolSearchResult) => void;
}

export default function ChatInterface({
  messages,
  isLoading,
  error,
  recommendedTools,
  onSend,
  onReset,
  onToolSelect,
}: ChatInterfaceProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [resolvedTools, setResolvedTools] = useState<ToolSearchResult[]>([]);
  const [loadingTools, setLoadingTools] = useState(false);

  // Background toggle state — respects the same localStorage + custom event as BackgroundCarousel
  const [bgEnabled, setBgEnabled] = useState(() => {
    return localStorage.getItem('ee-bg-enabled') !== 'false';
  });

  useEffect(() => {
    const handleUpdate = () => {
      setBgEnabled(localStorage.getItem('ee-bg-enabled') !== 'false');
    };
    window.addEventListener('storage', handleUpdate);
    window.addEventListener('ee-bg-toggle', handleUpdate);
    return () => {
      window.removeEventListener('storage', handleUpdate);
      window.removeEventListener('ee-bg-toggle', handleUpdate);
    };
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // When recommendedTools come in, fetch full details for each
  useEffect(() => {
    if (recommendedTools.length === 0) return;

    let cancelled = false;
    setLoadingTools(true);

    async function loadTools() {
      try {
        const tools = await Promise.all(
          recommendedTools.map(async (rec) => {
            const tool = await fetchTool(rec.id);
            return { ...tool, similarity: rec.similarity } as ToolSearchResult;
          })
        );
        if (!cancelled) {
          setResolvedTools(tools);
        }
      } catch {
        // If individual tool fetches fail, show what we can
      } finally {
        if (!cancelled) {
          setLoadingTools(false);
        }
      }
    }

    loadTools();
    return () => { cancelled = true; };
  }, [recommendedTools]);

  return (
    <div className="relative min-h-screen flex flex-col lg:flex-row">
      {/* Background — respects the bg toggle */}
      <div className="absolute inset-0">
        {bgEnabled ? (
          <>
            <img
              src="/hero-bg.png"
              alt=""
              className="w-full h-full object-cover"
            />
            <div
              className="absolute inset-0"
              style={{ backgroundColor: 'rgba(3, 53, 41, 0.85)' }}
            />
          </>
        ) : (
          <div className="absolute inset-0 bg-cgiar-dark" />
        )}
      </div>

      {/* Chat side — 38% width with subtle left accent */}
      <div className="relative z-10 lg:w-[38%] lg:min-w-[380px] flex flex-col pt-20 pb-4 border-r border-white/5">
        {/* Purple accent line at top of chat panel */}
        <div className="absolute top-16 left-0 right-0 h-[2px] bg-gradient-to-r from-s4i-purple/60 via-s4i-purple/30 to-transparent" />

        {/* Mini header */}
        <div className="px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img
              src="/branding/individual-block.svg"
              alt=""
              className="h-6 opacity-80"
              aria-hidden="true"
            />
            <div>
              <h2 className="text-lg font-semibold text-white tracking-tight">
                Enabling Environment
              </h2>
              <span className="text-white/60 text-xs font-light">
                The tools, the cases, the science
              </span>
            </div>
          </div>
          <button
            onClick={onReset}
            className="flex items-center gap-1.5 text-white/70 hover:text-white text-sm transition-colors px-2.5 py-1.5 rounded-md hover:bg-white/5"
            aria-label="Start new conversation"
            title="New conversation"
          >
            <RotateCcw size={14} aria-hidden="true" />
            <span className="hidden sm:inline">New chat</span>
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {messages.map(msg => (
            <ChatMessage key={msg.id} message={msg} />
          ))}

          {isLoading && (
            <div role="status" aria-label="Assistant is typing" className="flex gap-3">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-white/10 flex items-center justify-center">
                <LoadingSpinner size={16} />
              </div>
              <div className="bg-white/10 rounded-2xl rounded-bl-md px-4 py-3">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-white/60 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 bg-white/60 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 bg-white/60 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}

          {error && (
            <div role="alert" className="bg-red-500/20 border border-red-500/30 rounded-lg px-4 py-3 text-red-200 text-sm">
              {error}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <ChatInput onSend={onSend} disabled={isLoading} />
      </div>

      {/* Tools side — takes remaining space */}
      {(resolvedTools.length > 0 || loadingTools) && (
        <div className="relative z-10 lg:flex-1 flex flex-col justify-center p-6 pt-20 lg:pt-6">
          {loadingTools ? (
            <div className="flex items-center justify-center h-64">
              <LoadingSpinner size={32} message="Loading recommended tools..." />
            </div>
          ) : (
            <ToolCarousel tools={resolvedTools} onToolClick={onToolSelect} />
          )}
        </div>
      )}
    </div>
  );
}
