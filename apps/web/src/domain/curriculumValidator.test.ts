import assert from 'node:assert/strict';
import test from 'node:test';
import { DAILY_GOAL_BLUEPRINTS, LEARNING_UNITS, SYSTEM_CURRICULUM_CONCEPTS } from '../data/curriculumEngine.ts';
import { CurriculumCoverageValidator, CurriculumValidationError } from './curriculumValidator.ts';

test('the production curriculum has no orphan or cyclic content', () => {
  assert.doesNotThrow(() => new CurriculumCoverageValidator().validate(
    SYSTEM_CURRICULUM_CONCEPTS, LEARNING_UNITS, DAILY_GOAL_BLUEPRINTS,
  ));
});

test('invalid references and cycles fail validation with concrete ids', () => {
  const concepts = SYSTEM_CURRICULUM_CONCEPTS.slice(0, 1).map((concept) => ({ ...concept, prerequisiteIds: [concept.conceptId] }));
  assert.throws(
    () => new CurriculumCoverageValidator().validate(concepts, [], []),
    (error: unknown) => error instanceof CurriculumValidationError
      && error.message.includes(concepts[0].conceptId)
      && error.message.includes('cycle'),
  );
});
