import assert from 'node:assert/strict';
import test from 'node:test';
import { ConceptProgress, DailyGoalBlueprint } from '../types.ts';
import {
  calculateCommunicationOutcomePercent,
  calculateGoalCompletion,
  calculateModuleLearnedPercent,
  calculateModuleMasteredPercent,
  deriveStatus,
  isConceptLearned,
  isConceptMastered,
  masteredProgressScore,
  normalizeUnitScore,
  projectProgress,
} from './progress.ts';
import { createDefaultConceptProgress, reduceConceptProgress } from './conceptProgressReducer.ts';

const baseProgress: ConceptProgress = {
  learnerId: 'test',
  conceptId: 'c1',
  learnedPercent: 100,
  masteryScore: 0.9,
  retentionAtReview: 1,
  decayLambda: 0.2,
  successfulSpacedRetrievals: 3,
  evidenceDays: 3,
  averageQuality: 0.9,
  averageReviewQuality: 0.9,
  status: 'almost_mastered',
  lastReviewedAt: '2026-09-01T00:00:00.000Z',
  nextReviewAt: '2026-09-08T00:00:00.000Z',
};

test('mastery requires four spaced retrievals, three evidence days, and review quality >= 0.80', () => {
  assert.equal(deriveStatus(baseProgress), 'almost_mastered');
  assert.equal(isConceptMastered(baseProgress), false);

  const mastered = { ...baseProgress, successfulSpacedRetrievals: 4 };
  assert.equal(deriveStatus(mastered), 'mastered');
  assert.equal(isConceptMastered(mastered), true);
});

test('legacy percent mastery values are normalized to unit scores', () => {
  assert.equal(normalizeUnitScore(100), 1);
  assert.equal(normalizeUnitScore(85), 0.85);
  assert.equal(normalizeUnitScore(0.85), 0.85);
  assert.equal(normalizeUnitScore(250), 1);
});

test('Completing all required first-learning steps changes concept Learned to 100%', () => {
  let progress = createDefaultConceptProgress('hsk1_c01', 'test_learner');
  assert.equal(progress.learnedPercent, 0);
  assert.equal(isConceptLearned(progress), false);

  // Completing only one card leaves Learned < 100%
  progress = reduceConceptProgress(progress, {
    id: 'e1',
    learnerId: 'test_learner',
    planItemId: 'p1',
    conceptIds: ['hsk1_c01'],
    eventType: 'card',
    startedAt: '2026-09-01T10:00:00.000Z',
    lastActiveAt: '2026-09-01T10:01:00.000Z',
    activeSeconds: 60,
    estimatedMinutes: 1,
    engagementScore: 1,
    createdAt: '2026-09-01T10:01:00.000Z',
  });
  assert.equal(progress.learnedPercent, 40);
  assert.equal(isConceptLearned(progress), false);

  // Completing atomic unit gives 100%
  progress = reduceConceptProgress(progress, {
    id: 'e2',
    learnerId: 'test_learner',
    planItemId: 'p1',
    conceptIds: ['hsk1_c01'],
    eventType: 'attempt',
    startedAt: '2026-09-01T10:05:00.000Z',
    lastActiveAt: '2026-09-01T10:06:00.000Z',
    activeSeconds: 60,
    estimatedMinutes: 1,
    engagementScore: 1,
    gradingResult: { exerciseId: 'ex1', passedGates: true, confidence: 1, feedback: 'ok', scores: { grammaticalCorrectness: 1, semanticPrecision: 1, pragmaticAppropriateness: 1 }, detectedErrors: [], graderVersion: 'v1' },
    createdAt: '2026-09-01T10:06:00.000Z',
  }, { completesAtomicUnit: true });
  assert.equal(progress.learnedPercent, 100);
  assert.equal(isConceptLearned(progress), true);
});

