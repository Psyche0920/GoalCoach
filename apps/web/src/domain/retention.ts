/**
 * Deterministic spaced repetition forgetting curve algorithms and retention mathematics.
 * R = R_0 * exp(-lambda * delta_t)
 */

export function calculateRetention(
  retentionAtReview: number,
  lastReviewedAt: string | Date,
  at: string | Date = new Date(),
  decayLambda: number = 0.05
): number {
  if (decayLambda <= 0) {
    decayLambda = 0.05;
  }

  const reviewTime = typeof lastReviewedAt === 'string' ? new Date(lastReviewedAt).getTime() : lastReviewedAt.getTime();
  const targetTime = typeof at === 'string' ? new Date(at).getTime() : at.getTime();

  const elapsedSeconds = Math.max(0, (targetTime - reviewTime) / 1000);
  const elapsedDays = elapsedSeconds / 86400.0;

  const decayed = retentionAtReview * Math.exp(-decayLambda * elapsedDays);
  return Math.max(0.0, Math.min(1.0, decayed));
}

export function isConceptReviewDue(
  nextReviewAt?: string,
  at: string | Date = new Date()
): boolean {
  if (!nextReviewAt) return false;
  const nextReview = new Date(nextReviewAt).getTime();
  const targetTime = typeof at === 'string' ? new Date(at).getTime() : at.getTime();
  return nextReview <= targetTime;
}
