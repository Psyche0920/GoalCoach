import React from 'react';
import { BookOpen, CheckCircle2, Target } from 'lucide-react';
import { CurriculumConcept, LearnerState, ProgressSummary } from '../types.ts';

interface RetentionVisualizerProps {
  learnerState: LearnerState | null;
  concepts: CurriculumConcept[];
  overallProgress: number;
  progressSummary: ProgressSummary | null;
}

const toPercent = (value: number): number => Math.round(Math.max(0, Math.min(100, value)));

/** Displays server state only; client-side learning analytics intentionally do not live here. */
export const RetentionVisualizer: React.FC<RetentionVisualizerProps> = ({
  learnerState,
  concepts,
  overallProgress,
  progressSummary,
}) => {
  const goalCompletion = toPercent(overallProgress);
  const tracked = concepts.filter((concept) => learnerState?.conceptProgress?.[concept.conceptId]);
  const learned = toPercent(progressSummary?.learnedProgress ?? 0);
  const mastered = toPercent(progressSummary?.masteredProgress ?? 0);
  const masteredConceptRate = toPercent(progressSummary?.masteredConceptRate ?? 0);

  return (
    <div className="space-y-6 pb-12">
      <section className="rounded-3xl border-2 border-zinc-900 bg-white p-6 shadow-[0_5px_0_#18181b]">
        <p className="inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1 text-xs font-black text-emerald-800"><Target className="h-3.5 w-3.5" /> Progress</p>
        <h1 className="mt-3 text-3xl font-black">Goal Completion {goalCompletion}%</h1>
        <p className="mt-2 text-sm text-zinc-600">Calculated by the backend from learning, mastery, and communication evidence.</p>
        <div className="mt-5 h-4 overflow-hidden rounded-full border-2 border-zinc-200 bg-zinc-100 p-0.5"><div className="h-full rounded-full bg-emerald-500 transition-all" style={{ width: `${goalCompletion}%` }} /></div>
      </section>

      <section className="grid gap-3 sm:grid-cols-3">
        <Metric icon={<BookOpen className="h-5 w-5" />} label="Learned" value={`${learned}%`} />
        <Metric icon={<CheckCircle2 className="h-5 w-5" />} label="Effective mastery" value={`${mastered}%`} />
        <Metric icon={<CheckCircle2 className="h-5 w-5" />} label="Strictly mastered" value={`${masteredConceptRate}%`} />
      </section>

      <section className="grid gap-3 sm:grid-cols-3">
        <Metric icon={<Target className="h-5 w-5" />} label="Today" value={`${progressSummary?.dailyEffectiveMinutes ?? 0} min`} />
        <Metric icon={<Target className="h-5 w-5" />} label="Total study" value={`${progressSummary?.totalEffectiveMinutes ?? 0} min`} />
        <Metric icon={<Target className="h-5 w-5" />} label="Active days" value={`${progressSummary?.activeDays ?? 0}`} />
      </section>

      <section className="rounded-3xl border-2 border-zinc-200 bg-white p-6">
        <h2 className="text-lg font-black">Roadmap progress</h2>
        <p className="mt-1 text-sm text-zinc-600">Each value below is the current backend state for that concept.</p>
        <div className="mt-4 space-y-3">
          {tracked.length === 0 && <p className="rounded-xl bg-zinc-50 p-4 text-sm font-bold text-zinc-500">Start today’s plan to create learning progress.</p>}
          {tracked.map((concept) => {
            const progress = learnerState?.conceptProgress?.[concept.conceptId];
            if (!progress) return null;
            return <div key={concept.conceptId} className="flex w-full items-center justify-between rounded-2xl border-2 border-zinc-200 p-4"><span><strong className="block">{concept.titleEn}</strong><span className="text-xs text-zinc-500">{progress.status.replaceAll('_', ' ')}</span></span><span className="text-right text-sm font-black text-emerald-700">Learned {toPercent(progress.learnedPercent)}%</span></div>;
          })}
        </div>
      </section>
    </div>
  );
};

const Metric: React.FC<{ icon: React.ReactNode; label: string; value: string }> = ({ icon, label, value }) => <div className="rounded-2xl border-2 border-zinc-200 bg-white p-4"><div className="flex items-center gap-2 text-zinc-500">{icon}<span className="text-xs font-black uppercase">{label}</span></div><p className="mt-2 text-2xl font-black text-zinc-950">{value}</p></div>;
