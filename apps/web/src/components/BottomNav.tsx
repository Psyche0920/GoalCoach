import React from 'react';
import { Compass, BookOpen, TrendingUp } from 'lucide-react';

interface BottomNavProps {
  activeTab: 'plan' | 'curriculum' | 'retention';
  setActiveTab: (tab: 'plan' | 'curriculum' | 'retention') => void;
}

export const BottomNav: React.FC<BottomNavProps> = ({
  activeTab,
  setActiveTab,
}) => {
  return (
    <nav className="lg:hidden fixed bottom-3 left-3 right-3 z-40 rounded-2xl bg-white/95 border border-slate-200 px-4 py-2 flex items-center justify-around select-none shadow-[0_12px_35px_rgba(15,23,42,0.18)] backdrop-blur-xl">
      <button
        onClick={() => setActiveTab('plan')}
        className={`flex flex-col items-center gap-1 py-1 px-3 rounded-xl transition-all ${
          activeTab === 'plan' ? 'text-emerald-600 font-extrabold' : 'text-zinc-500 font-bold'
        }`}
      >
        <Compass className="w-5 h-5" />
        <span className="text-[10px] uppercase">Today</span>
      </button>

      <button
        onClick={() => setActiveTab('curriculum')}
        className={`flex flex-col items-center gap-1 py-1 px-3 rounded-xl transition-all ${
          activeTab === 'curriculum' ? 'text-emerald-600 font-extrabold' : 'text-zinc-500 font-bold'
        }`}
      >
        <BookOpen className="w-5 h-5" />
        <span className="text-[10px] uppercase">Roadmap</span>
      </button>

      <button
        onClick={() => setActiveTab('retention')}
        className={`flex flex-col items-center gap-1 py-1 px-3 rounded-xl transition-all ${
          activeTab === 'retention' ? 'text-emerald-600 font-extrabold' : 'text-zinc-500 font-bold'
        }`}
      >
        <TrendingUp className="w-5 h-5" />
        <span className="text-[10px] uppercase">Progress</span>
      </button>

    </nav>
  );
};
