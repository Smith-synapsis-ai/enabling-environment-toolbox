import { useState } from 'react';
import { Download, Bot, Loader2 } from 'lucide-react';
import DateRangePicker from './DateRangePicker';
import KpiCards from './KpiCards';
import TimeseriesChart from './TimeseriesChart';
import SearchesChart from './SearchesChart';
import EngagementFunnel from './EngagementFunnel';
import TopToolsChart from './TopToolsChart';
import SearchTermsChart from './SearchTermsChart';
import GeographyChart from './GeographyChart';
import GoalTracker from './GoalTracker';
import MauGrowthChart from './MauGrowthChart';
import PathwayFunnel from './PathwayFunnel';
import PulseSurveyGauges from './PulseSurveyGauges';
import TrafficSourcesChart from './TrafficSourcesChart';
import { downloadExport } from '../../services/analytics';

export default function AnalyticsDashboard() {
  const [days, setDays] = useState(30);
  const [exporting, setExporting] = useState(false);
  const [humanOnly, setHumanOnly] = useState(true);

  const handleExport = async () => {
    setExporting(true);
    try {
      await downloadExport(days);
    } catch (err) {
      console.error('Export failed:', err);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Controls bar */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 className="text-xl font-bold text-cgiar-dark">
          Analytics Dashboard
        </h2>

        <div className="flex flex-wrap items-center gap-4">
          {/* Bot filter toggle */}
          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer select-none">
            <Bot size={16} className="shrink-0" />
            <span className="whitespace-nowrap">
              {humanOnly ? 'Human only' : 'All sessions'}
            </span>
            <button
              type="button"
              role="switch"
              aria-checked={humanOnly}
              onClick={() => setHumanOnly(!humanOnly)}
              className={`relative inline-flex h-5 w-10 shrink-0 items-center rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cgiar-accent focus-visible:ring-offset-2 ${
                humanOnly ? 'bg-cgiar-accent' : 'bg-gray-300'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform ${
                  humanOnly ? 'translate-x-5' : 'translate-x-0.5'
                }`}
              />
            </button>
          </label>

          {/* Date range picker */}
          <DateRangePicker days={days} onChange={setDays} />

          {/* Export button */}
          <button
            type="button"
            onClick={handleExport}
            disabled={exporting}
            className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-white bg-cgiar-dark rounded-md hover:bg-cgiar-dark/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {exporting ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Download size={14} />
            )}
            {exporting ? 'Exporting...' : 'Export XLSX'}
          </button>
        </div>
      </div>

      {/* Row 1: KPI cards (full width) */}
      <KpiCards days={days} />

      {/* Rows 2-7: Chart grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Row 2 */}
        <TimeseriesChart days={days} />
        <SearchesChart days={days} />

        {/* Row 3 */}
        <EngagementFunnel days={days} />
        <TopToolsChart days={days} />

        {/* Row 4 */}
        <SearchTermsChart days={days} />
        <GeographyChart days={days} />

        {/* Row 5 */}
        <GoalTracker days={days} />
        <MauGrowthChart />

        {/* Row 6 */}
        <PathwayFunnel days={days} />
        <PulseSurveyGauges days={days} />

        {/* Row 7 */}
        <TrafficSourcesChart days={days} />
      </div>
    </div>
  );
}
