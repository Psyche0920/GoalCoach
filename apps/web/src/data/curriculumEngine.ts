import { HSK1_CONCEPTS_EXPANDED } from './concepts.ts';
import {
  CurriculumConcept,
  DailyGoalBlueprint,
  FreeformAssessmentSpec,
  LearningStepType,
  LearningUnit,
} from '../types.ts';

const CORE_STEPS: LearningStepType[] = [
  'hook',
  'notice',
  'explain',
  'controlled_practice',
  'retrieval',
  'output',
];

const moduleGroups = new Map<string, CurriculumConcept[]>();
for (const concept of HSK1_CONCEPTS_EXPANDED) {
  const key = concept.module;
  moduleGroups.set(key, [...(moduleGroups.get(key) ?? []), concept]);
}
for (const concepts of moduleGroups.values()) {
  concepts.sort((left, right) => left.sequenceNo - right.sequenceNo);
}

const prerequisiteByConcept = new Map<string, string[]>();
for (const concepts of moduleGroups.values()) {
  concepts.forEach((concept, index) => {
    prerequisiteByConcept.set(concept.conceptId, index === 0 ? [] : [concepts[index - 1].conceptId]);
  });
}

const earlyCurriculumPrerequisites: Readonly<Record<string, string[]>> = {
  hsk1_p01: [],
  hsk1_c01: [],
  hsk1_p02: [],
  hsk1_c02: ['hsk1_c01'],
  hsk1_c05: ['hsk1_c02'],
  hsk1_p03: ['hsk1_p02'],
  hsk1_c03: ['hsk1_c02'],
  hsk1_p04: ['hsk1_p03'],
  hsk1_c04: ['hsk1_c03'],
  hsk1_p05: ['hsk1_p03'],
  hsk1_c07: ['hsk1_c04'],
  hsk1_p06: ['hsk1_p05'],
  hsk1_c16: ['hsk1_c07'],
};
for (const [conceptId, prerequisiteIds] of Object.entries(earlyCurriculumPrerequisites)) {
  prerequisiteByConcept.set(conceptId, prerequisiteIds);
}

export const LEARNING_UNITS: LearningUnit[] = HSK1_CONCEPTS_EXPANDED.map((concept) => ({
  id: `unit_${concept.conceptId}`,
  conceptIds: [concept.conceptId],
  functionId: concept.slug,
  role: 'new_learning',
  prerequisiteConceptIds: prerequisiteByConcept.get(concept.conceptId) ?? [],
  steps: CORE_STEPS.map((type, index) => ({
    id: `unit_${concept.conceptId}_${type}`,
    type,
    instruction: `${type.replace('_', ' ')}: ${concept.communicativeGoal}`,
    estimatedMinutes: index < 3 ? 0.4 : 0.6,
  })),
  supportedThemes: [concept.theme],
  vocabularySlots: concept.vocabularyFocus.slice(0, 4),
  estimatedMinutes: 3,
  difficulty: concept.difficulty,
}));

const coverageGroups = Array.from({ length: Math.ceil(LEARNING_UNITS.length / 4) }, (_, index) =>
  LEARNING_UNITS.slice(index * 4, index * 4 + 4),
);

const coverageBlueprints: DailyGoalBlueprint[] = coverageGroups.map((units, index) => {
  const conceptIds = units.flatMap((unit) => unit.conceptIds);
  const concepts = conceptIds.map((id) => HSK1_CONCEPTS_EXPANDED.find((item) => item.conceptId === id)!);
  const allowedLanguage = Array.from(new Set(concepts.flatMap((concept) => concept.vocabularyFocus))).slice(0, 12);
  return {
    id: `coverage_goal_${String(index + 1).padStart(2, '0')}`,
    title: `HSK 1 communication step ${index + 1}`,
    outcome: concepts.map((concept) => concept.communicativeGoal).join(' '),
    requiredConceptIds: conceptIds,
    requiredUnitIds: units.map((unit) => unit.id),
    outputTemplateId: index < 4 ? 'two_turn_dialogue' : 'guided_writing',
    prerequisiteConceptIds: Array.from(new Set(units.flatMap((unit) => unit.prerequisiteConceptIds)))
      .filter((id) => !conceptIds.includes(id)),
    estimatedMinutes: units.reduce((sum, unit) => sum + unit.estimatedMinutes, 0) + 4,
    supportedThemes: Array.from(new Set(concepts.map((concept) => concept.theme))),
    freeformAssessment: {
      mode: index < 4 ? 'scenario_writing' : 'translation',
      targetConceptIds: conceptIds,
      allowedInputScripts: ['hanzi', 'pinyin_tone_marks', 'pinyin_tone_numbers'],
      minimumTurns: index < 4 ? 2 : undefined,
      completionGate: { targetConceptScore: 0.75, taskAchievementScore: 0.75 },
      allowedLanguage,
      example: index === 0 ? 'bā, mā, nǐ hǎo' : allowedLanguage.slice(0, 4).join(' '),
    },
    planningEnabled: false,
  };
});

