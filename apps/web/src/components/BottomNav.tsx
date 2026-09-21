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
    <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-40 bg-white border-t-2 border-zinc-200 px-4 py-2 flex items-center justify-around select-none">
      <button
        onClick={() => setActiveTab('plan')}
        className={`flex flex-col items-center gap-1 py-1 px-3 rounded-xl transition-all ${
          activeTab === 'plan' ? 'text-emerald-600 font-extrabold' : 'text-zinc-500 font-bold'
        }`}
      >
        <Compass className="w-5 h-5" />
        <span className="text-[10px] uppercase">Plan</span>
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
