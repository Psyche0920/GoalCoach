import {
  ConceptProgress,
  CurriculumConcept,
  DailyGoalBlueprint,
  DailyPlan,
  ErrorRecord,
  LearningUnit,
  PlanItem,
} from '../types.ts';
import { curriculumShortTitle } from '../data/curriculumPresentation.ts';

export const DAILY_PLANNER_VERSION = 5;

export interface PlannerInput {
  learnerId: string;
  date: string;
  budgetMinutes: number;
  concepts: readonly CurriculumConcept[];
  units: readonly LearningUnit[];
  blueprints: readonly DailyGoalBlueprint[];
  progress: Readonly<Record<string, ConceptProgress>>;
  errors: readonly ErrorRecord[];
  interests: readonly string[];
  stateVersion: number;
}

export const deriveDailyPlanStatus = (plan: Pick<DailyPlan, 'items' | 'freeformCompleted'>): DailyPlan['status'] => {
  if (!plan.items.every((item) => item.completed)) return 'active';
  const requiresFreeform = plan.items.some((item) => item.kind === 'free_play');
  return requiresFreeform && !plan.freeformCompleted ? 'assessment_required' : 'completed';
};

const hasSatisfiedPrerequisites = (
  prerequisiteIds: readonly string[],
  progress: Readonly<Record<string, ConceptProgress>>,
): boolean => prerequisiteIds.every((id) => (progress[id]?.learnedPercent ?? 0) >= 100);

const createItem = (
  id: string,
  kind: PlanItem['kind'],
  conceptIds: string[],
  unitIds: string[],
  outcome: string,
  minutes: number,
  title: string,
): PlanItem => ({
  id,
  conceptId: conceptIds[0],
  conceptIds,
  unitIds,
  kind,
  title,
  outcome,
  objective: outcome,
  estimatedMinutes: minutes,
  completedMinutes: 0,
  completionCredit: 0,
  completionRules: conceptIds.map((conceptId) => ({
    evidenceType: kind === 'free_play' ? 'output' : kind === 'review' ? 'retrieval' : 'controlled_practice',
    conceptId,
    requiredCount: 1,
    minimumQuality: kind === 'new' ? 0.6 : 0.75,
  })),
  completed: false,
});

