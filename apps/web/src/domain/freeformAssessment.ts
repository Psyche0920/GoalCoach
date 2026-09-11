import { FreeformAssessmentSpec, GradingResult, RubricScores } from '../types.ts';

export interface FreeformAssessmentResult {
  score: number;
  passed: boolean;
  feedback: string;
  scores: RubricScores;
  detectedErrors: string[];
  targetConceptIds: string[];
  gradingResult: GradingResult;
}

export function normalizeLearnerInput(value: string): string {
  return value
    .toLowerCase()
    .replace(/u:|v/g, 'ü')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[1-5]/g, '')
    .replace(/[\s\p{P}\p{S}]/gu, '');
}

export function gradeFreeformAssessment(
  input: string,
  specification: FreeformAssessmentSpec,
): FreeformAssessmentResult {
  const normalizedInput = normalizeLearnerInput(input);
  const patternGroups = specification.requiredResponsePatterns ?? [];
  const emptyResult = (feedback: string, error: string): FreeformAssessmentResult => {
    const scores = { grammaticalCorrectness: 0, semanticPrecision: 0, pragmaticAppropriateness: 0 };
    const gradingResult: GradingResult = {
      exerciseId: 'freeform', scores, passedGates: false, confidence: 1,
      feedback,
      detectedErrors: [error],
      conceptErrors: specification.targetConceptIds.map((conceptId) => ({ code: error, conceptId, explanation: feedback })),
      graderVersion: 'freeform-deterministic-v2',
    };
    return { score: 0, passed: false, feedback, scores, detectedErrors: [error], targetConceptIds: specification.targetConceptIds, gradingResult };
  };
  if (!normalizedInput) return emptyResult('Add your response, then try again.', 'ERR_EMPTY_OUTPUT');
  if (patternGroups.length === 0) return emptyResult('This task is not ready yet.', 'ERR_ASSESSMENT_NOT_READY');

  const matchedGroups = patternGroups.filter((alternatives) => alternatives
    .some((alternative) => normalizedInput.includes(normalizeLearnerInput(alternative)))).length;
  const score = matchedGroups / patternGroups.length;
  const scores: RubricScores = {
    grammaticalCorrectness: score,
    semanticPrecision: score,
    pragmaticAppropriateness: matchedGroups === patternGroups.length ? 1 : 0.5,
  };
  const passed = scores.semanticPrecision >= specification.completionGate.targetConceptScore
    && scores.pragmaticAppropriateness >= specification.completionGate.taskAchievementScore;
  const detectedErrors = passed ? [] : ['ERR_TARGET_STRUCTURE'];
  const feedback = passed
    ? 'Clear and complete. You achieved today’s goal.'
    : `Almost there. Include every required part. Example: ${specification.example} Try again.`;
  const gradingResult: GradingResult = {
    exerciseId: 'freeform',
    scores,
    passedGates: passed,
    confidence: 0.85,
    feedback,
    detectedErrors,
    conceptErrors: passed ? [] : specification.targetConceptIds.map((conceptId) => ({
      code: 'ERR_TARGET_STRUCTURE',
      conceptId,
      explanation: 'The required meaning or sentence pattern is incomplete.',
    })),
    evidence: `Matched ${matchedGroups} of ${patternGroups.length} target groups.`,
    graderVersion: 'freeform-deterministic-v2',
  };
  return {
    score,
    passed,
    feedback,
    scores,
    detectedErrors,
    targetConceptIds: specification.targetConceptIds,
    gradingResult,
  };
}
