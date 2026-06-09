import { useState, useEffect } from 'react';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';
import '../../theme/echarts-cgiar';
import { fetchEngagementFunnel } from '../../services/analytics';
import type { EngagementFunnelData } from '../../services/analytics';

interface EngagementFunnelProps {
  days: number;
}

const FUNNEL_COLORS = ['#1B3B2F', '#2D5A3D', '#4CAF50', '#81C784', '#C8E6C9'];

export default function EngagementFunnel({ days }: EngagementFunnelProps) {
  const [data, setData] = useState<EngagementFunnelData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    fetchEngagementFunnel(days)
      .then(result => { if (!cancelled) setData(result); })
      .catch(err => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [days]);

  if (loading) return <div className="animate-pulse bg-gray-100 rounded-lg h-64" />;
  if (error) return <div className="text-red-500 text-sm p-4">{error}</div>;
  if (!data || data.stages.length === 0) return null;

  // Sort descending by count for horizontal bars (widest at top)
  const sorted = [...data.stages].sort((a, b) => b.count - a.count);
  const stages = sorted.map(s => s.stage);
  const counts = sorted.map(s => s.count);

  // Calculate % of previous stage (in the original funnel order)
  const originalOrder = data.stages;
  const pctLabels: Record<string, string> = {};
  for (let i = 0; i < originalOrder.length; i++) {
    if (i === 0) {
      pctLabels[originalOrder[i].stage] = '100%';
    } else {
      const prev = originalOrder[i - 1].count;
      const pct = prev > 0 ? ((originalOrder[i].count / prev) * 100).toFixed(1) : '0';
      pctLabels[originalOrder[i].stage] = `${pct}%`;
    }
  }

  const option: EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const arr = params as unknown as Array<{ name: string; value: number }>;
        const item = Array.isArray(arr) ? arr[0] : (params as unknown as { name: string; value: number });
        const pctVal = pctLabels[item.name] || '';
        return `<strong>${item.name}</strong><br/>Count: ${item.value.toLocaleString()}<br/>Conv: ${pctVal}`;
      },
    },
    grid: {
      left: 120,
      right: 60,
      top: 10,
      bottom: 20,
    },
    xAxis: {
      type: 'value',
    },
    yAxis: {
      type: 'category',
      data: stages,
      inverse: true,
      axisLabel: { fontSize: 11 },
    },
    series: [
      {
        type: 'bar',
        data: counts.map((v, i) => ({
          value: v,
          itemStyle: { color: FUNNEL_COLORS[i % FUNNEL_COLORS.length] },
        })),
        barMaxWidth: 32,
        label: {
          show: true,
          position: 'right',
          fontSize: 11,
          formatter: (params) => {
            const p = params as unknown as { name: string; value: number };
            const pct = pctLabels[p.name] || '';
            return `${p.value.toLocaleString()} (${pct})`;
          },
        },
      },
    ],
  };

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h3 className="text-sm font-semibold text-cgiar-dark mb-3">Engagement Funnel</h3>
      <ReactECharts option={option} theme="cgiar" style={{ height: '300px' }} />
    </div>
  );
}
