import { ConceptProgress, DailyGoalBlueprint, LearningEvent, ProgressSummary } from '../types.ts';
import { calculateRetention } from './retention.ts';

export const normalizeUnitScore = (value: number): number => {
  if (!Number.isFinite(value) || value <= 0) return 0;
  const normalized = value > 1 ? value / 100 : value;
  return Math.max(0, Math.min(1, normalized));
};

export const currentMasteryScore = (progress: ConceptProgress, at: string): number => {
  const retention = progress.lastReviewedAt
    ? calculateRetention(normalizeUnitScore(progress.retentionAtReview), progress.lastReviewedAt, at, progress.decayLambda)
    : (progress.masteryScore > 0 ? 1 : 0);
  return normalizeUnitScore(progress.masteryScore) * retention;
};

/** Current retained mastery shown in Curriculum and memory decay curve. */
export const masteredProgressScore = (
  progress: ConceptProgress,
  at: string = new Date().toISOString(),
): number => currentMasteryScore(progress, at);

export const effectiveMinutes = (event: LearningEvent): number =>
  Math.min(event.activeSeconds / 60, event.estimatedMinutes) * event.engagementScore;

/**
 * Product Rule 1:
 * Learned means the learner completed the required first-learning flow for a curriculum concept or unit.
 * A concept becomes Learned = 100% only after all required learning evidence for that concept is completed.
 */
export const isConceptLearned = (progress?: ConceptProgress | null): boolean => {
  if (!progress) return false;
  return (progress.learnedPercent ?? 0) >= 100;
};

/**
 * Product Rule 2:
 * Mastered means stable recall after spaced reviews. Completing the first-learning flow is not mastery.
 * A concept becomes Mastered = 100% only when:
 * successfulSpacedRetrievals >= 4
 * evidenceDays >= 3
 * averageReviewQuality >= 0.80
 * After a concept qualifies, light the Mastered indicator at 100%. Keep historical mastery status.
 */
export const isConceptMastered = (progress?: ConceptProgress | null): boolean => {
  if (!progress) return false;
  if (progress.isMastered === true) return true;
  if (progress.status === 'mastered') return true;
  const avgQuality = progress.averageReviewQuality ?? progress.averageQuality ?? 0;
  return (
    progress.successfulSpacedRetrievals >= 4 &&
    progress.evidenceDays >= 3 &&
    avgQuality >= 0.80
  );
};

export const deriveStatus = (progress: ConceptProgress): ConceptProgress['status'] => {
  if (isConceptMastered(progress)) return 'mastered';
  if ((progress.learnedPercent ?? 0) === 0) return 'not_started';
  if ((progress.learnedPercent ?? 0) < 100) return 'learning';
  return 'almost_mastered';
};

/**
 * Product Rule 1:
 * A module's Learned percentage is the weighted aggregation of the concepts in that module:
 * moduleLearnedPercent = 100 * sum(concept.weight for learned concepts) / sum(concept.weight for all concepts in the module)
 * Do not calculate the denominator from existing progress records only. Include every curriculum concept in the module so missing records count as zero.
 */
export function calculateModuleLearnedPercent(
  concepts: readonly { conceptId: string; weight?: number }[],
  progressMap: Readonly<Record<string, ConceptProgress>>,
): number {
  if (!concepts || concepts.length === 0) return 0;
  const denominator = concepts.reduce((sum, c) => sum + (c.weight ?? 1), 0);
  if (denominator <= 0) return 0;
  const numerator = concepts.reduce((sum, c) => {
    const p = progressMap[c.conceptId];
    const learnedPercent = p ? (p.learnedPercent ?? 0) : 0;
    return sum + (c.weight ?? 1) * Math.max(0, Math.min(100, learnedPercent));
  }, 0);
  const percent = numerator / denominator;
  return Math.round(Math.max(0, Math.min(100, percent)));
}

/**
 * Product Rule 2:
 * A module's Mastered percentage is:
 * moduleMasteredPercent = 100 * sum(concept.weight for mastered concepts) / sum(concept.weight for all concepts in the module)
 * Include every curriculum concept in the module so missing records count as zero.
 */
export function calculateModuleMasteredPercent(
  concepts: readonly { conceptId: string; weight?: number }[],
  progressMap: Readonly<Record<string, ConceptProgress>>,
): number {
  if (!concepts || concepts.length === 0) return 0;
  const denominator = concepts.reduce((sum, c) => sum + (c.weight ?? 1), 0);
  if (denominator <= 0) return 0;
  const numerator = concepts.reduce((sum, c) => {
    const p = progressMap[c.conceptId];
    return sum + (isConceptMastered(p) ? (c.weight ?? 1) : 0);
  }, 0);
  const percent = (100 * numerator) / denominator;
  return Math.round(Math.max(0, Math.min(100, percent)));
}

