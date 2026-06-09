import { useState, useEffect } from 'react';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';
import '../../theme/echarts-cgiar';
import { fetchPathwayCompletion } from '../../services/analytics';
import type { PathwayCompletionData } from '../../services/analytics';

interface PathwayFunnelProps {
  days: number;
}

const STAGE_COLORS = ['#1B3B2F', '#2D5A3D', '#4CAF50'];

export default function PathwayFunnel({ days }: PathwayFunnelProps) {
  const [data, setData] = useState<PathwayCompletionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    fetchPathwayCompletion(days)
      .then(result => { if (!cancelled) setData(result); })
      .catch(err => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [days]);

  if (loading) return <div className="animate-pulse bg-gray-100 rounded-lg h-64" />;
  if (error) return <div className="text-red-500 text-sm p-4">{error}</div>;
  if (!data || data.stages.length === 0) return null;

  const stages = data.stages;
  const names = stages.map(s => s.stage);
  const counts = stages.map(s => s.count);

  // Calculate conversion between consecutive stages
  const conversionLabels: string[] = [];
  for (let i = 0; i < stages.length; i++) {
    if (i === 0) {
      conversionLabels.push(`${stages[i].count.toLocaleString()}`);
    } else {
      const prev = stages[i - 1].count;
      const pct = prev > 0 ? ((stages[i].count / prev) * 100).toFixed(1) : '0';
      conversionLabels.push(`${stages[i].count.toLocaleString()} (${pct}%)`);
    }
  }

  const option: EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const arr = params as unknown as Array<{ dataIndex: number; name: string; value: number }>;
        const item = Array.isArray(arr) ? arr[0] : (params as unknown as { dataIndex: number; name: string; value: number });
        const stage = stages[item.dataIndex];
        return `<strong>${item.name}</strong><br/>${stage.description}<br/>Count: ${item.value.toLocaleString()}`;
      },
    },
    grid: {
      left: 110,
      right: 80,
      top: 10,
      bottom: 20,
    },
    xAxis: {
      type: 'value',
    },
    yAxis: {
      type: 'category',
      data: names,
      inverse: true,
      axisLabel: { fontSize: 12, fontWeight: 500 },
    },
    series: [
      {
        type: 'bar',
        data: counts.map((v, i) => ({
          value: v,
          itemStyle: { color: STAGE_COLORS[i % STAGE_COLORS.length] },
        })),
        barMaxWidth: 36,
        label: {
          show: true,
          position: 'right',
          fontSize: 11,
          formatter: (params) => {
            const p = params as unknown as { dataIndex: number };
            return conversionLabels[p.dataIndex];
          },
        },
      },
    ],
  };

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h3 className="text-sm font-semibold text-cgiar-dark mb-3">
        Pathway Completion Funnel
      </h3>
      <ReactECharts option={option} theme="cgiar" style={{ height: '200px' }} />
    </div>
  );
}
