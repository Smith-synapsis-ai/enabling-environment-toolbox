import { useState, useEffect } from 'react';
import { Star } from 'lucide-react';
import { rateTool, fetchRatings } from '../../services/api';
import type { RatingsResponse } from '../../types';

interface StarRatingProps {
  toolId: string;
  initialAverage?: number;
  initialCount?: number;
}

function getUserId(): string {
  let userId = localStorage.getItem('ee-user-id');
  if (!userId) {
    userId = crypto.randomUUID();
    localStorage.setItem('ee-user-id', userId);
  }
  return userId;
}

export default function StarRating({ toolId, initialAverage = 0, initialCount = 0 }: StarRatingProps) {
  const [hoveredStar, setHoveredStar] = useState(0);
  const [average, setAverage] = useState(initialAverage);
  const [count, setCount] = useState(initialCount);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    setAverage(initialAverage);
    setCount(initialCount);
    setSubmitted(false);
  }, [toolId, initialAverage, initialCount]);

  const handleRate = async (rating: number) => {
    if (submitting) return;
    setSubmitting(true);

    try {
      await rateTool(toolId, {
        rating,
        user_id: getUserId(),
      });

      const ratings: RatingsResponse = await fetchRatings(toolId);
      setAverage(ratings.average);
      setCount(ratings.count);
      setSubmitted(true);
    } catch {
      // Silently fail rating submission
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex items-center gap-3">
      <div className="flex gap-0.5" role="group" aria-label="Star rating"  >
        {[1, 2, 3, 4, 5].map(star => {
          const filled = hoveredStar > 0 ? star <= hoveredStar : star <= Math.round(average);
          return (
            <button
              key={star}
              onClick={() => handleRate(star)}
              onMouseEnter={() => setHoveredStar(star)}
              onMouseLeave={() => setHoveredStar(0)}
              disabled={submitting}
              className="p-0.5 transition-transform hover:scale-110 disabled:cursor-not-allowed"
              aria-label={`Rate ${star} stars`}
            >
              <Star
                size={20}
                className={`transition-colors ${
                  filled
                    ? 'fill-yellow-400 text-yellow-400'
                    : 'fill-none text-gray-300'
                }`}
              />
            </button>
          );
        })}
      </div>
      <span className="text-sm text-gray-500">
        {average > 0 ? average.toFixed(1) : '0.0'} ({count} {count === 1 ? 'rating' : 'ratings'})
      </span>
      {submitted && (
        <span className="text-xs text-cgiar-accent font-medium animate-fade-in">
          Thank you!
        </span>
      )}
    </div>
  );
}
