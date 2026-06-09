import { Link } from 'react-router-dom'
import { Scale, Smartphone, ShoppingCart, BarChart2, Users, ArrowRight, Mail, Sparkles, Database } from 'lucide-react'
import { Navbar } from '@/components/app/Navbar'
import { Footer } from '@/components/app/Footer'
import { PILLARS, ENABLERS } from '@/lib/constants'

const pillarIcons = [Scale, Users, ShoppingCart, Smartphone, BarChart2]
const pillarDescriptions = [
  'This pillar focuses on the formal and informal rules governing agricultural systems -- including laws, regulations, policies, and norms that enable or constrain the adoption and scaling of agricultural innovations. Effective policy and institutional frameworks reduce barriers, create incentives, and provide the legal certainty that innovators and investors need.',
  'Gender equality and social inclusion are both intrinsically important and critical determinants of scaling success. This pillar addresses the gender norms, institutional barriers, and programmatic approaches needed to ensure that agricultural innovations benefit women and marginalized groups equitably.',
  'Access to reliable, profitable markets is a fundamental requirement for sustainable agricultural innovation scaling. This pillar encompasses market infrastructure, value chain development, price information systems, standards and certification, and the institutional arrangements that connect smallholder farmers to commercial markets.',
  'Digital platforms, mobile infrastructure, and data systems are increasingly critical enablers for agricultural innovation scaling. This pillar covers digital infrastructure, mobile services, agricultural data systems, and the regulatory frameworks that govern digital service provision in agricultural contexts.',
  'Financial inclusion and robust monitoring, evaluation, and learning systems are essential for scaling. This pillar covers financial access, insurance, results-based management, and the institutional capacity to use evidence effectively in agricultural program management.',
]

