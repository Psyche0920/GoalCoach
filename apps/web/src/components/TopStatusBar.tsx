import React from 'react';
import { RefreshCw, MessageSquare } from 'lucide-react';
import { GoalCoachLogo } from './GoalCoachLogo.tsx';
import { LearnerState, NextAction } from '../types.ts';

interface TopStatusBarProps {
  learnerState: LearnerState | null;
  overallProgress: number;
  nextAction: NextAction;
  onRegeneratePlan: () => void;
  onOpenChat: () => void;
  onOpenProfile?: () => void;
}

export const TopStatusBar: React.FC<TopStatusBarProps> = ({
  learnerState,
  overallProgress,
  nextAction,
  onRegeneratePlan,
  onOpenChat,
  onOpenProfile,
}) => {
  const goalCompletionPercent = Math.round(overallProgress > 1 ? Math.min(100, overallProgress) : Math.max(0, overallProgress) * 100);
  return (
    <header className="sticky top-0 z-30 bg-white/95 backdrop-blur-md border-b-2 border-zinc-200 px-4 sm:px-8 py-3 select-none">
      <div className="max-w-5xl mx-auto flex items-center justify-between">
        {/* Mobile Brand (Click to open Profile Drawer) */}
        <div className="flex items-center gap-2 lg:hidden">
          <GoalCoachLogo 
            size="sm" 
            showSubtitle={false} 
            onClick={onOpenProfile} 
            isClickable={true} 
          />
        </div>

        {/* Status in clean Duolingo / HelloChinese style without flame/zap/shield icons */}
        <div className="flex items-center gap-3">
          <button
            onClick={onOpenProfile}
            className="flex items-center gap-2 px-3 py-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 font-extrabold text-xs rounded-xl border border-emerald-300 transition-colors cursor-pointer"
            title="Open learner profile"
          >
            <span className="w-2 h-2 rounded-full bg-emerald-600" />
            <span>Goal Completion · {goalCompletionPercent}%</span>
          </button>
        </div>

        {/* Right side controls */}
        <div className="flex items-center gap-2">
          <button
            id="btn-top-regenerate"
            onClick={onRegeneratePlan}
            className="p-2 text-zinc-600 hover:text-zinc-950 hover:bg-zinc-100 rounded-xl transition-colors border-2 border-zinc-200 shadow-[0_2px_0_#e4e4e7] active:translate-y-0.5 active:shadow-none cursor-pointer"
            title="Re-plan today based on memory decay & error profile"
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          <button
            id="btn-top-coach"
            onClick={onOpenChat}
            className="lg:hidden flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-extrabold uppercase shadow-[0_2px_0_#15803d] cursor-pointer"
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>Coach</span>
          </button>
        </div>
      </div>
    </header>
  );
};
