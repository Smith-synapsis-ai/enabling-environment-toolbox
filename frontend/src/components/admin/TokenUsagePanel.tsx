import { useState, useEffect } from 'react';
import { DollarSign, Coins, Layers, Cpu } from 'lucide-react';
import { fetchTokenSummary, fetchTokenRecent } from '../../services/analytics';
import type { TokenSummary, TokenRecentData } from '../../services/analytics';

// C6 Wave A / Thread 2 — durable per-turn token usage + cost captured at the
// orchestrator ResultMessage chokepoint (covers WS + CLI paths).

function StatCard({
  icon,
  label,
  value,
  sub,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-center gap-2 mb-1 text-gray-500">
        {icon}
        <span className="text-xs font-medium uppercase tracking-wide">{label}</span>
      </div>
      <div className="text-2xl font-bold text-cgiar-dark">{value}</div>
      {sub && <div className="text-xs text-gray-400 mt-1">{sub}</div>}
    </div>
  );
}

export default function TokenUsagePanel() {
  const [summary, setSummary] = useState<TokenSummary | null>(null);
  const [recent, setRecent] = useState<TokenRecentData | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([fetchTokenSummary(), fetchTokenRecent(50)])
      .then(([s, r]) => {
        if (cancelled) return;
        setSummary(s);
        setRecent(r);
      })
      .catch(err => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  if (loading) return <div className="animate-pulse bg-gray-100 rounded-lg h-64" />;
  if (error) return <div className="text-red-500 text-sm p-4">{error}</div>;
  if (!summary) return null;

  const avg = summary.avg_cost_per_query_usd;
  const withinBenchmark =
    summary.runs === 0 || avg <= summary.benchmark_high_usd;

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-500">
        Per-turn token usage + cost (SDK-authoritative), persisted to the durable
        Postgres store at the orchestrator result chokepoint.
      </p>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={<DollarSign size={15} />}
          label="Total spend"
          value={`$${summary.total_cost_usd.toFixed(4)}`}
          sub={`${summary.runs.toLocaleString()} runs`}
        />
        <StatCard
          icon={<Coins size={15} />}
          label="Avg $/query"
          value={`$${avg.toFixed(4)}`}
          sub={`benchmark $${summary.benchmark_low_usd.toFixed(2)}–$${summary.benchmark_high_usd.toFixed(2)}`}
        />
        <StatCard
          icon={<Layers size={15} />}
          label="Total turns"
          value={summary.total_turns.toLocaleString()}
          sub={`${(summary.total_input_tokens + summary.total_output_tokens).toLocaleString()} tokens`}
        />
        <div
          className={`rounded-lg shadow p-4 ${
            withinBenchmark ? 'bg-green-50' : 'bg-amber-50'
          }`}
        >
          <div className="flex items-center gap-2 mb-1 text-gray-500">
            <Cpu size={15} />
            <span className="text-xs font-medium uppercase tracking-wide">vs benchmark</span>
          </div>
          <div
            className={`text-2xl font-bold ${
              withinBenchmark ? 'text-green-700' : 'text-amber-700'
            }`}
          >
            {withinBenchmark ? 'On target' : 'Over'}
          </div>
          <div className="text-xs text-gray-400 mt-1">
            {summary.runs === 0 ? 'no runs yet' : `avg $${avg.toFixed(4)}/query`}
          </div>
        </div>
      </div>

      {summary.by_model.length > 0 && (
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-sm font-semibold text-cgiar-dark mb-3">Cost by model</h3>
          <div className="space-y-2">
            {summary.by_model.map(m => (
              <div key={m.model} className="flex items-center justify-between text-sm">
                <span className="font-mono text-xs text-gray-700">{m.model}</span>
                <span className="text-gray-500">
                  {m.runs} runs · ${m.cost_usd.toFixed(4)} ·{' '}
                  {(m.input_tokens + m.output_tokens).toLocaleString()} tok
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              {['When', 'Session', 'Turn', 'Model', 'In', 'Out', 'Cost', 'Err'].map(h => (
                <th
                  key={h}
                  className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {recent && recent.rows.length > 0 ? (
              recent.rows.map((r, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-3 py-2 text-gray-600 whitespace-nowrap">
                    {r.created_at?.replace('T', ' ').replace('+00:00', '') ?? '-'}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs text-gray-500">
                    {r.session_id ? r.session_id.slice(0, 8) : '-'}
                  </td>
                  <td className="px-3 py-2 text-gray-600">{r.turn ?? '-'}</td>
                  <td className="px-3 py-2 font-mono text-xs text-gray-500">
                    {r.orchestrator_model ?? '-'}
                  </td>
                  <td className="px-3 py-2 text-gray-600">
                    {r.input_tokens?.toLocaleString() ?? '-'}
                  </td>
                  <td className="px-3 py-2 text-gray-600">
                    {r.output_tokens?.toLocaleString() ?? '-'}
                  </td>
                  <td className="px-3 py-2 text-gray-700">
                    {r.total_cost_usd != null ? `$${r.total_cost_usd.toFixed(4)}` : '-'}
                  </td>
                  <td className="px-3 py-2">
                    {r.is_error ? (
                      <span className="text-red-500 font-medium">yes</span>
                    ) : (
                      <span className="text-gray-400">no</span>
                    )}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={8} className="px-3 py-8 text-center text-gray-400">
                  No token-usage rows yet — run an assistant challenge to populate.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
