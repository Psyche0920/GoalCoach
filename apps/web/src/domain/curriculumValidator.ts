import { CurriculumConcept, DailyGoalBlueprint, LearningUnit } from '../types.ts';
import { PinyinContentQualityChecklist } from '../types.ts';

export class CurriculumValidationError extends Error {
  public constructor(public readonly violations: string[]) {
    super(`Curriculum validation failed:\n${violations.join('\n')}`);
    this.name = 'CurriculumValidationError';
  }
}

export class CurriculumCoverageValidator {
  public validate(
    concepts: readonly CurriculumConcept[],
    units: readonly LearningUnit[],
    blueprints: readonly DailyGoalBlueprint[],
  ): void {
    const violations: string[] = [];
    const conceptIds = new Set(concepts.map((concept) => concept.conceptId));
    const unitIds = new Set(units.map((unit) => unit.id));
    const blueprintUnitIds = new Set(blueprints.flatMap((blueprint) => blueprint.requiredUnitIds));

    for (const concept of concepts) {
      if (!units.some((unit) => unit.conceptIds.includes(concept.conceptId))) violations.push(`Orphan concept: ${concept.conceptId}`);
      for (const prerequisiteId of concept.prerequisiteIds ?? []) {
        if (!conceptIds.has(prerequisiteId)) violations.push(`Invalid prerequisite ${prerequisiteId} in ${concept.conceptId}`);
      }
    }
    for (const unit of units) {
      if (!blueprintUnitIds.has(unit.id)) violations.push(`Orphan unit: ${unit.id}`);
      for (const conceptId of [...unit.conceptIds, ...unit.prerequisiteConceptIds]) {
        if (!conceptIds.has(conceptId)) violations.push(`Invalid concept ${conceptId} in ${unit.id}`);
      }
    }
    for (const blueprint of blueprints) {
      for (const conceptId of [...blueprint.requiredConceptIds, ...blueprint.prerequisiteConceptIds]) {
        if (!conceptIds.has(conceptId)) violations.push(`Invalid concept ${conceptId} in ${blueprint.id}`);
      }
      for (const unitId of blueprint.requiredUnitIds) {
        if (!unitIds.has(unitId)) violations.push(`Invalid unit ${unitId} in ${blueprint.id}`);
      }
      const requiredMinutes = units
        .filter((unit) => blueprint.requiredUnitIds.includes(unit.id))
        .reduce((sum, unit) => sum + unit.estimatedMinutes, 0);
      if (blueprint.estimatedMinutes < requiredMinutes) violations.push(`Insufficient time budget in ${blueprint.id}`);
    }

    const edges = new Map(concepts.map((concept) => [concept.conceptId, concept.prerequisiteIds ?? []]));
    const visiting = new Set<string>();
    const visited = new Set<string>();
    const visit = (id: string, path: string[]): void => {
      if (visiting.has(id)) {
        violations.push(`Prerequisite cycle: ${[...path, id].join(' -> ')}`);
        return;
      }
      if (visited.has(id)) return;
      visiting.add(id);
      for (const prerequisiteId of edges.get(id) ?? []) visit(prerequisiteId, [...path, id]);
      visiting.delete(id);
      visited.add(id);
    };
    for (const id of conceptIds) visit(id, []);

    if (violations.length > 0) throw new CurriculumValidationError(violations);
  }

  public validatePinyinCards(cards: readonly { id: string; pinyin: string; hanziPinyin: string; exampleWords?: readonly { pinyin: string }[]; metadata?: { targetSyllables: readonly string[]; reviewedByHuman: boolean }; qualityChecklist?: PinyinContentQualityChecklist }[]): void {
    const violations: string[] = [];
    for (const card of cards) {
      if (card.pinyin !== card.hanziPinyin && card.hanziPinyin.trim() !== '') violations.push(`Pinyin mismatch: ${card.id}`);
      if (!card.metadata) violations.push(`Missing Pinyin metadata: ${card.id}`);
      else {
        const searchable = [card.pinyin, ...(card.exampleWords ?? []).map((word) => word.pinyin)].join(' ').toLowerCase();
        if (!card.metadata.targetSyllables.some((syllable) => searchable.includes(syllable.toLowerCase()))) violations.push(`Target syllable not present: ${card.id}`);
        if (!card.metadata.reviewedByHuman) violations.push(`Pinyin card is not human-reviewed: ${card.id}`);
      }
      if (card.qualityChecklist && !card.qualityChecklist.productionReady) violations.push(`Pinyin card is not production-ready: ${card.id}`);
    }
    if (violations.length > 0) throw new CurriculumValidationError(violations);
  }
}
