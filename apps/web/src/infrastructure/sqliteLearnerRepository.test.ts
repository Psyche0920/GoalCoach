import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { ConceptProgress, LearnerState, LearningEvent } from '../types.ts';
import { SqliteLearnerRepository } from './sqliteLearnerRepository.ts';

test('daily plan and item completion survive a repository restart', () => {
  const directory = mkdtempSync(join(tmpdir(), 'goalcoach-repository-'));
  const databasePath = join(directory, 'learner.sqlite');
  const state: LearnerState = {
    learnerId: 'persistence-test',
    goal: null,
    goalChanged: false,
    mastery: {},
    errorProfile: [],
    sessions: [],
    stateVersion: 7,
    updatedAt: '2026-09-09T10:00:00.000Z',
    conceptProgress: {},
    activePlan: {
      id: 'plan_persistence-test_2026-09-09',
      learnerId: 'persistence-test',
      date: '2026-09-09T10:00:00.000Z',
      blueprintId: 'daily_goal_01',
      title: 'Meet someone',
      outcome: 'Introduce yourself.',
      budgetMinutes: 20,
      estimatedMinutes: 7,
      effectiveMinutes: 3,
      status: 'active',
      rationale: 'Deterministic test plan.',
      stateVersion: 7,
      generatedAt: '2026-09-09T10:00:00.000Z',
      createdAt: '2026-09-09T10:00:00.000Z',
      items: [{
        id: 'new_unit_hsk1_p01',
        conceptIds: ['hsk1_p01'],
        unitIds: ['unit_hsk1_p01'],
        kind: 'new',
        title: 'Sound practice',
        objective: 'Produce a foundational sound.',
        outcome: 'Produce a foundational sound.',
        estimatedMinutes: 3,
        completedMinutes: 3,
        completionCredit: 1,
        completionRules: [{ evidenceType: 'controlled_practice', conceptId: 'hsk1_p01', requiredCount: 1 }],
        completed: true,
      }],
    },
  };

  try {
    const firstRepository = new SqliteLearnerRepository(databasePath);
    firstRepository.saveState(state);
    const progress: ConceptProgress = {
      learnerId: state.learnerId,
      conceptId: 'hsk1_p01',
      learnedPercent: 40,
      masteryScore: 0.1,
      retentionAtReview: 1,
      decayLambda: 0.05,
      successfulSpacedRetrievals: 0,
      evidenceDays: 1,
      averageQuality: 1,
      status: 'learning',
    };
    const event: LearningEvent = {
      id: 'event-1',
      learnerId: state.learnerId,
      planItemId: 'new_unit_hsk1_p01',
      conceptIds: ['hsk1_p01'],
      eventType: 'attempt',
      startedAt: state.updatedAt,
      lastActiveAt: state.updatedAt,
      activeSeconds: 60,
      estimatedMinutes: 1,
      engagementScore: 1,
      createdAt: state.updatedAt,
    };
    firstRepository.appendEventAndProgress(event, [progress], state);
    firstRepository.close();

    const restartedRepository = new SqliteLearnerRepository(databasePath);
    const restored = restartedRepository.findState(state.learnerId);
    const restoredEvents = restartedRepository.findEventsForLearner(state.learnerId);
    restartedRepository.close();

    assert.equal(restored?.activePlan?.id, state.activePlan?.id);
    assert.equal(restored?.activePlan?.items[0].completed, true);
    assert.equal(restored?.stateVersion, 7);
    assert.equal(restoredEvents.length, 1);
    assert.deepEqual(restoredEvents[0].conceptIds, ['hsk1_p01']);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});
