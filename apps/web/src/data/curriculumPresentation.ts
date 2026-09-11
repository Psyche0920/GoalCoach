import { CurriculumConcept } from '../types.ts';

const SHORT_TITLES: Readonly<Record<string, string>> = {
  hsk1_p01: 'Pinyin Structure',
  hsk1_p02: 'Greeting Tones',
  hsk1_p03: 'Sound Contrasts',
  hsk1_p04: 'Compound Finals',
  hsk1_p05: 'Tone Flow',
  hsk1_p06: 'Natural Rhythm',
  hsk1_c01: 'Greetings',
  hsk1_c02: 'Names',
  hsk1_c03: 'Identity',
  hsk1_c04: 'Yes No Questions',
  hsk1_c05: 'Ask Back',
  hsk1_c07: 'Negation',
  hsk1_c16: 'Wants',
};

const PINYIN_SUMMARIES: Readonly<Record<string, string>> = {
  hsk1_p01: '拼音结构与基础声母',
  hsk1_p02: '四声听辨与发音',
  hsk1_p03: '常见声母对比',
  hsk1_p04: '复韵母与鼻韵母',
  hsk1_p05: '连续声调与变调',
  hsk1_p06: '自然语流与节奏',
};

export function curriculumShortTitle(concept: CurriculumConcept): string {
  if (SHORT_TITLES[concept.conceptId]) return SHORT_TITLES[concept.conceptId];
  const cleaned = concept.titleEn
    .replace(/[\p{Script=Han}]/gu, '')
    .replace(/^(Pinyin\s*\d+|Scenario|General Knowledge|General\s*&\s*Scenario)\s*:\s*/i, '')
    .replace(/[^A-Za-z0-9/\s-]/g, ' ');
  const stopWords = new Set(['a', 'an', 'and', 'the', 'with', 'of', 'to', 'in', 'using']);
  return cleaned.split(/\s+/)
    .filter((word) => word && !stopWords.has(word.toLowerCase()))
    .slice(0, 3)
    .join(' ') || 'Lesson';
}

export function curriculumChineseSummary(concept: CurriculumConcept): string {
  if (PINYIN_SUMMARIES[concept.conceptId]) return PINYIN_SUMMARIES[concept.conceptId];
  return concept.titleZh
    .replace(/^(情境|常识与场景|常识与量词|常识)\s*[：:]\s*/, '')
    .replace(/[（(][^）)]*[）)]/g, '')
    .replace(/^Pinyin\s*\d+\s*:\s*/i, '')
    .trim();
}
