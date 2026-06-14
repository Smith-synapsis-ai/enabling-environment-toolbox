import { useState, useEffect, useCallback, useRef } from 'react';
import {
  BarChart3,
  Wrench,
  Users,
  LogOut,
  LayoutDashboard,
  Coins,
  ShieldCheck,
  Image as ImageIcon,
} from 'lucide-react';
import {
  fetchAdminTools,
  createTool,
  updateTool,
  deleteTool,
} from '../services/api';
import { adminLogin } from '../services/analytics';
import type { ToolDetail, ToolCreate, AdminToolsResponse } from '../types';
import { PILLARS, DOMAINS, TYPES, STAGES, TARGET_USERS, GEOGRAPHIES } from '../types';
import AnalyticsDashboard from '../components/admin/AnalyticsDashboard';
import SessionExplorer from '../components/admin/SessionExplorer';
import OverviewPanel from '../components/admin/OverviewPanel';
import TokenUsagePanel from '../components/admin/TokenUsagePanel';
import GovernanceQueue from '../components/admin/GovernanceQueue';
import ThumbnailsPanel from '../components/admin/ThumbnailsPanel';

// ---------------------------------------------------------------------------
// Tab definition
// ---------------------------------------------------------------------------

const TABS = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'dashboard', label: 'Analytics', icon: BarChart3 },
  { id: 'tokens', label: 'Token Usage', icon: Coins },
  { id: 'governance', label: 'Governance', icon: ShieldCheck },
  { id: 'thumbnails', label: 'Thumbnails', icon: ImageIcon },
  { id: 'tools', label: 'Tools', icon: Wrench },
  { id: 'sessions', label: 'Sessions', icon: Users },
] as const;

type TabId = (typeof TABS)[number]['id'];

// ---------------------------------------------------------------------------
// LoginForm
// ---------------------------------------------------------------------------

