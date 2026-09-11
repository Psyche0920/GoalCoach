import assert from 'node:assert/strict';
import test from 'node:test';
import { ConceptProgress } from '../types.ts';
import { applyLearningEvidence, completeLearningUnit } from './learningCompletion.ts';

const emptyProgress: ConceptProgress = {
  learnerId: 'learner', conceptId: 'concept', learnedPercent: 0, masteryScore: 0,
  retentionAtReview: 0, decayLambda: 0.05, successfulSpacedRetrievals: 0,
  evidenceDays: 0, averageQuality: 0, status: 'not_started',
};

test('learned completion uses independent 40/40/20 evidence dimensions', () => {
  const practice = applyLearningEvidence(emptyProgress, { practiceCompletion: 1 });
  assert.equal(practice.learnedPercent, 40);

  const cards = applyLearningEvidence({ ...emptyProgress, ...practice }, { cardCompletion: 1 });
  assert.equal(cards.learnedPercent, 80);

  const output = applyLearningEvidence({ ...emptyProgress, ...cards }, { outputCompletion: 1 });
  assert.equal(output.learnedPercent, 100);
});

test('repeated evidence of the same type cannot inflate learned completion', () => {
  const first = applyLearningEvidence(emptyProgress, { practiceCompletion: 1 });
  const repeated = applyLearningEvidence({ ...emptyProgress, ...first }, { practiceCompletion: 1 });
  assert.equal(repeated.learnedPercent, 40);
});

test('spaced review does not change course learning completion', () => {
  const unchanged = applyLearningEvidence(emptyProgress, {});
  assert.equal(unchanged.learnedPercent, 0);
});

test('completing an atomic LearningUnit sets learned completion to 100 percent', () => {
  const completed = completeLearningUnit(emptyProgress);
  assert.equal(completed.learnedPercent, 100);
  assert.deepEqual(completed.learningEvidence, {
    cardCompletion: 1,
    practiceCompletion: 1,
    outputCompletion: 1,
  });
});
