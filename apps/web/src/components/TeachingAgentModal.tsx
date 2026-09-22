import React, { useEffect, useState } from 'react';
import { BookOpenText, CheckCircle2, HelpCircle, Lightbulb, Send, Sparkles, X } from 'lucide-react';
import { GradingResult, TeachingAction } from '../types.ts';

interface TeachingAgentModalProps {
  isOpen: boolean;
  action: TeachingAction | null;
  loading: boolean;
  error: string | null;
  gradingResult: GradingResult | null;
  replanned: boolean;
  onClose: () => Promise<void>;
  onContinue: () => Promise<void>;
  onRequestHelp: (query: string) => Promise<void>;
  onSubmitAnswer: (answer: string) => Promise<void>;
}

const TeachingContent: React.FC<{ content: string }> = ({ content }) => (
  <div className="space-y-3 text-sm leading-7 text-slate-700">
    {content.split('\n').map((line, index) => {
      if (/^\|\s*:?-+/.test(line)) return null;
      if (line.trim().startsWith('|')) {
        const cells = line.split('|').slice(1, -1).map((cell) => cell.trim());
        const isHeader = cells.some((cell) => cell === 'Character');
        return (
          <div key={`${line}-${index}`} className={`grid grid-cols-3 gap-3 rounded-xl px-3 py-2 ${isHeader ? 'bg-indigo-100 font-black text-indigo-950' : 'border border-indigo-100 bg-white'}`}>
            {cells.map((cell, cellIndex) => <span key={`${cell}-${cellIndex}`}>{cell.replaceAll('**', '')}</span>)}
          </div>
        );
      }
      const normalized = line.replaceAll('**', '');
      return normalized
        ? <p key={`${line}-${index}`} className="rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm">{normalized}</p>
        : null;
    })}
  </div>
);

