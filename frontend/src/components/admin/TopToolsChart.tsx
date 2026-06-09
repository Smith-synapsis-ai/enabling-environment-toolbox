import { useState, useEffect } from 'react';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';
import '../../theme/echarts-cgiar';
import { fetchTopTools } from '../../services/analytics';
import type { TopToolsData } from '../../services/analytics';

interface TopToolsChartProps {
  days: number;
}

export default function TopToolsChart({ days }: TopToolsChartProps) {
  const [data, setData] = useState<TopToolsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    fetchTopTools(days, 10, 'views')
      .then(result => { if (!cancelled) setData(result); })
      .catch(err => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [days]);

  if (loading) return <div className="animate-pulse bg-gray-100 rounded-lg h-64" />;
  if (error) return <div className="text-red-500 text-sm p-4">{error}</div>;
  if (!data || data.tools.length === 0) return null;

  // Sort ascending so the highest is at the top in horizontal bar
  const sorted = [...data.tools].sort((a, b) => a.views - b.views);
  const titles = sorted.map(t =>
    t.title.length > 35 ? t.title.slice(0, 32) + '...' : t.title,
  );
  const views = sorted.map(t => t.views);

  const option: EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
    },
    grid: {
      left: 180,
      right: 40,
      top: 10,
      bottom: 20,
    },
    xAxis: {
      type: 'value',
      minInterval: 1,
    },
    yAxis: {
      type: 'category',
      data: titles,
      axisLabel: {
        fontSize: 11,
        width: 160,
        overflow: 'truncate',
      },
    },
    series: [
      {
        type: 'bar',
        data: views,
        barMaxWidth: 24,
        itemStyle: { color: '#2D5A3D' },
        label: {
          show: true,
          position: 'right',
          fontSize: 11,
          color: '#333',
        },
      },
    ],
  };

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h3 className="text-sm font-semibold text-cgiar-dark mb-3">Top 10 Tools by Views</h3>
      <ReactECharts option={option} theme="cgiar" style={{ height: '300px' }} />
    </div>
  );
}
