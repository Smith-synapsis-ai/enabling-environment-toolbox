import { Leaf, Shield, BarChart3, Scale, Store, Smartphone, MessageSquare, Search, Compass, Users, Globe, Target, ArrowRight, ExternalLink } from 'lucide-react';

const pillars = [
  {
    icon: Shield,
    title: 'Gender Equality and Social Inclusion',
    description:
      'Methods, frameworks, scorecards, manuals, toolkits, guides, briefs, scales, matrices that indicate how an innovation can close enabling environment barriers related to inclusion for marginalized groups of people.',
  },
  {
    icon: BarChart3,
    title: 'Monitoring, Evaluation and Learning',
    description:
      'Methods, frameworks, and tools that indicate how an innovation can close enabling environment barriers related to feedback loops for iterative improvement.',
  },
  {
    icon: Scale,
    title: 'Policy and Regulatory',
    description:
      'Methods, frameworks, and tools that indicate how an innovation can reduce policies and institutional bottlenecks and guide innovations at scale.',
  },
  {
    icon: Store,
    title: 'Market Systems',
    description:
      'Methods, frameworks, and tools that indicate how an innovation can address constraints to effective functioning of markets such as market actors (producers, firms, consumers), supporting services (finance, infrastructure, information, logistics), and the formal and informal rules (policies, standards, norms) that shape market behavior and access.',
  },
  {
    icon: Smartphone,
    title: 'Digital and Financial Services',
    description:
      'Methods, frameworks, and tools that indicate how an innovation can close enabling environment barriers related to technological integration and financial access using AI and digital tools to enhance scaling efficiency and adaptability as well as accessible, targeted financing opportunities.',
  },
];

const domains = [
  {
    title: 'Agri-food Systems',
    description:
      'The integrated system through which food and agricultural products are produced, processed, distributed, and consumed, representing the primary level where enabling environment pillars translate into development outcomes (e.g., food security, livelihoods, and sustainability).',
    color: 'bg-green-500',
  },
  {
    title: 'Scaling Innovation',
    description:
      'The process through which innovations are adopted, expanded, and sustained across systems and contexts, translating enabling environment conditions into large-scale development outcomes.',
    color: 'bg-blue-500',
  },
  {
    title: 'Climate Resilience',
    description:
      'The capacity of systems and populations to withstand, adapt to, and recover from climate risks, representing a critical outcome of effective enabling environment conditions and innovation scaling.',
    color: 'bg-orange-500',
  },
];

const howItWorks = [
  {
    step: 1,
    icon: MessageSquare,
    title: 'Describe Your Challenge',
    description:
      'Tell our AI assistant about your context, geography, and enabling environment challenge.',
  },
  {
    step: 2,
    icon: Search,
    title: 'Get Smart Recommendations',
    description:
      'Our system searches 90+ curated tools using semantic understanding to find the best matches.',
  },
  {
    step: 3,
    icon: Compass,
    title: 'Apply & Adapt',
    description:
      'Access detailed guidance, methodology, and resources to apply tools in your specific context.',
  },
];

const team = [
  {
    name: 'Taisa Marotta Brosler',
    initials: 'TM',
    role: 'Product Manager',
    organization: 'CGIAR',
    bio: 'Bio coming soon',
    color: 'bg-emerald-600',
  },
  {
    name: 'Ojongetakah Enokenwa Baa (Ojong)',
    initials: 'OE',
    role: 'Domain Expert & Coordinator',
    organization: 'CGIAR',
    bio: 'Bio coming soon',
    color: 'bg-teal-600',
  },
  {
    name: 'Samuel Adedoyin',
    initials: 'SA',
    role: 'Data Engineer',
    organization: 'CGIAR',
    bio: 'Bio coming soon',
    color: 'bg-cyan-700',
  },
  {
    name: 'Jose Luis Berenguer',
    initials: 'JB',
    role: 'Tech Lead / AI & Data Engineering',
    organization: 'Synapsis Analytics',
    bio: 'Bio coming soon',
    color: 'bg-blue-700',
  },
];

