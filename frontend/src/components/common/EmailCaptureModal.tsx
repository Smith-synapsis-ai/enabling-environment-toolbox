import { useState, useEffect, useCallback, useRef } from 'react';
import { X, Mail } from 'lucide-react';
import { captureEmail, getSessionId } from '../../services/api';

interface EmailCaptureModalProps {
  toolViewCount: number;
}

export default function EmailCaptureModal({ toolViewCount }: EmailCaptureModalProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [validationError, setValidationError] = useState('');
  const modalRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  const dismiss = useCallback(() => {
    setIsOpen(false);
    sessionStorage.setItem('email_captured', 'true');
  }, []);

  useEffect(() => {
    if (sessionStorage.getItem('email_captured')) return;

    const timer = setTimeout(() => {
      if (!sessionStorage.getItem('email_captured')) {
        setIsOpen(true);
      }
    }, 30000);

    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (sessionStorage.getItem('email_captured')) return;
    if (toolViewCount >= 2) {
      setIsOpen(true);
    }
  }, [toolViewCount]);

  // Focus trap + Escape key
  useEffect(() => {
    if (!isOpen) return;

    // Focus the close button when modal opens
    closeButtonRef.current?.focus();

    // Prevent body scroll
    document.body.style.overflow = 'hidden';

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        dismiss();
        return;
      }

      // Focus trap: cycle focus within modal
      if (e.key === 'Tab' && modalRef.current) {
        const focusable = modalRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (focusable.length === 0) return;

        const first = focusable[0];
        const last = focusable[focusable.length - 1];

        if (e.shiftKey) {
          if (document.activeElement === first) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [isOpen, dismiss]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError('');

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setValidationError('Please enter a valid email address');
      return;
    }

    setSubmitting(true);

    try {
      await captureEmail(email, getSessionId());
      setSubmitted(true);
      sessionStorage.setItem('email_captured', 'true');

      setTimeout(() => {
        setIsOpen(false);
      }, 2000);
    } catch {
      setValidationError('Something went wrong. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="email-modal-title"
      ref={modalRef}
    >
      {/* Backdrop click to dismiss */}
      <div className="absolute inset-0" onClick={dismiss} aria-hidden="true" />

      <div className="relative bg-cgiar-dark rounded-xl shadow-2xl max-w-md w-full mx-4 p-8 text-white animate-fade-in">
        <button
          ref={closeButtonRef}
          onClick={dismiss}
          className="absolute top-4 right-4 text-white/70 hover:text-white transition-colors"
          aria-label="Close email subscription dialog"
        >
          <X size={20} />
        </button>

        {submitted ? (
          <div className="text-center py-4">
            <div className="w-16 h-16 bg-cgiar-accent/20 rounded-full flex items-center justify-center mx-auto mb-4">
              <Mail size={28} className="text-cgiar-accent" aria-hidden="true" />
            </div>
            <h3 id="email-modal-title" className="text-xl font-semibold mb-2">Thank you!</h3>
            <p className="text-white/80">You'll receive updates on new tools and resources.</p>
          </div>
        ) : (
          <>
            <div className="w-16 h-16 bg-cgiar-accent/20 rounded-full flex items-center justify-center mx-auto mb-6">
              <Mail size={28} className="text-cgiar-accent" aria-hidden="true" />
            </div>
            <h3 id="email-modal-title" className="text-xl font-semibold text-center mb-2">
              Stay updated on new tools and resources
            </h3>
            <p className="text-white/80 text-center text-sm mb-6">
              Get notified when new enabling environment tools are added to the collection.
            </p>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="email-capture-input" className="sr-only">Email address</label>
                <input
                  id="email-capture-input"
                  type="email"
                  value={email}
                  onChange={(e) => { setEmail(e.target.value); setValidationError(''); }}
                  placeholder="your@email.com"
                  className="w-full px-4 py-3 rounded-lg bg-white/10 border border-white/20 text-white placeholder-white/60 focus:outline-none focus:border-cgiar-accent focus:ring-1 focus:ring-cgiar-accent transition-colors"
                  aria-describedby={validationError ? 'email-error' : undefined}
                  aria-invalid={validationError ? 'true' : undefined}
                />
                {validationError && (
                  <p id="email-error" className="text-red-400 text-xs mt-1" role="alert">{validationError}</p>
                )}
              </div>
              <button
                type="submit"
                disabled={submitting}
                className="w-full py-3 bg-cgiar-accent hover:bg-cgiar-accent/90 text-white font-semibold rounded-lg transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {submitting ? 'Subscribing...' : 'Subscribe'}
              </button>
            </form>
            <button
              onClick={dismiss}
              className="w-full mt-3 text-sm text-white/70 hover:text-white transition-colors"
            >
              No thanks
            </button>
          </>
        )}
      </div>
    </div>
  );
}
