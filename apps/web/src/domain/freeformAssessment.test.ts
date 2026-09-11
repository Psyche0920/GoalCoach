import assert from 'node:assert/strict';
import test from 'node:test';
import { DAILY_GOAL_BLUEPRINTS } from '../data/curriculumEngine.ts';
import { gradeFreeformAssessment, normalizeLearnerInput } from './freeformAssessment.ts';

test('normalization accepts tone marks, tone numbers and v variants', () => {
  assert.equal(normalizeLearnerInput('Nǐ hǎo!'), normalizeLearnerInput('ni3 hao3'));
  assert.equal(normalizeLearnerInput('nǚ'), normalizeLearnerInput('nv3'));
});

test('each communication blueprint grades its own matching response', () => {
  for (const blueprint of DAILY_GOAL_BLUEPRINTS.filter((item) => item.planningEnabled)) {
    const response = blueprint.freeformAssessment.responseChoices?.[0];
    assert.ok(response, `${blueprint.id} must provide a response choice`);
    assert.equal(gradeFreeformAssessment(response, blueprint.freeformAssessment).passed, true, blueprint.id);
  }
});

test('a greeting does not pass the desire assessment', () => {
  const desire = DAILY_GOAL_BLUEPRINTS.find((item) => item.id === 'anchor_06_say_what_you_want');
  assert.ok(desire);
  const result = gradeFreeformAssessment('你好，再见', desire.freeformAssessment);
  assert.equal(result.passed, false);
  assert.deepEqual(result.targetConceptIds, desire.freeformAssessment.targetConceptIds);
  assert.ok(result.gradingResult.conceptErrors?.every((error) =>
    desire.freeformAssessment.targetConceptIds.includes(error.conceptId)));
});

test('freeform blueprints expose only translation or scenario writing', () => {
  for (const blueprint of DAILY_GOAL_BLUEPRINTS) {
    assert.ok(['translation', 'scenario_writing'].includes(blueprint.freeformAssessment.mode));
  }
});
