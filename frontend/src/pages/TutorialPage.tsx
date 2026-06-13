import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Play,
  MessageSquare,
  HelpCircle,
  Search,
  BookOpen,
  Filter,
  Star,
  ChevronDown,
  ChevronUp,
  Lightbulb,
  Layers,
  MousePointer,
  ArrowRight,
  Globe,
  Users,
  Video,
} from 'lucide-react';

/* ------------------------------------------------------------------ */
/*  Data                                                               */
/* ------------------------------------------------------------------ */

const chatSteps = [
  {
    icon: MessageSquare,
    title: 'Start a Conversation',
    description:
      'Navigate to the homepage and type your challenge or question in the chat box. Be specific about your geography, target audience, and the enabling environment barrier you\'re facing.',
  },
  {
    icon: HelpCircle,
    title: 'Answer Clarifying Questions',
    description:
      'The AI will ask 2-3 follow-up questions to better understand your needs. These help narrow down from 90+ tools to the most relevant ones for your situation.',
  },
  {
    icon: Layers,
    title: 'Review Recommendations',
    description:
      'Based on your conversation, the AI recommends the most relevant tools. Each recommendation includes a brief explanation of why it was selected for your context.',
  },
  {
    icon: BookOpen,
    title: 'Explore Tool Details',
    description:
      'Click any recommended tool to see its full profile: what it does, when to use it, who it\'s for, the source document, and community ratings.',
  },
];

const catalogSteps = [
  {
    icon: MousePointer,
    title: 'Go to Search by Catalog',
    description:
      'Click "Search by Catalog" in the navigation bar to access the full tool collection.',
  },
  {
    icon: Filter,
    title: 'Apply Filters',
    description:
      'Use the sidebar filters to narrow tools by Pillar (e.g., Gender Equality), Domain (e.g., Climate Resilience), Type (Framework, Manual, Toolkit...), Stage, Target Users, or Geography.',
  },
  {
    icon: Search,
    title: 'Search by Keyword',
    description:
      'Use the search bar to find tools by name or topic. Combine keywords with filters for precise results.',
  },
  {
    icon: ArrowRight,
    title: 'Sort and Browse',
    description:
      'Sort results by relevance, date, or rating. Click any tool card to read its full details, access the source document, or rate its usefulness.',
  },
];

const tips = [
  {
    icon: Globe,
    title: 'Be Specific',
    description:
      'Include your country or region, target audience, and specific challenge when chatting with the AI.',
  },
  {
    icon: Layers,
    title: 'Try Both Methods',
    description:
      'Start with the AI chat for discovery, then use the catalog filters to explore related tools.',
  },
  {
    icon: Search,
    title: 'Check Maturity Stage',
    description:
      'Look at the Stage tag — "Established and field-tested" tools have real-world track records.',
  },
  {
    icon: Star,
    title: 'Rate What You Use',
    description:
      'Your ratings help other practitioners find the best tools faster.',
  },
];

