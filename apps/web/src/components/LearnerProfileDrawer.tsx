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
import { GOAL_PRESETS } from '../data/curriculumThemes.ts';

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
  const [minutes, setMinutes] = useState<number>(goal?.dailyAvailableMinutes || 15);
  const [targetDomain, setTargetDomain] = useState<string>(goal?.targetDomain || 'general');
  const activePreset = GOAL_PRESETS.find((p) => p.id === targetDomain) || GOAL_PRESETS[0];
  const [selectedInterests, setSelectedInterests] = useState<string[]>(
    goal?.interests || activePreset.priorityThemes
  );
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    const nextDomain = goal?.targetDomain || 'general';
    const nextPreset = GOAL_PRESETS.find((preset) => preset.id === nextDomain) || GOAL_PRESETS[0];
    setMinutes(goal?.dailyAvailableMinutes || 20);
    setTargetDomain(nextDomain);
    setSelectedInterests(goal?.interests || nextPreset.priorityThemes);
  }, [goal, isOpen]);

  if (!isOpen) return null;

  const handleSelectFocus = (presetId: string) => {
    const preset = GOAL_PRESETS.find((p) => p.id === presetId) || GOAL_PRESETS[0];
    setTargetDomain(preset.id);
    setSelectedInterests(preset.priorityThemes);
  };

  const handleSave = async (): Promise<void> => {
    const preset = GOAL_PRESETS.find((p) => p.id === targetDomain) || GOAL_PRESETS[0];
    setSaving(true);
    try {
      await onUpdateGoal({
        targetHskLevel: 1,
        dailyAvailableMinutes: minutes,
        interests: (preset.priorityThemes || selectedInterests) as LearningGoal['interests'],
        targetDomain: targetDomain as LearningGoal['targetDomain'],
      });
      onClose();
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
          {/* Fixed goal */}
          <div className="rounded-2xl border-2 border-zinc-200 bg-white p-4">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-black uppercase tracking-wider text-zinc-500">Goal</h4>
              <span className="rounded-lg bg-zinc-900 px-2.5 py-1 text-xs font-black text-white">HSK 1</span>
            </div>
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
                onChange={(event) => setMinutes(event.currentTarget.valueAsNumber)}
                aria-label="Daily study minutes"
                className="min-w-0 flex-1 bg-transparent py-3 text-lg font-black outline-none"
              />
              <span className="text-xs font-black uppercase text-zinc-500">min / day</span>
            </div>
          </div>

          {/* Interest */}
          <div className="space-y-2.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-black uppercase tracking-wider text-zinc-500 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
                Interest
              </label>
              <span className="text-[10px] font-bold text-emerald-700">
                Active: {activePreset.badge || activePreset.titleEn}
              </span>
            </div>

            <div className="space-y-2">
              {GOAL_PRESETS.map((preset) => {
                const isSelected = targetDomain === preset.id;
                return (
                  <div
                    key={preset.id}
                    onClick={() => handleSelectFocus(preset.id)}
                    className={`p-3.5 rounded-2xl border-2 transition-all cursor-pointer flex items-center justify-between ${
                      isSelected
                        ? 'bg-emerald-50 border-emerald-500 text-emerald-950 shadow-xs'
                        : 'bg-zinc-50 border-zinc-200 text-zinc-700 hover:bg-zinc-100'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">{preset.icon}</span>
                      <div>
                        <div className="text-xs font-black flex items-center gap-2">
                          <span>{preset.badge || preset.titleEn}</span>
                        </div>
                        <p className="text-[11px] text-zinc-500 font-medium line-clamp-1 mt-0.5">
                          {preset.descriptionEn}
                        </p>
                      </div>
                    </div>
                    <div
                      className={`w-5 h-5 rounded-full flex items-center justify-center transition-colors shrink-0 ml-2 ${
                        isSelected ? 'bg-emerald-600 text-white' : 'border border-zinc-300'
                      }`}
                    >
                      {isSelected && <Check className="w-3 h-3 stroke-[3]" />}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-5 border-t-2 border-zinc-200 bg-zinc-50 flex items-center justify-between">
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
            disabled={saving || !Number.isInteger(minutes) || minutes < 5 || minutes > 120}
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
