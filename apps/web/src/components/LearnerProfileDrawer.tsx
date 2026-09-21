import React, { useEffect, useState } from 'react';
import { 
  X, 
  Sparkles,
  Check, 
  Save, 
  Compass,
  HelpCircle,
  Award
} from 'lucide-react';
import { LearningGoal } from '../types.ts';
import { PandaMascot } from './PandaMascot.tsx';

interface LearnerProfileDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  displayName: string;
  goal: LearningGoal | null;
  learnedProgress: number;
  masteredProgress: number;
  onUpdateGoal: (updated: Partial<LearningGoal>) => Promise<void>;
}

export const LearnerProfileDrawer: React.FC<LearnerProfileDrawerProps> = ({
  isOpen,
  onClose,
  displayName,
  goal,
  learnedProgress,
  masteredProgress,
  onUpdateGoal,
}) => {
  const masteredPercent = Math.round(masteredProgress > 1 ? Math.min(100, masteredProgress) : Math.max(0, masteredProgress) * 100);
  const learnedPercent = Math.round(learnedProgress > 1 ? Math.min(100, learnedProgress) : Math.max(0, learnedProgress) * 100);
  const [goalText, setGoalText] = useState(goal?.title || 'Learn practical HSK 1 Chinese');
  const [minutes, setMinutes] = useState<number>(goal?.dailyAvailableMinutes || 15);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    setGoalText(goal?.title || 'Learn practical HSK 1 Chinese');
    setMinutes(goal?.dailyAvailableMinutes || 20);
    setFormError(null);
  }, [goal, isOpen]);

  if (!isOpen) return null;

  const handleSave = async (): Promise<void> => {
    const normalizedGoal = goalText.trim();
    if (normalizedGoal.length < 3) {
      setFormError('Describe your learning goal in at least 3 characters.');
      return;
    }
    if (!Number.isInteger(minutes) || minutes < 5 || minutes > 120) {
      setFormError('Daily study time must be a whole number between 5 and 120 minutes.');
      return;
    }
    setSaving(true);
    setFormError(null);
    try {
      await onUpdateGoal({
        title: normalizedGoal,
        targetHskLevel: 1,
        dailyAvailableMinutes: minutes,
      });
      onClose();
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Your goal could not be saved. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-zinc-950/40 backdrop-blur-xs select-none animate-in fade-in duration-200">
      <div className="bg-white w-full max-w-md h-full shadow-2xl flex flex-col border-l-2 border-zinc-950 animate-in slide-in-from-right duration-300">
        {/* Header */}
        <div className="px-6 py-5 border-b-2 border-zinc-200 bg-white flex items-center justify-between">
          <div className="flex items-center gap-3">
            <PandaMascot mood="happy" size={44} />
            <h3 className="text-base font-black text-zinc-950">{displayName} Profile</h3>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-zinc-400 hover:text-zinc-900 rounded-xl hover:bg-zinc-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Custom goal */}
          <div>
            <div className="mb-2 flex items-center justify-between">
              <label htmlFor="learning-goal" className="text-xs font-black uppercase tracking-wider text-zinc-500">Your goal</label>
              <span className="rounded-lg bg-zinc-900 px-2.5 py-1 text-xs font-black text-white">HSK 1</span>
            </div>
            <textarea
              id="learning-goal"
              value={goalText}
              maxLength={255}
              onChange={(event) => { setGoalText(event.currentTarget.value); setFormError(null); }}
              placeholder="Example: I want to travel to China for two weeks."
              className="min-h-24 w-full resize-none rounded-2xl border-2 border-zinc-200 bg-zinc-50 p-4 text-sm font-bold outline-none focus:border-emerald-500"
            />
            <p className="mt-1 text-right text-[10px] font-bold text-zinc-400">{goalText.length}/255</p>
          </div>

          {/* Daily study time */}
          <div>
            <label className="text-xs font-black uppercase tracking-wider text-zinc-500 block mb-2">
              Daily Target Time
            </label>
            <div className="flex items-center rounded-2xl border-2 border-zinc-200 bg-zinc-50 px-4 focus-within:border-emerald-500">
              <input
                type="number"
                min={5}
                max={120}
                step={1}
                value={Number.isFinite(minutes) ? minutes : ''}
                onChange={(event) => { setMinutes(event.currentTarget.valueAsNumber); setFormError(null); }}
                aria-label="Daily study minutes"
                className="min-w-0 flex-1 bg-transparent py-3 text-lg font-black outline-none"
              />
              <span className="text-xs font-black uppercase text-zinc-500">min / day</span>
            </div>
          </div>

        </div>

        {/* Footer */}
        <div className="p-5 border-t-2 border-zinc-200 bg-zinc-50 flex items-center justify-between">
          {formError && <p role="alert" className="mr-3 flex-1 text-xs font-bold text-rose-700">{formError}</p>}
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2.5 text-xs font-black text-zinc-600 hover:text-zinc-900 rounded-xl transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 px-6 py-3 bg-emerald-500 hover:bg-emerald-400 text-zinc-950 rounded-2xl border-2 border-zinc-950 font-black text-xs uppercase tracking-wider shadow-[0_3px_0_#15803d] active:translate-y-0.5 active:shadow-none transition-all cursor-pointer"
          >
            <Save className="w-4 h-4" />
            <span>{saving ? 'Saving…' : 'Save'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
