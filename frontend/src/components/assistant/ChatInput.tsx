import { useState, useRef, useEffect, type RefObject } from 'react';
import { Send, Loader2, Paperclip, Mic, MicOff } from 'lucide-react';

interface ChatInputProps {
  disabled: boolean;
  busy: boolean;
  onSend: (text: string) => void;
  inputRef: RefObject<HTMLTextAreaElement | null>;
  /** Optional file-attachment callback.  When provided, a paperclip button is
   *  shown.  The parent decides what to do with the FileList (e.g. prepend a
   *  filename notice to the next message, or upload to a server-side endpoint). */
  onAttach?: (files: FileList) => void;
}

// ---------------------------------------------------------------------------
// Browser Speech Recognition shim
// ---------------------------------------------------------------------------
// The Web Speech API (SpeechRecognition / webkitSpeechRecognition) is
// experimental and not in TypeScript's DOM lib for all TS versions.  We
// access it entirely through (window as any) so the code compiles cleanly
// regardless of the TS version used in CI.  `any` is intentional here —
// adding @types/dom-speech-recognition as a dep would be disproportionate
// for a progressive-enhancement feature that degrades gracefully when absent.
// ---------------------------------------------------------------------------
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type SpeechRecognitionCtor = new () => any;

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const SpeechRecognitionAPI: SpeechRecognitionCtor | null =
  typeof window !== 'undefined'
    ? // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ((window as any).SpeechRecognition ??
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (window as any).webkitSpeechRecognition ??
        null)
    : null;

export default function ChatInput({
  disabled,
  busy,
  onSend,
  inputRef,
  onAttach,
}: ChatInputProps) {
  const [text, setText] = useState('');
  const [listening, setListening] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Stop any live recognition session when the component is unmounted.
  useEffect(() => {
    return () => {
      recognitionRef.current?.abort();
    };
  }, []);

  // ── Send ──────────────────────────────────────────────────────────────────

  const submit = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText('');
  };

  // ── Voice-to-text ─────────────────────────────────────────────────────────

  const toggleMic = () => {
    if (!SpeechRecognitionAPI) return;

    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
      return;
    }

    const recognition = new SpeechRecognitionAPI();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.continuous = false;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      // Append the transcript to whatever is already in the textarea,
      // separated by a space if there is existing text.
      setText(prev => {
        const sep = prev.trimEnd() ? ' ' : '';
        return prev.trimEnd() + sep + transcript;
      });
    };

    recognition.onend = () => setListening(false);
    // Treat any recognition error (including user denying mic) as a stop.
    recognition.onerror = () => setListening(false);

    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  };

  // ── File attachment ───────────────────────────────────────────────────────

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onAttach?.(e.target.files);
    }
    // Reset value so the same file can be selected again in a subsequent pick.
    e.target.value = '';
  };

  const hasSpeech = !!SpeechRecognitionAPI;
  const hasAttach = !!onAttach;

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="flex items-end gap-2 rounded-2xl bg-white/10 border border-white/15 p-2 backdrop-blur-sm">
      {/* Hidden native file input — triggered programmatically by the paperclip
          button so we can style the trigger without fighting browser defaults. */}
      {hasAttach && (
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={handleFileChange}
          aria-hidden="true"
          tabIndex={-1}
        />
      )}

      {/* Main textarea */}
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

      {/* Paperclip — file attachment (only rendered when onAttach is provided) */}
      {hasAttach && (
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled}
          className="shrink-0 rounded-xl text-white/60 p-2 hover:text-white hover:bg-white/10 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          aria-label="Attach file"
          title="Attach file"
        >
          <Paperclip size={18} aria-hidden="true" />
        </button>
      )}

      {/* Microphone — voice-to-text (only rendered when SpeechRecognition is available) */}
      {hasSpeech && (
        <button
          type="button"
          onClick={toggleMic}
          disabled={disabled}
          className={[
            'shrink-0 rounded-xl p-2 transition-colors',
            'disabled:opacity-40 disabled:cursor-not-allowed',
            listening
              ? 'text-red-400 bg-red-400/10 hover:bg-red-400/20 animate-pulse'
              : 'text-white/60 hover:text-white hover:bg-white/10',
          ].join(' ')}
          aria-label={listening ? 'Stop recording' : 'Record voice input'}
          title={listening ? 'Stop recording' : 'Speak your challenge'}
        >
          {listening ? (
            <MicOff size={18} aria-hidden="true" />
          ) : (
            <Mic size={18} aria-hidden="true" />
          )}
        </button>
      )}

      {/* Send */}
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
