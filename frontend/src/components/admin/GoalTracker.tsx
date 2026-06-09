import { useState, useEffect } from 'react';
import { Target } from 'lucide-react';
import { fetchOverview } from '../../services/analytics';
import type { OverviewData } from '../../services/analytics';

interface GoalTrackerProps {
  days: number;
}

const USER_GOAL = 5000;

export default function GoalTracker({ days }: GoalTrackerProps) {
  const [data, setData] = useState<OverviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    fetchOverview(days)
      .then(result => { if (!cancelled) setData(result); })
      .catch(err => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [days]);

  if (loading) return <div className="animate-pulse bg-gray-100 rounded-lg h-32" />;
  if (error) return <div className="text-red-500 text-sm p-4">{error}</div>;
  if (!data) return null;

  const current = data.total_users;
  const pct = Math.min((current / USER_GOAL) * 100, 100);
  const pctDisplay = pct.toFixed(1);

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-center gap-2 mb-3">
        <Target size={18} className="text-cgiar-accent" />
        <h3 className="text-sm font-semibold text-cgiar-dark">
          Goal: {USER_GOAL.toLocaleString()} Users
        </h3>
      </div>

      <div className="flex items-end gap-3 mb-3">
        <span className="text-3xl font-bold text-cgiar-dark">
          {current.toLocaleString()}
        </span>
        <span className="text-sm text-gray-500 mb-1">
          / {USER_GOAL.toLocaleString()} ({pctDisplay}%)
        </span>
      </div>

      <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{
            width: `${pct}%`,
            background: 'linear-gradient(90deg, #1B3B2F 0%, #4CAF50 100%)',
          }}
        />
      </div>

      <p className="text-xs text-gray-400 mt-2">
        {(USER_GOAL - current) > 0
          ? `${(USER_GOAL - current).toLocaleString()} users remaining`
          : 'Goal reached!'}
      </p>
    </div>
  );
}
