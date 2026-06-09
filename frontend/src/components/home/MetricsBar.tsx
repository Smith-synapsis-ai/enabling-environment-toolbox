import { useMetrics } from '../../hooks/useMetrics';
import { Wrench, Layers, Globe } from 'lucide-react';

export default function MetricsBar() {
  const { metrics, loading, error } = useMetrics();

  // Loading state
  if (loading) {
    return (
      <div className="bg-cgiar-dark/80 backdrop-blur-sm border-t border-white/10">
        <div className="max-w-4xl mx-auto px-4 py-4 flex justify-center">
          <div className="text-white/70 text-sm">Loading metrics...</div>
        </div>
      </div>
    );
  }

  // Error state — show graceful fallback instead of infinite loading
  if (error || !metrics) {
    return (
      <div className="bg-cgiar-dark/80 backdrop-blur-sm border-t border-white/10">
        <div className="max-w-4xl mx-auto px-4 py-4 flex justify-center gap-12 sm:gap-16">
          {[
            { icon: Wrench, value: '90+', label: 'tools' },
            { icon: Layers, value: '20+', label: 'frameworks' },
            { icon: Globe, value: '30+', label: 'countries' },
          ].map(stat => (
            <div key={stat.label} className="flex items-center gap-2.5 text-white">
              <stat.icon size={18} className="text-cgiar-accent" aria-hidden="true" />
              <span className="text-lg font-bold">{stat.value}</span>
              <span className="text-white/70 text-sm">{stat.label}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  const stats = [
    { icon: Wrench, value: metrics.total_tools, label: 'tools' },
    { icon: Layers, value: metrics.total_frameworks, label: 'frameworks' },
    { icon: Globe, value: metrics.geography_coverage, label: 'countries' },
  ];

  return (
    <div className="bg-cgiar-dark/80 backdrop-blur-sm border-t border-white/10">
      <div className="max-w-4xl mx-auto px-4 py-4 flex justify-center gap-12 sm:gap-16">
        {stats.map(stat => (
          <div key={stat.label} className="flex items-center gap-2.5 text-white">
            <stat.icon size={18} className="text-cgiar-accent" aria-hidden="true" />
            <span className="text-lg font-bold">{stat.value}</span>
            <span className="text-white/70 text-sm">{stat.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
