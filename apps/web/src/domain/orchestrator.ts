import { LearnerState, NextAction, PlanStatus } from '../types.ts';
import { calculateRetention, isConceptReviewDue } from './retention.ts';

export function isStateReviewDue(state: LearnerState, at: string | Date = new Date()): boolean {
  if (!state.mastery) return false;
  return Object.values(state.mastery).some((concept) =>
    isConceptReviewDue(concept.nextReviewAt, at)
  );
}

export function computeOverallProgress(state: LearnerState, at: string | Date = new Date()): number {
  if (!state.mastery) return 0.0;
  const items = Object.values(state.mastery);
  if (items.length === 0) return 0.0;

  // Full HSK 1 target scope: 15 core curriculum concepts + 5 pinyin foundation units = 20 total target units
  const FULL_HSK1_BENCHMARK_WEIGHT = 20.0;

  const weightedSum = items.reduce((acc, item) => {
    const currentRet = calculateRetention(
      item.retentionScore,
      item.lastReviewedAt,
      at,
      item.decayLambda
    );
    return acc + (item.weight || 1.0) * item.masteryScore * currentRet;
  }, 0);

  return Math.max(0.0, Math.min(1.0, weightedSum / FULL_HSK1_BENCHMARK_WEIGHT));
}

/**
 * Deterministically routes the learner's state to the next action based on priority rules:
 * 1. Goal Planning: If state.goal is null or state.goalChanged is true -> PLAN_GOAL
 * 2. Spaced Review: If review is due -> PLAN_REVIEW
 * 3. Plan Regeneration: If activePlan is null or activePlan.status != 'active' -> REGENERATE_PLAN
 * 4. Interactive Teaching (Default): Otherwise -> TEACH
 */
export function route(state: LearnerState): NextAction {
  if (!state.goal || state.goalChanged) {
    return 'plan_goal';
  }
  if (isStateReviewDue(state)) {
    return 'plan_review';
  }
  if (!state.activePlan || state.activePlan.status !== 'active') {
    return 'regenerate_plan';
  }
  return 'teach';
}
