import assert from 'node:assert/strict';
import test from 'node:test';
import { DAILY_GOAL_BLUEPRINTS, LEARNING_UNITS, SYSTEM_CURRICULUM_CONCEPTS } from '../data/curriculumEngine.ts';
import { ConceptProgress } from '../types.ts';
import { deriveDailyPlanStatus, generateDailyPlan } from './planner.ts';

const now = '2026-09-08T10:00:00.000Z';
const baseInput = (progress: Record<string, ConceptProgress> = {}) => ({
  learnerId: 'test', date: now, budgetMinutes: 20,
  concepts: SYSTEM_CURRICULUM_CONCEPTS, units: LEARNING_UNITS, blueprints: DAILY_GOAL_BLUEPRINTS,
  progress, errors: [], interests: [], stateVersion: 1,
});

const dueProgress = (conceptId: string): ConceptProgress => ({
  learnerId: 'test', conceptId, learnedPercent: 100, masteryScore: 0.4,
  retentionAtReview: 0.8, decayLambda: 0.05, successfulSpacedRetrievals: 1,
  evidenceDays: 1, averageQuality: 0.8, status: 'almost_mastered',
  lastReviewedAt: '2026-09-01T10:00:00.000Z', nextReviewAt: '2026-09-07T10:00:00.000Z',
});

test('a 20 minute plan never exceeds its hard budget', () => {
  const plan = generateDailyPlan(baseInput());
  assert.ok(plan.items.reduce((sum, item) => sum + item.estimatedMinutes, 0) <= 20);
  assert.ok(plan.items.every((item) => item.conceptIds && item.unitIds));
});

test('every profile time option is enforced as the plan budget', () => {
  for (const budgetMinutes of [5, 10, 15, 20, 30]) {
    const plan = generateDailyPlan({ ...baseInput(), budgetMinutes });
    assert.equal(plan.budgetMinutes, budgetMinutes);
    assert.ok(plan.estimatedMinutes! <= budgetMinutes);
    assert.ok(plan.items.reduce((sum, item) => sum + item.estimatedMinutes, 0) <= budgetMinutes);
  }
});

test('larger profile budgets schedule more complete curriculum units when available', () => {
  const shortPlan = generateDailyPlan({ ...baseInput(), budgetMinutes: 10 });
  const longPlan = generateDailyPlan({ ...baseInput(), budgetMinutes: 30 });
  assert.ok(longPlan.estimatedMinutes! > shortPlan.estimatedMinutes!);
  assert.ok(longPlan.items.filter((item) => item.kind === 'new').length
    > shortPlan.items.filter((item) => item.kind === 'new').length);
  assert.ok(longPlan.estimatedMinutes! <= 30);
});

test('a five minute profile budget still produces a complete assessed goal', () => {
  const plan = generateDailyPlan({ ...baseInput(), budgetMinutes: 5 });
  assert.equal(plan.estimatedMinutes, 5);
  assert.equal(plan.items.filter((item) => item.kind === 'new').length, 1);
  assert.equal(plan.items.filter((item) => item.kind === 'free_play').length, 1);
});

test('a new learner receives one communication goal across curriculum modules', () => {
  const plan = generateDailyPlan(baseInput());
  const categories = new Set(plan.items
    .flatMap((item) => item.conceptIds ?? [])
    .map((id) => SYSTEM_CURRICULUM_CONCEPTS.find((concept) => concept.conceptId === id)?.category));
  assert.equal(plan.blueprintId, 'anchor_01_greet');
  assert.equal(plan.title, 'Greetings');
  assert.ok(categories.has('pinyin'));
  assert.ok(categories.has('scenario'));
  assert.ok(plan.items.some((item) => item.kind === 'free_play'));
});

test('free play is included in the hard budget', () => {
  const plan = generateDailyPlan({ ...baseInput(), budgetMinutes: 10 });
  assert.ok(plan.items.reduce((sum, item) => sum + item.estimatedMinutes, 0) <= 10);
  assert.ok(plan.items.filter((item) => item.kind === 'free_play').length <= 1);
});

test('a complete learning unit is never split or partially scheduled', () => {
  const plan = generateDailyPlan({ ...baseInput(), budgetMinutes: 2 });
  assert.ok(plan.items.every((item) => item.kind !== 'new' || item.estimatedMinutes <= 2));
});

test('review demand at 80 percent produces a review-only plan', () => {
  const ids = SYSTEM_CURRICULUM_CONCEPTS.slice(0, 6).map((concept) => concept.conceptId);
  const progress = Object.fromEntries(ids.map((id) => [id, dueProgress(id)]));
  const plan = generateDailyPlan(baseInput(progress));
  assert.ok(plan.items.length > 0);
  assert.ok(plan.items.every((item) => item.kind === 'review'));
});

test('the same curriculum stage preserves concepts across interests', () => {
  const travel = generateDailyPlan({ ...baseInput(), interests: ['travel_directions'] });
  const dining = generateDailyPlan({ ...baseInput(), interests: ['dining_food'] });
  assert.deepEqual(travel.items.flatMap((item) => item.conceptIds ?? []), dining.items.flatMap((item) => item.conceptIds ?? []));
});

test('remedial learning never exceeds 25 percent of the budget', () => {
  const errors = SYSTEM_CURRICULUM_CONCEPTS.slice(0, 4).map((concept, index) => ({
    code: `error_${index}`, conceptId: concept.conceptId, occurrences: 10 - index, lastSeenAt: now, examples: [],
  }));
  const plan = generateDailyPlan({ ...baseInput(), errors });
  const remedialMinutes = plan.items.filter((item) => item.kind === 'remedial').reduce((sum, item) => sum + item.estimatedMinutes, 0);
  assert.ok(remedialMinutes <= 5);
});

test('remedial learning cannot consume reserved freeform time', () => {
  const plan = generateDailyPlan({
    ...baseInput(),
    budgetMinutes: 10,
    errors: [{ code: 'sound_error', conceptId: 'hsk1_p01', occurrences: 8, lastSeenAt: now, examples: [] }],
  });
  assert.equal(plan.items.some((item) => item.kind === 'remedial'), false);
  assert.equal(plan.items.some((item) => item.kind === 'free_play'), true);
  assert.equal(plan.estimatedMinutes, 10);
});

test('an irrelevant historical error is not scheduled', () => {
  const plan = generateDailyPlan({
    ...baseInput(),
    errors: [{ code: 'irrelevant', conceptId: 'missing_concept', occurrences: 99, lastSeenAt: now, examples: [] }],
  });
  assert.equal(plan.items.some((item) => item.kind === 'remedial'), false);
});

test('identical planner input produces an identical core plan', () => {
  const first = generateDailyPlan(baseInput());
  const second = generateDailyPlan(baseInput());
  assert.deepEqual(first, second);
});

test('freeform remains a completion gate after learning items finish', () => {
  const plan = generateDailyPlan(baseInput());
  const completed = { ...plan, items: plan.items.map((item) => ({ ...item, completed: true })), freeformCompleted: false };
  assert.equal(deriveDailyPlanStatus(completed), completed.items.some((item) => item.kind === 'free_play') ? 'assessment_required' : 'completed');
  assert.equal(deriveDailyPlanStatus({ ...completed, freeformCompleted: true }), 'completed');
});
