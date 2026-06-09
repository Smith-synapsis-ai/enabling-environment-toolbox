import { useState, useEffect } from 'react';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';
import '../../theme/echarts-cgiar';
import { fetchPulseSurveyScores } from '../../services/analytics';
import type { PulseSurveyScoresData, PulseSurveyScore } from '../../services/analytics';

interface PulseSurveyGaugesProps {
  days: number;
}

const QUESTION_LABELS: Record<string, string> = {
  trust_recommendations: 'Trust in Recommendations',
  helped_decide: 'Helped Make Decisions',
};

function buildGaugeOption(score: PulseSurveyScore): EChartsOption {
  const label = QUESTION_LABELS[score.question_key] || score.question_key;
  return {
    series: [
      {
        type: 'gauge',
        startAngle: 200,
        endAngle: -20,
        min: 0,
        max: 5,
        splitNumber: 5,
        radius: '90%',
        axisLine: {
          lineStyle: {
            width: 20,
            color: [
              [0.4, '#E65100'],
              [0.6, '#FF9800'],
              [0.8, '#4CAF50'],
              [1, '#1B3B2F'],
            ],
          },
        },
        pointer: {
          itemStyle: { color: '#333' },
          width: 4,
          length: '60%',
        },
        axisTick: {
          distance: -20,
          length: 6,
          lineStyle: { color: '#fff', width: 1 },
        },
        splitLine: {
          distance: -24,
          length: 16,
          lineStyle: { color: '#fff', width: 2 },
        },
        axisLabel: {
          color: '#666',
          distance: 28,
          fontSize: 10,
        },
        anchor: {
          show: true,
          size: 12,
          itemStyle: { borderWidth: 2, borderColor: '#999' },
        },
        title: {
          show: true,
          offsetCenter: [0, '70%'],
          fontSize: 11,
          color: '#555',
        },
        detail: {
          valueAnimation: true,
          fontSize: 22,
          fontWeight: 'bold',
          color: '#1B3B2F',
          offsetCenter: [0, '45%'],
          formatter: (val: number) => val.toFixed(1),
        },
        markLine: {
          silent: true,
          symbol: 'none',
        },
        data: [
          {
            value: score.avg_score,
            name: `${label}\n(${score.response_count} responses)`,
          },
        ],
      },
      // Target marker at 4.0 — a thin pointer-less gauge overlay
      {
        type: 'gauge',
        startAngle: 200,
        endAngle: -20,
        min: 0,
        max: 5,
        radius: '90%',
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        pointer: {
          show: true,
          length: '75%',
          width: 2,
          itemStyle: { color: '#C62828' },
        },
        detail: { show: false },
        title: { show: false },
        data: [{ value: 4.0 }],
      },
    ],
  };
}

export default function PulseSurveyGauges({ days }: PulseSurveyGaugesProps) {
  const [data, setData] = useState<PulseSurveyScoresData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    fetchPulseSurveyScores(days)
      .then(result => { if (!cancelled) setData(result); })
      .catch(err => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [days]);

  if (loading) return <div className="animate-pulse bg-gray-100 rounded-lg h-64" />;
  if (error) return <div className="text-red-500 text-sm p-4">{error}</div>;
  if (!data || data.scores.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-sm font-semibold text-cgiar-dark mb-3">Pulse Survey Scores</h3>
        <p className="text-gray-400 text-sm">No survey data available yet.</p>
      </div>
    );
  }

  // Find the two expected questions (or show whatever is there)
  const trustScore = data.scores.find(s => s.question_key === 'trust_recommendations');
  const helpedScore = data.scores.find(s => s.question_key === 'helped_decide');
  const gauges = [trustScore, helpedScore].filter(
    (s): s is PulseSurveyScore => s !== undefined,
  );

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-cgiar-dark">Pulse Survey Scores</h3>
        <span className="text-xs text-gray-400">
          Target: 4.0 (red line) | Overall: {data.overall_avg.toFixed(1)}
        </span>
      </div>
      <div className={`grid gap-4 ${gauges.length > 1 ? 'grid-cols-2' : 'grid-cols-1'}`}>
        {gauges.map(score => (
          <ReactECharts
            key={score.question_key}
            option={buildGaugeOption(score)}
            theme="cgiar"
            style={{ height: '250px' }}
          />
        ))}
      </div>
    </div>
  );
}
