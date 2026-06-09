import { useState, useMemo, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Search, X, Filter, ArrowUpDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Navbar } from '@/components/app/Navbar'
import { Footer } from '@/components/app/Footer'
import { ItemCard } from '@/components/app/ItemCard'
import { WorldMap } from '@/components/app/WorldMap'
import { PILLARS, ENABLERS, REGIONS, STAGES, TYPES, SOURCES } from '@/lib/constants'
import { tools, stories, allItems } from '@/data/items'

type Tab = 'all' | 'tools' | 'stories'
type SortOption = 'relevance' | 'newest' | 'az'

export function ExplorePage() {
  const [searchParams] = useSearchParams()

  const [query, setQuery] = useState('')
  const [activeTab, setActiveTab] = useState<Tab>('all')
  const [selectedRegion, setSelectedRegion] = useState<string>('All regions')
  const [activePillars, setActivePillars] = useState<string[]>([])
  const [activeEnablers, setActiveEnablers] = useState<string[]>([])
  const [selectedStage, setSelectedStage] = useState<string>('All stages')
  const [selectedType, setSelectedType] = useState<string>('All types')
  const [selectedSource, setSelectedSource] = useState<string>('All sources')
  const [sortBy, setSortBy] = useState<SortOption>('relevance')
  const [filtersOpen, setFiltersOpen] = useState(false)

  useEffect(() => {
    const p = searchParams.get('pillar')
    const e = searchParams.get('enabler')
    if (p) setActivePillars([p])
    if (e) setActiveEnablers([e])
  }, [])

  function togglePillar(pillar: string) {
    setActivePillars(prev =>
      prev.includes(pillar) ? prev.filter(a => a !== pillar) : [...prev, pillar]
    )
  }

  function toggleEnabler(enabler: string) {
    setActiveEnablers(prev =>
      prev.includes(enabler) ? prev.filter(a => a !== enabler) : [...prev, enabler]
    )
  }

  function handleTagClick(tag: string) {
    if ((PILLARS as readonly string[]).includes(tag)) {
      togglePillar(tag)
    } else if ((ENABLERS as readonly string[]).includes(tag)) {
      toggleEnabler(tag)
    }
  }

  function handleRegionClick(region: string) {
    setSelectedRegion(prev => prev === region ? 'All regions' : region)
  }

  function clearAllFilters() {
    setQuery('')
    setActivePillars([])
    setActiveEnablers([])
    setSelectedRegion('All regions')
    setSelectedStage('All stages')
    setSelectedType('All types')
    setSelectedSource('All sources')
    setSortBy('relevance')
  }

  const hasActiveFilters = query || activePillars.length > 0 || activeEnablers.length > 0 ||
    selectedRegion !== 'All regions' || selectedStage !== 'All stages' || selectedType !== 'All types' || selectedSource !== 'All sources'

  const filteredItems = useMemo(() => {
    let items = activeTab === 'tools'
      ? [...tools]
      : activeTab === 'stories'
      ? [...stories]
      : [...allItems]

    if (query) {
      const q = query.toLowerCase()
      items = items.filter(item =>
        item.title.toLowerCase().includes(q) ||
        item.description.toLowerCase().includes(q) ||
        item.pillars.some(a => a.toLowerCase().includes(q)) ||
        item.enablers.some(a => a.toLowerCase().includes(q)) ||
        (item.kind === 'story' && item.region.toLowerCase().includes(q)) ||
        (item.kind === 'tool' && item.countries.some(c => c.toLowerCase().includes(q)))
      )
    }

    if (activePillars.length > 0) {
      items = items.filter(item =>
        activePillars.some(p => item.pillars.includes(p))
      )
    }

    if (activeEnablers.length > 0) {
      items = items.filter(item =>
        activeEnablers.some(e => item.enablers.includes(e))
      )
    }

    if (selectedRegion !== 'All regions') {
      items = items.filter(item => {
        if (item.kind === 'story') return item.region === selectedRegion
        if (item.kind === 'tool') {
          return item.regions.includes(selectedRegion)
        }
        return true
      })
    }

    if (selectedStage !== 'All stages') {
      items = items.filter(item =>
        item.kind === 'tool' && item.stage === selectedStage
      )
    }

    if (selectedType !== 'All types') {
      items = items.filter(item =>
        item.kind === 'tool' && item.type === selectedType
      )
    }

    if (selectedSource !== 'All sources') {
      items = items.filter(item => {
        if (item.kind === 'tool') return item.source === selectedSource
        if (item.kind === 'story') return item.source === selectedSource
        return true
      })
    }

    // Sort
    if (sortBy === 'newest') {
      items.sort((a, b) => {
        const yearA = 'year' in a ? a.year : 0
        const yearB = 'year' in b ? b.year : 0
        return yearB - yearA
      })
    } else if (sortBy === 'az') {
      items.sort((a, b) => a.title.localeCompare(b.title))
    }

    return items
  }, [query, activeTab, activePillars, activeEnablers, selectedRegion, selectedStage, selectedType, selectedSource, sortBy])

  const toolCount = filteredItems.filter(i => i.kind === 'tool').length
  const storyCount = filteredItems.filter(i => i.kind === 'story').length

  return (
    <div className="min-h-screen flex flex-col bg-[#F8F9FA]">
      <Navbar />

      {/* Page header */}
      <div className="bg-[#00524D] text-white">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <h1 className="text-2xl font-bold mb-1">Enabling Environment Explorer</h1>
          <p className="text-white/75 text-sm">
            Browse tools, approaches, stories, and cases for agricultural innovation enabling environments.
          </p>
        </div>
      </div>

      {/* Search bar */}
      <div className="bg-white border-b border-gray-200 shadow-sm sticky top-16 z-30">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center gap-4">
          <div className="relative flex-1">
            <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Search by keyword, innovation, country, or challenge..."
              className="w-full pl-11 pr-10 py-3 rounded-xl border border-gray-200 bg-gray-50 text-sm text-[#1A1A2E] placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#00524D]/30 focus:border-[#00524D] transition-all"
            />
            {query && (
              <button
                onClick={() => setQuery('')}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <X size={16} />
              </button>
            )}
          </div>
          <div className="hidden md:flex items-center gap-2">
            <ArrowUpDown size={14} className="text-gray-400" />
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value as SortOption)}
              className="px-3 py-2 rounded-lg border border-gray-200 bg-gray-50 text-sm text-[#1A1A2E] focus:outline-none focus:ring-2 focus:ring-[#00524D]/30"
            >
              <option value="relevance">Relevance</option>
              <option value="newest">Newest first</option>
              <option value="az">A-Z</option>
            </select>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8 w-full flex-1">
        {/* Mobile filter toggle */}
        <div className="flex items-center justify-between mb-6 lg:hidden">
          <button
            onClick={() => setFiltersOpen(!filtersOpen)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-200 bg-white text-sm font-medium text-[#4A5568] hover:border-[#00524D]/40"
          >
            <Filter size={14} />
            Filters
            {hasActiveFilters && (
              <span className="w-5 h-5 rounded-full bg-[#00524D] text-white text-[10px] flex items-center justify-center">
                {activePillars.length + activeEnablers.length + (selectedRegion !== 'All regions' ? 1 : 0)}
              </span>
            )}
          </button>
          {hasActiveFilters && (
            <button onClick={clearAllFilters} className="text-xs text-[#00524D] font-medium hover:underline">
              Clear all
            </button>
          )}
        </div>

        <div className="flex gap-8">
          {/* Left sidebar */}
          <div className={cn(
            "w-72 flex-shrink-0 space-y-6",
            "hidden lg:block",
            filtersOpen && "block"
          )}>
            {/* World Map */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-1 h-5 bg-[#00524D] rounded-full" />
                <h3 className="font-semibold text-[#1A1A2E] text-sm">Explore by geography</h3>
              </div>
              <WorldMap
                selectedRegion={selectedRegion !== 'All regions' ? selectedRegion : undefined}
                onRegionClick={handleRegionClick}
              />
            </div>

            {/* Filter panel */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-2">
                  <div className="w-1 h-5 bg-[#6B21A8] rounded-full" />
                  <h3 className="font-semibold text-[#1A1A2E] text-sm">Filter results</h3>
                </div>
                {hasActiveFilters && (
                  <button
                    onClick={clearAllFilters}
                    className="text-xs text-[#6B21A8] font-medium hover:underline"
                  >
                    Clear all
                  </button>
                )}
              </div>

              {/* Region dropdown */}
              <FilterGroup label="Region">
                <select
                  value={selectedRegion}
                  onChange={e => setSelectedRegion(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 bg-gray-50 text-sm text-[#1A1A2E] focus:outline-none focus:ring-2 focus:ring-[#00524D]/30 focus:border-[#00524D]"
                >
                  {REGIONS.map(r => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
              </FilterGroup>

              {/* Pillars */}
              <FilterGroup label="Pillars">
                <div className="flex flex-wrap gap-1.5">
                  {PILLARS.map(pillar => (
                    <button
                      key={pillar}
                      onClick={() => togglePillar(pillar)}
                      className={cn(
                        "px-2.5 py-1 rounded-full text-xs font-medium transition-all duration-150",
                        activePillars.includes(pillar)
                          ? "bg-[#00524D] text-white"
                          : "bg-[#E0F5F0] text-[#00524D] hover:bg-[#B2DDD4]"
                      )}
                    >
                      {pillar}
                    </button>
                  ))}
                </div>
              </FilterGroup>

              {/* Enablers */}
              <FilterGroup label="Enablers">
                <div className="flex flex-wrap gap-1.5">
                  {ENABLERS.map(enabler => (
                    <button
                      key={enabler}
                      onClick={() => toggleEnabler(enabler)}
                      className={cn(
                        "px-2.5 py-1 rounded-full text-xs font-medium transition-all duration-150",
                        activeEnablers.includes(enabler)
                          ? "bg-[#6B21A8] text-white"
                          : "bg-[#F3E8FF] text-[#6B21A8] hover:bg-[#E9D5FF]"
                      )}
                    >
                      {enabler}
                    </button>
                  ))}
                </div>
              </FilterGroup>

              {/* Type dropdown */}
              <FilterGroup label="Type">
                <select
                  value={selectedType}
                  onChange={e => setSelectedType(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 bg-gray-50 text-sm text-[#1A1A2E] focus:outline-none focus:ring-2 focus:ring-[#00524D]/30 focus:border-[#00524D]"
                >
                  <option value="All types">All types</option>
                  {TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </FilterGroup>

              {/* Stage dropdown */}
              <FilterGroup label="Stage">
                <select
                  value={selectedStage}
                  onChange={e => setSelectedStage(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 bg-gray-50 text-sm text-[#1A1A2E] focus:outline-none focus:ring-2 focus:ring-[#00524D]/30 focus:border-[#00524D]"
                >
                  <option value="All stages">All stages</option>
                  {STAGES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </FilterGroup>

              {/* Source dropdown */}
              <FilterGroup label="Source" last>
                <select
                  value={selectedSource}
                  onChange={e => setSelectedSource(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 bg-gray-50 text-sm text-[#1A1A2E] focus:outline-none focus:ring-2 focus:ring-[#00524D]/30 focus:border-[#00524D]"
                >
                  <option value="All sources">All sources</option>
                  {SOURCES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </FilterGroup>
            </div>
          </div>

          {/* Main content */}
          <div className="flex-1 min-w-0">
            {/* Results summary */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm px-5 py-3.5 mb-4 flex items-center justify-between flex-wrap gap-2">
              <p className="text-sm text-[#4A5568]">
                Showing{' '}
                <span className="font-bold text-[#1A1A2E]">{toolCount}</span>{' '}
                tools &amp; approaches
                <span className="mx-2 text-gray-300">|</span>
                <span className="font-bold text-[#1A1A2E]">{storyCount}</span>{' '}
                stories &amp; cases
              </p>
              {hasActiveFilters && (
                <div className="flex items-center gap-2 flex-wrap">
                  {activePillars.map(a => (
                    <ActiveFilterChip key={a} label={a} onRemove={() => togglePillar(a)} />
                  ))}
                  {activeEnablers.map(a => (
                    <ActiveFilterChip key={a} label={a} onRemove={() => toggleEnabler(a)} />
                  ))}
                  {selectedRegion !== 'All regions' && (
                    <ActiveFilterChip label={selectedRegion} onRemove={() => setSelectedRegion('All regions')} />
                  )}
                  {selectedSource !== 'All sources' && (
                    <ActiveFilterChip label={selectedSource} onRemove={() => setSelectedSource('All sources')} />
                  )}
                </div>
              )}
            </div>

            {/* Tab navigation */}
            <div className="flex gap-1 mb-6">
              {([
                { key: 'all', label: 'All', count: filteredItems.length },
                { key: 'tools', label: 'Tools & approaches', count: toolCount },
                { key: 'stories', label: 'Stories & cases', count: storyCount },
              ] as const).map(tab => (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={cn(
                    "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-150",
                    activeTab === tab.key
                      ? "bg-[#00524D] text-white shadow-sm"
                      : "text-[#4A5568] hover:bg-white hover:text-[#1A1A2E] hover:shadow-sm"
                  )}
                >
                  {tab.label}
                  <span className={cn(
                    "inline-flex items-center justify-center rounded-full text-[10px] font-bold w-5 h-5",
                    activeTab === tab.key ? "bg-white/20 text-white" : "bg-gray-200 text-gray-600"
                  )}>
                    {tab.count}
                  </span>
                </button>
              ))}
            </div>

            {/* Results grid */}
            {filteredItems.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-5">
                {filteredItems.map(item => (
                  <ItemCard
                    key={item.id}
                    item={item}
                    onTagClick={handleTagClick}
                  />
                ))}
              </div>
            ) : (
              <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
                <div className="w-14 h-14 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Search size={24} className="text-gray-400" />
                </div>
                <h3 className="font-semibold text-[#1A1A2E] mb-2">No results found</h3>
                <p className="text-sm text-[#4A5568] mb-4">
                  Try adjusting your search or filters to see more results.
                </p>
                <button
                  onClick={clearAllFilters}
                  className="text-sm text-[#00524D] font-medium hover:underline"
                >
                  Clear all filters
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      <Footer />
    </div>
  )
}

function FilterGroup({ label, children, last }: { label: string; children: React.ReactNode; last?: boolean }) {
  return (
    <div className={cn("mb-4", !last && "pb-4 border-b border-gray-100")}>
      <p className="text-xs font-semibold text-[#4A5568] uppercase tracking-wide mb-2.5">{label}</p>
      {children}
    </div>
  )
}

function ActiveFilterChip({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-[#E0F5F0] text-[#00524D] text-xs font-medium">
      {label}
      <button onClick={onRemove} className="hover:text-[#003D39]">
        <X size={11} />
      </button>
    </span>
  )
}
