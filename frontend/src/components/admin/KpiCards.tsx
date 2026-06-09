import { useState, useEffect } from 'react';
import { Users, UserCheck, Search, Eye, Star, Mail } from 'lucide-react';
import { fetchOverview } from '../../services/analytics';
import type { OverviewData } from '../../services/analytics';

interface KpiCardsProps {
  days: number;
}

const CARDS = [
  { key: 'total_users' as const, label: 'Users', icon: Users },
  { key: 'active_users' as const, label: 'Active Users', icon: UserCheck },
  { key: 'total_searches' as const, label: 'Searches', icon: Search },
  { key: 'total_views' as const, label: 'Tool Views', icon: Eye },
  { key: 'total_ratings' as const, label: 'Ratings', icon: Star },
  { key: 'total_emails' as const, label: 'Emails', icon: Mail },
];

function formatNumber(n: number): string {
  return n.toLocaleString();
}

export default function KpiCards({ days }: KpiCardsProps) {
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

  if (loading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {CARDS.map(c => (
          <div key={c.key} className="animate-pulse bg-gray-100 rounded-lg h-24" />
        ))}
      </div>
    );
  }

  if (error) return <div className="text-red-500 text-sm p-4">{error}</div>;
  if (!data) return null;

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      {CARDS.map(card => {
        const Icon = card.icon;
        const value = data[card.key];
        return (
          <div
            key={card.key}
            className="bg-white rounded-lg shadow p-4 border-l-4 border-cgiar-accent flex flex-col gap-2"
          >
            <div className="flex items-center gap-2 text-cgiar-green">
              <Icon size={18} strokeWidth={2} />
              <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                {card.label}
              </span>
            </div>
            <span className="text-2xl font-bold text-cgiar-dark">
              {formatNumber(value)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