const createCommunicationBlueprint = (
  id: string,
  title: string,
  outcome: string,
  conceptIds: string[],
  prerequisiteConceptIds: string[],
  allowedLanguage: string[],
  example: string,
): DailyGoalBlueprint => ({
  id,
  title,
  outcome,
  requiredConceptIds: conceptIds,
  requiredUnitIds: conceptIds.map((conceptId) => `unit_${conceptId}`),
  outputTemplateId: 'two_turn_dialogue',
  prerequisiteConceptIds,
  estimatedMinutes: conceptIds.length * 3 + 4,
  supportedThemes: Array.from(new Set(conceptIds.map((conceptId) =>
    HSK1_CONCEPTS_EXPANDED.find((concept) => concept.conceptId === conceptId)!.theme))),
  freeformAssessment: {
    mode: 'scenario_writing',
    targetConceptIds: conceptIds,
    allowedInputScripts: ['hanzi', 'pinyin_tone_marks', 'pinyin_tone_numbers'],
    minimumTurns: 2,
    completionGate: { targetConceptScore: 0.75, taskAchievementScore: 0.75 },
    allowedLanguage,
    example,
  },
  planningEnabled: true,
});

const COMMUNICATION_BLUEPRINTS: DailyGoalBlueprint[] = [
  {
    ...createCommunicationBlueprint('anchor_00_hello', 'Say hello', 'Greet someone and reply naturally.', ['hsk1_c01'], [], ['你', '好', '你好', '再见'], 'A: 你好！ B: 你好！'),
    estimatedMinutes: 5,
    maximumDailyBudgetMinutes: 5,
  },
  createCommunicationBlueprint('anchor_01_greet', 'Greetings', 'Greet someone and close politely.', ['hsk1_p02', 'hsk1_c01'], [], ['你', '好', '你好', '谢谢', '再见'], '你好！谢谢，再见！'),
  createCommunicationBlueprint('anchor_02_meet_someone', 'Meet someone', 'Introduce yourself and ask back naturally.', ['hsk1_c02', 'hsk1_c05'], ['hsk1_p02', 'hsk1_c01'], ['我', '你', '叫', '呢', '你好', '名字'], '你好，我叫 Ann。你呢？'),
  createCommunicationBlueprint('anchor_03_identity', 'Introduce yourself', 'Say whether you are a student or teacher.', ['hsk1_p03', 'hsk1_c03'], ['hsk1_p02', 'hsk1_c02'], ['我', '你', '他', '她', '是', '学生', '老师'], 'A: 你是学生吗？ B: 我是学生。'),
  createCommunicationBlueprint('anchor_04_ask_question', 'Ask a question', 'Ask and answer a simple identity question with 吗.', ['hsk1_c04'], ['hsk1_p03', 'hsk1_c03'], ['我', '你', '是', '学生', '老师', '吗'], '你是学生吗？是，我是学生。'),
  createCommunicationBlueprint('anchor_05_say_no', 'Correct someone', 'Use 不 to correct a simple statement.', ['hsk1_p05', 'hsk1_c07'], ['hsk1_p04', 'hsk1_c04'], ['我', '你', '是', '不', '学生', '老师'], 'A: 你是老师吗？ B: 我不是老师，我是学生。'),
  createCommunicationBlueprint('anchor_06_say_what_you_want', 'Say what you want', 'Use 我想… to express one simple wish.', ['hsk1_p04', 'hsk1_c16'], ['hsk1_p05', 'hsk1_c07'], ['我', '想', '喝', '茶', '吃', '米饭', '去', '中国'], '我想喝茶。你呢？'),
];

