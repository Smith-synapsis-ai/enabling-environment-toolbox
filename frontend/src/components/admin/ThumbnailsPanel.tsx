import { useState, useEffect, useCallback } from 'react';
import { Image as ImageIcon, Check, X, RefreshCw, Zap } from 'lucide-react';
import {
  fetchThumbnailJobs,
  generateThumbnailBatch,
  approveThumbnail,
  rejectThumbnail,
  regenerateThumbnail,
} from '../../services/analytics';
import type { ThumbnailJob } from '../../services/analytics';

// ---------------------------------------------------------------------------
// C6 Wave B / Thread 3 — AI thumbnail pipeline admin tab.
//
// (a) TRIGGER a small, budget-gated batch generation (operator-controlled).
//     The trigger only ENQUEUES jobs; the controlled agent/CI path generates
//     the images and stages them in S3 (no long-lived backend write-IAM).
// (b) REVIEW staged results in a grid with Approve / Reject / Regenerate.
//     Approve promotes staging->live (CI) and sets cover_image_url so the live
//     catalog card/detail render the real image instead of the letter avatar.
// ---------------------------------------------------------------------------

const STATUS_FILTERS = ['staged', 'requested', 'approved', 'rejected', 'failed', 'all'] as const;
type StatusFilter = (typeof STATUS_FILTERS)[number];

const STATUS_STYLES: Record<string, string> = {
  requested: 'bg-amber-100 text-amber-800',
  generating: 'bg-blue-100 text-blue-800',
  staged: 'bg-indigo-100 text-indigo-800',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-700',
  failed: 'bg-red-100 text-red-700',
};

