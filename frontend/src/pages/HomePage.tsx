import { useState, useCallback } from 'react';
import HeroSection from '../components/home/HeroSection';
import ChatInterface from '../components/chat/ChatInterface';
import BackgroundCarousel from '../components/home/BackgroundCarousel';
import ToolDetailPanel from '../components/tool/ToolDetailPanel';
import { useChat } from '../hooks/useChat';
import type { ToolSearchResult } from '../types';

interface HomePageProps {
  onToolViewed?: () => void;
  onSearchPerformed?: () => void;
}

export default function HomePage({ onToolViewed, onSearchPerformed }: HomePageProps) {
  const {
    messages,
    isLoading,
    error,
    isActive,
    recommendedTools,
    sendMessage,
    resetChat,
  } = useChat();

  const [selectedToolId, setSelectedToolId] = useState<string | null>(null);

  const handleSendMessage = useCallback((msg: string) => {
    onSearchPerformed?.();
    sendMessage(msg);
  }, [sendMessage, onSearchPerformed]);

  const handleToolSelect = useCallback((tool: ToolSearchResult) => {
    setSelectedToolId(tool.id);
  }, []);

  const handleCloseDetail = useCallback(() => {
    setSelectedToolId(null);
  }, []);

  return (
    <div className="relative">
      {/* Persistent blurred background visible behind ChatInterface */}
      {isActive && (
        <div className="fixed inset-0 z-0">
          <BackgroundCarousel isBlurred={true} />
        </div>
      )}

      {!isActive ? (
        <HeroSection onSendMessage={handleSendMessage} />
      ) : (
        <div className="relative z-10">
          <ChatInterface
            messages={messages}
            isLoading={isLoading}
            error={error}
            recommendedTools={recommendedTools}
            onSend={handleSendMessage}
            onReset={resetChat}
            onToolSelect={handleToolSelect}
          />
        </div>
      )}

      {/* Tool Detail Panel */}
      {selectedToolId && (
        <ToolDetailPanel
          toolId={selectedToolId}
          onClose={handleCloseDetail}
          onToolViewed={onToolViewed}
        />
      )}
    </div>
  );
}
