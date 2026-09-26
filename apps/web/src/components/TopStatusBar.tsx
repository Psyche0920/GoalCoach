import React from 'react';
import { GoalCoachLogo } from './GoalCoachLogo.tsx';

interface TopStatusBarProps {
  goalCompletion: number;
  onOpenProfile?: () => void;
}

export const TopStatusBar: React.FC<TopStatusBarProps> = ({
  goalCompletion,
  onOpenProfile,
}) => {
  const goalCompletionPercent = Math.round(Math.max(0, Math.min(100, goalCompletion)));
  return (
    <header className="sticky top-0 z-30 bg-white/80 backdrop-blur-xl border-b border-slate-200/80 px-4 sm:px-8 py-3 select-none">
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
            <span className="hidden sm:inline">Goal Completion · {goalCompletionPercent}%</span>
            <span className="sm:hidden">{goalCompletionPercent}%</span>
          </button>
        </div>

        <span className="w-8 lg:hidden" aria-hidden="true" />
      </div>
    </header>
  );
};