export const TeachingAgentModal: React.FC<TeachingAgentModalProps> = ({
  isOpen,
  action,
  loading,
  error,
  gradingResult,
  replanned,
  onClose,
  onContinue,
  onRequestHelp,
  onSubmitAnswer,
}) => {
  const [answer, setAnswer] = useState('');
  const [helpQuery, setHelpQuery] = useState('I do not understand this yet. Please explain it differently.');

  useEffect(() => {
    setAnswer('');
  }, [action?.exercisePayload?.exercise_id]);

  if (!isOpen) return null;

  const exercise = action?.exercisePayload;
  const countsTowardProgress = action?.metadata?.progress_eligible !== false;
  const progressNotice = typeof action?.metadata?.progress_notice === 'string'
    ? action.metadata.progress_notice
    : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/75 p-3 backdrop-blur-sm sm:p-5">
      <div className="max-h-[94vh] w-full max-w-3xl overflow-y-auto rounded-[2rem] border border-white/30 bg-[#f8faf7] p-5 shadow-2xl sm:p-7">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.16em] text-emerald-700"><Sparkles className="h-4 w-4" />Your private coach</p>
            <h2 className="mt-1 text-2xl font-black text-slate-950">{action?.actionKind?.replaceAll('_', ' ') || 'Preparing your lesson'}</h2>
          </div>
          <button type="button" onClick={() => void onClose()} aria-label="Close lesson" className="rounded-xl p-2 text-zinc-500 hover:bg-zinc-100 hover:text-zinc-950">
            <X className="h-5 w-5" />
          </button>
        </div>

        {loading && <p className="mt-6 rounded-2xl bg-zinc-100 p-4 text-sm font-bold text-zinc-600">Adapting the lesson to your goal and progress…</p>}
        {error && <p role="alert" className="mt-6 rounded-2xl bg-rose-50 p-4 text-sm font-bold text-rose-800">{error}</p>}

        {action && !loading && (
          <div className="mt-6 space-y-5">
            <div className={`flex items-center gap-3 rounded-2xl px-4 py-3 text-xs font-bold ${countsTowardProgress ? 'bg-emerald-100 text-emerald-900' : 'bg-indigo-100 text-indigo-900'}`}>
              {countsTowardProgress ? <CheckCircle2 className="h-5 w-5" /> : <BookOpenText className="h-5 w-5" />}
              <span>{progressNotice ?? (countsTowardProgress ? 'This planned lesson counts toward progress.' : 'Free practice · progress and study time stay unchanged.')}</span>
            </div>

            <section className="rounded-3xl border border-indigo-100 bg-indigo-50/70 p-4 sm:p-5">
              <h3 className="mb-3 flex items-center gap-2 text-xs font-black uppercase tracking-wider text-indigo-800"><Lightbulb className="h-4 w-4" />Coach’s explanation</h3>
              <TeachingContent content={action.content} />
            </section>
            {action.pinyin && <p className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-bold text-amber-900"><span className="mr-2 text-xs uppercase tracking-wider">Say it</span>{action.pinyin}</p>}

            {exercise?.prompt && (
              <form
                className="space-y-4 rounded-3xl border border-emerald-200 bg-gradient-to-br from-emerald-50 to-lime-50 p-5 sm:p-6"
                onSubmit={(event) => { event.preventDefault(); void onSubmitAnswer(answer.trim()); }}
              >
                <p className="text-xs font-black uppercase tracking-[0.16em] text-emerald-800">Try it yourself</p>
                {exercise.instruction && <p className="text-sm text-zinc-600">{exercise.instruction}</p>}
                <p className="text-xl font-black leading-8 text-slate-950">{exercise.prompt}</p>
                <div className="flex flex-col gap-2 sm:flex-row">
                  <input value={answer} onChange={(event) => setAnswer(event.currentTarget.value)} className="min-w-0 flex-1 rounded-xl border-2 border-zinc-200 bg-white px-4 py-3 outline-none focus:border-emerald-500" placeholder="Type your answer…" />
                  <button disabled={!answer.trim() || loading || gradingResult?.passedGates} className="flex items-center justify-center gap-2 rounded-xl bg-emerald-500 px-5 py-3 font-black text-emerald-950 shadow-[0_4px_0_#15803d] active:translate-y-0.5 active:shadow-none disabled:opacity-50"><Send className="h-4 w-4" />Check</button>
                </div>
              </form>
            )}

            {gradingResult && (
              <div className={`rounded-2xl p-4 text-sm font-bold ${gradingResult.passedGates ? 'bg-emerald-50 text-emerald-900' : 'bg-amber-50 text-amber-950'}`}>
                <p>{gradingResult.feedback}</p>
                {replanned && <p className="mt-2">Your daily plan was adjusted because this error has repeated.</p>}
                <button type="button" disabled={loading} onClick={() => void onContinue()} className="mt-3 rounded-xl bg-zinc-950 px-4 py-2.5 text-xs font-black text-white disabled:opacity-50">
                  {gradingResult.passedGates ? 'Continue to next lesson' : 'Try a new teaching approach'}
                </button>
              </div>
            )}

            <div className="rounded-3xl border border-slate-200 bg-white p-4 sm:p-5">
              <label htmlFor="coach-help" className="flex items-center gap-2 text-xs font-black uppercase tracking-wider text-zinc-600"><HelpCircle className="h-4 w-4" />Need a different explanation?</label>
              <textarea id="coach-help" value={helpQuery} onChange={(event) => setHelpQuery(event.currentTarget.value)} className="mt-3 min-h-20 w-full rounded-xl border-2 border-zinc-200 p-3 text-sm outline-none focus:border-emerald-500" />
              <button type="button" disabled={!helpQuery.trim() || loading} onClick={() => void onRequestHelp(helpQuery.trim())} className="mt-3 rounded-xl bg-zinc-900 px-4 py-2.5 text-xs font-black text-white disabled:opacity-50">Explain another way</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
