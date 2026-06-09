import { useState, useCallback } from 'react';
import type { ChatMessage, ToolRecommendation } from '../types';
import { sendChatMessage } from '../services/api';

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isActive, setIsActive] = useState(false);
  const [recommendedTools, setRecommendedTools] = useState<ToolRecommendation[]>([]);
  const [conversationComplete, setConversationComplete] = useState(false);

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return;

    setIsActive(true);
    setError(null);

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: content.trim(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await sendChatMessage({
        message: content.trim(),
        conversation_id: conversationId,
      });

      setConversationId(response.conversation_id);

      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: response.message,
        tools_recommended: response.tools_recommended,
      };

      setMessages(prev => [...prev, assistantMessage]);

      if (response.tools_recommended && response.tools_recommended.length > 0) {
        setRecommendedTools(response.tools_recommended);
      }

      setConversationComplete(response.conversation_complete);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message');
    } finally {
      setIsLoading(false);
    }
  }, [conversationId, isLoading]);

  const resetChat = useCallback(() => {
    setMessages([]);
    setConversationId(undefined);
    setIsActive(false);
    setRecommendedTools([]);
    setConversationComplete(false);
    setError(null);
  }, []);

  return {
    messages,
    isLoading,
    error,
    isActive,
    recommendedTools,
    conversationComplete,
    sendMessage,
    resetChat,
  };
}
