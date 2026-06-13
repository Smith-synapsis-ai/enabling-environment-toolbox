import { useState, useEffect, useCallback } from 'react';
import { ShieldCheck, Check, X, Clock } from 'lucide-react';
import {
  fetchProposals,
  approveProposal,
  rejectProposal,
} from '../../services/analytics';
import type { Proposal } from '../../services/analytics';

// C7 governance review-queue UI (folded into C6 Wave A) — lists pending content
// proposals and wires Approve / Reject to the existing admin-gated endpoints.

const STATUS_FILTERS = ['pending', 'approved', 'rejected', 'all'] as const;
type StatusFilter = (typeof STATUS_FILTERS)[number];

export default function GovernanceQueue() {
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [filter, setFilter] = useState<StatusFilter>('pending');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await fetchProposals(filter === 'all' ? undefined : filter);
      setProposals(data.proposals);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load proposals');
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    load();
  }, [load]);

  const handleApprove = async (id: string) => {
    setBusyId(id);
    try {
      await approveProposal(id);
      setFeedback('Proposal approved and applied to the live tool.');
      setTimeout(() => setFeedback(''), 3000);
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Approve failed');
    } finally {
      setBusyId(null);
    }
  };

  const handleReject = async (id: string) => {
    const notes = window.prompt('Rejection notes (optional):') ?? undefined;
    setBusyId(id);
    try {
      await rejectProposal(id, notes);
      setFeedback('Proposal rejected.');
      setTimeout(() => setFeedback(''), 3000);
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Reject failed');
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <ShieldCheck size={18} className="text-cgiar-accent" />
        <h3 className="text-sm font-semibold text-cgiar-dark">
          Content Governance — Review Queue (C7)
        </h3>
      </div>

      {feedback && (
        <div className="bg-green-50 text-green-700 px-4 py-2 rounded text-sm">{feedback}</div>
      )}
      {error && (
        <div className="bg-red-50 text-red-700 px-4 py-2 rounded text-sm">{error}</div>
      )}

      <div className="flex gap-1 bg-gray-100 rounded-lg p-1 w-fit">
        {STATUS_FILTERS.map(s => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-3 py-1.5 rounded-md text-xs font-medium capitalize transition-colors ${
              filter === s ? 'bg-cgiar-dark text-white' : 'text-gray-600 hover:bg-gray-200'
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="animate-pulse bg-gray-100 rounded-lg h-40" />
      ) : proposals.length === 0 ? (
        <div className="text-center text-gray-400 py-12 bg-white rounded-lg shadow">
          <Clock size={28} className="mx-auto mb-2 opacity-40" />
          No {filter === 'all' ? '' : filter} proposals.
        </div>
      ) : (
        <div className="space-y-3">
          {proposals.map(p => (
            <div key={p.id} className="bg-white rounded-lg shadow p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-cgiar-accent/15 text-cgiar-dark">
                      {p.proposal_type}
                    </span>
                    <span
                      className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                        p.status === 'pending'
                          ? 'bg-amber-100 text-amber-700'
                          : p.status === 'approved'
                          ? 'bg-green-100 text-green-700'
                          : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {p.status}
                    </span>
                    <span className="text-xs text-gray-400">
                      {p.submitted_at?.replace('T', ' ').slice(0, 16)}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mb-2">
                    {p.submitted_by ? `by ${p.submitted_by}` : 'anonymous'}
                    {p.provenance ? ` · ${p.provenance}` : ''}
                    {p.tool_id ? ` · tool ${p.tool_id.slice(0, 8)}` : ' · new tool'}
                  </p>
                  <div className="bg-gray-50 rounded p-2 text-xs font-mono text-gray-700 max-h-40 overflow-y-auto">
                    {Object.entries(p.proposed_fields).map(([k, v]) => (
                      <div key={k} className="truncate">
                        <span className="text-cgiar-dark font-semibold">{k}:</span>{' '}
                        {typeof v === 'string' ? v : JSON.stringify(v)}
                      </div>
                    ))}
                  </div>
                  {p.reviewer_notes && (
                    <p className="text-xs text-gray-500 mt-2">Notes: {p.reviewer_notes}</p>
                  )}
                </div>
                {p.status === 'pending' && (
                  <div className="flex flex-col gap-2 shrink-0">
                    <button
                      disabled={busyId === p.id}
                      onClick={() => handleApprove(p.id)}
                      className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-white bg-green-600 rounded-md hover:bg-green-700 disabled:opacity-50"
                    >
                      <Check size={14} /> Approve
                    </button>
                    <button
                      disabled={busyId === p.id}
                      onClick={() => handleReject(p.id)}
                      className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-red-600 bg-red-50 rounded-md hover:bg-red-100 disabled:opacity-50"
                    >
                      <X size={14} /> Reject
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
