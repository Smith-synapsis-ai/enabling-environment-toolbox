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
        className="flex-1 px-4 py-3 bg-white/10 border border-white/20 rounded-full text-white text-sm placeholder-white/50 focus:outline-none focus:border-s4i-purple/60 focus:ring-2 focus:ring-s4i-purple/30 focus:bg-white/[0.12] transition-all disabled:opacity-50"
      />
      <button
        type="submit"
        disabled={!value.trim() || disabled}
        className="w-10 h-10 rounded-full flex items-center justify-center text-white transition-all flex-shrink-0 disabled:bg-white/10 disabled:text-white/30 hover:shadow-lg hover:shadow-s4i-purple/20 active:scale-95"
        style={{
          background: !value.trim() || disabled
            ? undefined
            : 'linear-gradient(135deg, #2D5A3D, #7904B4)',
        }}
        aria-label="Send message"
      >
        <SendHorizonal size={16} aria-hidden="true" />
      </button>
    </form>
  );
}
