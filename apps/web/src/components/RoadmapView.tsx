import React from 'react';
import { BookOpen, CheckCircle2, Flag, Map as MapIcon } from 'lucide-react';
import { CurriculumConcept, LearnerState } from '../types.ts';

interface RoadmapViewProps {
  concepts: CurriculumConcept[];
  learnerState: LearnerState | null;
  coverageRationale: string;
  onStartConcept: (conceptId: string) => void;
}

const clampPercent = (value: number): number => Math.round(Math.max(0, Math.min(100, value)));

const compactTitle = (title: string): string => {
  const english = title.split(/\s+with\s+/i)[0].trim();
  const words = english.split(/\s+/).filter(Boolean);
  if (words.length <= 3) return english;
  if (/measure word/i.test(english)) return 'Measure Words';
  if (/asking quantity/i.test(english)) return 'Ask Quantity';
  return words.slice(0, 3).join(' ');
};

export const RoadmapView: React.FC<RoadmapViewProps> = ({
  concepts,
  learnerState,
  coverageRationale,
  onStartConcept,
}) => {
  if (!learnerState?.goal) {
    return (
      <section className="empty-state-card">
        <MapIcon className="mx-auto h-10 w-10 text-emerald-600" />
        <h2 className="mt-4 text-2xl font-black">Your route starts with a goal</h2>
        <p className="mt-2 text-sm text-slate-500">Tell your coach what you want to do in Chinese.</p>
      </section>
    );
  }

  return (
    <div className="mx-auto max-w-3xl pb-28">
      <section className="roadmap-header">
        <div className="relative z-10 max-w-xl">
          <h1 className="text-2xl font-black leading-tight text-emerald-950">{learnerState.goal.title}</h1>
        </div>
        <Flag className="absolute right-7 top-1/2 h-10 w-10 -translate-y-1/2 text-emerald-300" />
      </section>

      {coverageRationale && (
        <section className="mx-auto mt-5 max-w-3xl rounded-3xl border border-emerald-100 bg-white/70 p-5">
          <h2 className="text-xs font-black uppercase tracking-wider text-emerald-700">Goal coverage</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">{coverageRationale}</p>
        </section>
      )}

      {concepts.length === 0 ? (
        <p className="mt-8 rounded-3xl border border-slate-200 bg-white p-7 text-center text-sm font-bold text-slate-500">Your Planning Agent has not selected roadmap units yet.</p>
      ) : (
        <ol className="roadmap-path mt-8">
          {concepts.map((concept, index) => {
            const progress = learnerState.conceptProgress?.[concept.conceptId];
            const learned = clampPercent(progress?.learnedPercent ?? 0);
            const mastery = clampPercent((progress?.masteryScore ?? 0) * 100);
            const mastered = Boolean(progress?.isMastered);
            const side = index % 2 === 0 ? 'roadmap-node-left' : 'roadmap-node-right';
            return (
              <li key={concept.conceptId} className={`roadmap-node ${side}`}>
                {index < concepts.length - 1 && <span className="roadmap-connector" />}
                <button
                  type="button"
                  onClick={() => onStartConcept(concept.conceptId)}
                  className={`roadmap-orb group ${mastered ? 'roadmap-orb-mastered' : ''}`}
                  aria-label={`Practice ${concept.titleEn}`}
                >
                  <span className="max-w-20 text-center text-xs font-black leading-4">{compactTitle(concept.titleEn)}</span>
                  <span className="mt-2 flex items-center gap-2 text-[9px] font-black">
                    <span className="inline-flex items-center gap-0.5" title={`Learned ${learned}%`}><BookOpen className="h-3 w-3" />{learned}</span>
                    <span className="inline-flex items-center gap-0.5" title={mastered ? 'Mastered' : `Mastery ${mastery}%`}><CheckCircle2 className="h-3 w-3" />{mastery}</span>
                  </span>
                </button>
              </li>
            );
          })}
          <li className="mx-auto mt-1 flex h-14 w-14 items-center justify-center rounded-full border-4 border-white bg-emerald-700 text-white shadow-[0_6px_0_#064e3b]"><Flag className="h-6 w-6" /></li>
        </ol>
      )}
    </div>
  );
};
