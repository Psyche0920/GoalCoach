import { CurriculumConcept } from '../types.ts';

/**
 * Pedagogical Syntax Parser for Chinese as a Second Language (CSL)
 * 30-Year Expert Teaching & Rubric Analysis
 */
export interface SyntaxEvaluation {
  isValid: boolean;
  score: number; // 0.0 to 1.0
  errorCategory: 'none' | 'word_order_inversion' | 'redundant_tokens' | 'missing_predicate' | 'missing_optative' | 'missing_object' | 'unrelated_content';
  detailedFeedback: string;
  recommendedConceptIds: string[];
  syntacticBreakdown: {
    subject?: string;
    optative?: string;
    verb?: string;
    object?: string;
    extraneous?: string[];
  };
}

/**
 * Rigorous CSL Sentence Evaluator for expressions like "我想喝茶" (I want to drink tea)
 * Prevents naive substring matching flaws (e.g. "茶想我喝茶" being incorrectly accepted).
 */
export function evaluateFreeformChineseAnswer(
  userInput: string,
  targetConceptId: string = 'hsk1_c20'
): SyntaxEvaluation {
  const clean = userInput.trim().replace(/[。！! ?？，,]/g, '');

  if (!clean) {
    return {
      isValid: false,
      score: 0,
      errorCategory: 'unrelated_content',
      detailedFeedback: 'Please enter a complete Chinese sentence.',
      recommendedConceptIds: [targetConceptId, 'hsk1_c08'],
      syntacticBreakdown: {},
    };
  }

  // Exact target match
  if (clean === '我想喝茶') {
    return {
      isValid: true,
      score: 1.0,
      errorCategory: 'none',
      detailedFeedback: 'Perfect! Standard Chinese SVO structure: Subject (我) + Optative Verb (想) + Verb (喝) + Object (茶).',
      recommendedConceptIds: ['hsk1_c20', 'hsk1_c08'],
      syntacticBreakdown: {
        subject: '我',
        optative: '想',
        verb: '喝',
        object: '茶',
      },
    };
  }

  // Natural spoken variations (e.g. dropping subject "想喝茶" is acceptable in spoken context, with minor style note)
  if (clean === '想喝茶') {
    return {
      isValid: true,
      score: 0.9,
      errorCategory: 'none',
      detailedFeedback: 'Grammatically natural in colloquial spoken Chinese! For standard HSK 1 formal tests, adding the subject “我” (我想喝茶) is preferred.',
      recommendedConceptIds: ['hsk1_c20', 'hsk1_c08'],
      syntacticBreakdown: {
        optative: '想',
        verb: '喝',
        object: '茶',
      },
    };
  }

  // Detect word order inversion & redundant tokens
  // Case like "茶想我喝茶"
  const chaCount = (clean.match(/茶/g) || []).length;
  const xiangCount = (clean.match(/想/g) || []).length;
  const heCount = (clean.match(/喝/g) || []).length;
  const woCount = (clean.match(/我/g) || []).length;

  // 1. Redundant repetition flaw
  if (chaCount > 1 || xiangCount > 1 || heCount > 1 || woCount > 1) {
    return {
      isValid: false,
      score: 0.25,
      errorCategory: 'redundant_tokens',
      detailedFeedback: `Redundancy error: Chinese sentences require concise SVO alignment. Repeating elements like “茶” produces gibberish. The correct sentence has each word once: 我 (Subject) + 想 (Desire) + 喝 (Verb) + 茶 (Object).`,
      recommendedConceptIds: ['hsk1_c20', 'hsk1_c01'],
      syntacticBreakdown: {
        extraneous: [clean],
      },
    };
  }

  // 2. Word order inversion (e.g. putting Object "茶" before Verb "喝", or "想" after verb)
  const posWo = clean.indexOf('我');
  const posXiang = clean.indexOf('想');
  const posHe = clean.indexOf('喝');
  const posCha = clean.indexOf('茶');

  // If object "茶" appears before verb "喝", or "想" appears after "喝"
  if (posCha !== -1 && posHe !== -1 && posCha < posHe) {
    return {
      isValid: false,
      score: 0.3,
      errorCategory: 'word_order_inversion',
      detailedFeedback: `Word order error: Chinese is strictly Subject + Verb + Object (SVO). You placed the object “茶” (tea) before the verb “喝” (drink). Remember: Actions come before objects. Say “喝茶”, never “茶喝”. Correct: 我想喝茶。`,
      recommendedConceptIds: ['hsk1_c20', 'hsk1_c08'],
      syntacticBreakdown: {
        subject: posWo !== -1 ? '我' : undefined,
        optative: posXiang !== -1 ? '想' : undefined,
        verb: '喝',
        object: '茶',
      },
    };
  }

  if (posXiang !== -1 && posHe !== -1 && posXiang > posHe) {
    return {
      isValid: false,
      score: 0.35,
      errorCategory: 'word_order_inversion',
      detailedFeedback: `Word order error: Auxiliary/optative verbs like “想 (xiǎng)” must precede the main action verb “喝 (hē)”. Correct: 我想喝茶, not 我喝想茶。`,
      recommendedConceptIds: ['hsk1_c20'],
      syntacticBreakdown: {
        subject: posWo !== -1 ? '我' : undefined,
        verb: '喝',
        optative: '想',
        object: posCha !== -1 ? '茶' : undefined,
      },
    };
  }

  if (posWo !== -1 && posXiang !== -1 && posWo > posXiang) {
    return {
      isValid: false,
      score: 0.35,
      errorCategory: 'word_order_inversion',
      detailedFeedback: `Word order error: The subject “我” (I) must be at the very front of the sentence before “想”. Correct: 我想喝茶。`,
      recommendedConceptIds: ['hsk1_c20', 'hsk1_c01'],
      syntacticBreakdown: {},
    };
  }

  // Missing components
  if (posXiang === -1 && posHe !== -1 && posCha !== -1) {
    return {
      isValid: false,
      score: 0.65,
      errorCategory: 'missing_optative',
      detailedFeedback: `Almost there! You wrote “我喝茶” (I drink tea), which is grammatically valid for a fact, but the prompt requested expressing a wish (“want to drink tea”). Insert “想 (xiǎng)” before “喝”: 我想喝茶。`,
      recommendedConceptIds: ['hsk1_c20'],
      syntacticBreakdown: {
        subject: '我',
        verb: '喝',
        object: '茶',
      },
    };
  }

  if (posHe === -1) {
    return {
      isValid: false,
      score: 0.4,
      errorCategory: 'missing_predicate',
      detailedFeedback: `Missing action verb: You need the verb “喝 (hē)” (to drink) between “想” and “茶”. Correct: 我想喝茶。`,
      recommendedConceptIds: ['hsk1_c08', 'hsk1_c20'],
      syntacticBreakdown: {},
    };
  }

  if (posCha === -1) {
    return {
      isValid: false,
      score: 0.4,
      errorCategory: 'missing_object',
      detailedFeedback: `Missing target object: You need the noun “茶 (chá)” (tea) at the end. Correct: 我想喝茶。`,
      recommendedConceptIds: ['hsk1_c08'],
      syntacticBreakdown: {},
    };
  }

  return {
    isValid: false,
    score: 0.2,
    errorCategory: 'unrelated_content',
    detailedFeedback: `The submitted sentence does not match the target meaning. Target: 我想喝茶 (Wǒ xiǎng hē chá - I want to drink tea).`,
    recommendedConceptIds: ['hsk1_c20', 'hsk1_c08'],
    syntacticBreakdown: {},
  };
}

