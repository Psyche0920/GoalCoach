// Real-time Learned Vocabulary Matcher for Pinyin Practice
// Dynamically binds pinyin phonemes and syllables to words the learner has ACTUALLY studied.
// If the user has not studied any words with the sound, falls back to pure pinyin display.

import { CurriculumConcept, LearnerState } from '../types.ts';

export interface LearnedVocabItem {
  hanzi: string;
  pinyin: string;
  meaningEn: string;
  sourceConceptId: string;
  sourceConceptTitle: string;
  syllables: string[]; // ['ni', 'hao'] without tone accents
  tones: number[]; // [3, 3]
}

// Strip tone accents to get base syllable letters
export const stripToneAccents = (pinyin: string): string => {
  return pinyin
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/ü/g, 'v')
    .trim();
};

// Extract all learned vocabulary items from learnerState + concepts
export const extractLearnedVocabPool = (
  learnerState: LearnerState | null,
  concepts: CurriculumConcept[]
): LearnedVocabItem[] => {
  if (!learnerState?.mastery) return [];

  const pool: LearnedVocabItem[] = [];
  const seenHanzi = new Set<string>();

  for (const concept of concepts) {
    const mastery = learnerState.mastery[concept.conceptId];
    const isLearned = (mastery?.masteryScore || 0) >= 0.65 || (mastery?.evidenceCount || 0) > 0;
    if (!isLearned) continue;

    // 1. From tailored examples
    if (concept.tailoredExamples) {
      for (const ex of Object.values(concept.tailoredExamples)) {
        if (!ex?.zh || seenHanzi.has(ex.zh)) continue;

        // Clean parenthetical annotations like "喝茶 (chá)" -> "喝茶"
        const cleanHanzi = ex.zh.replace(/\s*\([^)]*\)/g, '').trim();
        if (!cleanHanzi || seenHanzi.has(cleanHanzi)) continue;
        seenHanzi.add(cleanHanzi);

        const cleanPinyin = (ex.pinyin || '').replace(/\s*\([^)]*\)/g, '').trim();
        const baseSyllables = stripToneAccents(cleanPinyin).split(/\s+/);

        pool.push({
          hanzi: cleanHanzi,
          pinyin: cleanPinyin || cleanHanzi,
          meaningEn: ex.en || concept.titleEn,
          sourceConceptId: concept.conceptId,
          sourceConceptTitle: concept.titleZh,
          syllables: baseSyllables,
          tones: extractTonesFromPinyin(cleanPinyin),
        });
      }
    }

    // 2. From vocabularyFocus if Chinese characters
    if (concept.vocabularyFocus && Array.isArray(concept.vocabularyFocus)) {
      for (const word of concept.vocabularyFocus) {
        if (/[\u4e00-\u9fa5]/.test(word) && !seenHanzi.has(word)) {
          seenHanzi.add(word);
          pool.push({
            hanzi: word,
            pinyin: word,
            meaningEn: concept.titleEn,
            sourceConceptId: concept.conceptId,
            sourceConceptTitle: concept.titleZh,
            syllables: [stripToneAccents(word)],
            tones: [],
          });
        }
      }
    }
  }

  return pool;
};

// Helper to deduce tones from standard pinyin accent marks
export const extractTonesFromPinyin = (pinyin: string): number[] => {
  const words = pinyin.split(/\s+/);
  return words.map((w) => {
    if (/[āēīōūǖ]/.test(w)) return 1;
    if (/[áéíóúǘ]/.test(w)) return 2;
    if (/[ǎěǐǒǔǚ]/.test(w)) return 3;
    if (/[àèìòùǜ]/.test(w)) return 4;
    return 0; // neutral
  });
};

export interface MatchQuery {
  targetPinyin?: string; // e.g. "bā", "mā", "zhī", "nǐ hǎo"
  initial?: string; // e.g. "b", "zh", "sh", "j"
  final?: string; // e.g. "an", "ang", "ai", "ao"
  tone?: number; // 1, 2, 3, 4, 0
  sandhiRuleId?: string; // "sandhi_3_3", "sandhi_bu", "sandhi_yi"
}

// Find a matching vocabulary word that the user has ACTUALLY learned
export const matchLearnedVocab = (
  query: MatchQuery,
  learnedPool: LearnedVocabItem[]
): LearnedVocabItem | null => {
  if (learnedPool.length === 0) return null;

  // 1. Sandhi rule matching
  if (query.sandhiRuleId) {
    if (query.sandhiRuleId.includes('3_3')) {
      const match = learnedPool.find(
        (item) => item.hanzi.includes('你好') || item.hanzi.includes('可以') || item.hanzi.includes('很好')
      );
      if (match) return match;
    }
    if (query.sandhiRuleId.includes('bu')) {
      const match = learnedPool.find((item) => item.hanzi.includes('不'));
      if (match) return match;
    }
    if (query.sandhiRuleId.includes('yi')) {
      const match = learnedPool.find((item) => item.hanzi.includes('一'));
      if (match) return match;
    }
  }

  // 2. Exact syllable matching
  if (query.targetPinyin) {
    const baseTarget = stripToneAccents(query.targetPinyin);
    // Direct match against syllables
    const directMatch = learnedPool.find((item) => {
      const itemBases = item.syllables.map(stripToneAccents);
      return itemBases.includes(baseTarget) || stripToneAccents(item.pinyin).includes(baseTarget);
    });
    if (directMatch) return directMatch;
  }

  // 3. Initial matching (e.g. words starting with "zh", "sh", "b", "m")
  if (query.initial) {
    const initMatch = learnedPool.find((item) => {
      return item.syllables.some((syl) => syl.startsWith(query.initial!.toLowerCase()));
    });
    if (initMatch) return initMatch;
  }

  // 4. Final matching (e.g. words ending in "-an", "-ang", "ai")
  if (query.final) {
    const finalClean = query.final.toLowerCase().replace(/ü/g, 'v');
    const finalMatch = learnedPool.find((item) => {
      return item.syllables.some((syl) => syl.endsWith(finalClean));
    });
    if (finalMatch) return finalMatch;
  }

  // 5. Tone matching
  if (typeof query.tone === 'number') {
    const toneMatch = learnedPool.find((item) => item.tones.includes(query.tone!));
    if (toneMatch) return toneMatch;
  }

  return null;
};
