import React, { useMemo, useState } from 'react';
import { BookOpen, CalendarDays, CheckCircle2, Clock3, MessagesSquare, Target } from 'lucide-react';
import { CurriculumConcept, LearnerState, ProgressSummary } from '../types.ts';

interface RetentionVisualizerProps {
  learnerState: LearnerState | null;
  concepts: CurriculumConcept[];
  goalCompletion: number;
  progressSummary: ProgressSummary | null;
}

const toPercent = (value: number): number => Math.round(Math.max(0, Math.min(100, value)));

/** Displays server state only; client-side learning analytics intentionally do not live here. */
export const RetentionVisualizer: React.FC<RetentionVisualizerProps> = ({
  learnerState,
  concepts,
  goalCompletion,
  progressSummary,
}) => {
  const goalCompletionPercent = toPercent(goalCompletion);
  const learned = toPercent(progressSummary?.learnedProgress ?? 0);
  const mastered = toPercent(progressSummary?.masteredProgress ?? 0);
  const courseCoverage = toPercent(progressSummary?.courseCoverage ?? 0);
  const communicationOutcome = toPercent(progressSummary?.communicationOutcomePercent ?? 0);
  const activeDays = progressSummary?.activeDays ?? 0;

  return (
    <div className="space-y-6 pb-12">
      <section className="hero-card overflow-hidden">
        <div className="relative z-10 flex items-center justify-between gap-4">
          <h1 className="text-2xl font-black text-emerald-950">Goal Completion</h1>
          <span className="text-3xl font-black text-emerald-700">{goalCompletionPercent}%</span>
        </div>
        <div className="relative z-10 mt-4 h-2 overflow-hidden rounded-full bg-emerald-100"><div className="h-full rounded-full bg-emerald-500 transition-all" style={{ width: `${goalCompletionPercent}%` }} /></div>
      </section>

      <section className="grid gap-3 sm:grid-cols-3">
        <Metric icon={<BookOpen className="h-5 w-5" />} label="Learned" value={`${learned}%`} />
        <Metric icon={<CheckCircle2 className="h-5 w-5" />} label="Effective mastery" value={`${mastered}%`} />
        <Metric
          icon={<Clock3 className="h-5 w-5" />}
          label="Today"
          value={`${progressSummary?.dailyEffectiveMinutes ?? 0} min`}
        />
      </section>

      <section className="grid gap-3 sm:grid-cols-3">
        <Metric icon={<Target className="h-5 w-5" />} label="Course coverage" value={`${courseCoverage}%`} />
        <Metric icon={<MessagesSquare className="h-5 w-5" />} label="Communication" value={`${communicationOutcome}%`} />
        <Metric icon={<CalendarDays className="h-5 w-5" />} label="Active days" value={String(activeDays)} />
      </section>

      <StudyCurve
        history={progressSummary?.dailyStudyHistory ?? []}
        timezone={progressSummary?.dailyStudyHistory.at(-1)?.timezone ?? learnerState?.goal?.timezone ?? 'UTC'}
      />
      <p className="mt-3 text-xs font-bold text-slate-500">
        A check-in is one completed teaching session. Calendar days use your profile timezone.
      </p>

      <BambooProgress concepts={concepts} learnerState={learnerState} />
    </div>
  );
};

const Metric: React.FC<{ icon: React.ReactNode; label: string; value: string }> = ({ icon, label, value }) => <div className="rounded-2xl border-2 border-zinc-200 bg-white p-4"><div className="flex items-center gap-2 text-zinc-500">{icon}<span className="text-xs font-black uppercase">{label}</span></div><p className="mt-2 text-2xl font-black text-zinc-950">{value}</p></div>;

type StudyPoint = ProgressSummary['dailyStudyHistory'][number];
type CurveRange = 'week' | 'month' | 'all';

