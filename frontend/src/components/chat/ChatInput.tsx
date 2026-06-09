import { useState } from 'react';
import { SendHorizonal } from 'lucide-react';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export default function ChatInput({ onSend, disabled = false, placeholder }: ChatInputProps) {
  const [value, setValue] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (value.trim() && !disabled) {
      onSend(value.trim());
      setValue('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2 p-4 border-t border-white/10">
      <label htmlFor="chat-input" className="sr-only">Chat message</label>
      <input
        id="chat-input"
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder={placeholder || 'Type your response...'}
        className="flex-1 px-4 py-3 bg-white/10 border border-white/20 rounded-full text-white text-sm placeholder-white/60 focus:outline-none focus:border-cgiar-accent focus:ring-1 focus:ring-cgiar-accent transition-colors disabled:opacity-50"
      />
      <button
        type="submit"
        disabled={!value.trim() || disabled}
        className="w-10 h-10 bg-cgiar-accent hover:bg-cgiar-green disabled:bg-white/10 disabled:text-white/30 rounded-full flex items-center justify-center text-white transition-colors flex-shrink-0"
        aria-label="Send message"
      >
        <SendHorizonal size={16} />
      </button>
    </form>
  );
}
