import { Link } from 'react-router-dom';
import {
  Sparkles,
  Info,
  ArrowRight,
  ExternalLink,
  Leaf,
  MapPin,
  Route as RouteIcon,
  Wrench,
} from 'lucide-react';
import { successStories } from '../data/successStories';

export default function SuccessStoriesPage() {
  return (
    <div className="min-h-screen bg-cgiar-light pt-16">
      {/* ------------------------------------------------------------------ */}
      {/* Hero                                                                */}
      {/* ------------------------------------------------------------------ */}
      <div className="bg-cgiar-dark text-white py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <Sparkles size={40} className="text-cgiar-accent mx-auto mb-4" aria-hidden="true" />
          <h1 className="text-3xl sm:text-4xl font-bold mb-4">Success Stories</h1>
          <p className="text-lg text-white/80 max-w-2xl mx-auto leading-relaxed">
            How the EE Toolbox turns an agricultural innovation challenge into an integrated
            pathway of enabling-environment tools — composed across the eight pillars.
          </p>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Honesty disclaimer                                                  */}
      {/* ------------------------------------------------------------------ */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pt-10">
        <div className="flex items-start gap-3 rounded-lg border border-amber-300 bg-amber-50 p-4">
          <Info size={20} className="text-amber-600 mt-0.5 shrink-0" aria-hidden="true" />
          <p className="text-sm text-amber-900 leading-relaxed">
            <strong>These are illustrative example pathways.</strong> The EE Toolbox is newly
            launched, so the stories below demonstrate how the Scaling Challenge Assistant composes{' '}
            <em>real tools from the catalog</em> into an integrated, multi-pillar pathway for a
            realistic challenge. They are not verified field case studies and contain no claimed
            outcome figures. Every tool named is a genuine catalog entry — select it to open its
            full profile. See the{' '}
            <Link to="/transparency" className="font-medium underline hover:text-amber-700">
              AI Transparency
            </Link>{' '}
            page for how the assistant works.
          </p>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Stories                                                             */}
      {/* ------------------------------------------------------------------ */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-10">
        {successStories.map((story, index) => (
          <article
            key={story.id}
            id={story.id}
            className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden"
          >
            {/* Header band */}
            <div className="bg-cgiar-green/5 border-b border-gray-100 px-6 py-5 sm:px-8">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-cgiar-green mb-2">
                <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-cgiar-green text-white">
                  {index + 1}
                </span>
                <MapPin size={14} aria-hidden="true" />
                <span className="normal-case tracking-normal text-gray-600 font-medium">
                  {story.region}
                </span>
              </div>
              <h2 className="text-xl sm:text-2xl font-bold text-gray-900">{story.title}</h2>
              <div className="mt-3 flex flex-wrap gap-2">
                {story.pillars.map(pillar => (
                  <span
                    key={pillar}
                    className="inline-block px-2.5 py-1 rounded-full bg-s4i-purple/15 text-s4i-purple-deep text-xs font-medium"
                  >
                    {pillar}
                  </span>
                ))}
              </div>
            </div>

            <div className="px-6 py-6 sm:px-8 space-y-6">
              {/* Challenge */}
              <div>
                <h3 className="text-sm font-semibold text-gray-900 mb-1">The challenge</h3>
                <p className="text-gray-600 leading-relaxed text-sm">{story.challenge}</p>
              </div>

              {/* Synthesis */}
              <div className="rounded-lg bg-cgiar-light p-4 border-l-4 border-cgiar-accent">
                <p className="text-sm text-gray-800 leading-relaxed">
                  <strong className="text-cgiar-dark">Integrated pathway:</strong> {story.synthesis}
                </p>
              </div>

              {/* Pathway steps */}
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <RouteIcon size={18} className="text-cgiar-accent" aria-hidden="true" />
                  <h3 className="text-sm font-semibold text-gray-900">
                    How the assistant composes the pathway
                  </h3>
                </div>
                <ol className="space-y-3">
                  {story.pathway.map((step, i) => (
                    <li key={i} className="flex gap-3">
                      <span className="shrink-0 mt-0.5 inline-flex items-center justify-center w-5 h-5 rounded-full bg-cgiar-accent/15 text-cgiar-green text-xs font-bold">
                        {i + 1}
                      </span>
                      <div>
                        <span className="text-xs font-semibold uppercase tracking-wide text-cgiar-green">
                          {step.pillar}
                        </span>
                        <p className="text-sm text-gray-600 leading-relaxed">{step.detail}</p>
                      </div>
                    </li>
                  ))}
                </ol>
              </div>

              {/* Tools it draws on */}
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <Wrench size={18} className="text-cgiar-accent" aria-hidden="true" />
                  <h3 className="text-sm font-semibold text-gray-900">
                    Real catalog tools in this pathway
                  </h3>
                </div>
                <ul className="space-y-2">
                  {story.tools.map(tool => (
                    <li
                      key={tool.id}
                      className="rounded-lg border border-gray-200 hover:border-cgiar-accent transition-colors p-3"
                    >
                      <Link
                        to={`/catalog?tool=${tool.id}`}
                        className="group inline-flex items-start gap-1.5 text-cgiar-green font-medium text-sm hover:underline"
                      >
                        <span>{tool.title}</span>
                        <ExternalLink
                          size={13}
                          className="mt-0.5 shrink-0 opacity-60 group-hover:opacity-100"
                          aria-hidden="true"
                        />
                      </Link>
                      <p className="text-xs text-gray-500 mt-1 leading-relaxed">{tool.role}</p>
                    </li>
                  ))}
                </ul>
              </div>

              {/* CTA */}
              <div className="pt-1">
                <Link
                  to="/assistant"
                  className="inline-flex items-center gap-1.5 text-sm font-medium text-s4i-purple-deep hover:underline"
                >
                  Bring your own challenge to the assistant
                  <ArrowRight size={15} aria-hidden="true" />
                </Link>
              </div>
            </div>
          </article>
        ))}
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Closing CTA band                                                    */}
      {/* ------------------------------------------------------------------ */}
      <div className="bg-white border-t border-gray-200 py-14">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-3">Have a challenge of your own?</h2>
          <p className="text-gray-600 leading-relaxed mb-6 max-w-2xl mx-auto">
            Describe your agricultural innovation challenge to the Scaling Challenge Assistant and it
            will compose an integrated pathway from the real EE Toolbox catalog — or browse the full
            catalog yourself.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <Link
              to="/assistant"
              className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-full bg-cgiar-dark text-white text-sm font-medium hover:bg-cgiar-green transition-colors"
            >
              Open the Assistant
              <ArrowRight size={15} aria-hidden="true" />
            </Link>
            <Link
              to="/catalog"
              className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-full border border-cgiar-dark/30 text-cgiar-dark text-sm font-medium hover:bg-cgiar-light transition-colors"
            >
              Browse the catalog
            </Link>
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* CGIAR Attribution footer                                            */}
      {/* ------------------------------------------------------------------ */}
      <footer className="bg-cgiar-dark text-white py-12">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="flex items-center justify-center gap-2 mb-4">
            <Leaf size={24} className="text-cgiar-accent" aria-hidden="true" />
            <span className="text-lg font-bold">CGIAR</span>
          </div>
          <p className="text-white/80 text-sm max-w-xl mx-auto leading-relaxed mb-2">
            CGIAR is a global research partnership for a food-secure future dedicated to transforming
            food, land, and water systems in a climate crisis.
          </p>
          <p className="text-white/70 text-sm mb-1">
            Part of the CGIAR Scaling for Impact Initiative
          </p>
          <p className="text-white/70 text-sm mb-4">Area of Work 3: Enabling Environment</p>
          <a
            href="https://www.cgiar.org/"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-cgiar-accent text-sm font-medium hover:underline"
          >
            Learn more about CGIAR
            <ExternalLink size={14} aria-hidden="true" />
          </a>
        </div>
      </footer>
    </div>
  );
}
