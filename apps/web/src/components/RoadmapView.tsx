import React from 'react';
import { Check, Clock, Map as MapIcon, Play } from 'lucide-react';
import { CurriculumConcept, LearnerState } from '../types.ts';

interface RoadmapViewProps {
  concepts: CurriculumConcept[];
  learnerState: LearnerState | null;
  onStartStudy: () => void;
}

const percent = (value: number): number => Math.round(Math.max(0, Math.min(100, value)));

/** Renders the backend-selected roadmap in the exact order returned by the API. */
export const RoadmapView: React.FC<RoadmapViewProps> = ({
  concepts,
  learnerState,
  onStartStudy,
}) => {
  const activeItems = new Map(
    (learnerState?.activePlan?.items ?? []).map((item) => [item.conceptId, item]),
  );

  if (!learnerState?.goal) {
    return (
      <section className="rounded-3xl border-2 border-zinc-200 bg-white p-8 text-center">
        <MapIcon className="mx-auto h-10 w-10 text-emerald-600" />
        <h2 className="mt-3 text-xl font-black">Create a goal to build your roadmap</h2>
        <p className="mt-2 text-sm text-zinc-500">Your roadmap will contain only the units selected for that goal.</p>
      </section>
    );
  }

  return (
    <div className="space-y-5 pb-20">
      <section className="rounded-3xl border-2 border-zinc-900 bg-white p-6 shadow-[0_5px_0_#18181b]">
        <p className="text-xs font-black uppercase tracking-wider text-emerald-700">Roadmap</p>
        <h1 className="mt-2 text-2xl font-black">{learnerState.goal.title}</h1>
        <p className="mt-2 text-sm text-zinc-600">Selected and ordered by the Planning Agent from your goal and learning state.</p>
      </section>

      {concepts.length === 0 ? (
        <p className="rounded-2xl border-2 border-zinc-200 bg-white p-6 text-sm font-bold text-zinc-500">No roadmap units are available yet. Refresh today’s plan.</p>
      ) : (
        <ol className="space-y-3">
          {concepts.map((concept, index) => {
            const progress = learnerState.conceptProgress?.[concept.conceptId];
            const planItem = activeItems.get(concept.conceptId);
            const learned = percent(progress?.learnedPercent ?? 0);
            return (
              <li key={concept.conceptId} className="rounded-2xl border-2 border-zinc-200 bg-white p-5">
                <div className="flex items-start gap-4">
                  <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl font-black ${progress?.isMastered ? 'bg-emerald-500 text-white' : 'bg-zinc-100 text-zinc-700'}`}>
                    {progress?.isMastered ? <Check className="h-5 w-5" /> : index + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <h2 className="font-black text-zinc-950">{concept.titleEn}</h2>
                        <p className="text-sm text-zinc-500">{concept.titleZh} · {concept.communicativeGoal}</p>
                      </div>
                      {planItem && <span className="rounded-full bg-sky-50 px-3 py-1 text-xs font-black text-sky-800">Today · {planItem.kind}</span>}
                    </div>
                    <div className="mt-4 flex items-center gap-3">
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-zinc-100"><div className="h-full rounded-full bg-emerald-500" style={{ width: `${learned}%` }} /></div>
                      <span className="text-xs font-black text-zinc-600">Learned {learned}%</span>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-3 text-xs font-bold text-zinc-500">
                      <span>{progress?.status.replaceAll('_', ' ') ?? 'not started'}</span>
                      {progress?.nextReviewAt && <span className="flex items-center gap-1"><Clock className="h-3.5 w-3.5" />Review scheduled</span>}
                    </div>
                  </div>
                </div>
              </li>
            );
          })}
        </ol>
      )}

      <button type="button" onClick={onStartStudy} className="flex w-full items-center justify-center gap-2 rounded-2xl bg-emerald-500 px-5 py-4 font-black text-zinc-950 shadow-[0_4px_0_#15803d] active:translate-y-0.5 active:shadow-none">
        <Play className="h-4 w-4" /> Continue today’s plan
      </button>
    </div>
  );
};
