import React, { useMemo, useState } from 'react';
import { ArrowRight, Check, Clock, Send, Target, X } from 'lucide-react';
import { CurriculumConcept, DailyPlan, GradingResult, LearnerState, LearningGoal, LearningUpdateResponse } from '../types.ts';

const ITEM_VISUALS = {
  review: { label: 'Review', icon: '↻', card: 'border-amber-200 bg-amber-50/60', badge: 'bg-amber-100 text-amber-800' },
  remedial: { label: 'Fix', icon: '+', card: 'border-rose-200 bg-rose-50/60', badge: 'bg-rose-100 text-rose-800' },
  new: { label: 'Learn', icon: '▶', card: 'border-sky-200 bg-sky-50/60', badge: 'bg-sky-100 text-sky-800' },
  free_play: { label: 'Speak', icon: '★', card: 'border-emerald-300 bg-emerald-50', badge: 'bg-emerald-600 text-white' },
  daily_quiz: { label: 'Practice', icon: '✓', card: 'border-violet-200 bg-violet-50/60', badge: 'bg-violet-100 text-violet-800' },
} as const;

interface DailyPlanViewProps {
  plan: DailyPlan | null;
  goal: LearningGoal | null;
  concepts: CurriculumConcept[];
  learnerState: LearnerState | null;
  overallProgress: number;
  todayMistakes?: string[];
  onStartStudy: (conceptId: string, mode?: 'review' | 'new' | 'remedial' | 'daily_quiz') => void;
  onUpdateGoal: (goal: Partial<LearningGoal>) => void;
  onRegeneratePlan: () => void;
  onLearningUpdate?: (response: LearningUpdateResponse) => void;
}

interface FreeformFeedback {
  passed: boolean;
  message: string;
  scores?: GradingResult['scores'];
  detectedErrors?: string[];
}

