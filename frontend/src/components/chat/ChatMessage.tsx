import { User, Bot } from 'lucide-react';
import type { ChatMessage as ChatMessageType } from '../../types';

interface ChatMessageProps {
  message: ChatMessageType;
  onAction?: (response: string) => void; // Callback when user clicks an interactive action
}

export default function ChatMessage({ message, onAction }: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <div
      className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
      role="group"
      aria-label={isUser ? 'Your message' : 'Assistant message'}
    >
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser ? 'bg-cgiar-accent/30' : 'bg-white/10'
        }`}
        role="img"
        aria-label={isUser ? 'User' : 'Assistant'}
      >
        {isUser ? (
          <User size={16} className="text-cgiar-accent" aria-hidden="true" />
        ) : (
          <Bot size={16} className="text-white/70" aria-hidden="true" />
        )}
      </div>

      {/* Message bubble */}
      <div className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
        isUser
          ? 'bg-cgiar-accent/20 text-white rounded-br-md'
          : 'bg-white/10 text-white/90 rounded-bl-md'
      }`}>
        {message.content.split('\n').map((line, i) => (
          <p key={i} className={i > 0 ? 'mt-2' : ''}>
            {line}
          </p>
        ))}

        {/* Interactive actions (scaffolding for future backend support) */}
        {message.actions?.map((action, i) => (
          <div key={i} className="mt-3">
            {action.type === 'quick_reply' && (
              <div className="flex flex-wrap gap-2">
                {action.options.map((opt) => (
                  <button
                    key={opt}
                    onClick={() => onAction?.(opt)}
                    className="px-3 py-1.5 rounded-full border border-white/30 text-white/90 text-xs font-medium hover:bg-white/10 transition-all"
                    style={{ borderColor: 'rgba(214,133,255,0.4)' }}
                  >
                    {opt}
                  </button>
                ))}
              </div>
            )}
            {action.type === 'single_select' && (
              <div className="mt-2 space-y-1.5">
                <span className="text-xs text-white/60 font-medium">{action.label}</span>
                {action.options.map((opt) => (
                  <button
                    key={opt}
                    onClick={() => onAction?.(opt)}
                    className="flex items-center gap-2 w-full text-left px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-white/90 text-sm transition-colors"
                  >
                    <span className="w-4 h-4 rounded-full border-2 border-white/40 flex-shrink-0" aria-hidden="true" />
                    {opt}
                  </button>
                ))}
              </div>
            )}
            {action.type === 'multi_select' && (
              <div className="mt-2 space-y-1.5">
                <span className="text-xs text-white/60 font-medium">{action.label}</span>
                {action.options.map((opt) => (
                  <button
                    key={opt}
                    onClick={() => onAction?.(opt)}
                    className="flex items-center gap-2 w-full text-left px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-white/90 text-sm transition-colors"
                  >
                    <span className="w-4 h-4 rounded border-2 border-white/40 flex-shrink-0" aria-hidden="true" />
                    {opt}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
