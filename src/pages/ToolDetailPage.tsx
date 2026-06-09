import { useParams, Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, MapPin, CheckCircle2, Globe, Calendar, Building2, ExternalLink, Sparkles } from 'lucide-react'
import { Navbar } from '@/components/app/Navbar'
import { Footer } from '@/components/app/Footer'
import { TypeBadge } from '@/components/app/TypeBadge'
import { TagPill } from '@/components/app/TagPill'
import { ItemCard } from '@/components/app/ItemCard'
import { getItemById, getRelatedItems } from '@/data/items'
import type { Tool } from '@/data/items'

export function ToolDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const item = id ? getItemById(id) : undefined

  if (!item || item.kind !== 'tool') {
    return (
      <div className="min-h-screen flex flex-col">
        <Navbar />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <h2 className="text-xl font-bold text-[#1A1A2E] mb-2">Tool not found</h2>
            <Link to="/explore" className="text-[#00524D] text-sm font-medium hover:underline">
              Back to Explorer
            </Link>
          </div>
        </div>
        <Footer />
      </div>
    )
  }

  const tool = item as Tool
  const related = getRelatedItems(tool.relatedIds)

  function handleTagClick(tag: string) {
    navigate(`/explore?pillar=${encodeURIComponent(tag)}`)
  }

  return (
    <div className="min-h-screen flex flex-col bg-[#F8F9FA]">
      <Navbar />

      {/* Breadcrumb */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-3">
          <nav className="flex items-center gap-2 text-xs text-[#4A5568]">
            <Link to="/" className="hover:text-[#00524D] transition-colors">Home</Link>
            <span className="text-gray-300">/</span>
            <Link to="/explore" className="hover:text-[#00524D] transition-colors">Explore</Link>
            <span className="text-gray-300">/</span>
            <span className="text-[#1A1A2E] font-medium truncate max-w-48">{tool.title}</span>
          </nav>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8 w-full flex-1">
        <div className="flex gap-8 items-start">
          {/* Main content */}
          <div className="flex-1 min-w-0">
            <Link
              to="/explore"
              className="inline-flex items-center gap-1.5 text-sm text-[#4A5568] hover:text-[#00524D] transition-colors mb-6"
            >
              <ArrowLeft size={14} />
              Back to Explorer
            </Link>

            {/* Header */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-8 mb-6">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-4">
                    <TypeBadge type={tool.type} />
                    <span className="text-xs text-gray-400 flex items-center gap-1">
                      <Calendar size={11} />
                      {tool.year}
                    </span>
                    <span className="text-xs text-gray-400 flex items-center gap-1">
                      <Building2 size={11} />
                      {tool.source}
                    </span>
                  </div>
                  <h1 className="text-2xl font-extrabold text-[#1A1A2E] mb-3 leading-tight">
                    {tool.title}
                  </h1>
                  <p className="text-[#4A5568] text-base leading-relaxed mb-4">
                    {tool.description}
                  </p>
                  {tool.authors.length > 0 && (
                    <p className="text-xs text-gray-400 mb-5">
                      By: {tool.authors.join(', ')}
                    </p>
                  )}
                  <div className="flex flex-wrap gap-2">
                    {[...tool.pillars, ...tool.enablers, tool.stage].map(tag => (
                      <TagPill key={tag} label={tag} onClick={() => handleTagClick(tag)} />
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* AI Summary */}
            {tool.aiSummary && (
              <div className="bg-gradient-to-r from-[#E0F5F0] to-[#F0FDF9] rounded-xl border border-[#B2DDD4] p-6 mb-6">
                <div className="flex items-center gap-2 mb-3">
                  <Sparkles size={16} className="text-[#00524D]" />
                  <h3 className="text-sm font-bold text-[#00524D]">AI Summary</h3>
                </div>
                <p className="text-sm text-[#1A1A2E] leading-relaxed">{tool.aiSummary}</p>
              </div>
            )}

            {/* Full description */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-8 mb-6">
              <div className="flex items-center gap-2 mb-5">
                <div className="w-1 h-6 bg-[#00524D] rounded-full" />
                <h2 className="text-lg font-bold text-[#1A1A2E]">Overview</h2>
              </div>
              <div className="space-y-4">
                {tool.fullDescription.map((para, i) => (
                  <p key={i} className="text-sm text-[#4A5568] leading-relaxed">{para}</p>
                ))}
              </div>
            </div>

            {/* Key features */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-8 mb-6">
              <div className="flex items-center gap-2 mb-5">
                <div className="w-1 h-6 bg-[#16A34A] rounded-full" />
                <h2 className="text-lg font-bold text-[#1A1A2E]">Key Features</h2>
              </div>
              <ul className="space-y-3">
                {tool.keyFeatures.map((feat, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <CheckCircle2 size={16} className="text-[#16A34A] mt-0.5 flex-shrink-0" />
                    <span className="text-sm text-[#4A5568] leading-relaxed">{feat}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* How to use */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-8 mb-8">
              <div className="flex items-center gap-2 mb-5">
                <div className="w-1 h-6 bg-[#6B21A8] rounded-full" />
                <h2 className="text-lg font-bold text-[#1A1A2E]">How to Use</h2>
              </div>
              <ol className="space-y-4">
                {tool.howToUse.map((step, i) => (
                  <li key={i} className="flex items-start gap-4">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-[#F3E8FF] text-[#6B21A8] text-xs font-bold flex items-center justify-center">
                      {i + 1}
                    </span>
                    <span className="text-sm text-[#4A5568] leading-relaxed">{step}</span>
                  </li>
                ))}
              </ol>
            </div>

            {/* Related tools */}
            {related.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-5">
                  <div className="w-1 h-6 bg-[#007A72] rounded-full" />
                  <h2 className="text-lg font-bold text-[#1A1A2E]">Related Tools</h2>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {related.map(r => (
                    <ItemCard key={r.id} item={r} />
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="w-64 flex-shrink-0 space-y-5 hidden lg:block">
            {/* Source & URL */}
            {tool.url && (
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
                <h3 className="text-xs font-semibold text-[#4A5568] uppercase tracking-wide mb-3">Source</h3>
                <p className="text-sm font-medium text-[#1A1A2E] mb-2">{tool.source}</p>
                <a
                  href={tool.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-[#00524D] font-medium hover:underline"
                >
                  <ExternalLink size={11} />
                  View original resource
                </a>
              </div>
            )}

            {/* Stage */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
              <h3 className="text-xs font-semibold text-[#4A5568] uppercase tracking-wide mb-3">Development Stage</h3>
              <TagPill label={tool.stage} />
            </div>

            {/* Type */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
              <h3 className="text-xs font-semibold text-[#4A5568] uppercase tracking-wide mb-3">Type</h3>
              <TypeBadge type={tool.type} />
            </div>

            {/* Pillars */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
              <h3 className="text-xs font-semibold text-[#4A5568] uppercase tracking-wide mb-3">Pillars</h3>
              <div className="flex flex-wrap gap-2">
                {tool.pillars.map(a => (
                  <TagPill key={a} label={a} onClick={() => handleTagClick(a)} />
                ))}
              </div>
            </div>

            {/* Enablers */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
              <h3 className="text-xs font-semibold text-[#4A5568] uppercase tracking-wide mb-3">Enablers</h3>
              <div className="flex flex-wrap gap-2">
                {tool.enablers.map(a => (
                  <TagPill key={a} label={a} onClick={() => handleTagClick(a)} />
                ))}
              </div>
            </div>

            {/* SDGs */}
            {tool.sdgs.length > 0 && (
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
                <h3 className="text-xs font-semibold text-[#4A5568] uppercase tracking-wide mb-3">SDG Alignment</h3>
                <div className="flex flex-wrap gap-1.5">
                  {tool.sdgs.map(sdg => (
                    <span key={sdg} className="inline-flex items-center px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 text-[10px] font-medium">
                      {sdg}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Countries */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
              <h3 className="text-xs font-semibold text-[#4A5568] uppercase tracking-wide mb-3">
                <span className="flex items-center gap-1">
                  <Globe size={12} />
                  Countries Applied
                </span>
              </h3>
              <ul className="space-y-1.5">
                {tool.countries.map(c => (
                  <li key={c} className="flex items-center gap-1.5 text-xs text-[#4A5568]">
                    <MapPin size={10} className="text-[#00524D] flex-shrink-0" />
                    {c}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>

      <Footer />
    </div>
  )
}
