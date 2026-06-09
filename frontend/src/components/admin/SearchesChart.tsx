import { useState, useEffect } from 'react';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';
import '../../theme/echarts-cgiar';
import { fetchTimeseries } from '../../services/analytics';
import type { TimeseriesData } from '../../services/analytics';

interface SearchesChartProps {
  days: number;
}

const GRANULARITY_OPTIONS = ['daily', 'weekly', 'monthly'] as const;

export default function SearchesChart({ days }: SearchesChartProps) {
  const [granularity, setGranularity] = useState<string>('daily');
  const [data, setData] = useState<TimeseriesData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    fetchTimeseries(days, granularity, 'searches')
      .then(result => { if (!cancelled) setData(result); })
      .catch(err => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [days, granularity]);

  if (loading) return <div className="animate-pulse bg-gray-100 rounded-lg h-64" />;
  if (error) return <div className="text-red-500 text-sm p-4">{error}</div>;
  if (!data) return null;

  const dates = data.data.map(d => {
    const dt = new Date(d.date);
    return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  });
  const values = data.data.map(d => d.value);

  const option: EChartsOption = {
    tooltip: {
      trigger: 'axis',
    },
    grid: {
      left: 50,
      right: 20,
      top: 10,
      bottom: 30,
    },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false,
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
    },
    series: [
      {
        name: 'Searches',
        type: 'line',
        smooth: true,
        data: values,
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(21, 101, 192, 0.3)' },
              { offset: 1, color: 'rgba(21, 101, 192, 0.02)' },
            ],
          },
        },
        lineStyle: { color: '#1565C0', width: 2 },
        itemStyle: { color: '#1565C0' },
      },
    ],
  };

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-cgiar-dark">Search Volume</h3>
        <div className="flex gap-1">
          {GRANULARITY_OPTIONS.map(g => (
            <button
              key={g}
              onClick={() => setGranularity(g)}
              className={`px-2 py-0.5 text-xs rounded-full transition-colors ${
                granularity === g
                  ? 'bg-cgiar-accent text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {g.charAt(0).toUpperCase() + g.slice(1)}
            </button>
          ))}
        </div>
      </div>
      <ReactECharts option={option} theme="cgiar" style={{ height: '300px' }} />
    </div>
  );
}