const faqs: { question: string; answer: string }[] = [
  {
    question: 'What kind of tools are in the toolbox?',
    answer:
      'The toolbox contains over 90 curated resources including methods, frameworks, manuals, toolkits, guides, matrices, scorecards, briefs, and scales. All resources focus on enabling environment challenges in agricultural development and food systems transformation.',
  },
  {
    question: 'Who is the toolbox designed for?',
    answer:
      'The primary audiences are CGIAR researchers, policymakers, development practitioners, extension services, and anyone working on enabling environment challenges in agricultural and food systems. However, the tools are also relevant for NGOs, donors, government agencies, and agribusinesses.',
  },
  {
    question: 'How does the AI recommendation work?',
    answer:
      'When you describe your challenge, our AI system uses natural language understanding to match your description against the detailed profiles of all tools in our collection. It considers your geography, target audience, the type of enabling environment barrier, and the stage of your work to find the most relevant resources.',
  },
  {
    question: 'Can I browse without using the AI chat?',
    answer:
      'Absolutely! The "Search by Catalog" page lets you browse and filter the entire collection using taxonomy-based filters (pillars, domains, type, stage, target users, geography) and keyword search. Both approaches give you access to the same tools.',
  },
  {
    question: 'How are tools classified?',
    answer:
      'Every tool is tagged across multiple dimensions: 5 Enabling Environment Pillars (e.g., Gender Equality, Market Systems), 3 Domains (Agri-food Systems, Scaling Innovation, Climate Resilience), 10 Types (Framework, Manual, Toolkit...), 4 Maturity Stages, target user groups, and geographic relevance.',
  },
  {
    question: 'Where do the tools come from?',
    answer:
      'Tools are sourced from CGIAR research centers, international development organizations, and partners. Each tool links to its original source document or publication on platforms like CGSpace, the CGIAR open-access repository.',
  },
  {
    question: 'Can I rate the tools?',
    answer:
      'Yes! After viewing a tool\'s details, you can rate it on a 1-5 star scale. Your ratings help other users identify the most useful resources and improve the toolbox over time.',
  },
  {
    question: 'Is the toolbox regularly updated?',
    answer:
      'Yes. New tools are added as they are published and classified by our team. The AI recommendations also improve over time as more users interact with the system.',
  },
];

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function TutorialPage() {
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  const toggleFaq = (index: number) => {
    setOpenFaq(openFaq === index ? null : index);
  };

  return (
    <div className="min-h-screen bg-cgiar-light pt-16">
      {/* ── Hero ───────────────────────────────────────────────────── */}
      <div className="bg-cgiar-dark text-white py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-3xl sm:text-4xl font-bold mb-4">
            How to Use the Toolbox
          </h1>
          <p className="text-lg text-white/80 max-w-2xl mx-auto leading-relaxed">
            Learn how to find the right tools for your enabling environment
            challenges &mdash; whether through AI-guided conversation or direct
            catalog search.
          </p>
        </div>
      </div>

      {/* ── Video Placeholder ──────────────────────────────────────── */}
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="bg-gradient-to-br from-gray-800 to-gray-900 rounded-xl aspect-video flex flex-col items-center justify-center relative overflow-hidden">
          {/* Decorative film-strip bars */}
          <div className="absolute top-0 left-0 right-0 h-6 bg-gray-950/40 flex items-center gap-2 px-3">
            {Array.from({ length: 18 }).map((_, i) => (
              <div key={i} className="w-3 h-2 rounded-sm bg-gray-700/60" />
            ))}
          </div>
          <div className="absolute bottom-0 left-0 right-0 h-6 bg-gray-950/40 flex items-center gap-2 px-3">
            {Array.from({ length: 18 }).map((_, i) => (
              <div key={i} className="w-3 h-2 rounded-sm bg-gray-700/60" />
            ))}
          </div>

          <div className="flex items-center gap-3 mb-4">
            <Video size={28} className="text-cgiar-accent" />
            <div className="w-20 h-20 bg-cgiar-accent/20 hover:bg-cgiar-accent/30 rounded-full flex items-center justify-center transition-colors cursor-pointer">
              <Play size={36} className="text-white ml-1" />
            </div>
            <Video size={28} className="text-cgiar-accent" />
          </div>
          <p className="text-white font-semibold text-lg">
            Tutorial Video Coming Soon
          </p>
          <p className="text-gray-300 text-sm mt-1">
            A walkthrough of the toolbox features will be available here
          </p>
        </div>
      </div>

      {/* ── Method 1: AI-Guided Discovery ──────────────────────────── */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pb-16">
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 bg-cgiar-accent/10 text-cgiar-accent-dark rounded-full px-4 py-1.5 text-sm font-medium mb-4">
            <MessageSquare size={16} />
            Method 1
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            AI-Guided Discovery
          </h2>
          <p className="text-gray-600 max-w-xl mx-auto">
            Let our AI assistant help you find the right tools by understanding
            your specific context
          </p>
        </div>

        <div className="space-y-6">
          {chatSteps.map((step, idx) => (
            <div
              key={step.title}
              className="flex gap-5 bg-white rounded-xl p-6 shadow-sm border border-gray-100"
            >
              <div className="flex-shrink-0 w-12 h-12 bg-cgiar-accent/10 rounded-lg flex items-center justify-center">
                <step.icon size={24} className="text-cgiar-accent" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-1">
                  {idx + 1}. {step.title}
                </h3>
                <p className="text-sm text-gray-600 leading-relaxed">
                  {step.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Method 2: Catalog Search ───────────────────────────────── */}
      <div className="bg-white py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-10">
            <div className="inline-flex items-center gap-2 bg-blue-50 text-blue-600 rounded-full px-4 py-1.5 text-sm font-medium mb-4">
              <Search size={16} />
              Method 2
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              Catalog Search
            </h2>
            <p className="text-gray-600 max-w-xl mx-auto">
              Browse and filter the complete collection using taxonomy-based
              filters
            </p>
          </div>

          <div className="space-y-6">
            {catalogSteps.map((step, idx) => (
              <div
                key={step.title}
                className="flex gap-5 bg-cgiar-light rounded-xl p-6"
              >
                <div className="flex-shrink-0 w-12 h-12 bg-blue-50 rounded-lg flex items-center justify-center">
                  <step.icon size={24} className="text-blue-600" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-1">
                    {idx + 1}. {step.title}
                  </h3>
                  <p className="text-sm text-gray-600 leading-relaxed">
                    {step.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Tips for Best Results ──────────────────────────────────── */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-10">
          <Lightbulb size={28} className="text-cgiar-accent mx-auto mb-3" />
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Tips for Best Results
          </h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          {tips.map((tip) => (
            <div
              key={tip.title}
              className="bg-white rounded-xl p-6 shadow-sm border border-gray-100"
            >
              <div className="w-10 h-10 bg-cgiar-accent/10 rounded-lg flex items-center justify-center mb-3">
                <tip.icon size={20} className="text-cgiar-accent" />
              </div>
              <h3 className="text-base font-semibold text-gray-900 mb-1">
                {tip.title}
              </h3>
              <p className="text-sm text-gray-600 leading-relaxed">
                {tip.description}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* ── FAQ Section ────────────────────────────────────────────── */}
      <div className="bg-white py-16">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-10">
            <HelpCircle size={28} className="text-cgiar-accent mx-auto mb-3" />
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              Frequently Asked Questions
            </h2>
          </div>

          <div className="space-y-3">
            {faqs.map((faq, index) => (
              <div
                key={index}
                className="bg-cgiar-light rounded-xl border border-gray-100 overflow-hidden"
              >
                <button
                  onClick={() => toggleFaq(index)}
                  className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-gray-50 transition-colors"
                  aria-expanded={openFaq === index}
                  aria-controls={`faq-answer-${index}`}
                >
                  <span className="font-medium text-gray-900 pr-4">
                    {faq.question}
                  </span>
                  {openFaq === index ? (
                    <ChevronUp
                      size={20}
                      className="text-cgiar-accent flex-shrink-0"
                    />
                  ) : (
                    <ChevronDown
                      size={20}
                      className="text-gray-400 flex-shrink-0"
                    />
                  )}
                </button>
                {openFaq === index && (
                  <div id={`faq-answer-${index}`} className="px-6 pb-4">
                    <p className="text-sm text-gray-600 leading-relaxed">
                      {faq.answer}
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── CTA Section ────────────────────────────────────────────── */}
      <div className="bg-cgiar-dark text-white py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-2xl sm:text-3xl font-bold mb-4">
            Ready to find the right tool?
          </h2>
          <p className="text-white/80 mb-8 max-w-lg mx-auto">
            Whether you prefer an AI-guided conversation or hands-on browsing,
            the toolbox has you covered.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              to="/"
              className="inline-flex items-center gap-2 bg-cgiar-accent-dark hover:bg-cgiar-accent-dark/90 text-white font-medium px-6 py-3 rounded-lg transition-colors"
            >
              <MessageSquare size={18} />
              Start a Conversation
            </Link>
            <Link
              to="/catalog"
              className="inline-flex items-center gap-2 bg-white/10 hover:bg-white/20 text-white font-medium px-6 py-3 rounded-lg transition-colors border border-white/20"
            >
              <Search size={18} />
              Browse the Catalog
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
