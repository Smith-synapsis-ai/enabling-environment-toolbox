import { useState, useEffect, useCallback } from 'react';
import {
  Search,
  ChevronDown,
  ChevronRight,
  ChevronLeft,
  ChevronsLeft,
  ChevronsRight,
  Bot,
  User,
  Clock,
  Loader2,
} from 'lucide-react';
import { fetchSessions } from '../../services/analytics';

// ---------------------------------------------------------------------------
// Types matching the /sessions API response
// ---------------------------------------------------------------------------

interface Session {
  session_id: string;
  started_at: string;
  last_active_at: string;
  user_email: string | null;
  user_type: string | null;
  is_bot: boolean;
  user_agent: string;
  search_count: number;
  view_count: number;
  rating_count: number;
}

interface SessionsResponse {
  period_days: number;
  total: number;
  limit: number;
  offset: number;
  sessions: Session[];
}

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  }) + ', ' + d.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

function formatDuration(startIso: string, endIso: string): string {
  const start = new Date(startIso).getTime();
  const end = new Date(endIso).getTime();
  const diffMs = Math.max(0, end - start);
  const totalSeconds = Math.floor(diffMs / 1000);

  if (totalSeconds < 60) {
    return `${totalSeconds}s`;
  }

  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;

  if (minutes < 60) {
    return seconds > 0 ? `${minutes}m ${seconds}s` : `${minutes}m`;
  }

  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return remainingMinutes > 0
    ? `${hours}h ${remainingMinutes}m`
    : `${hours}h`;
}

function truncateSessionId(id: string): string {
  return id.length > 8 ? id.slice(0, 8) : id;
}

function parseBrowserName(ua: string): string {
  if (!ua) return '-';

  // Try to extract a recognizable browser name
  if (ua.includes('Firefox/')) return 'Firefox';
  if (ua.includes('Edg/')) return 'Edge';
  if (ua.includes('OPR/') || ua.includes('Opera/')) return 'Opera';
  if (ua.includes('Chrome/') && !ua.includes('Edg/')) return 'Chrome';
  if (ua.includes('Safari/') && !ua.includes('Chrome/')) return 'Safari';

  // Bot-like agents
  if (ua.includes('bot') || ua.includes('Bot') || ua.includes('crawler')) {
    return 'Bot';
  }

  // Fallback: first 30 chars
  return ua.length > 30 ? ua.slice(0, 30) + '...' : ua;
}

// ---------------------------------------------------------------------------
// Day-range options for the session explorer
// ---------------------------------------------------------------------------

const DAY_OPTIONS = [
  { value: 1, label: 'Last 24h' },
  { value: 7, label: 'Last 7 days' },
  { value: 14, label: 'Last 14 days' },
  { value: 30, label: 'Last 30 days' },
  { value: 90, label: 'Last 90 days' },
];

// ---------------------------------------------------------------------------
// SessionExplorer component
// ---------------------------------------------------------------------------