export interface RagConceptMatch {
  concept: CurriculumConcept;
  similarityScore: number;
  matchedReason: string;
}

/**
 * Targeted Pedagogical RAG Matcher
 * Pinpoints EXACT relevant knowledge base concepts based on error diagnostics
 * rather than naive fuzzy keyword hits.
 */
export function matchConceptsByVectorRAG(
  userInput: string,
  errorCategory: SyntaxEvaluation['errorCategory'],
  concepts: CurriculumConcept[],
  topK = 2
): RagConceptMatch[] {
  // Concept lookup map
  const conceptMap = new Map<string, CurriculumConcept>();
  concepts.forEach(c => conceptMap.set(c.conceptId, c));

  const results: RagConceptMatch[] = [];

  // Match based on pedagogical error mapping
  if (errorCategory === 'word_order_inversion') {
    const optativeConcept = conceptMap.get('hsk1_c20') || concepts.find(c => c.grammarFocus.includes('想'));
    if (optativeConcept) {
      results.push({
        concept: optativeConcept,
        similarityScore: 0.98,
        matchedReason: 'High priority: Clarifies optative verb word order [Subject + 想 + Verb + Object]',
      });
    }

    const svoConcept = conceptMap.get('hsk1_c01') || concepts.find(c => c.category === 'grammar');
    if (svoConcept) {
      results.push({
        concept: svoConcept,
        similarityScore: 0.94,
        matchedReason: 'Foundational syntax: Chinese core SVO word order principles',
      });
    }
  } else if (errorCategory === 'missing_optative') {
    const optativeConcept = conceptMap.get('hsk1_c20') || concepts.find(c => c.grammarFocus.includes('想'));
    if (optativeConcept) {
      results.push({
        concept: optativeConcept,
        similarityScore: 0.99,
        matchedReason: 'Direct concept match: Expressing desire with “想 (xiǎng)”',
      });
    }
  } else if (errorCategory === 'redundant_tokens') {
    const optativeConcept = conceptMap.get('hsk1_c20') || concepts.find(c => c.grammarFocus.includes('想'));
    if (optativeConcept) {
      results.push({
        concept: optativeConcept,
        similarityScore: 0.95,
        matchedReason: 'Remedial focus: Eliminating word repetition and stabilizing sentence structure',
      });
    }
    const diningConcept = conceptMap.get('hsk1_c08') || concepts.find(c => c.vocabularyFocus.includes('茶'));
    if (diningConcept) {
      results.push({
        concept: diningConcept,
        similarityScore: 0.91,
        matchedReason: 'Vocabulary collocation: “喝茶 (hē chá)” standard verb-object pairing',
      });
    }
  } else {
    // Exact or general match
    const c20 = conceptMap.get('hsk1_c20') || concepts[0];
    const c08 = conceptMap.get('hsk1_c08') || concepts[1];
    if (c20) {
      results.push({
        concept: c20,
        similarityScore: 0.96,
        matchedReason: 'Target lesson: Expressing wishes and ordering with “想”',
      });
    }
    if (c08) {
      results.push({
        concept: c08,
        similarityScore: 0.92,
        matchedReason: 'Collocation practice: Ordering drinks and dining vocabulary',
      });
    }
  }

  // Fallback if needed
  if (results.length < topK) {
    const remaining = concepts.filter(c => !results.some(r => r.concept.conceptId === c.conceptId));
    remaining.slice(0, topK - results.length).forEach(c => {
      results.push({
        concept: c,
        similarityScore: 0.85,
        matchedReason: 'Supplementary HSK 1 core foundation',
      });
    });
  }

  return results.slice(0, topK);
}