export function AboutPage() {
  return (
    <div className="min-h-screen flex flex-col bg-[#F8F9FA]">
      <Navbar />

      {/* Hero */}
      <div className="relative h-64 overflow-hidden">
        <img
          src="/images/hero-agriculture.jpeg"
          alt="About"
          className="w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-[#00524D]/90 to-[#003D39]/70" />
        <div className="absolute inset-0 flex items-center">
          <div className="max-w-7xl mx-auto px-6 w-full">
            <h1 className="text-3xl font-extrabold text-white mb-2">
              About the Enabling Environment Toolbox
            </h1>
            <p className="text-white/80 text-base max-w-xl">
              A knowledge platform for agricultural innovation scaling
            </p>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-12 w-full">

        {/* About section */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-8 mb-8">
          <div className="flex items-center gap-2 mb-5">
            <div className="w-1 h-6 bg-[#00524D] rounded-full" />
            <h2 className="text-xl font-bold text-[#1A1A2E]">About this Platform</h2>
          </div>
          <div className="space-y-4 max-w-3xl">
            <p className="text-sm text-[#4A5568] leading-relaxed">
              The Enabling Environment Toolbox is a knowledge platform developed by CGIAR's Scaling for Impact initiative
              to help researchers, practitioners, policymakers, and development professionals discover and apply tools
              and approaches for creating enabling environments that support agricultural innovation scaling.
            </p>
            <p className="text-sm text-[#4A5568] leading-relaxed">
              The platform brings together a curated collection of frameworks, methods, tools, and approaches developed
              and field-tested by CGIAR centers and partners across Africa, Asia, and Latin America. It also documents
              real-world stories and cases of enabling environment reform from across the CGIAR portfolio.
            </p>
            <p className="text-sm text-[#4A5568] leading-relaxed">
              Our goal is to make this knowledge accessible and actionable for those working at the frontlines of
              agricultural transformation -- helping connect the dots between research, policy, and practice in the
              complex work of scaling agricultural innovations for impact.
            </p>
          </div>
        </div>

        {/* What is the Questioning AI */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-8 mb-8">
          <div className="flex items-center gap-2 mb-5">
            <Sparkles size={18} className="text-[#00524D]" />
            <h2 className="text-xl font-bold text-[#1A1A2E]">What is the AI Guide?</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="space-y-4">
              <p className="text-sm text-[#4A5568] leading-relaxed">
                The AI Guide is an intelligent discovery feature that helps you find the most relevant tools
                and approaches in our catalog through a conversational interface.
              </p>
              <p className="text-sm text-[#4A5568] leading-relaxed">
                Instead of browsing through filters, you can describe your enabling environment challenge
                in natural language. The AI Guide will ask clarifying questions about your context, region,
                and needs, then recommend the most relevant tools from our catalog.
              </p>
              <p className="text-sm text-[#4A5568] leading-relaxed">
                The current version uses smart keyword matching to understand your needs and filter our
                tool catalog. Future versions will incorporate more advanced natural language understanding.
              </p>
              <Link
                to="/guide"
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-[#00524D] text-white rounded-lg font-semibold text-sm hover:bg-[#003D39] transition-colors"
              >
                <Sparkles size={14} />
                Try the AI Guide
              </Link>
            </div>
            <div className="bg-gradient-to-br from-[#E0F5F0] to-[#F0FDF9] rounded-xl p-6 border border-[#B2DDD4]">
              <h3 className="font-bold text-[#1A1A2E] text-sm mb-4">How it works:</h3>
              <ol className="space-y-3">
                {[
                  'Describe your enabling environment challenge or context',
                  'The AI Guide asks clarifying questions about your pillar area, region, and needs',
                  'Based on your responses, it searches and ranks tools from the catalog',
                  'You receive personalized tool recommendations with direct links',
                ].map((step, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-[#00524D] text-white text-xs font-bold flex items-center justify-center">
                      {i + 1}
                    </span>
                    <span className="text-sm text-[#4A5568]">{step}</span>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </div>

        {/* Data Sources */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-8 mb-8">
          <div className="flex items-center gap-2 mb-5">
            <Database size={18} className="text-[#00524D]" />
            <h2 className="text-xl font-bold text-[#1A1A2E]">Data Sources</h2>
          </div>
          <div className="space-y-4 max-w-3xl">
            <p className="text-sm text-[#4A5568] leading-relaxed">
              The tools and stories in this platform are curated from multiple authoritative sources across the
              CGIAR system and partner organizations:
            </p>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {[
                { name: 'CG Space', desc: 'CGIAR open access repository' },
                { name: 'FAO', desc: 'Food & Agriculture Organization' },
                { name: 'IFAD', desc: 'Intl. Fund for Agricultural Dev.' },
                { name: 'World Bank', desc: 'Agriculture & food practice' },
                { name: 'CGIAR Centers', desc: 'Research center publications' },
                { name: 'Partner Orgs', desc: 'National research institutes' },
              ].map(source => (
                <div key={source.name} className="bg-gray-50 rounded-lg p-3">
                  <p className="text-sm font-semibold text-[#1A1A2E]">{source.name}</p>
                  <p className="text-[10px] text-[#4A5568]">{source.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* What is an enabling environment */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-8 mb-8">
          <div className="flex items-center gap-2 mb-5">
            <div className="w-1 h-6 bg-[#6B21A8] rounded-full" />
            <h2 className="text-xl font-bold text-[#1A1A2E]">What is an Enabling Environment?</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="space-y-4">
              <p className="text-sm text-[#4A5568] leading-relaxed">
                An enabling environment refers to the conditions, systems, and structures that either facilitate or
                constrain the adoption and scaling of agricultural innovations. It encompasses policies, regulations,
                institutions, markets, and social norms that shape the context in which agricultural innovations operate.
              </p>
              <p className="text-sm text-[#4A5568] leading-relaxed">
                Creating enabling environments is not a technical fix -- it requires understanding complex systems,
                building coalitions of change, navigating political dynamics, and investing in institutional capacity
                over sustained periods of time.
              </p>
              <p className="text-sm text-[#4A5568] leading-relaxed">
                CGIAR's Scaling for Impact research has identified five core pillars and three enablers that together
                define the enabling environment for agricultural innovation scaling.
              </p>
            </div>
            <div className="bg-gradient-to-br from-[#E0F5F0] to-[#F3E8FF] rounded-xl p-6">
              <h3 className="font-bold text-[#1A1A2E] text-sm mb-4">The five core pillars:</h3>
              <ul className="space-y-2 mb-6">
                {PILLARS.map(pillar => (
                  <li key={pillar} className="flex items-start gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#00524D] mt-1.5 flex-shrink-0" />
                    <span className="text-sm text-[#4A5568]">{pillar}</span>
                  </li>
                ))}
              </ul>
              <h3 className="font-bold text-[#1A1A2E] text-sm mb-4">The three enablers:</h3>
              <ul className="space-y-2">
                {ENABLERS.map(enabler => (
                  <li key={enabler} className="flex items-start gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#6B21A8] mt-1.5 flex-shrink-0" />
                    <span className="text-sm text-[#4A5568]">{enabler}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        {/* Pillars detailed */}
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-6">
            <div className="w-1 h-6 bg-[#007A72] rounded-full" />
            <h2 className="text-xl font-bold text-[#1A1A2E]">Pillars Explained</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {PILLARS.map((pillar, i) => {
              const Icon = pillarIcons[i]
              return (
                <div key={pillar} className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
                  <div className="w-10 h-10 rounded-lg bg-[#E0F5F0] flex items-center justify-center mb-4">
                    <Icon size={18} color="#00524D" />
                  </div>
                  <h3 className="font-bold text-[#1A1A2E] text-sm mb-3">{pillar}</h3>
                  <p className="text-xs text-[#4A5568] leading-relaxed">{pillarDescriptions[i]}</p>
                  <Link
                    to={`/explore?pillar=${encodeURIComponent(pillar)}`}
                    className="inline-flex items-center gap-1 mt-4 text-xs text-[#00524D] font-medium hover:underline"
                  >
                    Explore resources
                    <ArrowRight size={11} />
                  </Link>
                </div>
              )
            })}
          </div>
        </div>

        {/* Enablers */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-8 mb-8">
          <div className="flex items-center gap-2 mb-5">
            <div className="w-1 h-6 bg-[#16A34A] rounded-full" />
            <h2 className="text-xl font-bold text-[#1A1A2E]">Enablers & Outcomes</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                area: ENABLERS[0],
                desc: 'Building the policy, institutional, and market systems that support smallholder farmers in adapting to and mitigating the impacts of climate change.',
                color: '#16A34A',
              },
              {
                area: ENABLERS[1],
                desc: 'Creating the enabling conditions for proven agricultural innovations to grow from successful pilots to significant national and regional scale.',
                color: '#6B21A8',
              },
              {
                area: ENABLERS[2],
                desc: 'Working toward sustainable, inclusive, and nutritious food systems by addressing systemic barriers across entire value chains and food environments.',
                color: '#00524D',
              },
            ].map(({ area, desc, color }) => (
              <div key={area} className="rounded-xl p-5 border border-gray-100" style={{ backgroundColor: color + '08' }}>
                <div className="w-3 h-3 rounded-full mb-4" style={{ backgroundColor: color }} />
                <h3 className="font-bold text-[#1A1A2E] text-sm mb-3">{area}</h3>
                <p className="text-xs text-[#4A5568] leading-relaxed">{desc}</p>
                <Link
                  to={`/explore?enabler=${encodeURIComponent(area)}`}
                  className="inline-flex items-center gap-1 mt-4 text-xs font-medium hover:underline"
                  style={{ color }}
                >
                  Explore resources
                  <ArrowRight size={11} />
                </Link>
              </div>
            ))}
          </div>
        </div>

        {/* Contact */}
        <div className="bg-gradient-to-r from-[#00524D] to-[#007A72] rounded-2xl p-10 text-white text-center">
          <div className="w-12 h-12 rounded-full bg-white/20 flex items-center justify-center mx-auto mb-4">
            <Mail size={20} />
          </div>
          <h2 className="text-xl font-bold mb-2">Share your feedback</h2>
          <p className="text-white/80 text-sm mb-6 max-w-md mx-auto leading-relaxed">
            Help us improve the Enabling Environment Toolbox. Share your experience, suggest new resources,
            or tell us about your enabling environment work.
          </p>
          <a
            href="mailto:scaling@cgiar.org"
            className="inline-flex items-center gap-2 px-6 py-3 bg-white text-[#00524D] rounded-lg font-semibold text-sm hover:bg-gray-50 transition-colors shadow-md"
          >
            <Mail size={14} />
            Contact us
          </a>
        </div>
      </div>

      <Footer />
    </div>
  )
}
