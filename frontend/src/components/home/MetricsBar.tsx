import { useMetrics } from '../../hooks/useMetrics';
import { Wrench, Layers, Globe } from 'lucide-react';

export default function MetricsBar() {
  const { metrics, loading, error } = useMetrics();

  const renderStats = (stats: { icon: typeof Wrench; value: string | number; label: string }[]) => (
    <div className="glass rounded-xl" role="group" aria-label="Platform statistics">
      <div className="max-w-4xl mx-auto px-6 py-4 flex justify-center gap-10 sm:gap-16">
        {stats.map(stat => (
          <div key={stat.label} className="flex items-center gap-2.5 group">
            <stat.icon
              size={18}
              className="text-s4i-purple-light group-hover:text-s4i-purple transition-colors"
              aria-hidden="true"
            />
            <span className="text-lg font-bold text-s4i-purple">{stat.value}</span>
            <span className="text-white/70 text-sm">{stat.label}</span>
          </div>
        ))}
      </div>
    </div>
  );

  // Loading state
  if (loading) {
    return (
      <div className="glass rounded-xl">
        <div className="max-w-4xl mx-auto px-4 py-4 flex justify-center">
          <div className="text-white/70 text-sm" role="status">Loading metrics...</div>
        </div>
      </div>
    );
  }

  // Error state — show graceful fallback
  if (error || !metrics) {
    return renderStats([
      { icon: Wrench, value: '90+', label: 'tools' },
      { icon: Layers, value: '20+', label: 'frameworks' },
      { icon: Globe, value: '30+', label: 'countries' },
    ]);
  }

  return renderStats([
    { icon: Wrench, value: metrics.total_tools, label: 'tools' },
    { icon: Layers, value: metrics.total_frameworks, label: 'frameworks' },
    { icon: Globe, value: metrics.geography_coverage, label: 'countries' },
  ]);
}
