import { ConceptProgress } from '../types.ts';

export interface LearningEvidencePatch {
  cardCompletion?: number;
  practiceCompletion?: number;
  outputCompletion?: number;
}

export const LEARNING_COMPLETION_VERSION = 2;

const clamp01 = (value: number): number => Math.max(0, Math.min(1, value));

export function inferLearningEvidence(progress: Pick<ConceptProgress, 'learnedPercent' | 'learningEvidence'>): Required<LearningEvidencePatch> {
  if (progress.learningEvidence) {
    return {
      cardCompletion: clamp01(progress.learningEvidence.cardCompletion),
      practiceCompletion: clamp01(progress.learningEvidence.practiceCompletion),
      outputCompletion: clamp01(progress.learningEvidence.outputCompletion),
    };
  }

  // Preserve persisted legacy completion conservatively until new typed evidence arrives.
  const learned = Math.max(0, Math.min(100, progress.learnedPercent));
  return {
    cardCompletion: clamp01(Math.max(0, learned - 40) / 40),
    practiceCompletion: clamp01(learned / 40),
    outputCompletion: clamp01(Math.max(0, learned - 80) / 20),
  };
}

export function calculateLearnedPercent(evidence: Required<LearningEvidencePatch>): number {
  return 100 * (
    0.4 * clamp01(evidence.cardCompletion)
    + 0.4 * clamp01(evidence.practiceCompletion)
    + 0.2 * clamp01(evidence.outputCompletion)
  );
}

export function applyLearningEvidence(
  progress: ConceptProgress,
  patch: LearningEvidencePatch,
): Pick<ConceptProgress, 'learnedPercent' | 'learningEvidence' | 'learningCompletionVersion'> {
  const current = inferLearningEvidence(progress);
  const learningEvidence = {
    cardCompletion: Math.max(current.cardCompletion, clamp01(patch.cardCompletion ?? 0)),
    practiceCompletion: Math.max(current.practiceCompletion, clamp01(patch.practiceCompletion ?? 0)),
    outputCompletion: Math.max(current.outputCompletion, clamp01(patch.outputCompletion ?? 0)),
  };
  return {
    learningEvidence,
    learnedPercent: calculateLearnedPercent(learningEvidence),
    learningCompletionVersion: LEARNING_COMPLETION_VERSION,
  };
}

/** Records completion of one atomic LearningUnit, including its required output step. */
export function completeLearningUnit(
  progress: ConceptProgress,
): Pick<ConceptProgress, 'learnedPercent' | 'learningEvidence' | 'learningCompletionVersion'> {
  return applyLearningEvidence(progress, {
    cardCompletion: 1,
    practiceCompletion: 1,
    outputCompletion: 1,
  });
}
