import { useEffect, useState } from 'react';
import { X } from 'lucide-react';

interface Props {
  sessionId: string;
  visible: boolean;
  onDismiss: () => void;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export function AssistantPulseSurveyBanner({ sessionId, visible, onDismiss }: Props) {
  const [selectedScore, setSelectedScore] = useState<number | null>(null);
  const [comment, setComment] = useState('');
  const [thanks, setThanks] = useState(false);

  const guardKey = `ee-assistant-pulse-shown-${sessionId}`;

  // If this session already saw the survey, dismiss immediately on mount.
  useEffect(() => {
    if (sessionStorage.getItem(guardKey)) {
      onDismiss();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!visible) return null;

  const handleSubmit = () => {
    if (selectedScore === null) return;
    sessionStorage.setItem(guardKey, 'true');

    fetch(`${API_BASE}/api/events`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        event_name: 'pulse_survey',
        session_id: sessionId,
        payload: { score: selectedScore, comment: comment.trim() || undefined },
      }),
      keepalive: true,
    }).catch(() => {});

    setThanks(true);
    setTimeout(() => {
      onDismiss();
    }, 2000);
  };

  const handleDismiss = () => {
    sessionStorage.setItem(guardKey, 'true');
    onDismiss();
  };

  return (
    <div
      className="fixed bottom-0 left-0 right-0 z-50"
      style={{ animation: 'slideUp 0.5s ease-out' }}
      role="complementary"
      aria-label="Session feedback survey"
    >
      <style>{`
        @keyframes slideUp {
          from { transform: translateY(100%); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }
      `}</style>

      <div className="bg-cgiar-dark/95 backdrop-blur-md border-t border-white/10 px-4 sm:px-6 py-4">
        <div className="max-w-4xl mx-auto relative">
          {/* Dismiss button */}
          <button
            onClick={handleDismiss}
            className="absolute top-0 right-0 text-white/50 hover:text-white transition-colors"
            aria-label="Dismiss survey"
          >
            <X size={18} />
          </button>

          {thanks ? (
            <p className="text-white/80 text-sm py-2">Thank you for your feedback!</p>
          ) : (
            <div className="flex flex-col gap-3">
              <p className="text-white text-sm font-medium pr-8">
                How useful was this session?
              </p>

              <div className="flex gap-1.5" role="radiogroup" aria-label="How useful was this session?">
                {[1, 2, 3, 4, 5].map(score => (
                  <button
                    key={score}
                    onClick={() => setSelectedScore(score)}
                    className={`w-9 h-9 rounded-md text-sm font-medium transition-all ${
                      selectedScore === score
                        ? 'bg-cgiar-accent text-white scale-110'
                        : 'bg-white/10 text-white/80 hover:bg-white/20 hover:text-white'
                    }`}
                    aria-label={`${score} out of 5`}
                    role="radio"
                    aria-checked={selectedScore === score}
                  >
                    {score}
                  </button>
                ))}
              </div>

              <textarea
                value={comment}
                onChange={e => setComment(e.target.value)}
                placeholder="Any comments? (optional)"
                rows={2}
                className="w-full rounded-md bg-white/10 border border-white/15 text-white text-sm placeholder-white/40 px-3 py-2 focus:outline-none focus:ring-1 focus:ring-cgiar-accent resize-none"
              />

              <div className="flex justify-end">
                <button
                  onClick={handleSubmit}
                  disabled={selectedScore === null}
                  className={`rounded-lg text-sm font-medium px-4 py-1.5 transition-colors ${
                    selectedScore === null
                      ? 'bg-white/10 text-white/40 cursor-not-allowed'
                      : 'bg-cgiar-accent text-white hover:bg-cgiar-accent/90'
                  }`}
                >
                  Submit
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default AssistantPulseSurveyBanner;
