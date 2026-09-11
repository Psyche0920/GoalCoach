export type Score = number; // 0.0 to 1.0

export type PlanItemKind = 'review' | 'remedial' | 'new' | 'free_play' | 'daily_quiz';
export type PlanStatus = 'active' | 'learning_complete' | 'assessment_required' | 'completed' | 'exhausted' | 'invalid';
export type NextAction = 'plan_goal' | 'plan_review' | 'regenerate_plan' | 'teach';

export type ConceptCategory = 'pinyin' | 'grammar' | 'general_knowledge' | 'scenario';

export type CurriculumModule = 'module1_pinyin' | 'module2_grammar' | 'module3_thematic' | 'module3_themes' | 'module1_grammar' | 'module2_vocabulary';

export type CurriculumTheme =
  | 'pinyin_basics'
  | 'core_grammar'
  | 'greetings_etiquette'
  | 'identity_family'
  | 'numbers_time'
  | 'dining_food'
  | 'shopping_prices'
  | 'travel_directions'
  | 'daily_life'
  | 'work_study'
  | 'weather_feelings';

export interface LearningGoal {
  id: string;
  title: string;
  targetHskLevel: number; // 1 to 6
  targetDate?: string;
  dailyAvailableMinutes: number;
  interests?: CurriculumTheme[];
  targetDomain?: 'general' | 'travel' | 'dining' | 'work' | 'daily';
  version: number;
  createdAt: string;
}

export interface ConceptMastery {
  conceptId: string;
  masteryScore: Score;
  retentionScore: Score;
  decayLambda: number;
  evidenceCount: number;
  intervalDays: number;
  lastReviewedAt: string;
  nextReviewAt?: string;
  weight: number;
}

export interface ErrorRecord {
  code: string;
  conceptId: string;
  occurrences: number;
  lastSeenAt: string;
  examples: string[];
}

export interface PlanItem {
  id: string;
  /** @deprecated Use conceptIds. Retained while legacy lesson launchers migrate. */
  conceptId?: string;
  conceptIds?: string[];
  unitIds?: string[];
  kind: PlanItemKind;
  title?: string;
  outcome?: string;
  objective: string;
  estimatedMinutes: number;
  completedMinutes?: number;
  completionCredit?: number;
  completionRules?: CompletionRule[];
  completed: boolean;
}

export interface DailyPlan {
  id: string;
  learnerId: string;
  date: string;
  status: PlanStatus;
  title?: string;
  budgetMinutes?: number;
  estimatedMinutes?: number;
  effectiveMinutes?: number;
  items: PlanItem[];
  rationale: string;
  blueprintId?: string;
  outcome?: string;
  freeformCompleted?: boolean;
  freeformAssessment?: FreeformAssessmentSpec;
  stateVersion?: number;
  generatedAt: string;
  createdAt?: string;
  completedAt?: string;
  plannerVersion?: number;
}

export type ExerciseType = 
  | 'meaning_mcq'
  | 'zh_to_en_mcq'
  | 'en_to_zh_mcq'
  | 'fill_blank'
  | 'reorder'
  | 'translate_to_zh'
  | 'dialogue_choice';

export interface Exercise {
  id: string;
  conceptId: string;
  exerciseOrder: number;
  exerciseType: ExerciseType;
  theme?: CurriculumTheme;
  tags?: string[];
  prompt: string;
  promptPinyin?: string;
  instruction: string;
  answer: string; // JSON string or plain text
  options?: string[];
  acceptedAnswers: string[];
  explanation: string;
  targetTokens: string[];
  errorTags: string[];
  difficulty: number;
  points?: number;
}

export interface TeachingCard {
  id: number;
  conceptId: string;
  cardOrder: number;
  cardType: 'goal' | 'vocab' | 'grammar' | 'example' | 'tip' | 'mini_dialogue' | 'communication' | 'mixed';
  category?: ConceptCategory;
  theme?: CurriculumTheme;
  tags?: string[];
  promptZh?: string;
  pinyin?: string;
  meaningEn?: string;
  explanationEn?: string;
  exampleZh?: string;
  examplePinyin?: string;
  exampleEn?: string;
  payload?: Record<string, any>;
  tailoredVariants?: Record<string, { exampleZh: string; examplePinyin: string; exampleEn: string; explanationEn?: string }>;
}

export interface CurriculumConcept {
  conceptId: string;
  hskLevel: number;
  sequenceNo: number;
  slug: string;
  titleZh: string;
  titleEn: string;
  conceptType: 'communication' | 'grammar' | 'vocabulary' | 'mixed';
  category: ConceptCategory;
  module: CurriculumModule;
  theme: CurriculumTheme;
  tags: string[];
  isCoreGrammar: boolean;
  communicativeGoal: string;
  grammarFocus: string[];
  vocabularyFocus: string[];
  difficulty: number;
  estimatedMinutes: number;
  prerequisiteIds?: string[];
  learningUnitIds?: string[];
  dailyGoalBlueprintIds?: string[];
  moduleId?: string;
  weight?: number;
  communicativeFunctions?: string[];
  allowedVocabularyLevel?: number;
  requiredOutputPattern?: string;
  tailoredExamples?: Record<string, { zh: string; pinyin: string; en: string }>;
}

export type LearningUnitRole = 'new_learning' | 'review' | 'remedial' | 'free_play_support';
export type LearningStepType = 'hook' | 'notice' | 'explain' | 'controlled_practice' | 'retrieval' | 'output';

export interface LearningStep {
  id: string;
  type: LearningStepType;
  instruction: string;
  estimatedMinutes: number;
}

