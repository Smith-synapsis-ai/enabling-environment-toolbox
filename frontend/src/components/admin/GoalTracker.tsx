import { useState, useEffect } from 'react';
import { Target } from 'lucide-react';
import { fetchKpi } from '../../services/analytics';
import type { KpiData } from '../../services/analytics';

// G4 (decision 2): the goal is 5,000 de-duplicated ACCESS EVENTS — someone
// opening the app, one per browser session. This reads the REAL C4
// access_event count from the durable /api/events/kpi endpoint, NOT Postgres
// total_users / distinct sessions. The frontend already de-duplicates access
// events per browser session (App.tsx 'ee-access-tracked' guard).

export default function GoalTracker() {
  const [data, setData] = useState<KpiData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    fetchKpi()
      .then(result => { if (!cancelled) setData(result); })
      .catch(err => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  if (loading) return <div className="animate-pulse bg-gray-100 rounded-lg h-32" />;
  if (error) return <div className="text-red-500 text-sm p-4">{error}</div>;
  if (!data) return null;

  const current = data.kpi_access_events;
  const goal = data.kpi_target;
  const pct = Math.min((current / goal) * 100, 100);
  const pctDisplay = pct.toFixed(1);

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-center gap-2 mb-3">
        <Target size={18} className="text-cgiar-accent" />
        <h3 className="text-sm font-semibold text-cgiar-dark">
          Goal: {goal.toLocaleString()} Access Events
        </h3>
      </div>

      <div className="flex items-end gap-3 mb-3">
        <span className="text-3xl font-bold text-cgiar-dark">
          {current.toLocaleString()}
        </span>
        <span className="text-sm text-gray-500 mb-1">
          / {goal.toLocaleString()} ({pctDisplay}%)
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
        {(goal - current) > 0
          ? `${(goal - current).toLocaleString()} access events remaining · de-duplicated per browser session (C4/G4)`
          : 'Goal reached!'}
      </p>
    </div>
  );
}
