import { Exercise, GradingResult, RubricScores } from '../types.ts';

function normalize(text: string): string {
  return text
    .trim()
    .toLowerCase()
    .replace(/[，。！？,.!?\s]/g, '');
}

export function gradeAnswer(exercise: Exercise, answer: string): GradingResult {
  const normUser = normalize(answer);
  const normCorrect = normalize(exercise.answer);
  const normAccepted = (exercise.acceptedAnswers || []).map(normalize);

  const isExact = normUser === normCorrect || normAccepted.includes(normUser);
  const detectedErrors: string[] = [];

  // Error pattern checks
  if (answer.includes('不有')) {
    detectedErrors.push('ERR_BU_YOU');
  }
  if (exercise.targetTokens.includes('吗') && !answer.includes('吗') && !normUser.includes('吗')) {
    detectedErrors.push('ERR_MISSING_MA');
  }
  if (exercise.targetTokens.includes('呢') && !answer.includes('呢') && !normUser.includes('呢')) {
    detectedErrors.push('ERR_MISSING_NE');
  }
  if (exercise.errorTags.includes('adjective_predicate') && answer.includes('是') && !exercise.answer.includes('是')) {
    detectedErrors.push('ERR_SHI_OVERUSE');
  }
  if (exercise.errorTags.includes('word_order') && !isExact) {
    detectedErrors.push('ERR_WORD_ORDER');
  }

  let scores: RubricScores;
  let passedGates = false;
  let feedback = '';

  if (isExact) {
    scores = {
      grammaticalCorrectness: 1.0,
      semanticPrecision: 1.0,
      pragmaticAppropriateness: 1.0,
    };
    passedGates = true;
    feedback = `Excellent! Exactly right. ${exercise.explanation}`;
  } else if (detectedErrors.length > 0) {
    scores = {
      grammaticalCorrectness: 0.4,
      semanticPrecision: 0.6,
      pragmaticAppropriateness: 0.5,
    };
    passedGates = false;
    const errorDetails: string[] = [];
    if (detectedErrors.includes('ERR_BU_YOU')) {
      errorDetails.push('“有” is always negated with “没有”, never “不有”.');
    }
    if (detectedErrors.includes('ERR_MISSING_MA')) {
      errorDetails.push('The question particle “吗” should be placed at the end of the sentence.');
    }
    if (detectedErrors.includes('ERR_MISSING_NE')) {
      errorDetails.push('Use the follow-up particle “呢” to ask “what about...”.');
    }
    if (detectedErrors.includes('ERR_SHI_OVERUSE')) {
      errorDetails.push('Adjective predicates in Chinese commonly use “很” instead of “是”.');
    }
    if (detectedErrors.includes('ERR_WORD_ORDER')) {
      errorDetails.push('Check the word order (Subject + Adverb/Verb + Object).');
    }
    feedback = `Needs adjustment. ${errorDetails.join(' ')} Correct answer: ${exercise.answer}. ${exercise.explanation}`;
  } else {
    // Partial or wrong answer
    scores = {
      grammaticalCorrectness: 0.3,
      semanticPrecision: 0.3,
      pragmaticAppropriateness: 0.4,
    };
    passedGates = false;
    feedback = `Not quite right. The target answer was: “${exercise.answer}”. ${exercise.explanation}`;
  }

  return {
    exerciseId: exercise.id,
    scores,
    passedGates,
    confidence: 0.95,
    feedback,
    detectedErrors,
    evidence: `Submitted: "${answer}", Expected: "${exercise.answer}"`,
    graderVersion: 'v1.0.0',
  };
}