const FREEFORM_DETAILS: Readonly<Record<string, Pick<FreeformAssessmentSpec, 'prompt' | 'responseChoices' | 'requiredResponsePatterns'>>> = {
  anchor_00_hello: {
    prompt: 'A: 你好!\nA: 再见!\nReply to both lines.',
    responseChoices: ['你好!\n再见!', '您好!\n再见!'],
    requiredResponsePatterns: [['你好', '您好', 'nihao', 'ninhao'], ['再见', 'zaijian']],
  },
  anchor_01_greet: {
    prompt: 'A: 你好!\nA: 再见!\nReply to both lines.',
    responseChoices: ['你好!\n再见!', '您好!\n谢谢，再见!'],
    requiredResponsePatterns: [['你好', '您好', 'nihao', 'ninhao'], ['再见', 'zaijian']],
  },
  anchor_02_meet_someone: {
    prompt: 'A: 你好，我叫小王。你呢?\nIntroduce yourself, then ask back.',
    responseChoices: ['你好，我叫 Ann。你呢?', '我叫 Ann，你呢?'],
    requiredResponsePatterns: [['我叫', 'wojiao'], ['你呢', 'nine']],
  },
  anchor_03_identity: {
    prompt: 'A: 我是老师。你呢?\nState your role, then ask back.',
    responseChoices: ['我是学生。你呢?', '我是老师。你呢?'],
    requiredResponsePatterns: [['我是学生', '我是老师', 'woshixuesheng', 'woshilaoshi'], ['你呢', 'nine']],
  },
  anchor_04_ask_question: {
    prompt: 'Ask whether someone is a student, then answer the same question.',
    responseChoices: ['你是学生吗?\n是，我是学生。', '你是老师吗?\n不，我是学生。'],
    requiredResponsePatterns: [['你是学生吗', '你是老师吗', 'nishixueshengma', 'nishilaoshima'], ['我是学生', '我是老师', 'woshixuesheng', 'woshilaoshi']],
  },
  anchor_05_say_no: {
    prompt: 'A: 你是老师。\nCorrect the statement and give the right role.',
    responseChoices: ['我不是老师。我是学生。', '我不是学生。我是老师。'],
    requiredResponsePatterns: [['我不是老师', '我不是学生', 'wobushilaoshi', 'wobushixuesheng'], ['我是学生', '我是老师', 'woshixuesheng', 'woshilaoshi']],
  },
  anchor_06_say_what_you_want: {
    prompt: 'A: 你想喝什么?\nAnswer, then ask back.',
    responseChoices: ['我想喝茶。你呢?', '我想吃米饭。你呢?'],
    requiredResponsePatterns: [['我想喝茶', '我想吃米饭', 'woxianghecha', 'woxiangchimifan'], ['你呢', 'nine']],
  },
};

for (const blueprint of COMMUNICATION_BLUEPRINTS) {
  Object.assign(blueprint.freeformAssessment, FREEFORM_DETAILS[blueprint.id]);
}

export const DAILY_GOAL_BLUEPRINTS: DailyGoalBlueprint[] = [...COMMUNICATION_BLUEPRINTS, ...coverageBlueprints];

const blueprintIdsByConcept = new Map<string, string[]>();
for (const blueprint of DAILY_GOAL_BLUEPRINTS) {
  for (const conceptId of blueprint.requiredConceptIds) {
    blueprintIdsByConcept.set(conceptId, [...(blueprintIdsByConcept.get(conceptId) ?? []), blueprint.id]);
  }
}

export const SYSTEM_CURRICULUM_CONCEPTS: CurriculumConcept[] = HSK1_CONCEPTS_EXPANDED.map((concept) => ({
  ...concept,
  prerequisiteIds: prerequisiteByConcept.get(concept.conceptId) ?? [],
  learningUnitIds: [`unit_${concept.conceptId}`],
  dailyGoalBlueprintIds: blueprintIdsByConcept.get(concept.conceptId) ?? [],
  moduleId: concept.module,
  weight: 1,
  communicativeFunctions: [concept.communicativeGoal],
  allowedVocabularyLevel: 1,
  requiredOutputPattern: concept.grammarFocus[0] ?? concept.communicativeGoal,
}));