export interface LearningUnit {
  id: string;
  conceptIds: string[];
  functionId: string;
  role: LearningUnitRole;
  prerequisiteConceptIds: string[];
  steps: LearningStep[];
  supportedThemes: CurriculumTheme[];
  vocabularySlots: string[];
  estimatedMinutes: number;
  difficulty: number;
}

export interface CompletionRule {
  evidenceType: 'view' | 'listen' | 'controlled_practice' | 'retrieval' | 'output';
  conceptId: string;
  requiredCount: number;
  minimumQuality?: number;
}

export interface FreeformAssessmentSpec {
  mode: 'translation' | 'scenario_writing';
  targetConceptIds: string[];
  allowedInputScripts: Array<'hanzi' | 'pinyin_tone_marks' | 'pinyin_tone_numbers'>;
  minimumTurns?: number;
  completionGate: { targetConceptScore: number; taskAchievementScore: number };
  allowedLanguage: string[];
  example: string;
  prompt?: string;
  responseChoices?: string[];
  requiredResponsePatterns?: string[][];
}

export interface DailyGoalBlueprint {
  id: string;
  title: string;
  outcome: string;
  requiredConceptIds: string[];
  requiredUnitIds: string[];
  outputTemplateId: string;
  prerequisiteConceptIds: string[];
  estimatedMinutes: number;
  maximumDailyBudgetMinutes?: number;
  supportedThemes: CurriculumTheme[];
  freeformAssessment: FreeformAssessmentSpec;
  planningEnabled?: boolean;
}

export interface ConceptProgress {
  learnerId: string;
  conceptId: string;
  learnedPercent: number;
  learningEvidence?: {
    cardCompletion: number;
    practiceCompletion: number;
    outputCompletion: number;
  };
  learningCompletionVersion?: number;
  retentionModelVersion?: number;
  masteryScore: number;
  retentionAtReview: number;
  decayLambda: number;
  successfulSpacedRetrievals: number;
  evidenceDays: number;
  averageQuality: number;
  qualityEvidenceCount?: number;
  reviewQualityCount?: number;
  averageReviewQuality?: number;
  isMastered?: boolean;
  status: 'not_started' | 'learning' | 'almost_mastered' | 'mastered';
  lastReviewedAt?: string;
  nextReviewAt?: string;
}

export interface LearningEvent {
  id: string;
  learnerId: string;
  planItemId: string;
  conceptIds: string[];
  eventType: 'card' | 'audio' | 'attempt' | 'output' | 'review';
  startedAt: string;
  lastActiveAt: string;
  activeSeconds: number;
  estimatedMinutes: number;
  engagementScore: number;
  gradingResult?: GradingResult;
  createdAt: string;
}

export interface ProgressSummary {
  stateVersion: number;
  courseCoverage: number;
  learnedProgress: number;
  masteredProgress: number;
  goalCompletion: number;
  goalScopeLearnedPercent?: number;
  goalScopeMasteredPercent?: number;
  communicationOutcomePercent?: number;
  dailyEffectiveMinutes: number;
}

export interface LearningUpdateResponse {
  stateVersion: number;
  plan: DailyPlan;
  affectedConcepts: ConceptProgress[];
  progressSummary: ProgressSummary;
  curriculumTree: {
    stateVersion: number;
    modules: Array<{ moduleId: string; concepts: Array<CurriculumConcept & { progress?: ConceptProgress }> }>;
  };
}

export interface PinyinContentMetadata {
  targetInitials: string[];
  targetFinals: string[];
  targetTones: number[];
  targetSyllables: string[];
  vocabularyLevel: 'known' | 'today' | 'optional_interest';
  prerequisiteConceptIds: string[];
  pedagogicalPurpose: 'perception' | 'articulation' | 'blending' | 'contrast' | 'production';
  reviewedByHuman: boolean;
  reviewNotes?: string;
}

export interface PinyinContentQualityChecklist {
  singleTeachingGoal: boolean;
  targetAlignment: boolean;
  beginnerAppropriate: boolean;
  naturalExamples: boolean;
  noUnintroducedGrammar: boolean;
  conciseBody: boolean;
  understandableExamples: boolean;
  audioPinyinHanziAligned: boolean;
  humanReviewed: boolean;
  productionReady: boolean;
}

export interface AnswerSubmission {
  learnerId: string;
  exerciseId: string;
  answer: string;
  submittedAt: string;
}

export interface RubricScores {
  grammaticalCorrectness: Score;
  semanticPrecision: Score;
  pragmaticAppropriateness: Score;
}

export interface GradingResult {
  exerciseId: string;
  scores: RubricScores;
  passedGates: boolean;
  confidence: Score;
  feedback: string;
  detectedErrors: string[];
  conceptErrors?: Array<{ code: string; conceptId: string; explanation: string }>;
  evidence?: string;
  graderVersion: string;
}

export interface SessionSummary {
  sessionId: string;
  startedAt: string;
  endedAt: string;
  conceptsCovered: string[];
  summary: string;
}

export interface LearnerState {
  learnerId: string;
  displayName?: string;
  goal: LearningGoal | null;
  goalChanged: boolean;
  mastery: Record<string, ConceptMastery>;
  errorProfile: ErrorRecord[];
  activePlan: DailyPlan | null;
  sessions: SessionSummary[];
  todayCheckedIn?: boolean;
  lastCheckInDate?: string;
  estimatedDaysRemaining?: number;
  todayMistakeExerciseIds?: string[];
  todayStudiedConceptIds?: string[];
  coachChatHistory?: Array<{ role: 'user' | 'assistant'; content: string; timestamp?: string }>;
  coachPreferences?: Record<string, any>;
  updatedAt: string;
  stateVersion?: number;
  conceptProgress?: Record<string, ConceptProgress>;
  passedBlueprintIds?: string[];
}
