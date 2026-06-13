/**
 * Illustrative success stories for the EE Toolbox.
 *
 * IMPORTANT — HONESTY NOTE:
 * These are *illustrative* example pathways that demonstrate how the Scaling
 * Challenge Assistant composes real tools from the EE Toolbox catalog into an
 * integrated, multi-pillar enabling-environment pathway. They are NOT verified
 * field case studies and contain NO fabricated outcome metrics. Every tool
 * referenced below is a real entry in `frontend/src/data/tools.ts`; the `id`
 * is the CGSpace handle and links into `/catalog?tool=<id>`, which opens that
 * tool's profile panel.
 *
 * This file is purely static frontend content — adding or editing it requires
 * no backend deploy.
 */

export interface StoryTool {
  /** CGSpace handle, matches the `id` field on the catalog tool record. */
  id: string;
  /** Real catalog title (referenced verbatim). */
  title: string;
  /** How this tool contributes to the pathway. */
  role: string;
}

export interface PathwayStep {
  /** Enabling-environment pillar this step advances. */
  pillar: string;
  /** What the assistant surfaces at this step of the pathway. */
  detail: string;
}

export interface SuccessStory {
  id: string;
  /** Short title shown on the card. */
  title: string;
  /** Region / geography label. */
  region: string;
  /** The agricultural innovation challenge the user brings to the assistant. */
  challenge: string;
  /** One-line synthesis of the integrated pathway. */
  synthesis: string;
  /** The integrated multi-pillar pathway, pillar by pillar. */
  pathway: PathwayStep[];
  /** Pillars this story touches (for the pill row). */
  pillars: string[];
  /** The real catalog tools this pathway draws on. */
  tools: StoryTool[];
}

