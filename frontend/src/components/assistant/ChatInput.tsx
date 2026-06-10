import { useState, type RefObject } from 'react';
import { Send, Loader2 } from 'lucide-react';

interface ChatInputProps {
  disabled: boolean;
  busy: boolean;
  onSend: (text: string) => void;
  inputRef: RefObject<HTMLTextAreaElement | null>;
}

export default function ChatInput({ disabled, busy, onSend, inputRef }: ChatInputProps) {
  const [text, setText] = useState('');

  const submit = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText('');
  };

  return (
    <div className="flex items-end gap-2 rounded-2xl bg-white/10 border border-white/15 p-2 backdrop-blur-sm">
      <textarea
        ref={inputRef}
        value={text}
        onChange={e => setText(e.target.value)}
        onKeyDown={e => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
        rows={2}
        placeholder={
          busy
            ? 'The assistant is working — you can type your next message…'
            : 'Describe your scaling challenge, or refine the current report…'
        }
        className="flex-1 resize-none bg-transparent text-sm text-white placeholder-white/40 focus:outline-none px-2 py-1.5"
        aria-label="Challenge message"
      />
      <button
        onClick={submit}
        disabled={disabled || !text.trim()}
        className="shrink-0 rounded-xl bg-cgiar-accent text-cgiar-dark p-2.5 hover:bg-green-400 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        aria-label="Send message"
      >
        {busy ? (
          <Loader2 size={18} className="animate-spin" aria-hidden="true" />
        ) : (
          <Send size={18} aria-hidden="true" />
        )}
      </button>
    </div>
  );
}
