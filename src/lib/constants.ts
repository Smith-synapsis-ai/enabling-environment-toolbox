export const COLORS = {
  brandTeal: '#00524D',
  brandTealDark: '#003D39',
  brandTealMid: '#007A72',
  brandTealLight: '#E0F5F0',
  brandPurple: '#6B21A8',
  brandPurpleMid: '#9333EA',
  brandPurpleLight: '#F3E8FF',
  brandGreen: '#16A34A',
  brandGreenLight: '#DCFCE7',
  brandCoralLight: '#FCE4EC',
  brandBlueLight: '#DBEAFE',
  brandBlue: '#2563EB',
  brandOrange: '#D97706',
  brandOrangeLight: '#FEF3C7',
  pageBg: '#F8F9FA',
  textDark: '#1A1A2E',
  textMid: '#4A5568',
} as const

export const PILLARS = [
  'Policy & Institutional',
  'Gender & Social Inclusion',
  'Market Systems',
  'Digital',
  'Financial Services & M&E',
] as const

export const ENABLERS = [
  'Climate Resilience',
  'Scaling of Innovation',
  'Improved Agri-Food Systems',
] as const

export const STAGES = [
  'Established and field-tested',
  'Emerging',
  'Pilot',
  'Conceptual',
] as const

export const TYPES = ['Framework', 'Method', 'Tool', 'Approach', 'Scorecard', 'Guidelines'] as const

export const REGIONS = [
  'All regions',
  'Sub-Saharan Africa',
  'South Asia',
  'Southeast Asia',
  'Latin America',
  'East Africa',
  'West Africa',
  'Southern Africa',
] as const

export const SOURCES = [
  'CG Space',
  'FAO',
  'IFAD',
  'World Bank',
  'Alliance of Bioversity-CIAT',
  'CIMMYT',
  'IRRI',
  'IWMI',
  'ICRISAT',
  'IITA',
  'ILRI',
  'WorldFish',
] as const

export type Pillar = typeof PILLARS[number]
export type Enabler = typeof ENABLERS[number]
export type Stage = typeof STAGES[number]
export type ItemType = typeof TYPES[number]
export type Region = typeof REGIONS[number]
export type Source = typeof SOURCES[number]

export function getTypeColor(type: string): string {
  switch (type.toLowerCase()) {
    case 'framework': return COLORS.brandPurple
    case 'method': return COLORS.brandTeal
    case 'tool': return COLORS.brandGreen
    case 'approach': return COLORS.brandBlue
    case 'scorecard': return COLORS.brandOrange
    case 'guidelines': return '#0891B2'
    default: return COLORS.textMid
  }
}

export function getTypeBg(type: string): string {
  switch (type.toLowerCase()) {
    case 'framework': return COLORS.brandPurpleLight
    case 'method': return COLORS.brandTealLight
    case 'tool': return COLORS.brandGreenLight
    case 'approach': return COLORS.brandBlueLight
    case 'scorecard': return COLORS.brandOrangeLight
    case 'guidelines': return '#ECFEFF'
    default: return '#F3F4F6'
  }
}

export function getPillarColor(_pillar: string): { bg: string; text: string } {
  return { bg: COLORS.brandTealLight, text: COLORS.brandTeal }
}

export function getEnablerColor(_enabler: string): { bg: string; text: string } {
  return { bg: COLORS.brandPurpleLight, text: COLORS.brandPurple }
}

export function getStageColor(stage: string): { bg: string; text: string } {
  switch (stage) {
    case 'Established and field-tested':
      return { bg: COLORS.brandGreenLight, text: COLORS.brandGreen }
    case 'Emerging':
      return { bg: '#FEF3C7', text: '#D97706' }
    case 'Pilot':
      return { bg: COLORS.brandBlueLight, text: COLORS.brandBlue }
    case 'Conceptual':
      return { bg: '#F3F4F6', text: COLORS.textMid }
    default:
      return { bg: '#F3F4F6', text: COLORS.textMid }
  }
}
