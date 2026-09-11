import { DatabaseSync } from 'node:sqlite';
import { ConceptProgress, DailyGoalBlueprint, LearnerState, LearningEvent, LearningUnit } from '../types.ts';

export class LearnerRepositoryError extends Error {
  public constructor(message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = 'LearnerRepositoryError';
  }
}

export class SqliteLearnerRepository {
  private readonly database: DatabaseSync;

  public constructor(databasePath: string) {
    this.database = new DatabaseSync(databasePath);
    this.database.exec('PRAGMA journal_mode = WAL; PRAGMA foreign_keys = ON;');
    this.migrate();
  }

  public close(): void {
    this.database.close();
  }

  public findState(learnerId: string): LearnerState | null {
    const row = this.database.prepare('SELECT state_json FROM learner_state WHERE learner_id = ?').get(learnerId) as { state_json: string } | undefined;
    return row ? JSON.parse(row.state_json) as LearnerState : null;
  }

  public saveState(state: LearnerState): void {
    try {
      this.database.prepare(`
        INSERT INTO learner_state (learner_id, state_json, state_version, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(learner_id) DO UPDATE SET
          state_json = excluded.state_json,
          state_version = excluded.state_version,
          updated_at = excluded.updated_at
      `).run(state.learnerId, JSON.stringify(state), state.stateVersion ?? 1, state.updatedAt);
    } catch (error) {
      throw new LearnerRepositoryError(`Failed to persist learner ${state.learnerId}`, { cause: error });
    }
  }

  public saveCurriculum(units: readonly LearningUnit[], blueprints: readonly DailyGoalBlueprint[]): void {
    this.database.exec('BEGIN IMMEDIATE');
    try {
      const unitStatement = this.database.prepare('INSERT OR REPLACE INTO learning_unit (id, payload_json) VALUES (?, ?)');
      const blueprintStatement = this.database.prepare('INSERT OR REPLACE INTO daily_goal_blueprint (id, payload_json) VALUES (?, ?)');
      for (const unit of units) unitStatement.run(unit.id, JSON.stringify(unit));
      for (const blueprint of blueprints) blueprintStatement.run(blueprint.id, JSON.stringify(blueprint));
      this.database.exec('COMMIT');
    } catch (error) {
      this.database.exec('ROLLBACK');
      throw new LearnerRepositoryError('Failed to persist curriculum', { cause: error });
    }
  }

  public appendEventAndProgress(event: LearningEvent, progressRows: readonly ConceptProgress[], state: LearnerState): void {
    this.database.exec('BEGIN IMMEDIATE');
    try {
      this.database.prepare(`INSERT INTO learning_event
        (id, learner_id, plan_item_id, concept_ids_json, event_type, started_at, last_active_at,
         active_seconds, estimated_minutes, engagement_score, grading_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`)
        .run(event.id, event.learnerId, event.planItemId, JSON.stringify(event.conceptIds), event.eventType,
          event.startedAt, event.lastActiveAt, event.activeSeconds, event.estimatedMinutes,
          event.engagementScore, event.gradingResult ? JSON.stringify(event.gradingResult) : null, event.createdAt);
      const statement = this.database.prepare(`INSERT INTO concept_progress
        (learner_id, concept_id, payload_json) VALUES (?, ?, ?)
        ON CONFLICT(learner_id, concept_id) DO UPDATE SET payload_json = excluded.payload_json`);
      for (const progress of progressRows) statement.run(progress.learnerId, progress.conceptId, JSON.stringify(progress));
      this.saveState(state);
      this.database.exec('COMMIT');
    } catch (error) {
      this.database.exec('ROLLBACK');
      throw new LearnerRepositoryError('Learning transaction failed', { cause: error });
    }
  }

  public countEventsForPlanItem(planItemId: string, evidenceType?: LearningEvent['eventType']): number {
    const row = evidenceType
      ? this.database.prepare('SELECT COUNT(*) AS count FROM learning_event WHERE plan_item_id = ? AND event_type = ?').get(planItemId, evidenceType) as { count: number }
      : this.database.prepare('SELECT COUNT(*) AS count FROM learning_event WHERE plan_item_id = ?').get(planItemId) as { count: number };
    return Number(row.count);
  }

