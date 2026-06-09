import { useState, useEffect } from 'react';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';
import '../../theme/echarts-cgiar';
import { fetchSearchTerms } from '../../services/analytics';
import type { SearchTermsData } from '../../services/analytics';

interface SearchTermsChartProps {
  days: number;
}

export default function SearchTermsChart({ days }: SearchTermsChartProps) {
  const [data, setData] = useState<SearchTermsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    fetchSearchTerms(days, 20)
      .then(result => { if (!cancelled) setData(result); })
      .catch(err => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [days]);

  if (loading) return <div className="animate-pulse bg-gray-100 rounded-lg h-64" />;
  if (error) return <div className="text-red-500 text-sm p-4">{error}</div>;
  if (!data || data.terms.length === 0) return null;

  // Sort ascending so the most frequent appears at top in horizontal bar
  const sorted = [...data.terms].sort((a, b) => a.count - b.count);
  const queries = sorted.map(t =>
    t.query_text.length > 30 ? t.query_text.slice(0, 27) + '...' : t.query_text,
  );
  const counts = sorted.map(t => t.count);

  const chartHeight = Math.max(300, sorted.length * 22 + 40);

  const option: EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
    },
    grid: {
      left: 170,
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
      data: queries,
      axisLabel: {
        fontSize: 11,
        width: 150,
        overflow: 'truncate',
      },
    },
    series: [
      {
        type: 'bar',
        data: counts,
        barMaxWidth: 20,
        itemStyle: { color: '#1565C0' },
        label: {
          show: true,
          position: 'right',
          fontSize: 10,
          color: '#333',
        },
      },
    ],
  };

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h3 className="text-sm font-semibold text-cgiar-dark mb-3">Top Search Terms</h3>
      <ReactECharts option={option} theme="cgiar" style={{ height: `${chartHeight}px` }} />
    </div>
  );
}
