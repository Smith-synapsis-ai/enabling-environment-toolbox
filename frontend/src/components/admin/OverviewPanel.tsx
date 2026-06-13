import { useState, useEffect } from 'react';
import { Target, Activity, MessageSquare, HeartPulse, Database, HardDrive, AlertTriangle } from 'lucide-react';
import {
  fetchKpi,
  fetchSurvey,
  fetchSystemHealth,
} from '../../services/analytics';
import type { KpiData, SurveyData, SystemHealthData } from '../../services/analytics';

// C6 Wave A Overview: durable C4 KPI access events (with corrected G4 count),
// C3 feature-usage breakdown, C5 canonical pulse-survey summary, and the
// honest system-health badge — all reading the durable Postgres store.

function Card({ children }: { children: React.ReactNode }) {
  return <div className="bg-white rounded-lg shadow p-5">{children}</div>;
}

function KpiAccessCard({ kpi }: { kpi: KpiData }) {
  const pct = Math.min(kpi.kpi_progress_pct, 100);
  return (
    <Card>
      <div className="flex items-center gap-2 mb-3">
        <Target size={18} className="text-cgiar-accent" />
        <h3 className="text-sm font-semibold text-cgiar-dark">
          KPI · Access Events (C4 / G4)
        </h3>
      </div>
      <div className="flex items-end gap-3 mb-3">
        <span className="text-3xl font-bold text-cgiar-dark">
          {kpi.kpi_access_events.toLocaleString()}
        </span>
        <span className="text-sm text-gray-500 mb-1">
          / {kpi.kpi_target.toLocaleString()} ({pct.toFixed(2)}%)
        </span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, background: 'linear-gradient(90deg,#1B3B2F,#4CAF50)' }}
        />
      </div>
      <p className="text-xs text-gray-400 mt-2">
        De-duplicated per browser session · source <code>/api/events/kpi</code> (durable)
      </p>
    </Card>
  );
}

function FeatureUsageCard({ kpi }: { kpi: KpiData }) {
  const entries = Object.entries(kpi.counts_by_event).sort((a, b) => b[1] - a[1]);
  const max = entries.length ? entries[0][1] : 1;
  return (
    <Card>
      <div className="flex items-center gap-2 mb-3">
        <Activity size={18} className="text-cgiar-accent" />
        <h3 className="text-sm font-semibold text-cgiar-dark">Feature Usage (C3)</h3>
      </div>
      {entries.length === 0 ? (
        <p className="text-sm text-gray-400">No events recorded yet.</p>
      ) : (
        <div className="space-y-2">
          {entries.map(([name, count]) => (
            <div key={name}>
              <div className="flex justify-between text-xs text-gray-600 mb-0.5">
                <span className="font-medium">{name}</span>
                <span>{count.toLocaleString()}</span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-2">
                <div
                  className="h-2 rounded-full bg-cgiar-accent"
                  style={{ width: `${(count / max) * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function SurveyCard({ survey }: { survey: SurveyData }) {
  return (
    <Card>
      <div className="flex items-center gap-2 mb-3">
        <MessageSquare size={18} className="text-cgiar-accent" />
        <h3 className="text-sm font-semibold text-cgiar-dark">Pulse Survey (C5)</h3>
      </div>
      <div className="flex items-end gap-3 mb-3">
        <span className="text-3xl font-bold text-cgiar-dark">
          {survey.average_score.toFixed(2)}
        </span>
        <span className="text-sm text-gray-500 mb-1">
          avg · {survey.total_responses.toLocaleString()} responses
        </span>
      </div>
      <div className="space-y-1">
        {Object.entries(survey.score_distribution).map(([score, count]) => {
          const total = survey.total_responses || 1;
          return (
            <div key={score} className="flex items-center gap-2 text-xs">
              <span className="w-4 text-gray-500">{score}</span>
              <div className="flex-1 bg-gray-100 rounded-full h-2">
                <div
                  className="h-2 rounded-full bg-cgiar-dark"
                  style={{ width: `${(count / total) * 100}%` }}
                />
              </div>
              <span className="w-8 text-right text-gray-500">{count}</span>
            </div>
          );
        })}
      </div>
      <p className="text-xs text-gray-400 mt-2">
        Canonical source <code>/api/events/survey</code> (durable)
      </p>
    </Card>
  );
}

function HealthCard({ health }: { health: SystemHealthData }) {
  const durableOk = health.durable_store_postgres.connected;
  const sessionState = health.session_store_sqlite.state;
  const restoreFailed = health.session_store_sqlite.restore_failed;
  const overall = health.status === 'ok';
  return (
    <Card>
      <div className="flex items-center gap-2 mb-3">
        <HeartPulse size={18} className="text-cgiar-accent" />
        <h3 className="text-sm font-semibold text-cgiar-dark">System Health (C12)</h3>
        <span
          className={`ml-auto text-xs font-medium px-2 py-0.5 rounded-full ${
            overall ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
          }`}
        >
          {overall ? 'OK' : 'DEGRADED'}
        </span>
      </div>
      <div className="space-y-2 text-sm">
        <div className="flex items-center gap-2">
          <Database size={15} className={durableOk ? 'text-green-600' : 'text-red-500'} />
          <span className="text-gray-700">Durable store (Postgres RDS):</span>
          <span className={`font-medium ${durableOk ? 'text-green-600' : 'text-red-500'}`}>
            {durableOk ? 'connected' : 'unavailable'}
          </span>
        </div>
        {durableOk && (
          <p className="text-xs text-gray-400 ml-7">
            {health.durable_store_postgres.analytics_events ?? 0} analytics rows ·{' '}
            {health.durable_store_postgres.token_usage ?? 0} token rows (survive instance refresh)
          </p>
        )}
        <div className="flex items-center gap-2">
          <HardDrive
            size={15}
            className={sessionState === 'connected' ? 'text-green-600' : 'text-amber-500'}
          />
          <span className="text-gray-700">Session store (SQLite):</span>
          <span className="font-medium text-gray-600">{sessionState}</span>
        </div>
        {restoreFailed && (
          <div className="flex items-start gap-2 bg-red-50 text-red-700 rounded p-2 text-xs">
            <AlertTriangle size={14} className="mt-0.5 shrink-0" />
            <span>
              Litestream restore failed on boot: {health.session_store_sqlite.restore_failed_detail}
            </span>
          </div>
        )}
      </div>
    </Card>
  );
}

export default function OverviewPanel() {
  const [kpi, setKpi] = useState<KpiData | null>(null);
  const [survey, setSurvey] = useState<SurveyData | null>(null);
  const [health, setHealth] = useState<SystemHealthData | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([fetchKpi(), fetchSurvey(), fetchSystemHealth()])
      .then(([k, s, h]) => {
        if (cancelled) return;
        setKpi(k);
        setSurvey(s);
        setHealth(h);
      })
      .catch(err => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[0, 1, 2, 3].map(i => (
          <div key={i} className="animate-pulse bg-gray-100 rounded-lg h-44" />
        ))}
      </div>
    );
  }
  if (error) return <div className="text-red-500 text-sm p-4">{error}</div>;

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-500">
        Durable KPI / analytics / survey / health — sourced from Postgres RDS,
        survives backend instance replacement.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {kpi && <KpiAccessCard kpi={kpi} />}
        {kpi && <FeatureUsageCard kpi={kpi} />}
        {survey && <SurveyCard survey={survey} />}
        {health && <HealthCard health={health} />}
      </div>
    </div>
  );
}