  public hasEvent(eventId: string): boolean {
    if (!eventId) return false;
    const row = this.database.prepare('SELECT 1 FROM learning_event WHERE id = ?').get(eventId);
    return Boolean(row);
  }

  public findEvent(eventId: string): LearningEvent | null {
    if (!eventId) return null;
    const row = this.database.prepare(`SELECT id, learner_id, plan_item_id, concept_ids_json, event_type,
      started_at, last_active_at, active_seconds, estimated_minutes, engagement_score, grading_json, created_at
      FROM learning_event WHERE id = ?`).get(eventId) as any;
    if (!row) return null;
    return {
      id: row.id,
      learnerId: row.learner_id,
      planItemId: row.plan_item_id,
      conceptIds: JSON.parse(row.concept_ids_json) as string[],
      eventType: row.event_type,
      startedAt: row.started_at,
      lastActiveAt: row.last_active_at,
      activeSeconds: row.active_seconds,
      estimatedMinutes: row.estimated_minutes,
      engagementScore: row.engagement_score,
      gradingResult: row.grading_json ? JSON.parse(row.grading_json) as LearningEvent['gradingResult'] : undefined,
      createdAt: row.created_at,
    };
  }

  public findEventsForLearner(learnerId: string): LearningEvent[] {
    const rows = this.database.prepare(`SELECT id, learner_id, plan_item_id, concept_ids_json, event_type,
      started_at, last_active_at, active_seconds, estimated_minutes, engagement_score, grading_json, created_at
      FROM learning_event WHERE learner_id = ? ORDER BY created_at`).all(learnerId) as Array<{
        id: string;
        learner_id: string;
        plan_item_id: string;
        concept_ids_json: string;
        event_type: LearningEvent['eventType'];
        started_at: string;
        last_active_at: string;
        active_seconds: number;
        estimated_minutes: number;
        engagement_score: number;
        grading_json: string | null;
        created_at: string;
      }>;
    return rows.map((row) => ({
      id: row.id,
      learnerId: row.learner_id,
      planItemId: row.plan_item_id,
      conceptIds: JSON.parse(row.concept_ids_json) as string[],
      eventType: row.event_type,
      startedAt: row.started_at,
      lastActiveAt: row.last_active_at,
      activeSeconds: row.active_seconds,
      estimatedMinutes: row.estimated_minutes,
      engagementScore: row.engagement_score,
      gradingResult: row.grading_json ? JSON.parse(row.grading_json) as LearningEvent['gradingResult'] : undefined,
      createdAt: row.created_at,
    }));
  }

  private migrate(): void {
    this.database.exec(`
      CREATE TABLE IF NOT EXISTS learner_state (
        learner_id TEXT PRIMARY KEY,
        state_json TEXT NOT NULL,
        state_version INTEGER NOT NULL,
        updated_at TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS concept_progress (
        learner_id TEXT NOT NULL,
        concept_id TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        PRIMARY KEY (learner_id, concept_id)
      );
      CREATE TABLE IF NOT EXISTS learning_event (
        id TEXT PRIMARY KEY,
        learner_id TEXT NOT NULL,
        plan_item_id TEXT NOT NULL,
        concept_ids_json TEXT NOT NULL,
        event_type TEXT NOT NULL,
        started_at TEXT NOT NULL,
        last_active_at TEXT NOT NULL,
        active_seconds INTEGER NOT NULL CHECK (active_seconds >= 0),
        estimated_minutes REAL NOT NULL CHECK (estimated_minutes >= 0),
        engagement_score REAL NOT NULL CHECK (engagement_score BETWEEN 0 AND 1),
        grading_json TEXT,
        created_at TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS learning_unit (id TEXT PRIMARY KEY, payload_json TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS daily_goal_blueprint (id TEXT PRIMARY KEY, payload_json TEXT NOT NULL);
    `);
  }
}