export default function ThumbnailsPanel() {
  const [jobs, setJobs] = useState<ThumbnailJob[]>([]);
  const [bucket, setBucket] = useState('');
  const [filter, setFilter] = useState<StatusFilter>('staged');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [feedback, setFeedback] = useState('');
  const [busyId, setBusyId] = useState<string | null>(null);
  const [batchCount, setBatchCount] = useState(5);
  const [generating, setGenerating] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await fetchThumbnailJobs(filter === 'all' ? undefined : filter);
      setJobs(data.jobs);
      setBucket(data.bucket);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load thumbnails');
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    load();
  }, [load]);

  const handleGenerate = async () => {
    setGenerating(true);
    setError('');
    try {
      const res = await generateThumbnailBatch(batchCount);
      if (res.enqueued > 0) {
        setFeedback(
          `Enqueued ${res.enqueued} tool(s) for generation (batch ${res.batch_id}). ` +
            `The controlled generation path will stage the images for review.`,
        );
      } else {
        setFeedback(res.note || 'No eligible tools to enqueue.');
      }
      setTimeout(() => setFeedback(''), 6000);
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Generate failed');
    } finally {
      setGenerating(false);
    }
  };

  const act = async (
    cgspaceId: string,
    fn: (id: string) => Promise<unknown>,
    msg: string,
  ) => {
    setBusyId(cgspaceId);
    setError('');
    try {
      await fn(cgspaceId);
      setFeedback(msg);
      setTimeout(() => setFeedback(''), 4000);
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Action failed');
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-5">
      {/* Header + trigger */}
      <div className="bg-white rounded-lg shadow p-5">
        <div className="flex items-center gap-2 mb-3">
          <ImageIcon size={18} className="text-cgiar-dark" />
          <h2 className="text-lg font-semibold text-cgiar-dark">AI Thumbnails</h2>
        </div>
        <p className="text-sm text-gray-500 mb-4">
          Budget-controlled, reviewable pipeline. Trigger a small batch, then review the
          staged results below and Approve / Reject / Regenerate. Approving promotes the
          image to the live key and renders it on the tool's catalog card. Bucket:{' '}
          <code className="text-xs bg-gray-100 px-1 py-0.5 rounded">{bucket || '…'}</code>
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-sm text-gray-700">Batch size</label>
          <select
            value={batchCount}
            onChange={e => setBatchCount(Number(e.target.value))}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cgiar-accent"
          >
            {[5, 6, 7, 8, 9, 10].map(n => (
              <option key={n} value={n}>
                {n} tools
              </option>
            ))}
          </select>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-cgiar-dark rounded-md hover:bg-cgiar-dark/90 transition-colors disabled:opacity-50"
          >
            <Zap size={15} />
            {generating ? 'Enqueuing…' : 'Generate batch'}
          </button>
        </div>
      </div>

      {/* Feedback */}
      {feedback && (
        <div className="bg-green-50 text-green-700 px-4 py-2 rounded text-sm">{feedback}</div>
      )}
      {error && (
        <div className="bg-red-50 text-red-700 px-4 py-2 rounded text-sm">{error}</div>
      )}

      {/* Filter */}
      <div className="flex gap-2">
        {STATUS_FILTERS.map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-md text-sm font-medium capitalize transition-colors ${
              filter === f
                ? 'bg-cgiar-dark text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Review grid */}
      {loading ? (
        <div className="text-center text-gray-500 py-12">Loading…</div>
      ) : jobs.length === 0 ? (
        <div className="text-center text-gray-500 py-12">No thumbnails in this status.</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {jobs.map(job => {
            const previewUrl =
              job.status === 'approved' ? job.live_url : job.staging_url;
            const isBusy = busyId === job.cgspace_id;
            return (
              <div
                key={job.id}
                className="bg-white rounded-lg shadow border border-gray-100 overflow-hidden flex flex-col"
              >
                {/* Preview */}
                {previewUrl ? (
                  <img
                    src={previewUrl}
                    alt={job.tool_title || job.cgspace_id}
                    className="w-full h-40 object-cover bg-gray-50"
                  />
                ) : (
                  <div className="w-full h-40 flex items-center justify-center bg-gray-50 text-gray-400 text-sm">
                    {job.status === 'requested' ? 'awaiting generation' : 'no image'}
                  </div>
                )}

                <div className="p-3 flex-1 flex flex-col">
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <h3 className="text-sm font-medium text-gray-900 line-clamp-2">
                      {job.tool_title || job.cgspace_id}
                    </h3>
                    <span
                      className={`shrink-0 text-xs px-2 py-0.5 rounded-full font-medium ${
                        STATUS_STYLES[job.status] || 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {job.status}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 mb-2">{job.cgspace_id}</p>
                  {job.cost_usd != null && (
                    <p className="text-xs text-gray-500 mb-2">
                      cost ${job.cost_usd.toFixed(4)}
                    </p>
                  )}
                  {job.error && (
                    <p className="text-xs text-red-600 mb-2 line-clamp-2">{job.error}</p>
                  )}

                  {/* Actions */}
                  <div className="mt-auto flex items-center gap-2 pt-2">
                    {(job.status === 'staged' || job.status === 'failed') && (
                      <button
                        onClick={() =>
                          act(job.cgspace_id, approveThumbnail, 'Thumbnail approved — promoting to live.')
                        }
                        disabled={isBusy || job.status === 'failed'}
                        className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-white bg-green-600 rounded hover:bg-green-700 disabled:opacity-40"
                      >
                        <Check size={13} /> Approve
                      </button>
                    )}
                    {job.status !== 'rejected' && (
                      <button
                        onClick={() =>
                          act(job.cgspace_id, rejectThumbnail, 'Thumbnail rejected.')
                        }
                        disabled={isBusy}
                        className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-red-600 bg-red-50 rounded hover:bg-red-100 disabled:opacity-40"
                      >
                        <X size={13} /> Reject
                      </button>
                    )}
                    <button
                      onClick={() =>
                        act(job.cgspace_id, regenerateThumbnail, 'Re-enqueued for regeneration.')
                      }
                      disabled={isBusy}
                      className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-gray-600 bg-gray-100 rounded hover:bg-gray-200 disabled:opacity-40"
                    >
                      <RefreshCw size={13} /> Regenerate
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
