import React from 'react';
import { Target, RefreshCw, MessageSquare, Flame, CheckCircle2, AlertTriangle, BookOpen } from 'lucide-react';
import { LearnerState, NextAction } from '../types.ts';

interface NavbarProps {
  learnerState: LearnerState | null;
  overallProgress: number;
  nextAction: NextAction;
  onRegeneratePlan: () => void;
  onOpenChat: () => void;
  activeTab: 'plan' | 'curriculum' | 'retention';
  setActiveTab: (tab: 'plan' | 'curriculum' | 'retention') => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  learnerState,
  overallProgress,
  nextAction,
  onRegeneratePlan,
  onOpenChat,
  activeTab,
  setActiveTab,
}) => {
  const getActionBadge = (action: NextAction) => {
    switch (action) {
      case 'plan_review':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200">
            <AlertTriangle className="w-3.5 h-3.5" />
            Spaced Review Due
          </span>
        );
      case 'regenerate_plan':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 border border-rose-200">
            <RefreshCw className="w-3.5 h-3.5" />
            Plan Regeneration Needed
          </span>
        );
      case 'plan_goal':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-sky-100 text-sky-800 border border-sky-200">
            <Target className="w-3.5 h-3.5" />
            Goal Planning
          </span>
        );
      case 'teach':
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Daily Plan Active
          </span>
        );
    }
  };

  const completedCount = learnerState?.activePlan?.items.filter((i) => i.completed).length || 0;
  const totalCount = learnerState?.activePlan?.items.length || 0;
  const overallPercent = Math.round(overallProgress > 1 ? Math.min(100, overallProgress) : Math.max(0, overallProgress) * 100);

  return (
    <header className="sticky top-0 z-40 bg-white/90 backdrop-blur-md border-b border-stone-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Core info */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-xl bg-amber-600 flex items-center justify-center text-white shadow-sm font-bold text-lg font-chinese">
                标
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-lg font-bold text-stone-900 tracking-tight">GoalCoach</h1>
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase bg-stone-100 text-stone-600 border border-stone-200">
                    HSK 1 MVP
                  </span>
                </div>
                <p className="text-xs text-stone-500 hidden sm:block">
                  Adaptive AI Learning Coach for Chinese
                </p>
              </div>
            </div>

            <div className="hidden md:block">
              {getActionBadge(nextAction)}
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="hidden lg:flex items-center gap-1 bg-stone-100 p-1 rounded-xl border border-stone-200 text-sm font-medium">
            <button
              id="nav-tab-plan"
              onClick={() => setActiveTab('plan')}
              className={`px-3.5 py-1.5 rounded-lg transition-all ${
                activeTab === 'plan'
                  ? 'bg-white text-stone-900 shadow-xs font-semibold'
                  : 'text-stone-600 hover:text-stone-900'
              }`}
            >
              Today's Plan
            </button>
            <button
              id="nav-tab-curriculum"
              onClick={() => setActiveTab('curriculum')}
              className={`px-3.5 py-1.5 rounded-lg transition-all ${
                activeTab === 'curriculum'
                  ? 'bg-white text-stone-900 shadow-xs font-semibold'
                  : 'text-stone-600 hover:text-stone-900'
              }`}
            >
              HSK 1 Curriculum & Mastery
            </button>
            <button
              id="nav-tab-retention"
              onClick={() => setActiveTab('retention')}
              className={`px-3.5 py-1.5 rounded-lg transition-all ${
                activeTab === 'retention'
                  ? 'bg-white text-stone-900 shadow-xs font-semibold'
                  : 'text-stone-600 hover:text-stone-900'
              }`}
            >
              Spaced Retention Curve
            </button>
          </nav>

          {/* Metrics & Actions */}
          <div className="flex items-center gap-3">
            {/* Progress Pill */}
            <div className="hidden sm:flex items-center gap-2 bg-stone-50 border border-stone-200 px-3 py-1.5 rounded-xl">
              <div className="text-right">
                <div className="text-[10px] font-bold tracking-wider text-stone-500 uppercase">
                  Retention-Weighted
                </div>
                <div className="text-xs font-bold text-stone-800">
                  {overallPercent}% Progress
                </div>
              </div>
              <div className="w-12 bg-stone-200 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-amber-600 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${overallPercent}%` }}
                />
              </div>
            </div>

            {/* Daily items tracker */}
            {totalCount > 0 && (
              <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-50 border border-emerald-100 text-xs font-semibold text-emerald-800">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                <span>{completedCount}/{totalCount} completed</span>
              </div>
            )}

            {/* Regenerate Plan Button */}
            <button
              id="btn-regenerate-plan"
              onClick={onRegeneratePlan}
              title="Regenerate today's adaptive plan based on mastery, retention decay, and recurring errors"
              className="p-2 text-stone-600 hover:text-stone-900 hover:bg-stone-100 rounded-xl transition-colors border border-stone-200"
            >
              <RefreshCw className="w-4 h-4" />
            </button>

            {/* AI Coach Chat Button */}
            <button
              id="btn-open-coach-chat"
              onClick={onOpenChat}
              className="flex items-center gap-1.5 px-3.5 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-xl text-sm font-semibold shadow-xs transition-colors"
            >
              <MessageSquare className="w-4 h-4" />
              <span>AI Coach</span>
            </button>
          </div>
        </div>

        {/* Mobile Tabs */}
        <div className="lg:hidden flex border-t border-stone-200 py-2 gap-1 overflow-x-auto text-xs font-medium">
          <button
            onClick={() => setActiveTab('plan')}
            className={`px-3 py-1 rounded-lg whitespace-nowrap ${
              activeTab === 'plan' ? 'bg-amber-600 text-white font-semibold' : 'text-stone-600'
            }`}
          >
            Today's Plan
          </button>
          <button
            onClick={() => setActiveTab('curriculum')}
            className={`px-3 py-1 rounded-lg whitespace-nowrap ${
              activeTab === 'curriculum' ? 'bg-amber-600 text-white font-semibold' : 'text-stone-600'
            }`}
          >
            HSK 1 Curriculum
          </button>
          <button
            onClick={() => setActiveTab('retention')}
            className={`px-3 py-1 rounded-lg whitespace-nowrap ${
              activeTab === 'retention' ? 'bg-amber-600 text-white font-semibold' : 'text-stone-600'
            }`}
          >
            Retention Curve
          </button>
        </div>
      </div>
    </header>
  );
};