/**
 * Product Rule 3:
 * communicationOutcomePercent is the weighted percentage of required daily communication
 * goal blueprints that have passed their final Freeform assessment at least once.
 */
export function calculateCommunicationOutcomePercent(
  blueprints: readonly DailyGoalBlueprint[],
  passedBlueprintIds: readonly string[],
): number {
  const requiredBlueprints = (blueprints ?? []).filter((b) => b.planningEnabled !== false);
  if (requiredBlueprints.length === 0) return 0;
  const passedSet = new Set(passedBlueprintIds ?? []);
  const denominator = requiredBlueprints.reduce((sum, b) => sum + ((b as any).weight ?? 1), 0);
  if (denominator <= 0) return 0;
  const numerator = requiredBlueprints.reduce((sum, b) => {
    return sum + (passedSet.has(b.id) ? ((b as any).weight ?? 1) : 0);
  }, 0);
  const percent = (100 * numerator) / denominator;
  return Math.round(Math.max(0, Math.min(100, percent)));
}

/**
 * Product Rule 3:
 * goalCompletion = round(
 *   0.45 * goalScopeLearnedPercent +
 *   0.35 * goalScopeMasteredPercent +
 *   0.20 * communicationOutcomePercent
 * )
 * Clamp every input and the result to 0–100.
 */
export function calculateGoalCompletion(
  goalScopeLearnedPercent: number,
  goalScopeMasteredPercent: number,
  communicationOutcomePercent: number,
): number {
  const learned = Math.max(0, Math.min(100, goalScopeLearnedPercent));
  const mastered = Math.max(0, Math.min(100, goalScopeMasteredPercent));
  const communication = Math.max(0, Math.min(100, communicationOutcomePercent));
  const raw = 0.45 * learned + 0.35 * mastered + 0.20 * communication;
  return Math.round(Math.max(0, Math.min(100, raw)));
}

export interface ProjectProgressOptions {
  allScopeConcepts?: readonly { conceptId: string; weight?: number }[];
  blueprints?: readonly DailyGoalBlueprint[];
  passedBlueprintIds?: readonly string[];
}

export function projectProgress(
  progress: readonly ConceptProgress[],
  weights: Readonly<Record<string, number>>,
  events: readonly LearningEvent[],
  at: string,
  stateVersion: number,
  options?: ProjectProgressOptions,
): ProgressSummary {
  const progressMap: Record<string, ConceptProgress> = {};
  for (const item of progress) {
    progressMap[item.conceptId] = item;
  }

  // If allScopeConcepts is provided, use it so missing concepts count as zero in the denominator.
  // Otherwise, construct concept list from the given progress items.
  const scopeConcepts = options?.allScopeConcepts ?? progress.map((p) => ({
    conceptId: p.conceptId,
    weight: weights[p.conceptId] ?? 1,
  }));

  const goalScopeLearnedPercent = calculateModuleLearnedPercent(scopeConcepts, progressMap);
  const goalScopeMasteredPercent = calculateModuleMasteredPercent(scopeConcepts, progressMap);
  const communicationOutcomePercent = calculateCommunicationOutcomePercent(
    options?.blueprints ?? [],
    options?.passedBlueprintIds ?? [],
  );

  const goalCompletion = calculateGoalCompletion(
    goalScopeLearnedPercent,
    goalScopeMasteredPercent,
    communicationOutcomePercent,
  );

  const totalDenominator = scopeConcepts.reduce((sum, c) => sum + (c.weight ?? 1), 0) || 1;
  const courseCoverage = scopeConcepts.reduce((sum, c) => {
    const p = progressMap[c.conceptId];
    return sum + ((p?.learnedPercent ?? 0) > 0 ? (c.weight ?? 1) : 0);
  }, 0) / totalDenominator;

  return {
    stateVersion,
    courseCoverage,
    learnedProgress: goalScopeLearnedPercent,
    masteredProgress: goalScopeMasteredPercent,
    goalCompletion,
    goalScopeLearnedPercent,
    goalScopeMasteredPercent,
    communicationOutcomePercent,
    dailyEffectiveMinutes: events.reduce((sum, event) => sum + effectiveMinutes(event), 0),
  };
}
