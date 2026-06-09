import { useState, useEffect, useCallback } from 'react';
import { X } from 'lucide-react';
import { getSessionId } from '../../services/api';

interface PulseSurveyProps {
  hasSearched: boolean;
  hasViewedTool: boolean;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

async function submitPulseSurvey(questionKey: string, score: number): Promise<void> {
  const sessionId = getSessionId();
  const response = await fetch(`${API_BASE}/api/pulse-survey`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, question_key: questionKey, score }),
  });
  if (!response.ok) throw new Error('Survey submission failed');
}

const QUESTIONS = [
  { key: 'trust_recommendations', label: 'Did you trust these recommendations?' },
  { key: 'helped_decide', label: 'Did this help you decide?' },
] as const;

export default function PulseSurvey({ hasSearched, hasViewedTool }: PulseSurveyProps) {
  const [visible, setVisible] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [submitted, setSubmitted] = useState<Record<string, boolean>>({});
  const [fadeOut, setFadeOut] = useState(false);

  // Determine whether to show
  useEffect(() => {
    if (!hasSearched || !hasViewedTool) return;
    if (sessionStorage.getItem('ee-pulse-survey-shown')) return;

    // Small delay so it doesn't appear instantly
    const timer = setTimeout(() => {
      if (!sessionStorage.getItem('ee-pulse-survey-shown')) {
        setVisible(true);
        sessionStorage.setItem('ee-pulse-survey-shown', 'true');
      }
    }, 1500);

    return () => clearTimeout(timer);
  }, [hasSearched, hasViewedTool]);

  const handleDismiss = useCallback(() => {
    setFadeOut(true);
    setTimeout(() => {
      setDismissed(true);
    }, 400);
  }, []);

  const handleScore = useCallback(async (questionKey: string, score: number) => {
    setAnswers(prev => ({ ...prev, [questionKey]: score }));
    try {
      await submitPulseSurvey(questionKey, score);
      setSubmitted(prev => ({ ...prev, [questionKey]: true }));
    } catch {
      // Silently fail — non-critical analytics
    }
  }, []);

  // Auto-dismiss after both are answered
  useEffect(() => {
    const allAnswered = QUESTIONS.every(q => submitted[q.key]);
    if (allAnswered) {
      const timer = setTimeout(() => {
        handleDismiss();
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [submitted, handleDismiss]);

  if (!visible || dismissed) return null;

  return (
    <div
      className={`fixed bottom-0 left-0 right-0 z-[90] transition-all duration-500 ${
        fadeOut ? 'translate-y-full opacity-0' : 'translate-y-0 opacity-100'
      }`}
      style={{ animation: fadeOut ? undefined : 'slideUp 0.5s ease-out' }}
      role="complementary"
      aria-label="Quick feedback survey"
    >
      <style>{`
        @keyframes slideUp {
          from { transform: translateY(100%); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }
      `}</style>

      <div className="bg-cgiar-dark/95 backdrop-blur-md border-t border-white/10 px-4 sm:px-6 py-4">
        <div className="max-w-4xl mx-auto">
          {/* Dismiss button */}
          <button
            onClick={handleDismiss}
            className="absolute top-3 right-4 text-white/70 hover:text-white transition-colors"
            aria-label="Dismiss survey"
          >
            <X size={18} aria-hidden="true" />
          </button>

          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 sm:gap-8">
            {QUESTIONS.map(question => (
              <div key={question.key} className="flex-1">
                {submitted[question.key] ? (
                  <p className="text-white/80 text-sm">Thank you for your feedback!</p>
                ) : (
                  <div>
                    <p className="text-white text-sm font-medium mb-2">
                      {question.label}
                    </p>
                    <div className="flex gap-1.5" role="radiogroup" aria-label={question.label}>
                      {[1, 2, 3, 4, 5].map(score => (
                        <button
                          key={score}
                          onClick={() => handleScore(question.key, score)}
                          className={`w-9 h-9 rounded-md text-sm font-medium transition-all ${
                            answers[question.key] === score
                              ? 'bg-cgiar-accent text-white scale-110'
                              : 'bg-white/10 text-white/80 hover:bg-white/20 hover:text-white'
                          }`}
                          aria-label={`${score} out of 5`}
                          role="radio"
                          aria-checked={answers[question.key] === score}
                        >
                          {score}
                        </button>
                      ))}
                    </div>
                    <p className="text-white/70 text-xs mt-1">
                      1 = Not at all &middot; 5 = Absolutely
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