export function generateDailyPlan(input: PlannerInput): DailyPlan {
  if (!Number.isFinite(input.budgetMinutes) || input.budgetMinutes <= 0) throw new RangeError('budgetMinutes must be positive');
  let remaining = input.budgetMinutes;
  const items: PlanItem[] = [];
  const due = Object.values(input.progress)
    .filter((item) => item.nextReviewAt && item.nextReviewAt <= input.date)
    .sort((left, right) => left.nextReviewAt!.localeCompare(right.nextReviewAt!));
  const dueDemand = due.reduce((sum) => sum + 3, 0);
  const reviewOnly = dueDemand >= input.budgetMinutes * 0.8;
  const minimumAnchorMinutes = input.blueprints
    .filter((blueprint) => blueprint.planningEnabled !== false
      && (blueprint.maximumDailyBudgetMinutes === undefined || input.budgetMinutes <= blueprint.maximumDailyBudgetMinutes)
      && hasSatisfiedPrerequisites(blueprint.prerequisiteConceptIds, input.progress)
      && blueprint.requiredConceptIds.some((id) => (input.progress[id]?.learnedPercent ?? 0) < 100))
    .reduce((minimum, blueprint) => Math.min(minimum, blueprint.estimatedMinutes), Number.POSITIVE_INFINITY);

  for (const progress of due) {
    if (remaining < 3) break;
    if (!reviewOnly && Number.isFinite(minimumAnchorMinutes) && remaining - 3 < minimumAnchorMinutes) break;
    const concept = input.concepts.find((candidate) => candidate.conceptId === progress.conceptId);
    items.push(createItem(`review_${progress.conceptId}`, 'review', [progress.conceptId], [], `Recall and use ${concept?.titleEn ?? 'a learned expression'}.`, 3, `Review · ${friendlyConceptName(progress.conceptId, concept)}`));
    remaining -= 3;
  }

  if (reviewOnly) return buildPlan(input, items, undefined, 'Review day');

  const unitById = new Map(input.units.map((unit) => [unit.id, unit]));
  const allEligibleBlueprints = input.blueprints.filter((blueprint) =>
    hasSatisfiedPrerequisites(blueprint.prerequisiteConceptIds, input.progress)
    && (blueprint.maximumDailyBudgetMinutes === undefined || input.budgetMinutes <= blueprint.maximumDailyBudgetMinutes)
    && blueprint.estimatedMinutes <= remaining
    && blueprint.requiredConceptIds.some((id) => (input.progress[id]?.learnedPercent ?? 0) < 100),
  );
  const communicationBlueprints = allEligibleBlueprints.filter((blueprint) => blueprint.planningEnabled !== false);
  const eligibleBlueprints = communicationBlueprints.length > 0 ? communicationBlueprints : allEligibleBlueprints;
  const scored = eligibleBlueprints.map((blueprint) => {
    const sequence = Math.min(...blueprint.requiredConceptIds.map((id) => input.concepts.find((c) => c.conceptId === id)?.sequenceNo ?? 999));
    const uncovered = blueprint.requiredConceptIds.filter((id) => (input.progress[id]?.learnedPercent ?? 0) < 100).length / blueprint.requiredConceptIds.length;
    const themeMatch = blueprint.supportedThemes.some((theme) => input.interests.includes(theme)) ? 1 : 0;
    const novelty = blueprint.requiredConceptIds.every((id) => !input.progress[id]) ? 1 : 0;
    return { blueprint, score: 0.45 * (1 / sequence) + 0.25 * uncovered + 0.15 * themeMatch + 0.15 * novelty };
  }).sort((left, right) => right.score - left.score || left.blueprint.id.localeCompare(right.blueprint.id));
  const anchor = scored[0]?.blueprint;

  const remedialSpace = anchor ? Math.max(0, remaining - anchor.estimatedMinutes) : 0;
  const remedialCap = Math.min(Math.floor(input.budgetMinutes * 0.25), remedialSpace);
  let remedialMinutes = 0;
  for (const error of [...input.errors].sort((a, b) => b.occurrences - a.occurrences)) {
    if (!anchor?.requiredConceptIds.includes(error.conceptId)) continue;
    const minutes = Math.min(3, remedialCap - remedialMinutes);
    if (minutes < 2 || minutes > remaining) break;
    const concept = input.concepts.find((candidate) => candidate.conceptId === error.conceptId);
    items.push(createItem(`remedial_${error.conceptId}`, 'remedial', [error.conceptId], [], `Correct one recurring issue before today’s speaking task.`, minutes, `Fix · ${friendlyConceptName(error.conceptId, concept)}`));
    remedialMinutes += minutes;
    remaining -= minutes;
  }

  if (anchor) {
    const scheduledConceptIds = new Set(items.flatMap((item) => item.conceptIds));
    for (const unitId of anchor.requiredUnitIds) {
      const unit = unitById.get(unitId);
      if (!unit || unit.estimatedMinutes > remaining) break;
      const concept = input.concepts.find((candidate) => candidate.conceptId === unit.conceptIds[0]);
      const prefix = concept?.category === 'pinyin' ? 'Sounds' : concept?.category === 'grammar' ? 'Pattern' : 'Use it';
      items.push(createItem(`new_${unit.id}`, 'new', unit.conceptIds, [unit.id], concept?.communicativeGoal ?? unit.functionId, unit.estimatedMinutes, `${prefix} · ${friendlyConceptName(unit.conceptIds[0], concept)}`));
      unit.conceptIds.forEach((conceptId) => scheduledConceptIds.add(conceptId));
      remaining -= unit.estimatedMinutes;
    }
    const freePlayReserve = remaining >= 4 ? 4 : 2;
    const anchorSequence = Math.min(...anchor.requiredConceptIds.map((conceptId) =>
      input.concepts.find((concept) => concept.conceptId === conceptId)?.sequenceNo ?? Number.POSITIVE_INFINITY));

    // Sort unlearned units: first by theme match with learner interests / anchor, then by curriculum sequence
    const supplementalUnits = input.units
      .filter((unit) => unit.role === 'new_learning'
        && !anchor.requiredUnitIds.includes(unit.id)
        && unit.conceptIds.some((conceptId) => (input.progress[conceptId]?.learnedPercent ?? 0) < 100))
      .sort((left, right) => {
        const leftThemeMatch = left.supportedThemes.some((t) => input.interests.includes(t) || anchor.supportedThemes.includes(t)) ? 1 : 0;
        const rightThemeMatch = right.supportedThemes.some((t) => input.interests.includes(t) || anchor.supportedThemes.includes(t)) ? 1 : 0;
        const leftSeq = input.concepts.find((c) => c.conceptId === left.conceptIds[0])?.sequenceNo ?? 999;
        const rightSeq = input.concepts.find((c) => c.conceptId === right.conceptIds[0])?.sequenceNo ?? 999;
        return rightThemeMatch - leftThemeMatch || leftSeq - rightSeq || left.id.localeCompare(right.id);
      });

    for (const unit of supplementalUnits) {
      const prerequisitesSatisfied = unit.prerequisiteConceptIds.every((conceptId) =>
        (input.progress[conceptId]?.learnedPercent ?? 0) >= 100 || scheduledConceptIds.has(conceptId));
      if (!prerequisitesSatisfied || unit.estimatedMinutes > remaining - freePlayReserve) continue;
      const concept = input.concepts.find((candidate) => candidate.conceptId === unit.conceptIds[0]);
      const prefix = concept?.category === 'pinyin' ? 'Sounds' : concept?.category === 'grammar' ? 'Pattern' : 'Use it';
      items.push(createItem(`new_${unit.id}`, 'new', unit.conceptIds, [unit.id], concept?.communicativeGoal ?? unit.functionId, unit.estimatedMinutes, `${prefix} · ${friendlyConceptName(unit.conceptIds[0], concept)}`));
      unit.conceptIds.forEach((conceptId) => scheduledConceptIds.add(conceptId));
      remaining -= unit.estimatedMinutes;
      if (remaining <= freePlayReserve) break;
    }

    // If remaining budget still exists, add consolidation reviews for learned concepts
    if (remaining - freePlayReserve >= 3) {
      const candidateConcepts = input.concepts.filter((c) =>
        (input.progress[c.conceptId]?.learnedPercent ?? 0) >= 100 &&
        !scheduledConceptIds.has(c.conceptId),
      );
      for (const concept of candidateConcepts) {
        if (remaining - freePlayReserve < 3) break;
        items.push(createItem(`review_${concept.conceptId}`, 'review', [concept.conceptId], [], `Consolidate ${concept.titleEn}.`, 3, `Consolidate · ${friendlyConceptName(concept.conceptId, concept)}`));
        scheduledConceptIds.add(concept.conceptId);
        remaining -= 3;
      }
    }

    const freePlayMinutes = Math.min(4, remaining);
    if (freePlayMinutes >= 2 && anchor.requiredConceptIds.every((id) =>
      items.some((item) => item.conceptIds.includes(id)) || (input.progress[id]?.learnedPercent ?? 0) > 0)) {
      items.push(createItem(`free_play_${anchor.id}`, 'free_play', anchor.requiredConceptIds, anchor.requiredUnitIds, anchor.outcome, freePlayMinutes, 'Speak · Try it yourself'));
      remaining -= freePlayMinutes;
    }
  }
  return buildPlan(input, items, anchor, remaining > 0 ? `${remaining} min open` : 'Ready');
}

