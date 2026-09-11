import { ConceptProgress, LearningEvent } from '../types.ts';
import { applyLearningEvidence, completeLearningUnit } from './learningCompletion.ts';
import { deriveStatus, isConceptMastered } from './progress.ts';

export const RETENTION_MODEL_VERSION = 2;

export interface ReduceConceptProgressOptions {
  isSpacedReview?: boolean;
  completesAtomicUnit?: boolean;
}

export function createDefaultConceptProgress(conceptId: string, learnerId: string): ConceptProgress {
  return {
    learnerId,
    conceptId,
    learnedPercent: 0,
    learningEvidence: {
      cardCompletion: 0,
      practiceCompletion: 0,
      outputCompletion: 0,
    },
    masteryScore: 0,
    retentionAtReview: 1,
    decayLambda: 0.05,
    successfulSpacedRetrievals: 0,
    evidenceDays: 0,
    averageQuality: 0,
    qualityEvidenceCount: 0,
    reviewQualityCount: 0,
    averageReviewQuality: 0,
    isMastered: false,
    status: 'not_started',
    retentionModelVersion: RETENTION_MODEL_VERSION,
  };
}

/**
 * Server-side deterministic reducer for ConceptProgress.
 * Single source of truth across all learning and review events.
 */
export function reduceConceptProgress(
  current: ConceptProgress,
  event: LearningEvent,
  options?: ReduceConceptProgressOptions,
): ConceptProgress {
  const evidenceAt = event.startedAt || event.createdAt || new Date().toISOString();
  const eventDay = evidenceAt.slice(0, 10);
  const lastReviewDay = current.lastReviewedAt ? current.lastReviewedAt.slice(0, 10) : null;
  const isDistinctDay = !lastReviewDay || lastReviewDay !== eventDay;

  const isSpacedReview = Boolean(
    options?.isSpacedReview ||
    event.eventType === 'review',
  );

  // 1. Learned evidence calculation (First-learning flow)
  // Completing the first-learning flow is not mastery. Finishing one card does not mark concept as learned.
  // A learned concept stays learned. Later forgetting must not reduce Learned.
  let learningPatch;
  if (options?.completesAtomicUnit) {
    learningPatch = completeLearningUnit(current);
  } else if (isSpacedReview) {
    // Spaced reviews do not alter the first-learning evidence
    learningPatch = {
      learnedPercent: current.learnedPercent,
      learningEvidence: current.learningEvidence,
    };
  } else if (event.eventType === 'card') {
    learningPatch = applyLearningEvidence(current, { cardCompletion: 1 });
  } else if (event.eventType === 'attempt') {
    const passed = event.gradingResult ? event.gradingResult.passedGates : true;
    learningPatch = applyLearningEvidence(current, { practiceCompletion: passed ? 1 : 0.5 });
  } else if (event.eventType === 'output') {
    const passed = event.gradingResult ? event.gradingResult.passedGates : true;
    learningPatch = applyLearningEvidence(current, { outputCompletion: passed ? 1 : 0.5 });
  } else {
    learningPatch = completeLearningUnit(current);
  }

  const learnedPercent = Math.max(current.learnedPercent, learningPatch.learnedPercent ?? 0);

  // 2. Evidence days tracking
  const evidenceDays = isDistinctDay ? current.evidenceDays + 1 : current.evidenceDays;

  // 3. Spaced reviews & mastery tracking
  // Product Rule 2:
  // Repeating four attempts in one session must not count as four spaced reviews.
  // A card completion, passive reading event, audio recording, Freeform completion,
  // or immediate retry must not increment successfulSpacedRetrievals.
  let successfulSpacedRetrievals = current.successfulSpacedRetrievals;
  let reviewQualityCount = current.reviewQualityCount ?? 0;
  let averageReviewQuality = current.averageReviewQuality ?? 0;

  const quality = event.gradingResult
    ? (event.gradingResult.passedGates ? 1.0 : (event.gradingResult.confidence ?? 0.75))
    : (event.engagementScore ?? 1.0);
  const passedGates = event.gradingResult ? event.gradingResult.passedGates : quality >= 0.80;

  if (isSpacedReview) {
    // Check for distinct valid review interval:
    // Must be on a distinct day or when due, preventing multiple attempts in one session from counting.
    const isDue = !current.nextReviewAt || current.nextReviewAt <= evidenceAt;
    const isValidInterval = isDistinctDay || isDue;

    if (isValidInterval && passedGates) {
      successfulSpacedRetrievals += 1;
    }

    const prevCount = reviewQualityCount;
    reviewQualityCount = prevCount + 1;
    averageReviewQuality = ((averageReviewQuality * prevCount) + quality) / reviewQualityCount;
  }

  // 4. Overall quality tracking
  const qualityEvidenceCount = current.qualityEvidenceCount
    ?? (current.averageQuality > 0 ? Math.max(1, current.evidenceDays) : 0);
  const averageQuality = ((current.averageQuality * qualityEvidenceCount) + quality) / (qualityEvidenceCount + 1);

  // 5. Check mastery qualification
  // Product Rule 2:
  // A concept becomes Mastered = 100% only when:
  // successfulSpacedRetrievals >= 4, evidenceDays >= 3, averageReviewQuality >= 0.80.
  // After a concept qualifies, light the Mastered indicator at 100%. Keep historical mastery status.
  const qualifiesForMastery = (
    successfulSpacedRetrievals >= 4 &&
    evidenceDays >= 3 &&
    (averageReviewQuality > 0 ? averageReviewQuality : averageQuality) >= 0.80
  );

  const isMastered = Boolean(current.isMastered || qualifiesForMastery);

  // 6. Retention & Next review interval
  const refreshesRetention = isSpacedReview || options?.completesAtomicUnit || passedGates;
  const retentionAtReview = refreshesRetention
    ? (isSpacedReview
      ? (passedGates ? quality : Math.max(0.3, current.retentionAtReview - 0.2))
      : Math.max(current.retentionAtReview, quality))
    : current.retentionAtReview;

  const evidenceTimeMs = Date.parse(evidenceAt) || Date.now();
  const scheduledIntervalDays = Math.max(1, successfulSpacedRetrievals * 2);
  const nextReviewAt = refreshesRetention
    ? new Date(evidenceTimeMs + scheduledIntervalDays * 86_400_000).toISOString()
    : current.nextReviewAt;

  // 7. Status and mastery score
  let status: ConceptProgress['status'];
  let masteryScore: number;

  if (isMastered) {
    status = 'mastered';
    masteryScore = 1.0;
  } else {
    status = deriveStatus({
      ...current,
      learnedPercent,
      successfulSpacedRetrievals,
      evidenceDays,
      averageReviewQuality,
      averageQuality,
      isMastered,
    });
    if (isSpacedReview) {
      masteryScore = Math.min(1.0, Math.max(0.25, current.masteryScore) + (passedGates ? 0.25 : 0.10));
    } else if (learnedPercent >= 100) {
      masteryScore = Math.max(current.masteryScore, 0.25);
    } else {
      masteryScore = Math.max(current.masteryScore, (learnedPercent / 100) * 0.20);
    }
  }

  return {
    ...current,
    learningEvidence: learningPatch.learningEvidence ?? current.learningEvidence,
    learningCompletionVersion: 2,
    learnedPercent,
    masteryScore,
    retentionAtReview,
    retentionModelVersion: RETENTION_MODEL_VERSION,
    successfulSpacedRetrievals,
    evidenceDays,
    averageQuality,
    qualityEvidenceCount: qualityEvidenceCount + 1,
    reviewQualityCount,
    averageReviewQuality,
    isMastered,
    status,
    lastReviewedAt: refreshesRetention ? evidenceAt : current.lastReviewedAt,
    nextReviewAt,
  };
}
