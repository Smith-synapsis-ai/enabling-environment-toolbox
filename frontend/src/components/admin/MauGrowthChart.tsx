import { useState, useEffect } from 'react';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';
import '../../theme/echarts-cgiar';
import { fetchMauGrowth } from '../../services/analytics';
import type { MauGrowthData } from '../../services/analytics';

export default function MauGrowthChart() {
  const [data, setData] = useState<MauGrowthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    fetchMauGrowth()
      .then(result => { if (!cancelled) setData(result); })
      .catch(err => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  if (loading) return <div className="animate-pulse bg-gray-100 rounded-lg h-64" />;
  if (error) return <div className="text-red-500 text-sm p-4">{error}</div>;
  if (!data || data.months.length === 0) return null;

  const months = data.months.map(m => {
    const dt = new Date(m.month);
    return dt.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
  });
  const mauValues = data.months.map(m => m.mau);
  const growthValues = data.months.map(m => m.mom_growth_pct);

  const option: EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
    },
    legend: {
      data: ['MAU', 'MoM Growth %'],
      top: 0,
    },
    grid: {
      left: 55,
      right: 55,
      top: 30,
      bottom: 30,
    },
    xAxis: {
      type: 'category',
      data: months,
    },
    yAxis: [
      {
        type: 'value',
        name: 'MAU',
        position: 'left',
        minInterval: 1,
        axisLabel: { fontSize: 11 },
      },
      {
        type: 'value',
        name: 'Growth %',
        position: 'right',
        axisLabel: {
          fontSize: 11,
          formatter: '{value}%',
        },
      },
    ],
    series: [
      {
        name: 'MAU',
        type: 'bar',
        data: mauValues,
        itemStyle: { color: '#2D5A3D' },
        barMaxWidth: 32,
      },
      {
        name: 'MoM Growth %',
        type: 'line',
        yAxisIndex: 1,
        data: growthValues,
        smooth: true,
        lineStyle: { color: '#FF9800', width: 2 },
        itemStyle: { color: '#FF9800' },
        symbol: 'circle',
        symbolSize: 6,
      },
    ],
  };

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h3 className="text-sm font-semibold text-cgiar-dark mb-3">Monthly Active Users Growth</h3>
      <ReactECharts option={option} theme="cgiar" style={{ height: '300px' }} />
    </div>
  );
}