const stats = [
  { label: 'Tools', value: '90+' },
  { label: 'Pillars', value: '5' },
  { label: 'Domains', value: '3' },
  { label: 'Countries', value: '30+' },
];

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-cgiar-light pt-16">
      {/* ------------------------------------------------------------------ */}
      {/* 1. Hero with stats                                                  */}
      {/* ------------------------------------------------------------------ */}
      <div className="bg-cgiar-dark text-white py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <Leaf size={40} className="text-cgiar-accent mx-auto mb-4" aria-hidden="true" />
          <h1 className="text-3xl sm:text-4xl font-bold mb-4">
            About the Enabling Environment
          </h1>
          <p className="text-lg text-white/80 max-w-2xl mx-auto leading-relaxed">
            The Enabling Environment Toolbox is a curated collection of tools,
            frameworks, methods, and resources developed by CGIAR and partners to
            support researchers, policymakers, and development practitioners
            working to transform agricultural and food systems.
          </p>

          {/* Stats row */}
          <div className="mt-8 flex flex-wrap items-center justify-center gap-6 sm:gap-10">
            {stats.map((s, i) => (
              <div key={s.label} className="flex items-center gap-2">
                <span className="text-2xl font-bold text-cgiar-accent">
                  {s.value}
                </span>
                <span className="text-sm text-white/70">{s.label}</span>
                {i < stats.length - 1 && (
                  <span className="hidden sm:inline text-white/20 ml-4">|</span>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* 2. Mission & Background                                             */}
      {/* ------------------------------------------------------------------ */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-14">
        {/* Mission */}
        <div className="flex items-center gap-2 mb-4">
          <Target size={22} className="text-cgiar-accent" aria-hidden="true" />
          <h2 className="text-2xl font-bold text-gray-900">Our Mission</h2>
        </div>
        <p className="text-gray-600 leading-relaxed mb-6">
          The Enabling Environment Toolbox is a digital, modular, AI-assisted
          platform that curates and connects methods aligned to CGIAR's enabling
          environment pillars. It guides users through application and adaptation
          across countries and regions, seeking to strengthen the systemic
          conditions for scaling inclusive agri-food and climate innovations.
        </p>

        {/* Background */}
        <div className="flex items-center gap-2 mb-4">
          <Globe size={22} className="text-cgiar-accent" aria-hidden="true" />
          <h2 className="text-2xl font-bold text-gray-900">Background</h2>
        </div>
        <p className="text-gray-600 leading-relaxed mb-6">
          Developed under CGIAR's Scaling for Impact initiative (Area of Work 3),
          this toolbox addresses a critical gap: while CGIAR and partners have
          developed numerous tools, frameworks, and methods for analyzing and
          shaping enabling environments, these resources are scattered across
          publications, websites, and institutional repositories. The Enabling
          Environment Toolbox brings them together in one searchable, AI-powered
          platform, making it easier for researchers, policymakers, and
          development practitioners to find exactly the right resource for their
          specific challenge.
        </p>

        {/* What is the Enabling Environment */}
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          What is the Enabling Environment?
        </h2>
        <p className="text-gray-600 leading-relaxed">
          The enabling environment refers to the broader conditions — policies,
          institutions, markets, social norms, and digital infrastructure — that
          either facilitate or constrain the adoption and scaling of agricultural
          innovations. Understanding and shaping these conditions is critical for
          achieving sustainable development outcomes.
        </p>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* 3. Tagline                                                          */}
      {/* ------------------------------------------------------------------ */}
      <div className="bg-white py-10">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <p className="text-2xl sm:text-3xl font-semibold italic text-cgiar-green tracking-tight">
            "The tools, the cases, the science"
          </p>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* 4. How It Works                                                     */}
      {/* ------------------------------------------------------------------ */}
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-14">
        <h2 className="text-2xl font-bold text-gray-900 mb-2 text-center">
          How It Works
        </h2>
        <p className="text-gray-500 text-center mb-10 max-w-xl mx-auto">
          Find the right enabling environment tool in three simple steps.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {howItWorks.map((item) => (
            <div
              key={item.step}
              className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 text-center relative"
            >
              {/* Step number circle */}
              <div className="w-10 h-10 rounded-full bg-cgiar-accent text-white text-lg font-bold flex items-center justify-center mx-auto mb-4">
                {item.step}
              </div>
              <item.icon size={28} className="text-cgiar-accent mx-auto mb-3" aria-hidden="true" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                {item.title}
              </h3>
              <p className="text-sm text-gray-600 leading-relaxed">
                {item.description}
              </p>
            </div>
          ))}
        </div>

        <div className="mt-8 text-center">
          <a
            href="/tutorial"
            className="inline-flex items-center gap-2 text-cgiar-green font-medium hover:underline focus:underline"
          >
            View the full tutorial
            <ArrowRight size={16} aria-hidden="true" />
          </a>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* 5. The Five Pillars                                                 */}
      {/* ------------------------------------------------------------------ */}
      <div className="bg-white py-14">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-2 text-center">
            The Five Pillars
          </h2>
          <p className="text-gray-500 text-center mb-8 max-w-xl mx-auto">
            The enabling environment is organized across five thematic pillars,
            each representing a critical dimension for scaling agricultural
            innovations.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {pillars.map((pillar) => (
              <div
                key={pillar.title}
                className="bg-cgiar-light rounded-xl p-6"
              >
                <pillar.icon size={28} className="text-cgiar-accent mb-3" aria-hidden="true" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  {pillar.title}
                </h3>
                <p className="text-sm text-gray-600 leading-relaxed">
                  {pillar.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* 6. The Three Domains                                                */}
      {/* ------------------------------------------------------------------ */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-14">
        <h2 className="text-2xl font-bold text-gray-900 mb-2 text-center">
          The Three Domains
        </h2>
        <p className="text-gray-500 text-center mb-8 max-w-xl mx-auto">
          Tools are further classified across three cross-cutting domains that
          reflect CGIAR's strategic priorities.
        </p>
        <div className="space-y-6">
          {domains.map((domain) => (
            <div
              key={domain.title}
              className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 flex gap-4"
            >
              <div
                className={`w-1.5 flex-shrink-0 rounded-full ${domain.color}`}
              />
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  {domain.title}
                </h3>
                <p className="text-sm text-gray-600 leading-relaxed">
                  {domain.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* 7. Meet the Team                                                    */}
      {/* ------------------------------------------------------------------ */}
      <div className="bg-white py-14">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-center gap-2 mb-2">
            <Users size={22} className="text-cgiar-accent" aria-hidden="true" />
            <h2 className="text-2xl font-bold text-gray-900">
              Meet the Team
            </h2>
          </div>
          <p className="text-gray-500 text-center mb-10 max-w-xl mx-auto">
            The people behind the Enabling Environment Toolbox.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {team.map((member) => (
              <div
                key={member.name}
                className="bg-cgiar-light rounded-xl p-6 text-center"
              >
                {/* Avatar */}
                <div
                  className={`w-16 h-16 ${member.color} rounded-full flex items-center justify-center mx-auto mb-4`}
                >
                  <span className="text-white text-xl font-bold">
                    {member.initials}
                  </span>
                </div>
                <h3 className="text-base font-semibold text-gray-900 mb-1">
                  {member.name}
                </h3>
                <p className="text-sm text-cgiar-accent font-medium mb-1">
                  {member.role}
                </p>
                <p className="text-xs text-gray-500 mb-3">
                  {member.organization}
                </p>
                <p className="text-xs text-gray-500 italic">{member.bio}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* 8. CGIAR Attribution footer                                         */}
      {/* ------------------------------------------------------------------ */}
      <footer className="bg-cgiar-dark text-white py-12">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="flex items-center justify-center gap-2 mb-4">
            <Leaf size={24} className="text-cgiar-accent" aria-hidden="true" />
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
            <ExternalLink size={14} aria-hidden="true" />
          </a>
        </div>
      </footer>
    </div>
  );
}