export const DailyPlanView: React.FC<DailyPlanViewProps> = ({
  plan,
  concepts,
  learnerState,
  onStartStudy,
  onRegeneratePlan,
  onLearningUpdate,
}) => {
  const [freeformOpen, setFreeformOpen] = useState(false);
  const [answer, setAnswer] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<FreeformFeedback | null>(null);
  const [freeformStartedAt, setFreeformStartedAt] = useState<string | null>(null);

  const completedCount = plan?.items.filter((item) => item.completed).length ?? 0;
  const remainingMinutes = useMemo(() => plan?.items
    .filter((item) => !item.completed)
    .reduce((sum, item) => sum + item.estimatedMinutes, 0) ?? 0, [plan]);
  const freeformItem = plan?.items.find((item) => item.kind === 'free_play');
  const allocation = useMemo(() => {
    if (!plan || !plan.estimatedMinutes) return [];
    const total = plan.estimatedMinutes;
    const reviewMin = plan.items.filter((i) => i.kind === 'review').reduce((s, i) => s + i.estimatedMinutes, 0);
    const fixMin = plan.items.filter((i) => i.kind === 'remedial').reduce((s, i) => s + i.estimatedMinutes, 0);
    const learnMin = plan.items.filter((i) => i.kind === 'new' || i.kind === 'free_play').reduce((s, i) => s + i.estimatedMinutes, 0);

    return [
      { kind: 'review', label: 'Review', minutes: reviewMin, color: 'bg-amber-400', percent: Math.round((reviewMin / total) * 100) },
      { kind: 'fix', label: 'Fix', minutes: fixMin, color: 'bg-rose-400', percent: Math.round((fixMin / total) * 100) },
      { kind: 'learn', label: 'Learn', minutes: learnMin, color: 'bg-emerald-500', percent: Math.round((learnMin / total) * 100) },
    ].filter((part) => part.minutes > 0);
  }, [plan]);
  const planSections = useMemo(() => {
    const items = plan?.items ?? [];
    return [
      { id: 'review', title: 'Review', icon: '↻', items: items.filter((item) => item.kind === 'review') },
      { id: 'fix', title: 'Fix', icon: '+', items: items.filter((item) => item.kind === 'remedial') },
      { id: 'learn', title: 'Learn', icon: '▶', items: items.filter((item) => item.kind === 'new' || item.kind === 'free_play') },
    ];
  }, [plan]);

  const learningType = (item: DailyPlan['items'][number]): string => {
    if (item.kind === 'free_play') return 'Freeform';
    const categories = (item.conceptIds ?? []).map((conceptId) => concepts.find((concept) => concept.conceptId === conceptId)?.category);
    return categories.includes('pinyin') ? 'Pinyin' : 'Grammar';
  };

  const launchItem = (itemId: string): void => {
    const item = plan?.items.find((candidate) => candidate.id === itemId);
    if (!item) return;
    if (item.kind === 'free_play') {
      setAnswer('');
      setFeedback(null);
      setFreeformStartedAt(new Date().toISOString());
      setFreeformOpen(true);
      return;
    }
    const conceptId = item.conceptIds?.[0] ?? item.conceptId;
    if (conceptId) {
      const isReview = item.completed || item.kind === 'review' || item.kind === 'remedial' || (learnerState?.conceptProgress?.[conceptId]?.learnedPercent ?? 0) >= 100;
      onStartStudy(conceptId, isReview ? 'review' : 'new');
    }
  };

  const submitFreeform = async (event: React.FormEvent): Promise<void> => {
    event.preventDefault();
    if (!answer.trim() || !freeformItem || !learnerState) return;
    setSubmitting(true);
    try {
      const gradeResponse = await fetch('/api/v1/grade-freeform', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userInput: answer.trim(), blueprintId: plan?.blueprintId }),
      });
      if (!gradeResponse.ok) throw new Error('Freeform grading failed.');
      const grade = await gradeResponse.json() as {
        score: number;
        passed: boolean;
        feedback: string;
        scores: GradingResult['scores'];
        detectedErrors: string[];
        targetConceptIds: string[];
        gradingResult: GradingResult;
      };
      setFeedback({ passed: grade.passed, message: grade.feedback, scores: grade.scores, detectedErrors: grade.detectedErrors });

      const now = new Date().toISOString();
      const startedAt = freeformStartedAt ?? now;
      const elapsedSeconds = Math.max(1, Math.round((Date.parse(now) - Date.parse(startedAt)) / 1000));
      const itemConceptIds = new Set(freeformItem.conceptIds ?? []);
      const targetConceptIds = grade.targetConceptIds.filter((conceptId) => itemConceptIds.has(conceptId));
      const evidenceResponse = await fetch('/api/v1/learning-events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          learnerId: learnerState.learnerId,
          planItemId: freeformItem.id,
          conceptIds: targetConceptIds,
          eventType: 'output',
          startedAt,
          lastActiveAt: now,
          activeSeconds: elapsedSeconds,
          engagementScore: grade.passed ? 1 : 0.75,
          gradingResult: { ...grade.gradingResult, exerciseId: freeformItem.id },
        }),
      });
      if (!evidenceResponse.ok) throw new Error('Learning evidence could not be saved.');
      onLearningUpdate?.(await evidenceResponse.json() as LearningUpdateResponse);
    } catch (error) {
      setFeedback({ passed: false, message: error instanceof Error ? error.message : 'Please try again.' });
    } finally {
      setSubmitting(false);
    }
  };

  if (!plan) {
    return (
      <section className="max-w-3xl mx-auto rounded-3xl border-2 border-zinc-200 bg-white p-8 text-center">
        <Target className="w-10 h-10 mx-auto text-emerald-600" />
        <h2 className="mt-3 text-xl font-black">Your plan is being prepared.</h2>
        <button type="button" onClick={onRegeneratePlan} className="mt-5 rounded-xl bg-emerald-500 px-5 py-3 font-black">Build today’s plan</button>
      </section>
    );
  }

  if (plan.status === 'completed') {
    return (
      <section className="max-w-3xl mx-auto rounded-3xl border-2 border-emerald-400 bg-emerald-50 p-8 text-center">
        <Check className="w-12 h-12 mx-auto text-emerald-700" />
        <h2 className="mt-3 text-2xl font-black">Done · {plan.effectiveMinutes ?? 0} active min</h2>
        <p className="mt-3 text-zinc-700">You can now: {plan.outcome}</p>
        <p className="mt-2 text-sm text-zinc-500">A short review returns tomorrow.</p>
      </section>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-5 pb-24">
      <section className="rounded-3xl border-2 border-zinc-200 bg-white p-6 shadow-xs">
        <p className="text-sm font-black text-emerald-700">Hi, Ann.</p>
        <h1 className="mt-2 text-2xl font-black text-zinc-950">{plan.estimatedMinutes ?? 0} minutes today</h1>
        <p className="mt-3 text-sm text-zinc-500">Today’s outcome</p>
        <p className="mt-1 text-lg font-black text-zinc-900">{plan.outcome}</p>
        <div className="mt-5 flex items-center gap-4 text-xs font-bold text-zinc-500">
          <span>{completedCount}/{plan.items.length} steps</span>
          <span className="flex items-center gap-1"><Clock className="w-4 h-4" />{remainingMinutes} min remaining</span>
        </div>
        <div className="mt-5 border-t border-zinc-100 pt-4">
          <div className="mb-2 flex items-center justify-between"><span className="text-xs font-black text-zinc-700">Time split</span><span className="text-xs text-zinc-400">{plan.estimatedMinutes} min</span></div>
          <div className="flex h-2.5 overflow-hidden rounded-full bg-zinc-100">
            {allocation.map((part) => <span key={part.kind} className={part.color} style={{ width: `${part.percent}%` }} />)}
          </div>
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
            {allocation.map((part) => <span key={part.kind} className="text-xs font-bold text-zinc-600">{part.label} {part.minutes}m · {part.percent}%</span>)}
          </div>
        </div>
      </section>

      {plan.items.every((item) => item.kind === 'review') && (
        <section className="flex items-center justify-between rounded-2xl border border-zinc-200 bg-zinc-50 px-4 py-3 text-xs font-bold text-zinc-600">
          <span>↻ Review day</span>
        </section>
      )}

      <section className="grid gap-4">
        {planSections.map((section) => (
          <div key={section.id} className="rounded-3xl border-2 border-zinc-200 bg-white p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="flex items-center gap-2 text-sm font-black text-zinc-900"><span>{section.icon}</span>{section.title}</h2>
              <span className="text-xs font-bold text-zinc-400">{section.items.reduce((sum, item) => sum + item.estimatedMinutes, 0)} min</span>
            </div>
            {section.items.length === 0 ? (
              <div className="flex items-center gap-2 rounded-xl bg-zinc-50 px-3 py-2 text-xs font-bold text-zinc-400"><Check className="h-4 w-4" />Not needed today</div>
            ) : (
              <div className="space-y-2">
                {section.items.map((item) => {
                  const visual = ITEM_VISUALS[item.kind];
                  return <button key={item.id} type="button" onClick={() => launchItem(item.id)} className={`w-full flex items-center gap-3 rounded-2xl border-2 p-4 text-left transition-all hover:-translate-y-0.5 hover:shadow-sm cursor-pointer ${visual.card}`}>
                    <span className={`w-9 h-9 rounded-xl flex items-center justify-center text-sm font-black ${item.completed ? 'bg-emerald-500 text-white' : visual.badge}`}>{item.completed ? <Check className="w-4 h-4" /> : visual.icon}</span>
                    <span className="flex-1 min-w-0">
                      <span className={`inline-flex rounded-md px-2 py-0.5 text-[10px] font-black ${visual.badge}`}>{section.id === 'learn' ? learningType(item) : visual.label}</span>
                      <span className="mt-1 block text-sm font-black text-zinc-950">{item.title?.replace(/^.*? · /, '') ?? item.objective}</span>
                      <span className="block truncate text-xs text-zinc-500">{item.outcome ?? item.objective}</span>
                    </span>
                    <span className="text-xs font-bold text-zinc-500">{item.estimatedMinutes} min</span>
                    {item.completed ? <Check className="h-5 w-5 text-emerald-600" /> : <ArrowRight className="w-4 h-4 text-emerald-700" />}
                  </button>;
                })}
              </div>
            )}
          </div>
        ))}
      </section>

      {plan.status === 'assessment_required' && <p className="rounded-2xl bg-amber-50 p-4 text-sm font-bold text-amber-900">One step left · Try it yourself</p>}

      {freeformOpen && freeformItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/70 p-4">
          <div className="w-full max-w-lg rounded-3xl border-2 border-zinc-950 bg-white p-6 shadow-xl">
            <div className="flex items-start justify-between gap-3">
              <div><p className="text-xs font-black uppercase text-emerald-700">{plan.freeformAssessment?.mode === 'translation' ? 'Translation' : 'Scenario writing'}</p><h2 className="mt-1 text-xl font-black">{plan.outcome}</h2></div>
              <button type="button" onClick={() => setFreeformOpen(false)}><X className="w-5 h-5" /></button>
            </div>
            <p className="mt-4 whitespace-pre-line text-sm font-bold text-zinc-700">{plan.freeformAssessment?.prompt ?? plan.outcome}</p>
            <p className="mt-3 text-xs text-zinc-500">Write in Hanzi or Pinyin.</p>
            <form onSubmit={submitFreeform} className="mt-4 space-y-3">
              <textarea value={answer} onChange={(event) => { setAnswer(event.target.value); setFeedback(null); }} className="min-h-28 w-full rounded-2xl border-2 border-zinc-200 p-3" placeholder="Type your response…" />
              {feedback && (
                <div className={`rounded-xl p-3 ${feedback.passed ? 'bg-emerald-50 text-emerald-800' : 'bg-amber-50 text-amber-900'}`}>
                  {feedback.scores && <div className="mb-2 grid grid-cols-3 gap-2 text-center text-[10px] font-black"><span>Meaning {Math.round(feedback.scores.semanticPrecision * 100)}%</span><span>Structure {Math.round(feedback.scores.grammaticalCorrectness * 100)}%</span><span>Task {Math.round(feedback.scores.pragmaticAppropriateness * 100)}%</span></div>}
                  <p className="text-sm font-bold">{feedback.message}</p>
                </div>
              )}
              <button disabled={!answer.trim() || submitting || feedback?.passed} className="w-full flex items-center justify-center gap-2 rounded-xl bg-emerald-500 px-5 py-3 font-black disabled:opacity-50"><Send className="w-4 h-4" />{submitting ? 'Checking…' : feedback?.passed ? 'Completed' : feedback ? 'Try again' : 'Check my answer'}</button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
