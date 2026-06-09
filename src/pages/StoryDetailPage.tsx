import { useParams, Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, MapPin, CheckCircle2, Lightbulb, Calendar, Building2, Tag } from 'lucide-react'
import { Navbar } from '@/components/app/Navbar'
import { Footer } from '@/components/app/Footer'
import { TagPill } from '@/components/app/TagPill'
import { ItemCard } from '@/components/app/ItemCard'
import { getItemById, getRelatedItems } from '@/data/items'
import type { Story } from '@/data/items'

export function StoryDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const item = id ? getItemById(id) : undefined

  if (!item || item.kind !== 'story') {
    return (
      <div className="min-h-screen flex flex-col">
        <Navbar />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <h2 className="text-xl font-bold text-[#1A1A2E] mb-2">Story not found</h2>
            <Link to="/explore" className="text-[#00524D] text-sm font-medium hover:underline">
              Back to Explorer
            </Link>
          </div>
        </div>
        <Footer />
      </div>
    )
  }

  const story = item as Story
  const related = getRelatedItems(story.relatedIds)

  function handleTagClick(tag: string) {
    navigate(`/explore?pillar=${encodeURIComponent(tag)}`)
  }

  return (
    <div className="min-h-screen flex flex-col bg-[#F8F9FA]">
      <Navbar />

      {/* Hero image */}
      <div className="relative h-72 md:h-96 overflow-hidden">
        <img
          src={story.image}
          alt={story.title}
          className="w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/75 via-black/40 to-black/10" />
        <div className="absolute inset-0 flex items-end">
          <div className="max-w-7xl mx-auto px-6 pb-10 w-full">
            <nav className="flex items-center gap-2 text-xs text-white/70 mb-4">
              <Link to="/" className="hover:text-white transition-colors">Home</Link>
              <span>/</span>
              <Link to="/explore" className="hover:text-white transition-colors">Explore</Link>
              <span>/</span>
              <span className="text-white font-medium truncate max-w-48">{story.title}</span>
            </nav>
            <span className="inline-flex items-center rounded-md px-2 py-0.5 text-[10px] font-bold tracking-widest uppercase bg-white/20 text-white backdrop-blur-sm border border-white/30 mb-3">
              STORY & CASE
            </span>
            <h1 className="text-2xl md:text-3xl font-extrabold text-white leading-tight mb-2">
              {story.title}
            </h1>
            <p className="text-white/80 text-sm">{story.subtitle}</p>
          </div>
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

            {/* Metadata bar */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 mb-6 flex items-center justify-between flex-wrap gap-4">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <MapPin size={16} className="text-[#00524D]" />
                  <span className="text-sm font-semibold text-[#1A1A2E]">{story.region}</span>
                </div>
                <div className="flex items-center gap-1.5 text-xs text-gray-400">
                  <Calendar size={12} />
                  {story.year}
                </div>
                <div className="flex items-center gap-1.5 text-xs text-gray-400">
                  <Building2 size={12} />
                  {story.source}
                </div>
                {story.innovationType && (
                  <div className="flex items-center gap-1.5 text-xs text-gray-400">
                    <Tag size={12} />
                    {story.innovationType}
                  </div>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                {[...story.pillars, ...story.enablers].map(tag => (
                  <TagPill key={tag} label={tag} onClick={() => handleTagClick(tag)} />
                ))}
              </div>
            </div>

            {/* Full narrative */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-8 mb-6">
              <div className="flex items-center gap-2 mb-5">
                <div className="w-1 h-6 bg-[#00524D] rounded-full" />
                <h2 className="text-lg font-bold text-[#1A1A2E]">The Story</h2>
              </div>
              <div className="space-y-4">
                {story.fullNarrative.map((para, i) => (
                  <p key={i} className="text-sm text-[#4A5568] leading-relaxed">{para}</p>
                ))}
              </div>
            </div>

            {/* Key outcomes */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-8 mb-6">
              <div className="flex items-center gap-2 mb-5">
                <div className="w-1 h-6 bg-[#16A34A] rounded-full" />
                <h2 className="text-lg font-bold text-[#1A1A2E]">Key Outcomes</h2>
              </div>
              <ul className="space-y-3">
                {story.keyOutcomes.map((outcome, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <CheckCircle2 size={16} className="text-[#16A34A] mt-0.5 flex-shrink-0" />
                    <span className="text-sm text-[#4A5568] leading-relaxed">{outcome}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Lessons learned */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-8 mb-8">
              <div className="flex items-center gap-2 mb-5">
                <div className="w-1 h-6 bg-[#6B21A8] rounded-full" />
                <h2 className="text-lg font-bold text-[#1A1A2E]">Lessons Learned</h2>
              </div>
              <ul className="space-y-4">
                {story.lessonsLearned.map((lesson, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <Lightbulb size={16} className="text-[#6B21A8] mt-0.5 flex-shrink-0" />
                    <span className="text-sm text-[#4A5568] leading-relaxed">{lesson}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Related */}
            {related.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-5">
                  <div className="w-1 h-6 bg-[#007A72] rounded-full" />
                  <h2 className="text-lg font-bold text-[#1A1A2E]">Related Stories</h2>
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
            {/* Quick stats */}
            <div className="bg-gradient-to-br from-[#00524D] to-[#007A72] rounded-xl p-5 text-white">
              <h3 className="text-xs font-semibold text-white/70 uppercase tracking-wide mb-4">At a Glance</h3>
              <div className="space-y-3">
                <div>
                  <div className="text-xl font-extrabold">{story.keyOutcomes.length}</div>
                  <div className="text-white/70 text-xs">Key outcomes documented</div>
                </div>
                <div className="border-t border-white/20 pt-3">
                  <div className="text-xl font-extrabold">{story.lessonsLearned.length}</div>
                  <div className="text-white/70 text-xs">Lessons learned</div>
                </div>
                <div className="border-t border-white/20 pt-3">
                  <div className="text-xl font-extrabold">{story.countries.length}</div>
                  <div className="text-white/70 text-xs">Countries</div>
                </div>
              </div>
            </div>

            {/* Region & Countries */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
              <h3 className="text-xs font-semibold text-[#4A5568] uppercase tracking-wide mb-3">Region & Countries</h3>
              <div className="flex items-center gap-2 mb-3">
                <MapPin size={14} className="text-[#00524D]" />
                <span className="text-sm font-medium text-[#1A1A2E]">{story.region}</span>
              </div>
              <ul className="space-y-1.5">
                {story.countries.map(c => (
                  <li key={c} className="flex items-center gap-1.5 text-xs text-[#4A5568]">
                    <MapPin size={10} className="text-[#00524D] flex-shrink-0" />
                    {c}
                  </li>
                ))}
              </ul>
            </div>

            {/* Innovation Type */}
            {story.innovationType && (
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
                <h3 className="text-xs font-semibold text-[#4A5568] uppercase tracking-wide mb-3">Innovation Type</h3>
                <span className="inline-flex items-center px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 text-xs font-medium">
                  {story.innovationType}
                </span>
              </div>
            )}

            {/* Authors */}
            {story.authors.length > 0 && (
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
                <h3 className="text-xs font-semibold text-[#4A5568] uppercase tracking-wide mb-3">Authors</h3>
                <ul className="space-y-1.5">
                  {story.authors.map(a => (
                    <li key={a} className="text-xs text-[#4A5568]">{a}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Pillars */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
              <h3 className="text-xs font-semibold text-[#4A5568] uppercase tracking-wide mb-3">Pillars</h3>
              <div className="flex flex-wrap gap-2">
                {story.pillars.map(a => (
                  <TagPill key={a} label={a} onClick={() => handleTagClick(a)} />
                ))}
              </div>
            </div>

            {/* Enablers */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
              <h3 className="text-xs font-semibold text-[#4A5568] uppercase tracking-wide mb-3">Enablers</h3>
              <div className="flex flex-wrap gap-2">
                {story.enablers.map(a => (
                  <TagPill key={a} label={a} onClick={() => handleTagClick(a)} />
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      <Footer />
    </div>
  )
}
