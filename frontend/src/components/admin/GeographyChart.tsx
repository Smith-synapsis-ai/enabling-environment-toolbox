import { useState, useEffect } from 'react';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';
import '../../theme/echarts-cgiar';
import { CGIAR_COLORS } from '../../theme/echarts-cgiar';
import { fetchGeography } from '../../services/analytics';
import type { GeographyData } from '../../services/analytics';

interface GeographyChartProps {
  days: number;
}

export default function GeographyChart({ days }: GeographyChartProps) {
  const [data, setData] = useState<GeographyData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    fetchGeography(days)
      .then(result => { if (!cancelled) setData(result); })
      .catch(err => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [days]);

  if (loading) return <div className="animate-pulse bg-gray-100 rounded-lg h-64" />;
  if (error) return <div className="text-red-500 text-sm p-4">{error}</div>;
  if (!data || data.geographies.length === 0) return null;

  const pieData = data.geographies.map((g, i) => ({
    name: g.geography,
    value: g.view_count,
    itemStyle: { color: CGIAR_COLORS[i % CGIAR_COLORS.length] },
  }));

  const option: EChartsOption = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} views ({d}%)',
    },
    legend: {
      type: 'scroll',
      orient: 'vertical',
      right: 10,
      top: 20,
      bottom: 20,
      textStyle: { fontSize: 11 },
    },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['35%', '50%'],
        avoidLabelOverlap: true,
        label: { show: false },
        emphasis: {
          label: {
            show: true,
            fontSize: 12,
            fontWeight: 'bold',
          },
        },
        data: pieData,
      },
    ],
  };

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h3 className="text-sm font-semibold text-cgiar-dark mb-3">Geography Distribution</h3>
      <ReactECharts option={option} theme="cgiar" style={{ height: '300px' }} />
    </div>
  );
}
