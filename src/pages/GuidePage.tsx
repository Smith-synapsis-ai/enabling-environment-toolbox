import { useState, useRef, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { Send, Sparkles, ArrowRight, ExternalLink, Building2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Navbar } from '@/components/app/Navbar'
import { Footer } from '@/components/app/Footer'
import { TypeBadge } from '@/components/app/TypeBadge'
import { tools } from '@/data/items'
import type { Tool } from '@/data/items'
import { PILLARS } from '@/lib/constants'

interface ChatMessage {
  id: string
  role: 'assistant' | 'user'
  content: string
  toolResults?: Tool[]
  filterLink?: string
}

// Keyword maps for matching user input to taxonomy
const PILLAR_KEYWORDS: Record<string, string[]> = {
  'Policy & Institutional': ['policy', 'regulation', 'regulatory', 'institutional', 'governance', 'government', 'law', 'legal', 'reform', 'legislation'],
  'Gender & Social Inclusion': ['gender', 'women', 'inclusion', 'equity', 'social', 'empowerment', 'youth', 'marginalized', 'inclusive'],
  'Market Systems': ['market', 'value chain', 'trade', 'commercial', 'price', 'buyer', 'seller', 'supply chain', 'agribusiness'],
  'Digital': ['digital', 'ict', 'mobile', 'technology', 'data', 'platform', 'app', 'information', 'tech', 'internet', 'phone'],
  'Financial Services & M&E': ['finance', 'financial', 'credit', 'loan', 'insurance', 'banking', 'monitoring', 'evaluation', 'M&E', 'melia', 'impact', 'measurement'],
}

const ENABLER_KEYWORDS: Record<string, string[]> = {
  'Climate Resilience': ['climate', 'resilience', 'adaptation', 'weather', 'drought', 'flood', 'temperature', 'rainfall', 'carbon', 'emission', 'environment'],
  'Scaling of Innovation': ['scaling', 'scale', 'innovation', 'readiness', 'pilot', 'expand', 'growth', 'adoption', 'diffusion', 'spread'],
  'Improved Agri-Food Systems': ['food system', 'nutrition', 'food security', 'agri-food', 'diet', 'food safety', 'value chain', 'production', 'agriculture'],
}

const REGION_KEYWORDS: Record<string, string[]> = {
  'East Africa': ['east africa', 'kenya', 'tanzania', 'uganda', 'ethiopia', 'rwanda'],
  'West Africa': ['west africa', 'nigeria', 'ghana', 'mali', 'senegal'],
  'Sub-Saharan Africa': ['sub-saharan', 'africa', 'sahel'],
  'Southern Africa': ['southern africa', 'zambia', 'mozambique', 'zimbabwe'],
  'South Asia': ['south asia', 'india', 'bangladesh', 'nepal', 'pakistan'],
  'Southeast Asia': ['southeast asia', 'vietnam', 'philippines', 'indonesia', 'myanmar', 'cambodia'],
  'Latin America': ['latin america', 'colombia', 'peru', 'guatemala'],
}

const TYPE_KEYWORDS: Record<string, string[]> = {
  'Framework': ['framework', 'conceptual', 'theoretical'],
  'Method': ['method', 'methodology', 'approach to analysis', 'assessment method'],
  'Tool': ['tool', 'toolkit', 'instrument', 'calculator'],
  'Approach': ['approach', 'strategy', 'model'],
  'Scorecard': ['scorecard', 'score', 'index', 'rating'],
  'Guidelines': ['guidelines', 'guide', 'manual', 'handbook'],
}

const STAGE_KEYWORDS: Record<string, string[]> = {
  'Established and field-tested': ['established', 'proven', 'field-tested', 'mature', 'validated'],
  'Emerging': ['emerging', 'developing', 'growing', 'new'],
  'Pilot': ['pilot', 'testing', 'experimental', 'trial'],
  'Conceptual': ['conceptual', 'theoretical', 'early stage'],
}

interface ParsedContext {
  pillars: string[]
  enablers: string[]
  regions: string[]
  types: string[]
  stages: string[]
  countries: string[]
}

function parseUserInput(text: string): ParsedContext {
  const lower = text.toLowerCase()
  const result: ParsedContext = { pillars: [], enablers: [], regions: [], types: [], stages: [], countries: [] }

  for (const [pillar, keywords] of Object.entries(PILLAR_KEYWORDS)) {
    if (keywords.some(k => lower.includes(k))) result.pillars.push(pillar)
  }
  for (const [enabler, keywords] of Object.entries(ENABLER_KEYWORDS)) {
    if (keywords.some(k => lower.includes(k))) result.enablers.push(enabler)
  }
  for (const [region, keywords] of Object.entries(REGION_KEYWORDS)) {
    if (keywords.some(k => lower.includes(k))) result.regions.push(region)
  }
  for (const [type, keywords] of Object.entries(TYPE_KEYWORDS)) {
    if (keywords.some(k => lower.includes(k))) result.types.push(type)
  }
  for (const [stage, keywords] of Object.entries(STAGE_KEYWORDS)) {
    if (keywords.some(k => lower.includes(k))) result.stages.push(stage)
  }

  // Direct country matching
  const countryList = ['kenya', 'ethiopia', 'uganda', 'tanzania', 'nigeria', 'ghana', 'mali', 'senegal',
    'india', 'bangladesh', 'nepal', 'pakistan', 'vietnam', 'philippines', 'indonesia', 'myanmar', 'cambodia',
    'colombia', 'peru', 'guatemala', 'zambia', 'mozambique', 'rwanda']
  for (const c of countryList) {
    if (lower.includes(c)) result.countries.push(c.charAt(0).toUpperCase() + c.slice(1))
  }

  return result
}

function filterTools(context: ParsedContext): Tool[] {
  let results = [...tools]

  if (context.pillars.length > 0) {
    results = results.filter(t => context.pillars.some(p => t.pillars.includes(p)))
  }
  if (context.enablers.length > 0) {
    results = results.filter(t => context.enablers.some(e => t.enablers.includes(e)))
  }
  if (context.regions.length > 0) {
    results = results.filter(t => context.regions.some(r => t.regions.includes(r)))
  }
  if (context.types.length > 0) {
    results = results.filter(t => context.types.includes(t.type))
  }
  if (context.stages.length > 0) {
    results = results.filter(t => context.stages.includes(t.stage))
  }
  if (context.countries.length > 0) {
    results = results.filter(t => context.countries.some(c => t.countries.includes(c)))
  }

  return results.slice(0, 6)
}

function getMissingInfo(context: ParsedContext): string[] {
  const missing: string[] = []
  if (context.pillars.length === 0) missing.push('pillar')
  if (context.regions.length === 0 && context.countries.length === 0) missing.push('region')
  if (context.types.length === 0) missing.push('type')
  if (context.stages.length === 0) missing.push('stage')
  return missing
}

function generateResponse(userText: string, conversationLength: number, accumulatedContext: ParsedContext): { message: string; toolResults?: Tool[]; filterLink?: string } {
  const newContext = parseUserInput(userText)

  // Merge with accumulated context
  for (const p of newContext.pillars) if (!accumulatedContext.pillars.includes(p)) accumulatedContext.pillars.push(p)
  for (const e of newContext.enablers) if (!accumulatedContext.enablers.includes(e)) accumulatedContext.enablers.push(e)
  for (const r of newContext.regions) if (!accumulatedContext.regions.includes(r)) accumulatedContext.regions.push(r)
  for (const t of newContext.types) if (!accumulatedContext.types.includes(t)) accumulatedContext.types.push(t)
  for (const s of newContext.stages) if (!accumulatedContext.stages.includes(s)) accumulatedContext.stages.push(s)
  for (const c of newContext.countries) if (!accumulatedContext.countries.includes(c)) accumulatedContext.countries.push(c)

  const missing = getMissingInfo(accumulatedContext)
  const hasEnoughContext = missing.length <= 1 || conversationLength >= 2

  if (hasEnoughContext) {
    const results = filterTools(accumulatedContext)
    if (results.length > 0) {
      const params = new URLSearchParams()
      if (accumulatedContext.pillars.length > 0) params.set('pillar', accumulatedContext.pillars[0])
      if (accumulatedContext.enablers.length > 0) params.set('enabler', accumulatedContext.enablers[0])

      const detectedParts: string[] = []
      if (accumulatedContext.pillars.length > 0) detectedParts.push(`pillar: ${accumulatedContext.pillars.join(', ')}`)
      if (accumulatedContext.regions.length > 0) detectedParts.push(`region: ${accumulatedContext.regions.join(', ')}`)
      if (accumulatedContext.countries.length > 0) detectedParts.push(`countries: ${accumulatedContext.countries.join(', ')}`)

      const contextSummary = detectedParts.length > 0 ? `Based on your context (${detectedParts.join('; ')}), h` : 'H'

      return {
        message: `${contextSummary}ere are the most relevant tools and approaches I found in our catalog. Each has been field-tested and can help with the challenge you described.`,
        toolResults: results,
        filterLink: `/explore?${params.toString()}`,
      }
    } else {
      return {
        message: 'I was not able to find exact matches for your specific criteria, but I would recommend browsing our full catalog. You might also try broadening your search to related pillars or regions.',
        filterLink: '/explore',
      }
    }
  }

  // Ask clarifying questions based on what is missing
  if (missing.includes('pillar') && missing.includes('region')) {
    return {
      message: 'Thank you for sharing that context. To help me narrow down the most relevant tools, could you tell me:\n\n1. **Which area** are you most focused on? For example: policy & institutional reform, gender & social inclusion, market systems, digital agriculture, or financial services & M&E?\n\n2. **What region or country** are you working in?',
    }
  }

  if (missing.includes('pillar')) {
    return {
      message: `Thanks for that information. Which of these enabling environment areas is most relevant to your work?\n\n${PILLARS.map(p => `- **${p}**`).join('\n')}`,
    }
  }

  if (missing.includes('region')) {
    return {
      message: 'That helps narrow things down. What region or country are you working in? We have tools and experiences from East Africa, West Africa, South Asia, Southeast Asia, Latin America, and more.',
    }
  }

  if (missing.includes('type')) {
    return {
      message: 'Great. Are you looking for a specific type of resource? For example:\n\n- **Framework** - Conceptual structure for analysis\n- **Tool** - Practical instrument for assessment\n- **Method** - Step-by-step methodology\n- **Approach** - Strategic way of working\n- **Guidelines** - Practical guidance documents',
    }
  }

  return {
    message: 'Let me search our catalog based on what you have shared so far...',
    toolResults: filterTools(accumulatedContext),
  }
}

export function GuidePage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '0',
      role: 'assistant',
      content: 'Welcome to the EE Guide. I will help you find the right tools and approaches for your enabling environment challenge.\n\nTell me about the context you are working in -- what is the challenge you are trying to address? For example, you might be working on seed system reform in East Africa, or trying to scale digital extension services in South Asia.',
    },
  ])
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const accumulatedContext = useRef<ParsedContext>({ pillars: [], enablers: [], regions: [], types: [], stages: [], countries: [] })

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  function handleSend() {
    if (!input.trim()) return

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsTyping(true)

    // Simulate typing delay
    setTimeout(() => {
      const userMessageCount = messages.filter(m => m.role === 'user').length + 1
      const response = generateResponse(userMessage.content, userMessageCount, accumulatedContext.current)

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.message,
        toolResults: response.toolResults,
        filterLink: response.filterLink,
      }

      setMessages(prev => [...prev, assistantMessage])
      setIsTyping(false)
    }, 800 + Math.random() * 600)
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const quickPrompts = [
    'I need tools for scaling seed system innovations in East Africa',
    'What frameworks exist for gender-inclusive agricultural value chains?',
    'I am working on climate adaptation policy in the Sahel',
    'Help me find digital agriculture assessment tools for South Asia',
  ]

  return (
    <div className="min-h-screen flex flex-col bg-[#F8F9FA]">
      <Navbar />

      <div className="flex-1 flex flex-col max-w-4xl mx-auto w-full px-4 md:px-6">
        {/* Header */}
        <div className="py-6 text-center">
          <div className="inline-flex items-center gap-2 bg-[#E0F5F0] rounded-full px-4 py-1.5 mb-4">
            <Sparkles size={14} className="text-[#00524D]" />
            <span className="text-xs font-semibold text-[#00524D]">AI-Guided Discovery</span>
          </div>
          <h1 className="text-2xl font-bold text-[#1A1A2E] mb-2">EE Guide</h1>
          <p className="text-sm text-[#4A5568] max-w-lg mx-auto">
            Describe your enabling environment challenge and I will recommend the most relevant tools and approaches from our catalog.
          </p>
        </div>

        {/* Chat area */}
        <div className="flex-1 overflow-y-auto pb-4 space-y-4">
          {messages.map(msg => (
            <div key={msg.id} className={cn("flex", msg.role === 'user' ? 'justify-end' : 'justify-start')}>
              <div className={cn(
                "max-w-[85%] rounded-2xl px-5 py-4",
                msg.role === 'user'
                  ? "bg-[#00524D] text-white rounded-br-md"
                  : "bg-white border border-gray-200 shadow-sm text-[#1A1A2E] rounded-bl-md"
              )}>
                {msg.role === 'assistant' && (
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-6 h-6 rounded-full bg-[#E0F5F0] flex items-center justify-center">
                      <Sparkles size={12} className="text-[#00524D]" />
                    </div>
                    <span className="text-[10px] font-semibold text-[#00524D] uppercase tracking-wide">EE Guide</span>
                  </div>
                )}
                <div className={cn(
                  "text-sm leading-relaxed whitespace-pre-wrap",
                  msg.role === 'user' ? 'text-white' : 'text-[#4A5568]'
                )}>
                  {msg.content.split(/(\*\*.*?\*\*)/).map((part, i) => {
                    if (part.startsWith('**') && part.endsWith('**')) {
                      return <strong key={i} className={msg.role === 'user' ? 'text-white' : 'text-[#1A1A2E]'}>{part.slice(2, -2)}</strong>
                    }
                    return <span key={i}>{part}</span>
                  })}
                </div>

                {/* Tool Results */}
                {msg.toolResults && msg.toolResults.length > 0 && (
                  <div className="mt-4 space-y-3">
                    {msg.toolResults.map(tool => (
                      <Link
                        key={tool.id}
                        to={`/tool/${tool.id}`}
                        className="block bg-[#F8F9FA] rounded-xl border border-gray-100 p-4 hover:border-[#00524D]/30 hover:shadow-sm transition-all"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1.5">
                              <TypeBadge type={tool.type} />
                              <span className="text-[10px] text-gray-400 flex items-center gap-0.5">
                                <Building2 size={9} />
                                {tool.source}
                              </span>
                            </div>
                            <h4 className="text-sm font-bold text-[#1A1A2E] mb-1">{tool.title}</h4>
                            <p className="text-xs text-[#4A5568] line-clamp-2">{tool.description}</p>
                          </div>
                          <ArrowRight size={14} className="text-gray-400 mt-1 flex-shrink-0" />
                        </div>
                      </Link>
                    ))}

                    {msg.filterLink && (
                      <Link
                        to={msg.filterLink}
                        className="inline-flex items-center gap-1.5 text-xs text-[#00524D] font-medium hover:underline mt-2"
                      >
                        <ExternalLink size={11} />
                        View all results in the catalog
                      </Link>
                    )}
                  </div>
                )}

                {msg.filterLink && !msg.toolResults && (
                  <div className="mt-3">
                    <Link
                      to={msg.filterLink}
                      className="inline-flex items-center gap-1.5 text-xs text-[#00524D] font-medium hover:underline"
                    >
                      <ExternalLink size={11} />
                      Browse the full catalog
                    </Link>
                  </div>
                )}
              </div>
            </div>
          ))}

          {isTyping && (
            <div className="flex justify-start">
              <div className="bg-white border border-gray-200 shadow-sm rounded-2xl rounded-bl-md px-5 py-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-6 h-6 rounded-full bg-[#E0F5F0] flex items-center justify-center">
                    <Sparkles size={12} className="text-[#00524D]" />
                  </div>
                  <span className="text-[10px] font-semibold text-[#00524D] uppercase tracking-wide">EE Guide</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-full bg-[#00524D]/40 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 rounded-full bg-[#00524D]/40 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 rounded-full bg-[#00524D]/40 animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Quick prompts - show only at start */}
        {messages.length <= 1 && (
          <div className="pb-4">
            <p className="text-xs text-gray-400 mb-2 font-medium">Try one of these:</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {quickPrompts.map((prompt, i) => (
                <button
                  key={i}
                  onClick={() => { setInput(prompt); inputRef.current?.focus() }}
                  className="text-left text-xs text-[#4A5568] bg-white border border-gray-200 rounded-xl px-4 py-3 hover:border-[#00524D]/30 hover:text-[#00524D] transition-all"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input */}
        <div className="sticky bottom-0 bg-[#F8F9FA] pb-6 pt-2">
          <div className="relative">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Describe your enabling environment challenge..."
              className="w-full pl-5 pr-14 py-4 rounded-2xl border border-gray-200 bg-white text-sm text-[#1A1A2E] placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#00524D]/30 focus:border-[#00524D] transition-all shadow-sm"
              disabled={isTyping}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isTyping}
              className={cn(
                "absolute right-3 top-1/2 -translate-y-1/2 w-9 h-9 rounded-xl flex items-center justify-center transition-all",
                input.trim() && !isTyping
                  ? "bg-[#00524D] text-white hover:bg-[#003D39]"
                  : "bg-gray-100 text-gray-400"
              )}
            >
              <Send size={16} />
            </button>
          </div>
          <p className="text-[10px] text-gray-400 text-center mt-2">
            The EE Guide uses keyword matching to recommend tools. It is not a large language model.
          </p>
        </div>
      </div>

      <Footer />
    </div>
  )
}