test('Completing four reviews in the same day does not qualify a concept as Mastered', () => {
  let progress = createDefaultConceptProgress('hsk1_c01', 'test_learner');
  progress.learnedPercent = 100;

  // 4 review attempts on the same calendar day
  for (let i = 1; i <= 4; i++) {
    progress = reduceConceptProgress(progress, {
      id: `rev_${i}`,
      learnerId: 'test_learner',
      planItemId: 'p_rev',
      conceptIds: ['hsk1_c01'],
      eventType: 'review',
      startedAt: `2026-09-01T10:0${i}:00.000Z`,
      lastActiveAt: `2026-09-01T10:0${i}:30.000Z`,
      activeSeconds: 30,
      estimatedMinutes: 1,
      engagementScore: 1,
      gradingResult: { exerciseId: 'ex1', passedGates: true, confidence: 1, feedback: 'ok', scores: { grammaticalCorrectness: 1, semanticPrecision: 1, pragmaticAppropriateness: 1 }, detectedErrors: [], graderVersion: 'v1' },
      createdAt: `2026-09-01T10:0${i}:30.000Z`,
    }, { isSpacedReview: true });
  }

  assert.equal(progress.evidenceDays, 1);
  assert.equal(isConceptMastered(progress), false);
  assert.notEqual(progress.status, 'mastered');
});

test('Completing four spaced reviews across three distinct valid review days with quality >= 0.80 qualifies as Mastered', () => {
  let progress = createDefaultConceptProgress('hsk1_c01', 'test_learner');
  progress.learnedPercent = 100;

  const days = [
    '2026-09-01T10:00:00.000Z',
    '2026-09-03T10:00:00.000Z',
    '2026-09-06T10:00:00.000Z',
    '2026-09-10T10:00:00.000Z',
  ];

  for (let i = 0; i < days.length; i++) {
    progress = reduceConceptProgress(progress, {
      id: `spaced_rev_${i + 1}`,
      learnerId: 'test_learner',
      planItemId: 'p_rev',
      conceptIds: ['hsk1_c01'],
      eventType: 'review',
      startedAt: days[i],
      lastActiveAt: days[i],
      activeSeconds: 45,
      estimatedMinutes: 1,
      engagementScore: 1,
      gradingResult: { exerciseId: 'ex1', passedGates: true, confidence: 1, feedback: 'ok', scores: { grammaticalCorrectness: 1, semanticPrecision: 1, pragmaticAppropriateness: 1 }, detectedErrors: [], graderVersion: 'v1' },
      createdAt: days[i],
    }, { isSpacedReview: true });
  }

  assert.equal(progress.successfulSpacedRetrievals, 4);
  assert.ok(progress.evidenceDays >= 3);
  assert.ok((progress.averageReviewQuality ?? 0) >= 0.80);
  assert.equal(isConceptMastered(progress), true);
  assert.equal(progress.status, 'mastered');
  assert.equal(progress.isMastered, true);
  assert.equal(progress.masteryScore, 1);
});

test('Module percentages include concepts with no progress record as zero', () => {
  const moduleConcepts = [
    { conceptId: 'c1', weight: 1 },
    { conceptId: 'c2', weight: 1 },
    { conceptId: 'c3', weight: 2 },
  ];
  // c1 is learned, c2 and c3 have no progress record
  const progressMap = {
    c1: { ...baseProgress, conceptId: 'c1', learnedPercent: 100, isMastered: false, status: 'almost_mastered' as const },
  };

  // Denominator is 1 + 1 + 2 = 4. Numerator for learned is 1. 1/4 = 25%
  const learnedPercent = calculateModuleLearnedPercent(moduleConcepts, progressMap);
  assert.equal(learnedPercent, 25);

  // Numerator for mastered is 0. 0/4 = 0%
  const masteredPercent = calculateModuleMasteredPercent(moduleConcepts, progressMap);
  assert.equal(masteredPercent, 0);
});

test('Goal Completion exactly follows the declared 45/35/20 formula', () => {
  // goalCompletion = round(0.45 * goalScopeLearnedPercent + 0.35 * goalScopeMasteredPercent + 0.20 * communicationOutcomePercent)
  // Test case 1: all 0
  assert.equal(calculateGoalCompletion(0, 0, 0), 0);

  // Test case 2: all 100
  assert.equal(calculateGoalCompletion(100, 100, 100), 100);

  // Test case 3: 50% learned, 20% mastered, 10% communication
  // 0.45 * 50 = 22.5, 0.35 * 20 = 7.0, 0.20 * 10 = 2.0. Total = 31.5 -> round = 32
  assert.equal(calculateGoalCompletion(50, 20, 10), 32);

  // Test case 4: clamp inputs to 0-100
  assert.equal(calculateGoalCompletion(150, 100, 100), 100);
});