export const successStories: SuccessStory[] = [
  {
    id: 'climate-smart-dairy-credit-kenya',
    title: 'Scaling climate-smart dairy credit for smallholders in Kenya',
    region: 'Kenya · East Africa',
    challenge:
      'A dairy development programme wants smallholder farmers to adopt climate-smart feed and fodder practices, but uptake is stalled because farmers cannot access affordable credit and lenders cannot price the weather risk on a dairy enterprise.',
    synthesis:
      'Map the dairy value chain, ground the lending case in feed-and-fodder economics, de-risk it with weather index insurance, and channel finance through digitised cooperatives.',
    pillars: ['Market Systems', 'Digital & Financial Services', 'M&E & Learning'],
    pathway: [
      {
        pillar: 'Market Systems',
        detail:
          'Start by mapping where value and risk sit along the dairy chain so the credit product targets the right actors and the right bottleneck.',
      },
      {
        pillar: 'Market Systems',
        detail:
          'Anchor the lending case in the economics of climate-smart feed and fodder — the input cost that most often determines whether a dairy enterprise is bankable.',
      },
      {
        pillar: 'Digital & Financial Services',
        detail:
          'Pair the loan with weather index insurance so lenders can price drought risk, then deliver and service the credit through digitised farmer cooperatives that already aggregate smallholders.',
      },
    ],
    tools: [
      {
        id: '10568-100636',
        title:
          'USAID Kenya Crops and Dairy Market Systems Activity: Dairy value chain assessment September 2018',
        role: 'Maps actors, margins and constraints across the Kenyan dairy value chain to locate the bottleneck.',
      },
      {
        id: '10568-100637',
        title:
          'USAID - Kenya Crops and Dairy Market Systems (KCDMS): Feed and fodder value chain assessment report',
        role: 'Grounds the lending case in feed-and-fodder economics, the key cost driver of dairy bankability.',
      },
      {
        id: '10568-100343',
        title:
          'South-South Collaboration in CCAFS for developing capacity on weather index insurance',
        role: 'Provides the weather index insurance approach lenders need to price drought risk on dairy loans.',
      },
      {
        id: '10568-100562',
        title:
          'Digitising farmer cooperatives to improve their financial and operational efficiency',
        role: 'Channels credit through digitised cooperatives that aggregate smallholders and lower delivery cost.',
      },
    ],
  },
  {
    id: 'seed-system-policy-east-africa',
    title: 'Strengthening seed-system policy for climate adaptation in East Africa',
    region: 'Kenya, Uganda & Tanzania · East Africa',
    challenge:
      'A national seed authority wants farmers to access climate-adapted varieties faster, but the formal seed system is slow and a policy framework for farmer-managed and open-source seed is missing.',
    synthesis:
      'Use open-source seed-system policy options as the spine, learn from a national act that pulled climate-smart varieties into public procurement, and de-risk the rollout with promotion lessons from a real variety scale-up.',
    pillars: ['Policy & Regulatory', 'Scaling Innovations', 'M&E & Learning'],
    pathway: [
      {
        pillar: 'Policy & Regulatory',
        detail:
          'Open the policy menu for farmer-managed and open-source seed systems so climate-adapted varieties can move through both formal and informal channels.',
      },
      {
        pillar: 'Policy & Regulatory',
        detail:
          'Borrow a proven demand-side lever: a national food-security act that stimulated public sourcing of climate-resilient crops, showing how procurement policy pulls varieties into use.',
      },
      {
        pillar: 'Scaling Innovations',
        detail:
          'De-risk the rollout with documented lessons on promoting a new variety so the policy is paired with a realistic adoption pathway.',
      },
    ],
    tools: [
      {
        id: '10568-100157',
        title:
          "Building resilience through 'Open Source Seed Systems' for climate change adaptation in Kenya, Uganda, and Tanzania: What are the options for policy?",
        role: 'The policy spine: options for farmer-managed and open-source seed systems across three East African countries.',
      },
      {
        id: '10568-100156',
        title:
          'National food security act supports climate smart agriculture in India by stimulating the sourcing of small Millets: An evaluation of Bioversity’s efforts to promote small Millets in India',
        role: 'A demand-side analogue showing how procurement policy can pull climate-resilient crops into use.',
      },
      {
        id: '10568-100676',
        title:
          'Lessons for promotion of new agricultural technology: a case of Vijay wheat variety in Nepal',
        role: 'Documented promotion-and-adoption lessons to pair the policy with a realistic scale-up pathway.',
      },
    ],
  },
  {
    id: 'gender-inclusive-livestock-value-chains',
    title: 'Building gender-inclusive livestock value chains in East Africa',
    region: 'Ethiopia & East Africa',
    challenge:
      'A livestock programme is designing interventions that risk reaching only male household heads, missing the women who do much of the feeding and herd management — and has no structured way to surface gendered entry points.',
    synthesis:
      'Diagnose gendered roles with a feed-assessment instrument, ground the design in a livestock-gender evidence review, build practitioner capacity with a gender-and-livestock training, and steer toward what demonstrably empowers women livestock farmers.',
    pillars: ['Gender Equality & Social Inclusion', 'Market Systems', 'M&E & Learning'],
    pathway: [
      {
        pillar: 'Gender Equality & Social Inclusion',
        detail:
          'Diagnose who does what in feeding and herd management with a gendered feed-assessment instrument so the intervention design starts from real roles, not assumptions.',
      },
      {
        pillar: 'Gender Equality & Social Inclusion',
        detail:
          'Ground the design in a livestock-specific gender evidence review to identify concrete entry points for gender-responsive research and development.',
      },
      {
        pillar: 'M&E & Learning',
        detail:
          'Build practitioner capacity with a gender-and-livestock training package, then steer the portfolio toward interventions that synthesised evidence shows actually empower women livestock farmers.',
      },
    ],
    tools: [
      {
        id: '10568-100243',
        title: 'Gendered Feed Assessment Tool (G-FEAST) focus group discussion guide',
        role: 'A ready instrument for diagnosing gendered roles in feeding and herd management.',
      },
      {
        id: '10568-100208',
        title:
          'Gender issues in livestock production in Ethiopia: A review of literature to identify potential entry points for gender responsive research and development',
        role: 'A livestock-specific evidence review surfacing concrete gender-responsive entry points.',
      },
      {
        id: '10568-100516',
        title:
          "Report of the FAO training 'Gender and Livestock Development in East Africa', Nairobi, Kenya, 28-30 May 2018",
        role: 'A capacity-building package for practitioners designing gender-responsive livestock work.',
      },
      {
        id: '10568-100513',
        title: 'What works to empower women livestock farmers? A synthesis of GAAP2 Livestock projects',
        role: 'Synthesised evidence on which interventions actually empower women livestock farmers.',
      },
    ],
  },
  {
    id: 'digital-gender-gap-agribusiness',
    title: 'Closing the digital gender gap in agribusiness',
    region: 'Sub-Saharan Africa',
    challenge:
      'A digital agriculture initiative is rolling out advisory and marketplace services, but women agripreneurs are being left behind by the design — and the team has no structured way to make the rollout inclusive and commercially durable.',
    synthesis:
      'Frame the digital gender gap, build inclusion into the business model, support women specifically in agribusiness, and route services through digitised cooperatives for reach.',
    pillars: ['Digital & Financial Services', 'Gender Equality & Social Inclusion', 'Market Systems'],
    pathway: [
      {
        pillar: 'Digital & Financial Services',
        detail:
          'Name the problem precisely — the gender gap in agricultural digitalisation — so inclusion is a design requirement, not an afterthought.',
      },
      {
        pillar: 'Market Systems',
        detail:
          'Build the inclusion goal into a durable multi-sided digital agribusiness business model rather than a one-off pilot.',
      },
      {
        pillar: 'Gender Equality & Social Inclusion',
        detail:
          'Apply targeted guidance on supporting women in agribusiness, and route services through digitised cooperatives so the reach actually lands with women aggregated in farmer groups.',
      },
    ],
    tools: [
      {
        id: '10568-100289',
        title: 'Spore 192: Digitalising agriculture - Bridging the gender gap',
        role: 'Frames the digital gender gap so inclusion becomes a design requirement.',
      },
      {
        id: '10568-100565',
        title:
          'Building multi-sided business models for stronger digital agribusiness market development',
        role: 'Provides the durable, multi-sided business model the service must sit inside.',
      },
      {
        id: '10568-100592',
        title: 'Gender and digitalisation supporting women in agribusiness',
        role: 'Targeted guidance for supporting women specifically within digital agribusiness.',
      },
      {
        id: '10568-100562',
        title:
          'Digitising farmer cooperatives to improve their financial and operational efficiency',
        role: 'Routes digital services through cooperatives so reach lands with women in farmer groups.',
      },
    ],
  },
  {
    id: 'scaling-climate-smart-coffee-cocoa',
    title: 'Scaling climate-smart coffee and cocoa',
    region: 'Latin America & West Africa',
    challenge:
      'A perennial-crop programme wants to move climate-smart coffee and cocoa practices from awareness to genuine scale, but growers struggle to translate climate information into farm decisions and the scaling approach is undefined.',
    synthesis:
      'Raise sector-specific climate-smart awareness for coffee and cocoa, turn awareness into decisions, then apply a deliberate scaling approach for both crops.',
    pillars: ['Climate Resilience', 'Market Systems', 'Scaling Innovations'],
    pathway: [
      {
        pillar: 'Climate Resilience',
        detail:
          'Build climate-smart awareness and decision-making capacity tuned to the coffee sector, then do the same for cocoa, so growers can read climate signals for their specific crop.',
      },
      {
        pillar: 'Market Systems',
        detail:
          'Connect that awareness to value-chain decisions so climate-smart practice changes what growers and buyers actually do.',
      },
      {
        pillar: 'Scaling Innovations',
        detail:
          'Apply a deliberate, documented approach to scaling climate-smart coffee and cocoa rather than relying on organic spread.',
      },
    ],
    tools: [
      {
        id: '10568-100136',
        title: 'Improving coffee sector Climate-Smart Awareness and decision-making',
        role: 'Builds coffee-specific climate-smart awareness and decision-making capacity.',
      },
      {
        id: '10568-100137',
        title: 'Improving Cocoa sector Climate-Smart Awareness and decision-making',
        role: 'Mirrors the awareness-and-decision approach for the cocoa sector.',
      },
      {
        id: '10568-100190',
        title: 'Scaling climate smart coffee and cocoa',
        role: 'Provides the deliberate scaling approach for both perennial crops.',
      },
    ],
  },
  {
    id: 'climate-information-services-livelihoods',
    title: 'Using climate information services to protect vulnerable livelihoods',
    region: 'Senegal, Uganda & East Africa',
    challenge:
      'A coastal and rural livelihoods programme wants climate information services to reach the people who most need them, but the policy environment, financial protection, and investment case are not yet aligned.',
    synthesis:
      'Show how climate information services already protect livelihoods, anchor them in a national adaptation policy analysis, add financial protection via weather index insurance, and direct investment with a value-chain options assessment.',
    pillars: ['Climate Resilience', 'Policy & Regulatory', 'Financial Services', 'M&E & Learning'],
    pathway: [
      {
        pillar: 'Climate Resilience',
        detail:
          'Start from demonstrated impact — how climate information services already save lives and livelihoods — to make the case concrete for decision-makers.',
      },
      {
        pillar: 'Policy & Regulatory',
        detail:
          'Anchor the services in a national climate-adaptation policy situation analysis so they are embedded in, not parallel to, government plans.',
      },
      {
        pillar: 'Financial Services',
        detail:
          'Add financial protection with weather index insurance, and direct scarce investment using a probabilistic assessment of value-chain investment options.',
      },
    ],
    tools: [
      {
        id: '10568-100125',
        title:
          'Forewarned is Forearmed how Climate Information Services are Saving the Lives and Livelihoods of Senegalese Fisherfolk',
        role: 'Demonstrates the real-world impact of climate information services on vulnerable livelihoods.',
      },
      {
        id: '10568-100216',
        title:
          'Policy Action for Climate Change Adaptation (PACCA) II Project: Situation Analysis Report - Uganda',
        role: 'A national adaptation policy situation analysis to embed the services in government plans.',
      },
      {
        id: '10568-100343',
        title:
          'South-South Collaboration in CCAFS for developing capacity on weather index insurance',
        role: 'Adds the financial-protection layer through weather index insurance capacity.',
      },
      {
        id: '10568-100142',
        title:
          'Probabilistic assessment of investment options in honey value chains in Lamu county, Kenya',
        role: 'Directs scarce investment with a probabilistic value-chain options assessment.',
      },
    ],
  },
];