export default function SessionExplorer() {
  const [days, setDays] = useState(7);
  const [emailFilter, setEmailFilter] = useState('');
  const [debouncedEmail, setDebouncedEmail] = useState('');
  const [data, setData] = useState<SessionsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [offset, setOffset] = useState(0);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const PAGE_SIZE = 50;

  // Debounce email filter
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedEmail(emailFilter);
      setOffset(0);
    }, 400);
    return () => clearTimeout(timer);
  }, [emailFilter]);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const result = await fetchSessions(days, PAGE_SIZE, offset);
      setData(result as SessionsResponse);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load sessions');
    } finally {
      setLoading(false);
    }
  }, [days, offset]);

  useEffect(() => {
    load();
  }, [load]);

  // Client-side email filtering (API does not support email param)
  const filteredSessions = data
    ? debouncedEmail
      ? data.sessions.filter(s =>
          s.user_email?.toLowerCase().includes(debouncedEmail.toLowerCase())
        )
      : data.sessions
    : [];

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  const goToPage = (page: number) => {
    const clamped = Math.max(1, Math.min(page, totalPages));
    setOffset((clamped - 1) * PAGE_SIZE);
  };

  const toggleExpand = (sessionId: string) => {
    setExpandedId(prev => (prev === sessionId ? null : sessionId));
  };

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Email search */}
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
          />
          <input
            type="text"
            placeholder="Filter by email..."
            value={emailFilter}
            onChange={e => setEmailFilter(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-cgiar-accent"
            aria-label="Filter sessions by email"
          />
        </div>

        {/* Day range selector */}
        <select
          value={days}
          onChange={e => {
            setDays(Number(e.target.value));
            setOffset(0);
          }}
          className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cgiar-accent"
          aria-label="Time range"
        >
          {DAY_OPTIONS.map(opt => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        {/* Session count */}
        {data && (
          <span className="text-sm text-gray-500 ml-auto">
            {data.total.toLocaleString()} session{data.total !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 text-red-700 px-4 py-2 rounded text-sm">
          {error}
        </div>
      )}

      {/* Loading state */}
      {loading && !data && (
        <div className="flex items-center justify-center py-16 text-gray-400">
          <Loader2 size={24} className="animate-spin mr-2" />
          Loading sessions...
        </div>
      )}

      {/* Table */}
      {data && filteredSessions.length > 0 && (
        <div className="bg-white rounded-lg shadow overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="w-8 px-3 py-3" />
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Session ID
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Started
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Last Active
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Duration
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Email
                </th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Searches
                </th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Views
                </th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Ratings
                </th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Bot?
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {filteredSessions.map(session => {
                const isExpanded = expandedId === session.session_id;
                const rowBaseClass = session.is_bot
                  ? 'bg-gray-50 text-gray-400'
                  : 'text-gray-900';

                return (
                  <SessionRow
                    key={session.session_id}
                    session={session}
                    isExpanded={isExpanded}
                    rowBaseClass={rowBaseClass}
                    onToggle={() => toggleExpand(session.session_id)}
                  />
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Empty state */}
      {data && filteredSessions.length === 0 && !loading && (
        <div className="text-center text-gray-500 py-16">
          No sessions found for the selected filters.
        </div>
      )}

      {/* Pagination */}
      {data && totalPages > 1 && (
        <div className="flex items-center justify-between text-sm text-gray-600">
          <span>
            Page {currentPage} of {totalPages}
          </span>
          <div className="flex items-center gap-1">
            <PaginationButton
              onClick={() => goToPage(1)}
              disabled={currentPage <= 1}
              aria-label="First page"
            >
              <ChevronsLeft size={14} />
            </PaginationButton>
            <PaginationButton
              onClick={() => goToPage(currentPage - 1)}
              disabled={currentPage <= 1}
              aria-label="Previous page"
            >
              <ChevronLeft size={14} />
            </PaginationButton>
            <span className="px-3 py-1 text-sm font-medium text-cgiar-dark">
              {currentPage}
            </span>
            <PaginationButton
              onClick={() => goToPage(currentPage + 1)}
              disabled={currentPage >= totalPages}
              aria-label="Next page"
            >
              <ChevronRight size={14} />
            </PaginationButton>
            <PaginationButton
              onClick={() => goToPage(totalPages)}
              disabled={currentPage >= totalPages}
              aria-label="Last page"
            >
              <ChevronsRight size={14} />
            </PaginationButton>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// SessionRow (extracted for expandability)
// ---------------------------------------------------------------------------

function SessionRow({
  session,
  isExpanded,
  rowBaseClass,
  onToggle,
}: {
  session: Session;
  isExpanded: boolean;
  rowBaseClass: string;
  onToggle: () => void;
}) {
  return (
    <>
      <tr
        className={`${rowBaseClass} hover:bg-gray-100 cursor-pointer transition-colors`}
        onClick={onToggle}
      >
        <td className="px-3 py-3 text-gray-400">
          {isExpanded ? (
            <ChevronDown size={14} />
          ) : (
            <ChevronRight size={14} />
          )}
        </td>
        <td className="px-4 py-3 text-sm font-mono">
          {truncateSessionId(session.session_id)}
        </td>
        <td className="px-4 py-3 text-sm whitespace-nowrap">
          {formatDate(session.started_at)}
        </td>
        <td className="px-4 py-3 text-sm whitespace-nowrap">
          {formatDate(session.last_active_at)}
        </td>
        <td className="px-4 py-3 text-sm whitespace-nowrap">
          <span className="inline-flex items-center gap-1">
            <Clock size={12} className="text-gray-400" />
            {formatDuration(session.started_at, session.last_active_at)}
          </span>
        </td>
        <td className="px-4 py-3 text-sm max-w-[180px] truncate">
          {session.user_email || (
            <span className="text-gray-400 italic">anonymous</span>
          )}
        </td>
        <td className="px-4 py-3 text-sm text-center">
          {session.search_count}
        </td>
        <td className="px-4 py-3 text-sm text-center">
          {session.view_count}
        </td>
        <td className="px-4 py-3 text-sm text-center">
          {session.rating_count}
        </td>
        <td className="px-4 py-3 text-center">
          {session.is_bot ? (
            <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full">
              <Bot size={12} />
              Bot
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 text-xs font-medium text-green-700 bg-green-50 px-2 py-0.5 rounded-full">
              <User size={12} />
              Human
            </span>
          )}
        </td>
      </tr>

      {/* Expanded detail row */}
      {isExpanded && (
        <tr className={session.is_bot ? 'bg-gray-50' : 'bg-blue-50/30'}>
          <td colSpan={10} className="px-6 py-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
              <DetailField label="Full Session ID" value={session.session_id} mono />
              <DetailField label="User Email" value={session.user_email || 'N/A'} />
              <DetailField label="User Type" value={session.user_type || 'N/A'} />
              <DetailField
                label="Started At"
                value={new Date(session.started_at).toLocaleString()}
              />
              <DetailField
                label="Last Active At"
                value={new Date(session.last_active_at).toLocaleString()}
              />
              <DetailField
                label="Duration"
                value={formatDuration(session.started_at, session.last_active_at)}
              />
              <DetailField
                label="Browser"
                value={parseBrowserName(session.user_agent)}
              />
              <DetailField
                label="User Agent"
                value={session.user_agent || 'N/A'}
                truncate
              />
              <DetailField
                label="Is Bot"
                value={session.is_bot ? 'Yes' : 'No'}
              />
              <DetailField
                label="Searches"
                value={String(session.search_count)}
              />
              <DetailField
                label="Tool Views"
                value={String(session.view_count)}
              />
              <DetailField
                label="Ratings Given"
                value={String(session.rating_count)}
              />
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// DetailField (key-value pair in expanded row)
// ---------------------------------------------------------------------------

function DetailField({
  label,
  value,
  mono,
  truncate,
}: {
  label: string;
  value: string;
  mono?: boolean;
  truncate?: boolean;
}) {
  return (
    <div>
      <dt className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-0.5">
        {label}
      </dt>
      <dd
        className={`text-gray-800 ${mono ? 'font-mono text-xs' : ''} ${
          truncate ? 'truncate max-w-[280px]' : ''
        }`}
        title={truncate ? value : undefined}
      >
        {value}
      </dd>
    </div>
  );
}

// ---------------------------------------------------------------------------
// PaginationButton
// ---------------------------------------------------------------------------

function PaginationButton({
  children,
  onClick,
  disabled,
  'aria-label': ariaLabel,
}: {
  children: React.ReactNode;
  onClick: () => void;
  disabled: boolean;
  'aria-label': string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={ariaLabel}
      className="p-1.5 border border-gray-300 rounded-md disabled:opacity-40 hover:bg-gray-100 transition-colors disabled:cursor-not-allowed"
    >
      {children}
    </button>
  );
}
