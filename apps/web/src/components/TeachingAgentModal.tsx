import React, { useEffect, useState } from 'react';
import { HelpCircle, Send, X } from 'lucide-react';
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
  <div className="rounded-2xl border-2 border-zinc-200 bg-zinc-50 p-5 text-sm leading-7 text-zinc-800">
    {content.split('\n').map((line, index) => {
      if (/^\|\s*:?-+/.test(line)) return null;
      if (line.trim().startsWith('|')) {
        const cells = line.split('|').slice(1, -1).map((cell) => cell.trim());
        const isHeader = cells.some((cell) => cell === 'Character');
        return (
          <div key={`${line}-${index}`} className={`grid grid-cols-3 gap-3 border-b border-zinc-200 px-2 py-1.5 last:border-0 ${isHeader ? 'font-black text-zinc-950' : ''}`}>
            {cells.map((cell, cellIndex) => <span key={`${cell}-${cellIndex}`}>{cell.replaceAll('**', '')}</span>)}
          </div>
        );
      }
      const normalized = line.replaceAll('**', '');
      return normalized
        ? <p key={`${line}-${index}`} className="mt-2 first:mt-0">{normalized}</p>
        : <div key={`space-${index}`} className="h-2" />;
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

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/70 p-4">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-3xl border-2 border-zinc-950 bg-white p-6 shadow-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-black uppercase tracking-wider text-emerald-700">Adaptive teaching agent</p>
            <h2 className="mt-1 text-xl font-black text-zinc-950">{action?.actionKind?.replaceAll('_', ' ') || 'Preparing your lesson'}</h2>
          </div>
          <button type="button" onClick={() => void onClose()} aria-label="Close lesson" className="rounded-xl p-2 text-zinc-500 hover:bg-zinc-100 hover:text-zinc-950">
            <X className="h-5 w-5" />
          </button>
        </div>

        {loading && <p className="mt-6 rounded-2xl bg-zinc-100 p-4 text-sm font-bold text-zinc-600">Adapting the lesson to your goal and progress…</p>}
        {error && <p role="alert" className="mt-6 rounded-2xl bg-rose-50 p-4 text-sm font-bold text-rose-800">{error}</p>}

        {action && !loading && (
          <div className="mt-6 space-y-5">
            <TeachingContent content={action.content} />
            {action.pinyin && <p className="rounded-xl bg-amber-50 px-4 py-3 text-sm font-bold text-amber-900">Pinyin: {action.pinyin}</p>}

            {exercise?.prompt && (
              <form
                className="space-y-3 rounded-2xl border-2 border-emerald-200 bg-emerald-50/60 p-5"
                onSubmit={(event) => { event.preventDefault(); void onSubmitAnswer(answer.trim()); }}
              >
                <p className="text-xs font-black uppercase tracking-wider text-emerald-800">Targeted practice</p>
                {exercise.instruction && <p className="text-sm text-zinc-600">{exercise.instruction}</p>}
                <p className="text-lg font-black text-zinc-950">{exercise.prompt}</p>
                <div className="flex gap-2">
                  <input value={answer} onChange={(event) => setAnswer(event.currentTarget.value)} className="min-w-0 flex-1 rounded-xl border-2 border-zinc-200 bg-white px-4 py-3 outline-none focus:border-emerald-500" placeholder="Type your answer…" />
                  <button disabled={!answer.trim() || loading || gradingResult?.passedGates} className="flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-3 font-black disabled:opacity-50"><Send className="h-4 w-4" />Check</button>
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

            <div className="rounded-2xl border-2 border-zinc-200 p-4">
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
