import { Bot, Database, Shield, AlertTriangle, MessageSquare, ExternalLink, Leaf } from 'lucide-react';

export default function TransparencyPage() {
  return (
    <div className="min-h-screen bg-cgiar-light pt-16">
      {/* ------------------------------------------------------------------ */}
      {/* Hero                                                                */}
      {/* ------------------------------------------------------------------ */}
      <div className="bg-cgiar-dark text-white py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <Bot size={40} className="text-cgiar-accent mx-auto mb-4" />
          <h1 className="text-3xl sm:text-4xl font-bold mb-4">
            AI Transparency
          </h1>
          <p className="text-lg text-white/80 max-w-2xl mx-auto leading-relaxed">
            How the Scaling Challenge Assistant works — model, data sources, privacy, and limitations.
          </p>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Section 1 — Model & Architecture (bg-cgiar-light)                  */}
      {/* ------------------------------------------------------------------ */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-14">
        <div className="flex items-center gap-2 mb-4">
          <Bot size={22} className="text-cgiar-accent" />
          <h2 className="text-2xl font-bold text-gray-900">Model & Agent Architecture</h2>
        </div>
        <p className="text-gray-600 leading-relaxed mb-6">
          The Scaling Challenge Assistant is powered by <strong>Claude Sonnet 4.5</strong> (Anthropic), accessed
          via the Anthropic API. It operates as a <strong>multi-agent orchestrator</strong>: when you submit a
          challenge, the system runs a pipeline that includes a triage step (interpreting your challenge and
          geography), a corpus search step (matching your challenge against the curated tool database), and a
          synthesis step (drafting a structured evidence report from the matched tools and their metadata).
        </p>
        <p className="text-gray-600 leading-relaxed mb-6">
          Each step is handled by a specialized sub-agent with a distinct system prompt and tool access. The
          orchestrator coordinates these steps sequentially, passing context forward through the pipeline. The
          full pipeline typically takes 1–4 minutes to complete a turn, depending on challenge complexity.
        </p>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Section 2 — Data Sources (bg-white)                                */}
      {/* ------------------------------------------------------------------ */}
      <div className="bg-white py-14">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-2 mb-4">
            <Database size={22} className="text-cgiar-accent" />
            <h2 className="text-2xl font-bold text-gray-900">Data Sources</h2>
          </div>
          <p className="text-gray-600 leading-relaxed mb-6">
            The assistant's knowledge is drawn entirely from the <strong>curated EE Toolbox corpus</strong>:
            approximately 100 enabling environment tools, frameworks, and methods, each annotated with pillar
            tags, domain classifications, geography coverage, and methodology metadata. This corpus is stored
            in a local SQLite database and is updated with each platform deployment — it is <strong>not</strong> a
            live web search.
          </p>
          <p className="text-gray-600 leading-relaxed mb-6">
            The assistant does not access the open web, external APIs, or any data beyond the EE Toolbox tool
            profiles and their associated evidence summaries. All recommendations are traceable to a specific
            tool entry in the corpus.
          </p>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Section 3 — Session Data & Privacy (bg-cgiar-light)                */}
      {/* ------------------------------------------------------------------ */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-14">
        <div className="flex items-center gap-2 mb-4">
          <Shield size={22} className="text-cgiar-accent" />
          <h2 className="text-2xl font-bold text-gray-900">Session Data & Privacy</h2>
        </div>
        <p className="text-gray-600 leading-relaxed mb-6">
          The assistant handles your data with a minimal-footprint approach:
        </p>
        <ul className="list-disc list-inside text-gray-600 space-y-2 text-sm">
          <li>
            <strong>Session isolation:</strong> Each browser tab creates a fresh, independent session.
            Sessions are not shared between tabs or users.
          </li>
          <li>
            <strong>Ephemeral by default:</strong> Your challenge text and conversation history exist only
            for the duration of your browser session. Report drafts are automatically deleted after 24 hours
            of inactivity.
          </li>
          <li>
            <strong>No PII collected:</strong> The assistant does not ask for, collect, or store personally
            identifiable information. Challenge text is processed to generate recommendations and is not
            retained beyond the active session.
          </li>
          <li>
            <strong>No third-party tracking:</strong> The assistant pipeline does not share your queries with
            any third-party analytics or advertising services.
          </li>
        </ul>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Section 4 — Limitations (bg-white)                                 */}
      {/* ------------------------------------------------------------------ */}
      <div className="bg-white py-14">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle size={22} className="text-amber-500" />
            <h2 className="text-2xl font-bold text-gray-900">Known Limitations</h2>
          </div>
          <ul className="list-disc list-inside text-gray-600 space-y-2 text-sm">
            <li>
              <strong>Corpus coverage:</strong> Recommendations are limited to tools currently in the EE
              Toolbox database. Newer publications, grey literature, or tools outside the CGIAR enabling
              environment scope will not appear.
            </li>
            <li>
              <strong>AI inference errors:</strong> Language models can produce plausible-sounding but
              incorrect statements. Always verify recommendations against the original tool documentation
              before applying them.
            </li>
            <li>
              <strong>Geography approximation:</strong> Geographic matching is based on tagged metadata.
              Tools tagged for a region may not be equally applicable across all contexts within that region.
            </li>
            <li>
              <strong>Single turn constraint:</strong> The system processes one challenge at a time. Complex,
              multi-part challenges may benefit from being broken into focused sub-questions across multiple
              turns.
            </li>
          </ul>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Section 5 — Feedback (bg-cgiar-light)                              */}
      {/* ------------------------------------------------------------------ */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-14">
        <div className="flex items-center gap-2 mb-4">
          <MessageSquare size={22} className="text-cgiar-accent" />
          <h2 className="text-2xl font-bold text-gray-900">Feedback & Issue Reporting</h2>
        </div>
        <p className="text-gray-600 leading-relaxed mb-6">
          If you encounter unexpected assistant behaviour, factually incorrect output, or want to suggest a
          tool that should be added to the corpus, please contact the CGIAR EE Toolbox team:
        </p>
        <a
          href="mailto:ee-toolbox@cgiar.org"
          className="inline-flex items-center gap-1.5 text-cgiar-accent text-sm font-medium hover:underline"
        >
          ee-toolbox@cgiar.org <ExternalLink size={14} />
        </a>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* CGIAR Attribution footer                                            */}
      {/* ------------------------------------------------------------------ */}
      <footer className="bg-cgiar-dark text-white py-12">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="flex items-center justify-center gap-2 mb-4">
            <Leaf size={24} className="text-cgiar-accent" />
            <span className="text-lg font-bold">CGIAR</span>
          </div>
          <p className="text-white/80 text-sm max-w-xl mx-auto leading-relaxed mb-2">
            CGIAR is a global research partnership for a food-secure future
            dedicated to transforming food, land, and water systems in a climate
            crisis.
          </p>
          <p className="text-white/70 text-sm mb-1">
            Part of the CGIAR Scaling for Impact Initiative
          </p>
          <p className="text-white/70 text-sm mb-4">
            Area of Work 3: Enabling Environment
          </p>
          <a
            href="https://www.cgiar.org/"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-cgiar-accent text-sm font-medium hover:underline"
          >
            Learn more about CGIAR
            <ExternalLink size={14} />
          </a>
        </div>
      </footer>
    </div>
  );
}
