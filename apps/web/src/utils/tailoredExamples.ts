import { CurriculumConcept, TeachingCard } from '../types.ts';

export type SupportedInterest = 'travel' | 'work' | 'dining' | 'daily' | 'general';

export interface TailoredExampleResult {
  zh: string;
  pinyin: string;
  en: string;
  scenarioTag: string;
}

/**
 * Returns tailored example sentence dynamically based on the user's active interest.
 * Priority:
 * 1. concept.tailoredExamples[targetDomain]
 * 2. card.tailoredVariants[targetDomain]
 * 3. concept.tailoredExamples['general']
 * 4. card.exampleZh / card.examplePinyin / card.exampleEn
 */
export function getTailoredExample(
  concept?: CurriculumConcept,
  card?: TeachingCard,
  interest?: string
): TailoredExampleResult {
  const safeInterest = (interest || 'general') as SupportedInterest;

  // 1. Try concept tailored examples
  if (concept?.tailoredExamples && concept.tailoredExamples[safeInterest]) {
    const item = concept.tailoredExamples[safeInterest];
    return {
      zh: item.zh,
      pinyin: item.pinyin,
      en: item.en,
      scenarioTag: getScenarioTagLabel(safeInterest),
    };
  }

  // 2. Try card tailored variants
  if (card?.tailoredVariants && card.tailoredVariants[safeInterest]) {
    const item = card.tailoredVariants[safeInterest];
    return {
      zh: item.exampleZh,
      pinyin: item.examplePinyin,
      en: item.exampleEn,
      scenarioTag: getScenarioTagLabel(safeInterest),
    };
  }

  // 3. Fallback to concept general
  if (concept?.tailoredExamples?.general) {
    const item = concept.tailoredExamples.general;
    return {
      zh: item.zh,
      pinyin: item.pinyin,
      en: item.en,
      scenarioTag: '通用场景',
    };
  }

  // 4. Default card example
  return {
    zh: card?.exampleZh || '你好！很高兴认识你。',
    pinyin: card?.examplePinyin || 'Nǐ hǎo! Hěn gāoxìng rènshi nǐ.',
    en: card?.exampleEn || 'Hello! Nice to meet you.',
    scenarioTag: '标准例句',
  };
}

function getScenarioTagLabel(interest: SupportedInterest): string {
  switch (interest) {
    case 'travel':
      return '✈️ 旅游出行定制例句';
    case 'work':
      return '💼 职场商务定制例句';
    case 'dining':
      return '🍜 美食餐饮定制例句';
    case 'daily':
      return '☕ 日常起居定制例句';
    default:
      return '🌟 HSK 1 标准例句';
  }
}