test('projectProgress derives all projections deterministically', () => {
  const concepts = [
    { conceptId: 'c1', weight: 1 },
    { conceptId: 'c2', weight: 1 },
  ];
  const blueprints: DailyGoalBlueprint[] = [
    {
      id: 'b1',
      title: 'Greeting',
      outcome: 'Say hello',
      requiredConceptIds: ['c1'],
      requiredUnitIds: ['unit_c1'],
      outputTemplateId: 'dialogue',
      prerequisiteConceptIds: [],
      estimatedMinutes: 5,
      supportedThemes: ['pinyin_basics'],
      planningEnabled: true,
      freeformAssessment: { mode: 'scenario_writing', targetConceptIds: ['c1'], allowedInputScripts: ['hanzi'], completionGate: { targetConceptScore: 0.75, taskAchievementScore: 0.75 }, allowedLanguage: ['你好'], example: '你好' },
    },
  ];

  const c1Progress: ConceptProgress = {
    ...baseProgress,
    conceptId: 'c1',
    learnedPercent: 100,
    isMastered: true,
    status: 'mastered',
  };

  const summary = projectProgress([c1Progress], { c1: 1, c2: 1 }, [], '2026-09-02T00:00:00.000Z', 1, {
    allScopeConcepts: concepts,
    blueprints,
    passedBlueprintIds: ['b1'],
  });

  // Learned: 1/2 = 50%
  assert.equal(summary.learnedProgress, 50);
  // Mastered: 1/2 = 50%
  assert.equal(summary.masteredProgress, 50);
  // Communication: 1/1 = 100%
  assert.equal(summary.communicationOutcomePercent, 100);
  // Goal completion: round(0.45 * 50 + 0.35 * 50 + 0.20 * 100) = round(22.5 + 17.5 + 20) = 60
  assert.equal(summary.goalCompletion, 60);
});

test('Learned concepts stay learned and do not regress from forgetting or reviews', () => {
  let progress = createDefaultConceptProgress('c1', 'test_learner');
  progress.learnedPercent = 100;

  // A later review with low score or decay does not reduce learnedPercent
  const afterReview = reduceConceptProgress(progress, {
    id: 'rev_decay',
    learnerId: 'test_learner',
    planItemId: 'p1',
    conceptIds: ['c1'],
    eventType: 'review',
    startedAt: '2026-09-20T10:00:00.000Z',
    lastActiveAt: '2026-09-20T10:01:00.000Z',
    activeSeconds: 60,
    estimatedMinutes: 1,
    engagementScore: 0.5,
    gradingResult: { exerciseId: 'ex1', passedGates: false, confidence: 0.5, feedback: 'needs review', scores: { grammaticalCorrectness: 0.5, semanticPrecision: 0.5, pragmaticAppropriateness: 0.5 }, detectedErrors: [], graderVersion: 'v1' },
    createdAt: '2026-09-20T10:01:00.000Z',
  }, { isSpacedReview: true });

  assert.equal(afterReview.learnedPercent, 100);
  assert.equal(isConceptLearned(afterReview), true);
});

test('Historical mastery status is preserved even if retention decays later', () => {
  const mastered: ConceptProgress = {
    ...baseProgress,
    isMastered: true,
    status: 'mastered',
    masteryScore: 1.0,
    retentionAtReview: 1.0,
    decayLambda: 0.2,
    lastReviewedAt: '2026-08-01T00:00:00.000Z',
    nextReviewAt: '2026-08-10T00:00:00.000Z',
  };

  // Retention score decays over time
  const scoreLater = masteredProgressScore(mastered, '2026-09-10T00:00:00.000Z');
  assert.ok(scoreLater < 0.5);

  // But isConceptMastered and status remain mastered
  assert.equal(isConceptMastered(mastered), true);
  assert.equal(deriveStatus(mastered), 'mastered');
});