function friendlyConceptName(conceptId: string, concept?: CurriculumConcept): string {
  return concept ? curriculumShortTitle(concept) : conceptId;
}

function buildPlan(
  input: PlannerInput,
  items: PlanItem[],
  blueprint: DailyGoalBlueprint | undefined,
  rationale: string,
): DailyPlan {
  // Cap items so total estimated minutes strictly does not exceed input.budgetMinutes
  let totalMinutes = 0;
  const prunedItems: PlanItem[] = [];
  for (const item of items) {
    if (totalMinutes + item.estimatedMinutes <= input.budgetMinutes) {
      prunedItems.push(item);
      totalMinutes += item.estimatedMinutes;
    } else {
      const avail = input.budgetMinutes - totalMinutes;
      if (avail >= 2) {
        prunedItems.push({ ...item, estimatedMinutes: avail });
        totalMinutes += avail;
      }
      break;
    }
  }

  return {
    id: `plan_${input.learnerId}_${input.date.slice(0, 10)}`,
    learnerId: input.learnerId,
    date: input.date,
    status: 'active',
    title: blueprint?.title ?? 'Daily consolidation',
    budgetMinutes: input.budgetMinutes,
    estimatedMinutes: totalMinutes,
    effectiveMinutes: 0,
    items: prunedItems,
    rationale,
    blueprintId: blueprint?.id,
    outcome: blueprint?.outcome ?? 'Consolidate today\'s learning and prepare for tomorrow.',
    freeformCompleted: false,
    freeformAssessment: blueprint?.freeformAssessment,
    stateVersion: input.stateVersion,
    generatedAt: input.date,
    createdAt: input.date,
    plannerVersion: DAILY_PLANNER_VERSION,
  };
}