const StudyCurve: React.FC<{ history: StudyPoint[]; timezone: string }> = ({ history, timezone }) => {
  const [range, setRange] = useState<CurveRange>('week');
  const [hoveredSession, setHoveredSession] = useState<number | null>(null);
  const points = useMemo(() => {
    const byDate = new Map(history.map((point) => [point.date, point]));
    const formatter = new Intl.DateTimeFormat('en-CA', {
      timeZone: timezone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    });
    const today = new Date(`${formatter.format(new Date())}T00:00:00`);
    const firstRecorded = history[0]?.date;
    const days = range === 'week' ? 7 : range === 'month' ? 30 : Math.max(
      1,
      firstRecorded ? Math.ceil((today.getTime() - new Date(`${firstRecorded}T00:00:00Z`).getTime()) / 86_400_000) + 1 : 1,
    );
    return Array.from({ length: days }, (_, index) => {
      const localDate = new Date(today);
      localDate.setDate(today.getDate() - (days - 1 - index));
      const key = formatter.format(localDate);
      return byDate.get(key) ?? {
        date: key,
        effectiveMinutes: 0,
        checkInCount: 0,
        timezone,
      };
    });
  }, [history, range, timezone]);
  const maxMinutes = Math.max(1, ...points.map((point) => point.effectiveMinutes));
  const maxCheckIns = Math.max(1, ...points.map((point) => point.checkInCount));
  const step = 64;
  const chartWidth = Math.max(420, points.length * step);
  const x = (index: number) => index * step + step / 2;
  const y = (count: number) => 96 - (count / maxCheckIns) * 72;
  const linePoints = points.map((point, index) => `${x(index)},${y(point.checkInCount)}`).join(' ');

  return (
    <section className="rounded-[1.75rem] border border-emerald-200 bg-white/90 p-5 shadow-[0_12px_35px_rgba(6,78,59,0.06)]">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-black text-emerald-950">Study Curve</h2>
        <div className="flex rounded-xl bg-emerald-50 p-1 text-[10px] font-black text-emerald-800">
          {([['week', '7 Days'], ['month', '30 Days'], ['all', 'All']] as const).map(([value, label]) => (
            <button key={value} type="button" onClick={() => setRange(value)} className={`rounded-lg px-2.5 py-1.5 ${range === value ? 'bg-white shadow-sm' : ''}`}>{label}</button>
          ))}
        </div>
      </div>
      <div className="relative mt-3 rounded-2xl bg-emerald-50/40 px-2 pt-3">
        <div className="overflow-x-auto pb-1">
          <div className="relative h-32" style={{ width: `${chartWidth}px` }}>
            {hoveredSession !== null && points[hoveredSession] && (
              <span
                className="pointer-events-none absolute z-40 -translate-x-1/2 -translate-y-full whitespace-nowrap rounded-lg bg-emerald-950 px-2 py-1 text-[9px] font-bold text-white shadow-lg"
                style={{ left: `${x(hoveredSession)}px`, top: `${Math.max(4, y(points[hoveredSession].checkInCount) * 0.92)}px` }}
              >
                {points[hoveredSession].checkInCount} {points[hoveredSession].checkInCount === 1 ? 'session' : 'sessions'}
              </span>
            )}
            <svg className="absolute inset-x-0 top-0 z-30 h-24 w-full overflow-visible" viewBox={`0 0 ${chartWidth} 104`} preserveAspectRatio="none" role="img" aria-label="Daily completed learning sessions">
              <polyline points={linePoints} fill="none" stroke="#065f46" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
              {points.map((point, index) => (
                <circle
                  key={point.date}
                  cx={x(index)}
                  cy={y(point.checkInCount)}
                  r="6"
                  fill={point.effectiveMinutes > 0 ? '#047857' : '#fff'}
                  stroke="#065f46"
                  strokeWidth="3"
                  className="cursor-pointer"
                  tabIndex={0}
                  onMouseEnter={() => setHoveredSession(index)}
                  onMouseLeave={() => setHoveredSession(null)}
                  onFocus={() => setHoveredSession(index)}
                  onBlur={() => setHoveredSession(null)}
                >
                  <title>{point.checkInCount} {point.checkInCount === 1 ? 'session' : 'sessions'}</title>
                </circle>
              ))}
            </svg>
            <div className="absolute inset-0 flex items-end">
              {points.map((point) => <div key={point.date} className="group relative flex h-full shrink-0 flex-col items-center justify-end gap-1" style={{ width: `${step}px` }}><span className="pointer-events-none absolute bottom-7 z-40 hidden rounded-lg bg-emerald-950 px-2 py-1 text-[9px] font-bold text-white shadow-lg group-hover:block">{point.effectiveMinutes} min</span><span title={`${point.effectiveMinutes} min`} className="relative z-20 w-5 rounded-t-full bg-gradient-to-t from-emerald-500 to-lime-300" style={{ height: `${Math.max(3, (point.effectiveMinutes / maxMinutes) * 72)}px` }} /><span className="text-[9px] font-bold text-slate-500">{point.date.slice(5).replace('-', '/')}</span></div>)}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

const shortConceptTitle = (title: string): string => {
  const english = title.split(/\s+with\s+/i)[0].trim();
  if (/this\s*\/\s*that/i.test(english)) return 'This/That';
  if (/have\s*\/\s*not have/i.test(english)) return 'Have/Not';
  if (/measure word/i.test(english)) return 'Measure';
  if (/asking quantity/i.test(english)) return 'Quantity';
  return english.split(/\s+/).slice(0, 2).join(' ');
};

const BambooProgress: React.FC<{ concepts: CurriculumConcept[]; learnerState: LearnerState | null }> = ({ concepts, learnerState }) => (
  <section className="relative overflow-hidden rounded-[1.75rem] border border-emerald-200 bg-gradient-to-b from-sky-50 via-emerald-50/80 to-lime-50 p-5 shadow-[0_18px_45px_rgba(6,78,59,0.08)]">
    <div className="pointer-events-none absolute -left-10 top-16 h-32 w-32 rounded-full bg-white/55 blur-2xl" />
    <div className="pointer-events-none absolute -right-12 top-28 h-40 w-40 rounded-full bg-lime-200/30 blur-2xl" />
    <div className="pointer-events-none absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-emerald-200/45 to-transparent" />
    <div className="relative z-10 flex items-center justify-between">
      <h2 className="text-lg font-black text-emerald-950">Bamboo Roadmap</h2>
      <div className="flex gap-3 text-[9px] font-bold text-emerald-800"><span>Sprout · New</span><span>Leaf · Learned</span><span>Flower · Mastered</span></div>
    </div>
    <div className="absolute bottom-0 left-1/2 top-14 w-5 -translate-x-1/2 rounded-full bg-[repeating-linear-gradient(to_bottom,#86efac_0,#34d399_42px,#047857_42px,#047857_47px)] opacity-75 shadow-[inset_4px_0_4px_rgba(255,255,255,.45),0_5px_18px_rgba(5,150,105,.18)]" />
    <div className="relative z-10 mt-4 grid grid-cols-2 gap-x-12 gap-y-1">
      {concepts.map((concept, index) => {
        const progress = learnerState?.conceptProgress?.[concept.conceptId];
        const learned = toPercent(progress?.learnedPercent ?? 0);
        const mastery = toPercent((progress?.masteryScore ?? 0) * 100);
        const mastered = Boolean(progress?.isMastered);
        const state = mastered ? 'flower' : learned > 0 ? 'leaf' : 'sprout';
        const learnedLightness = 78 - learned * 0.34;
        const masteryLightness = 82 - mastery * 0.3;
        const fill = state === 'flower'
          ? `hsl(326 72% ${masteryLightness}%)`
          : state === 'leaf'
            ? `hsl(145 58% ${learnedLightness}%)`
            : '#d9f99d';
        return (
          <button key={concept.conceptId} type="button" className={`group relative flex min-h-36 items-center justify-center ${index % 2 ? 'translate-y-5' : ''}`} aria-label={`${concept.titleEn}, learned ${learned}%, mastery ${mastery}%`}>
            <span className={`absolute top-1/2 h-2 w-1/2 -translate-y-1/2 rounded-full bg-gradient-to-r from-emerald-400/80 to-emerald-200/70 shadow-sm ${index % 2 === 0 ? 'right-0' : 'left-0 rotate-180'}`} />
            <svg viewBox="0 0 100 100" className="relative z-10 h-28 w-28 drop-shadow-md" aria-hidden="true">
              <defs><linearGradient id={`plant-${index}`} x1="20" y1="15" x2="80" y2="85"><stop stopColor="#ecfccb" /><stop offset="0.5" stopColor={fill} /><stop offset="1" stopColor="#059669" /></linearGradient></defs>
              {state === 'sprout' && <><path d="M50 85C45 69 43 50 49 31" stroke="#166534" strokeWidth="7" strokeLinecap="round" /><path d="M48 47C27 45 20 29 22 20C38 19 50 29 48 47Z" fill={`url(#plant-${index})`} stroke="#15803d" strokeWidth="3" /><path d="M50 60C67 57 78 43 77 32C61 31 51 42 50 60Z" fill={`url(#plant-${index})`} stroke="#15803d" strokeWidth="3" /><path d="M24 87Q50 70 76 87Z" fill="#92400e" /><ellipse cx="50" cy="86" rx="28" ry="5" fill="#d97706" opacity=".45" /></>}
              {state === 'leaf' && <><path d="M50 88C49 69 50 51 54 24" stroke="#166534" strokeWidth="7" strokeLinecap="round" /><path d="M52 71C22 67 15 43 20 25C43 27 57 45 52 71Z" fill={`url(#plant-${index})`} stroke="#047857" strokeWidth="3" /><path d="M52 52C72 49 85 34 83 20C64 20 53 33 52 52Z" fill={`url(#plant-${index})`} stroke="#047857" strokeWidth="3" /><path d="M28 35Q43 48 50 63M76 29Q63 39 54 48" stroke="#d1fae5" strokeWidth="2" strokeLinecap="round" opacity=".75" /></>}
              {state === 'flower' && <><path d="M50 91V56" stroke="#15803d" strokeWidth="7" strokeLinecap="round" />{[0, 72, 144, 216, 288].map((angle) => <ellipse key={angle} cx="50" cy="31" rx="12" ry="22" fill={`url(#plant-${index})`} stroke="#be185d" strokeWidth="2" transform={`rotate(${angle} 50 50)`} />)}<circle cx="50" cy="50" r="12" fill="#fef3c7" stroke="#be185d" strokeWidth="2" /><circle cx="50" cy="50" r="5" fill="#f59e0b" /></>}
            </svg>
            <span className="pointer-events-none absolute bottom-4 z-20 max-w-20 rounded-full border border-white/80 bg-white/85 px-2 py-1 text-center text-[9px] font-black leading-3 text-emerald-950 shadow-sm backdrop-blur">{shortConceptTitle(concept.titleEn)}</span>
            <span className="pointer-events-none absolute bottom-full left-1/2 z-30 mb-2 hidden w-56 -translate-x-1/2 rounded-2xl bg-emerald-950 p-3 text-left text-white shadow-xl group-hover:block group-focus:block">
              <strong className="block text-xs">{concept.titleEn}</strong>
              <span className="mt-1 block text-[10px] text-emerald-100">{concept.titleZh} · {concept.communicativeGoal}</span>
              <span className="mt-2 flex justify-between text-[10px] font-bold"><span>Learned {learned}%</span><span>Mastery {mastery}%</span></span>
            </span>
          </button>
        );
      })}
    </div>
  </section>
);
