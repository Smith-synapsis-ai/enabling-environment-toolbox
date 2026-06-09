import { Link, useNavigate } from 'react-router-dom'
import {
  Scale, Smartphone, ShoppingCart, BarChart2,
  Users, ArrowRight, Globe, BookOpen, Layers, Sparkles, Info
} from 'lucide-react'
import { Navbar } from '@/components/app/Navbar'
import { Footer } from '@/components/app/Footer'
import { PILLARS } from '@/lib/constants'

const pillarIcons = [Scale, Users, ShoppingCart, Smartphone, BarChart2]

const pillarDescriptions = [
  'Policy reform, regulatory frameworks, and institutional enabling conditions for agricultural innovation.',
  'Gender equity, social inclusion, and women\'s empowerment in agricultural systems.',
  'Market linkages, value chain development, and access to commercial agricultural markets.',
  'Digital platforms, mobile infrastructure, and data systems for inclusive agricultural services.',
  'Financial inclusion, M&E frameworks, and learning approaches for evidence-based decisions.',
]

export function HomePage() {
  const navigate = useNavigate()

  function handlePillarClick(pillar: string) {
    navigate(`/explore?pillar=${encodeURIComponent(pillar)}`)
  }

  return (
    <div className="min-h-screen flex flex-col bg-[#F8F9FA]">
      <Navbar />

      {/* Beta banner */}
      <div className="bg-amber-50 border-b border-amber-200">
        <div className="max-w-7xl mx-auto px-6 py-2 flex items-center gap-2">
          <Info size={14} className="text-amber-600 flex-shrink-0" />
          <p className="text-xs text-amber-700">
            <span className="font-semibold">Beta release</span> -- This is a preview of the Enabling Environment Toolbox. Content is being expanded and features are under active development.
          </p>
        </div>
      </div>

      {/* Hero */}
      <section className="relative h-[560px] flex items-center overflow-hidden">
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{ backgroundImage: "url('/images/hero-agriculture.jpeg')" }}
        />
        <div className="absolute inset-0 bg-gradient-to-r from-[#00524D]/90 via-[#003D39]/80 to-transparent" />
        <div className="relative z-10 max-w-7xl mx-auto px-6 w-full">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 bg-white/15 border border-white/30 rounded-full px-4 py-1.5 mb-6 backdrop-blur-sm">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-white text-xs font-medium tracking-wide">CGIAR Scaling for Impact</span>
            </div>
            <h1 className="text-4xl md:text-5xl font-extrabold text-white leading-tight mb-5">
              Enabling Environment<br />
              <span className="text-emerald-300">Toolbox</span>
            </h1>
            <p className="text-white/85 text-lg leading-relaxed mb-8 max-w-xl">
              Discover tools, approaches, and real-world experiences for creating enabling environments
              that support agricultural innovation scaling across countries.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link
                to="/explore"
                className="inline-flex items-center gap-2 px-6 py-3 bg-white text-[#00524D] rounded-lg font-semibold text-sm hover:bg-gray-50 transition-colors shadow-lg"
              >
                Browse the Catalog
                <ArrowRight size={16} />
              </Link>
              <Link
                to="/guide"
                className="inline-flex items-center gap-2 px-6 py-3 bg-emerald-400/20 border border-emerald-400/40 text-white rounded-lg font-semibold text-sm hover:bg-emerald-400/30 transition-colors backdrop-blur-sm"
              >
                <Sparkles size={16} />
                Ask the AI Guide
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Bar */}
      <section className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="grid grid-cols-3 gap-6 divide-x divide-gray-200">
            {[
              { number: '30+', label: 'Tools & Approaches', icon: <Layers size={20} className="text-[#00524D]" /> },
              { number: '12+', label: 'Stories & Cases', icon: <BookOpen size={20} className="text-[#6B21A8]" /> },
              { number: '40+', label: 'Countries Covered', icon: <Globe size={20} className="text-[#16A34A]" /> },
            ].map(stat => (
              <div key={stat.label} className="flex items-center gap-4 px-4 first:pl-0 last:pr-0">
                <div className="p-2 rounded-lg bg-gray-50">
                  {stat.icon}
                </div>
                <div>
                  <div className="text-2xl font-extrabold text-[#1A1A2E]">{stat.number}</div>
                  <div className="text-xs text-[#4A5568] font-medium">{stat.label}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pillars */}
      <section className="max-w-7xl mx-auto px-6 py-16">
        <div className="mb-10">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-1 h-8 bg-[#00524D] rounded-full" />
            <h2 className="text-2xl font-bold text-[#1A1A2E]">Explore by Pillar</h2>
          </div>
          <p className="text-[#4A5568] ml-4">
            Five core pillars of enabling environments for agricultural innovation scaling.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {PILLARS.map((pillar, i) => {
            const Icon = pillarIcons[i]
            return (
              <button
                key={pillar}
                onClick={() => handlePillarClick(pillar)}
                className="group text-left bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md hover:border-[#00524D]/30 transition-all duration-200 p-6 overflow-hidden relative"
              >
                <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-[#00524D] to-[#4CAF8A] rounded-l-xl opacity-0 group-hover:opacity-100 transition-opacity" />
                <div
                  className="w-11 h-11 rounded-xl flex items-center justify-center mb-4"
                  style={{ backgroundColor: '#E0F5F0' }}
                >
                  <Icon size={20} color="#00524D" />
                </div>
                <h3 className="font-bold text-[#1A1A2E] text-sm mb-2 group-hover:text-[#00524D] transition-colors">
                  {pillar}
                </h3>
                <p className="text-xs text-[#4A5568] leading-relaxed">
                  {pillarDescriptions[i]}
                </p>
                <div className="mt-4 flex items-center gap-1 text-[#00524D] text-xs font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                  Explore
                  <ArrowRight size={12} />
                </div>
              </button>
            )
          })}
        </div>
      </section>

      {/* Enablers */}
      <section className="bg-white py-16 border-y border-gray-200">
        <div className="max-w-7xl mx-auto px-6">
          <div className="mb-10">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-1 h-8 bg-[#6B21A8] rounded-full" />
              <h2 className="text-2xl font-bold text-[#1A1A2E]">Enablers & Outcomes</h2>
            </div>
            <p className="text-[#4A5568] ml-4">
              The three strategic enablers that guide CGIAR's scaling for impact work.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                title: 'Climate Resilience',
                desc: 'Building enabling environments for climate-smart agricultural practices that protect vulnerable farmers.',
                image: '/images/hero-farmer.jpeg',
                color: '#16A34A',
              },
              {
                title: 'Scaling of Innovation',
                desc: 'Creating the conditions for proven agricultural innovations to grow from pilot to national scale.',
                image: '/images/field-worker.jpeg',
                color: '#6B21A8',
              },
              {
                title: 'Improved Agri-Food Systems',
                desc: 'Enabling systemic change across entire food systems from production through consumption.',
                image: '/images/hero-agriculture.jpeg',
                color: '#00524D',
              },
            ].map(area => (
              <div
                key={area.title}
                className="group relative rounded-xl overflow-hidden h-64 cursor-pointer"
                onClick={() => navigate(`/explore?enabler=${encodeURIComponent(area.title)}`)}
              >
                <img
                  src={area.image}
                  alt={area.title}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-black/10" />
                <div
                  className="absolute top-4 left-4 w-1 h-8 rounded-full"
                  style={{ backgroundColor: area.color === '#00524D' ? '#4CAF8A' : area.color === '#6B21A8' ? '#A855F7' : '#4ADE80' }}
                />
                <div className="absolute bottom-0 left-0 right-0 p-5">
                  <h3 className="text-white font-bold text-base mb-1 leading-snug">{area.title}</h3>
                  <p className="text-white/75 text-xs leading-relaxed">{area.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* AI Guide CTA */}
      <section className="max-w-7xl mx-auto px-6 py-16">
        <div className="bg-gradient-to-r from-[#00524D] to-[#007A72] rounded-2xl p-10 text-white">
          <div className="flex flex-col md:flex-row items-center gap-8">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-3">
                <Sparkles size={20} className="text-emerald-300" />
                <span className="text-xs font-semibold text-emerald-300 uppercase tracking-wide">New Feature</span>
              </div>
              <h2 className="text-2xl font-bold mb-3">Not sure where to start?</h2>
              <p className="text-white/80 mb-6 max-w-lg text-sm leading-relaxed">
                Our AI Guide will ask you a few questions about your context, then recommend the most relevant tools and approaches from the catalog.
              </p>
              <Link
                to="/guide"
                className="inline-flex items-center gap-2 px-6 py-3 bg-white text-[#00524D] rounded-lg font-semibold text-sm hover:bg-gray-50 transition-colors shadow-md"
              >
                <Sparkles size={14} />
                Ask the AI Guide
              </Link>
            </div>
            <div className="w-64 h-48 bg-white/10 rounded-xl border border-white/20 flex flex-col items-center justify-center gap-3 backdrop-blur-sm">
              <div className="w-12 h-12 rounded-full bg-emerald-400/20 flex items-center justify-center">
                <Sparkles size={24} className="text-emerald-300" />
              </div>
              <p className="text-white/70 text-xs text-center px-4">Tell me about your enabling environment challenge...</p>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  )
}