function LoginForm({ onLogin }: { onLogin: () => void }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const { token } = await adminLogin(username, password);
      localStorage.setItem('admin-token', token);
      onLogin();
    } catch {
      setError('Invalid credentials');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <form
        onSubmit={handleSubmit}
        className="bg-white shadow-lg rounded-lg p-8 w-full max-w-sm space-y-4"
      >
        <h1 className="text-2xl font-bold text-cgiar-dark text-center">Admin Login</h1>
        {error && (
          <div className="bg-red-50 text-red-700 px-3 py-2 rounded text-sm">{error}</div>
        )}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
          <input
            type="text"
            value={username}
            onChange={e => setUsername(e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cgiar-accent"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cgiar-accent"
            required
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-cgiar-dark text-white py-2 rounded-md font-medium hover:bg-cgiar-dark/90 transition-colors disabled:opacity-50"
        >
          {loading ? 'Logging in...' : 'Log In'}
        </button>
      </form>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ToolModal (Create / Edit)
// ---------------------------------------------------------------------------

const EMPTY_TOOL: ToolCreate = {
  title: '',
  summary: '',
  what_it_does: '',
  when_to_use_it: '',
  who_its_for: '',
  type: '',
  stage: '',
  pillars: [],
  domains: [],
  target_users: [],
  geography: [],
  authors: [],
  date_published: '',
  source_url: '',
  source_organization: '',
  cgspace_id: '',
  is_visible: true,
};

function ToolModal({
  tool,
  onSave,
  onClose,
}: {
  tool: ToolDetail | null; // null = create mode
  onSave: (data: ToolCreate, id?: string) => Promise<void>;
  onClose: () => void;
}) {
  const isEdit = tool !== null;
  const modalRef = useRef<HTMLDivElement>(null);

  // Escape key to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const [form, setForm] = useState<ToolCreate>(() => {
    if (!tool) return { ...EMPTY_TOOL };
    return {
      title: tool.title,
      summary: tool.summary || '',
      what_it_does: tool.what_it_does || '',
      when_to_use_it: tool.when_to_use_it || '',
      who_its_for: tool.who_its_for || '',
      type: tool.type || '',
      stage: tool.stage || '',
      pillars: tool.pillars || [],
      domains: tool.domains || [],
      target_users: tool.target_users || [],
      geography: tool.geography || [],
      authors: tool.authors || [],
      date_published: tool.date_published || '',
      source_url: tool.source_url || '',
      source_organization: tool.source_organization || '',
      cgspace_id: tool.cgspace_id || '',
      is_visible: tool.is_visible,
    };
  });

  const [authorsText, setAuthorsText] = useState(
    (form.authors || []).join(', ')
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (field: keyof ToolCreate, value: unknown) => {
    setForm(prev => ({ ...prev, [field]: value }));
  };

  const toggleArrayItem = (field: keyof ToolCreate, item: string) => {
    setForm(prev => {
      const arr = (prev[field] as string[]) || [];
      const next = arr.includes(item)
        ? arr.filter(x => x !== item)
        : [...arr, item];
      return { ...prev, [field]: next };
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title.trim()) {
      setError('Title is required');
      return;
    }
    setError('');
    setSaving(true);
    try {
      const payload: ToolCreate = {
        ...form,
        authors: authorsText
          .split(',')
          .map(a => a.trim())
          .filter(Boolean),
        date_published: form.date_published || undefined,
      };
      await onSave(payload, isEdit ? tool.id : undefined);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/50 flex items-start justify-center overflow-y-auto py-8"
      role="dialog"
      aria-modal="true"
      aria-label={isEdit ? 'Edit tool' : 'Add new tool'}
      ref={modalRef}
    >
      <form
        onSubmit={handleSubmit}
        className="bg-white rounded-lg shadow-xl w-full max-w-3xl mx-4 p-6 space-y-5"
      >
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-cgiar-dark">
            {isEdit ? 'Edit Tool' : 'Add New Tool'}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl leading-none"
            aria-label="Close dialog"
          >
            &times;
          </button>
        </div>

        {error && (
          <div className="bg-red-50 text-red-700 px-3 py-2 rounded text-sm">{error}</div>
        )}

        {/* Title */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Title <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={form.title}
            onChange={e => handleChange('title', e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cgiar-accent"
            required
          />
        </div>

        {/* Summary */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Summary</label>
          <textarea
            rows={3}
            value={form.summary || ''}
            onChange={e => handleChange('summary', e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cgiar-accent"
          />
        </div>

        {/* What it does */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">What it does</label>
          <textarea
            rows={3}
            value={form.what_it_does || ''}
            onChange={e => handleChange('what_it_does', e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cgiar-accent"
          />
        </div>

        {/* When to use it */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">When to use it</label>
          <textarea
            rows={3}
            value={form.when_to_use_it || ''}
            onChange={e => handleChange('when_to_use_it', e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cgiar-accent"
          />
        </div>

        {/* Who it's for */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Who it's for</label>
          <textarea
            rows={3}
            value={form.who_its_for || ''}
            onChange={e => handleChange('who_its_for', e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cgiar-accent"
          />
        </div>

        {/* Type + Stage row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
            <select
              value={form.type || ''}
              onChange={e => handleChange('type', e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cgiar-accent"
            >
              <option value="">-- Select --</option>
              {TYPES.map(t => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Stage</label>
            <select
              value={form.stage || ''}
              onChange={e => handleChange('stage', e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cgiar-accent"
            >
              <option value="">-- Select --</option>
              {STAGES.map(s => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Pillars */}
        <fieldset>
          <legend className="text-sm font-medium text-gray-700 mb-2">Pillars</legend>
          <div className="flex flex-wrap gap-3">
            {PILLARS.map(p => (
              <label key={p} className="flex items-center gap-1.5 text-sm">
                <input
                  type="checkbox"
                  checked={(form.pillars || []).includes(p)}
                  onChange={() => toggleArrayItem('pillars', p)}
                  className="rounded border-gray-300 text-cgiar-accent focus:ring-cgiar-accent"
                />
                {p}
              </label>
            ))}
          </div>
        </fieldset>

        {/* Domains */}
        <fieldset>
          <legend className="text-sm font-medium text-gray-700 mb-2">Domains</legend>
          <div className="flex flex-wrap gap-3">
            {DOMAINS.map(d => (
              <label key={d} className="flex items-center gap-1.5 text-sm">
                <input
                  type="checkbox"
                  checked={(form.domains || []).includes(d)}
                  onChange={() => toggleArrayItem('domains', d)}
                  className="rounded border-gray-300 text-cgiar-accent focus:ring-cgiar-accent"
                />
                {d}
              </label>
            ))}
          </div>
        </fieldset>

        {/* Target Users */}
        <fieldset>
          <legend className="text-sm font-medium text-gray-700 mb-2">Target Users</legend>
          <div className="flex flex-wrap gap-3">
            {TARGET_USERS.map(u => (
              <label key={u} className="flex items-center gap-1.5 text-sm">
                <input
                  type="checkbox"
                  checked={(form.target_users || []).includes(u)}
                  onChange={() => toggleArrayItem('target_users', u)}
                  className="rounded border-gray-300 text-cgiar-accent focus:ring-cgiar-accent"
                />
                {u}
              </label>
            ))}
          </div>
        </fieldset>

        {/* Geography */}
        <fieldset>
          <legend className="text-sm font-medium text-gray-700 mb-2">Geography</legend>
          <div className="flex flex-wrap gap-3">
            {GEOGRAPHIES.map(g => (
              <label key={g} className="flex items-center gap-1.5 text-sm">
                <input
                  type="checkbox"
                  checked={(form.geography || []).includes(g)}
                  onChange={() => toggleArrayItem('geography', g)}
                  className="rounded border-gray-300 text-cgiar-accent focus:ring-cgiar-accent"
                />
                {g}
              </label>
            ))}
          </div>
        </fieldset>

        {/* Authors */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Authors <span className="text-gray-500 text-xs">(comma-separated)</span>
          </label>
          <input
            type="text"
            value={authorsText}
            onChange={e => setAuthorsText(e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cgiar-accent"
            placeholder="Author 1, Author 2"
          />
        </div>

        {/* Date Published */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Date Published</label>
          <input
            type="date"
            value={form.date_published || ''}
            onChange={e => handleChange('date_published', e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cgiar-accent"
          />
        </div>

        {/* Source URL + Source Organization */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Source URL</label>
            <input
              type="text"
              value={form.source_url || ''}
              onChange={e => handleChange('source_url', e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cgiar-accent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Source Organization
            </label>
            <input
              type="text"
              value={form.source_organization || ''}
              onChange={e => handleChange('source_organization', e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cgiar-accent"
            />
          </div>
        </div>

        {/* CGSpace ID */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">CGSpace ID</label>
          <input
            type="text"
            value={form.cgspace_id || ''}
            onChange={e => handleChange('cgspace_id', e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cgiar-accent"
          />
        </div>

        {/* Is Visible */}
        <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
          <input
            type="checkbox"
            checked={form.is_visible ?? true}
            onChange={e => handleChange('is_visible', e.target.checked)}
            className="rounded border-gray-300 text-cgiar-accent focus:ring-cgiar-accent"
          />
          Visible (published)
        </label>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 pt-2 border-t border-gray-200">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving}
            className="px-4 py-2 text-sm font-medium text-white bg-cgiar-dark rounded-md hover:bg-cgiar-dark/90 transition-colors disabled:opacity-50"
          >
            {saving ? 'Saving...' : isEdit ? 'Update Tool' : 'Create Tool'}
          </button>
        </div>
      </form>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ToolsPanel — the existing tool CRUD table, extracted for the Tools tab
// ---------------------------------------------------------------------------

function ToolsPanel({ onLogout }: { onLogout: () => void }) {
  const [data, setData] = useState<AdminToolsResponse | null>(null);
  const [page, setPage] = useState(1);
  const [keyword, setKeyword] = useState('');
  const [sortBy, setSortBy] = useState('title');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [feedback, setFeedback] = useState('');

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [editingTool, setEditingTool] = useState<ToolDetail | null>(null);

  const PAGE_SIZE = 50;

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const result = await fetchAdminTools({
        page,
        page_size: PAGE_SIZE,
        keyword: keyword || undefined,
        sort_by: sortBy,
      });
      setData(result);
    } catch (err: unknown) {
      if (err instanceof Error && err.message.includes('401')) {
        // Token expired or invalid
        localStorage.removeItem('admin-token');
        onLogout();
        return;
      }
      setError(err instanceof Error ? err.message : 'Failed to load tools');
    } finally {
      setLoading(false);
    }
  }, [page, keyword, sortBy, onLogout]);

  useEffect(() => {
    load();
  }, [load]);

  const handleSave = async (formData: ToolCreate, id?: string) => {
    if (id) {
      await updateTool(id, formData);
    } else {
      await createTool(formData);
    }
    setModalOpen(false);
    setEditingTool(null);
    setFeedback(id ? 'Tool updated successfully' : 'Tool created successfully');
    setTimeout(() => setFeedback(''), 3000);
    await load();
  };

  const handleDelete = async (tool: ToolDetail) => {
    if (!window.confirm(`Delete "${tool.title}"? This cannot be undone.`)) return;
    try {
      await deleteTool(tool.id);
      setFeedback('Tool deleted');
      setTimeout(() => setFeedback(''), 3000);
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Delete failed');
    }
  };

  const openCreate = () => {
    setEditingTool(null);
    setModalOpen(true);
  };

  const openEdit = (tool: ToolDetail) => {
    setEditingTool(tool);
    setModalOpen(true);
  };

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div className="space-y-4">
      {/* Feedback */}
      {feedback && (
        <div className="bg-green-50 text-green-700 px-4 py-2 rounded text-sm">
          {feedback}
        </div>
      )}
      {error && (
        <div className="bg-red-50 text-red-700 px-4 py-2 rounded text-sm">{error}</div>
      )}

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3">
        <input
          type="text"
          placeholder="Search tools..."
          value={keyword}
          onChange={e => {
            setKeyword(e.target.value);
            setPage(1);
          }}
          className="border border-gray-300 rounded-md px-3 py-2 text-sm w-full sm:w-64 focus:outline-none focus:ring-2 focus:ring-cgiar-accent"
          aria-label="Search tools"
        />
        <select
          value={sortBy}
          onChange={e => {
            setSortBy(e.target.value);
            setPage(1);
          }}
          className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cgiar-accent"
          aria-label="Sort tools by"
        >
          <option value="title">Sort by Title</option>
          <option value="date">Sort by Date</option>
          <option value="type">Sort by Type</option>
        </select>
        <button
          onClick={openCreate}
          className="ml-auto px-4 py-2 text-sm font-medium text-white bg-cgiar-dark rounded-md hover:bg-cgiar-dark/90 transition-colors"
        >
          + Add New Tool
        </button>
      </div>

      {/* Table */}
      {loading && !data ? (
        <div className="text-center text-gray-500 py-12">Loading...</div>
      ) : data && data.tools.length > 0 ? (
        <div className="bg-white rounded-lg shadow overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Title
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Stage
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Pillars
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Published
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Visible
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {data.tools.map(tool => (
                <tr
                  key={tool.id}
                  className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => openEdit(tool)}
                >
                  <td className="px-4 py-3 text-sm text-gray-900 max-w-xs truncate">
                    {tool.title}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">{tool.type || '-'}</td>
                  <td className="px-4 py-3 text-sm text-gray-600 max-w-[160px] truncate">
                    {tool.stage || '-'}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {(tool.pillars || []).map(p => (
                        <span
                          key={p}
                          className="inline-block bg-cgiar-accent/15 text-cgiar-dark text-xs px-2 py-0.5 rounded-full"
                        >
                          {p.length > 20 ? p.slice(0, 18) + '...' : p}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {tool.date_published || '-'}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {tool.is_visible ? (
                      <span className="text-green-600 font-medium">Yes</span>
                    ) : (
                      <span className="text-red-500 font-medium">No</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={e => {
                        e.stopPropagation();
                        handleDelete(tool);
                      }}
                      className="text-red-500 hover:text-red-700 text-sm font-medium"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="text-center text-gray-500 py-12">No tools found.</div>
      )}

      {/* Pagination */}
      {data && totalPages > 0 && (
        <div className="flex items-center justify-between mt-4 text-sm text-gray-600">
          <span>
            Page {data.page} of {totalPages} &middot; Total tools: {data.total}
          </span>
          <div className="flex gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage(p => p - 1)}
              className="px-3 py-1 border border-gray-300 rounded-md disabled:opacity-40 hover:bg-gray-100"
            >
              Previous
            </button>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage(p => p + 1)}
              className="px-3 py-1 border border-gray-300 rounded-md disabled:opacity-40 hover:bg-gray-100"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Modal */}
      {modalOpen && (
        <ToolModal
          tool={editingTool}
          onSave={handleSave}
          onClose={() => {
            setModalOpen(false);
            setEditingTool(null);
          }}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// AdminPanel (main authenticated view — tabbed layout)
// ---------------------------------------------------------------------------

function AdminPanel({ onLogout }: { onLogout: () => void }) {
  const [activeTab, setActiveTab] = useState<TabId>('overview');

  return (
    <div className="min-h-screen bg-gray-50 pt-20 pb-10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Top bar */}
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-cgiar-dark">Admin Panel</h1>
          <button
            onClick={onLogout}
            className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
          >
            <LogOut size={14} />
            Logout
          </button>
        </div>

        {/* Tab navigation */}
        <div className="flex gap-1 bg-gray-100 rounded-lg p-1 mb-6">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'bg-cgiar-dark text-white shadow-sm'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-200'
              }`}
            >
              <tab.icon size={16} />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {activeTab === 'overview' && <OverviewPanel />}
        {activeTab === 'dashboard' && <AnalyticsDashboard />}
        {activeTab === 'tokens' && <TokenUsagePanel />}
        {activeTab === 'governance' && <GovernanceQueue />}
        {activeTab === 'thumbnails' && <ThumbnailsPanel />}
        {activeTab === 'tools' && <ToolsPanel onLogout={onLogout} />}
        {activeTab === 'sessions' && <SessionExplorer />}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// AdminPage (entry point — handles auth state)
// ---------------------------------------------------------------------------

export default function AdminPage() {
  const [authenticated, setAuthenticated] = useState(
    () => !!localStorage.getItem('admin-token')
  );

  const handleLogout = useCallback(() => {
    localStorage.removeItem('admin-token');
    setAuthenticated(false);
  }, []);

  if (!authenticated) {
    return <LoginForm onLogin={() => setAuthenticated(true)} />;
  }

  return <AdminPanel onLogout={handleLogout} />;
}
