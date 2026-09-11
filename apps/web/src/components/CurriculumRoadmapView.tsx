import React, { useState } from 'react';
import { 
  Check, 
  Crown, 
  Sparkles, 
  Volume2, 
  Flame, 
  Trophy, 
  Compass, 
  ArrowRight,
  Info,
  CheckCircle2,
  Award,
  Zap,
  BookOpen
} from 'lucide-react';
import { PandaMascot } from './PandaMascot.tsx';
import { CurriculumConcept, LearningGoal, LearnerState, CurriculumTheme } from '../types.ts';
import { GOAL_PRESETS, THEME_REGISTRY } from '../data/curriculumThemes.ts';
import { playMandarinAudio } from '../utils/pinyinAudio.ts';
import { curriculumChineseSummary, curriculumShortTitle } from '../data/curriculumPresentation.ts';
import { masteredProgressScore } from '../domain/progress.ts';

interface CurriculumRoadmapViewProps {
  concepts: CurriculumConcept[];
  learnerState: LearnerState | null;
  goal: LearningGoal | null;
  onStartStudy: (conceptId: string, isPinyin: boolean) => void;
  onUpdateGoal: (goal: Partial<LearningGoal>) => void;
  onOpenProfile?: () => void;
}


export const CurriculumRoadmapView: React.FC<CurriculumRoadmapViewProps> = ({
  concepts,
  learnerState,
  goal,
  onStartStudy,
  onUpdateGoal,
  onOpenProfile,
}) => {
  const [activeModuleTab, setActiveModuleTab] = useState<'all' | 'module1' | 'module2' | 'module3'>('all');
  const [showPedagogyExplanation, setShowPedagogyExplanation] = useState(false);

  const activeTargetDomain = goal?.targetDomain || 'general';
  const activePreset = GOAL_PRESETS.find((p) => p.id === activeTargetDomain) || GOAL_PRESETS[0];

  // Group concepts into the 3 canonical modules
  // Module 1: 拼音 (Pinyin Foundation)
  const module1Concepts = concepts.filter(
    (c) => c.module === 'module1_pinyin' || c.category === 'pinyin'
  );

  // Module 2: 核心语法 (Core Grammar)
  const module2Concepts = concepts.filter(
    (c) => c.module === 'module2_grammar' || c.category === 'grammar' || c.isCoreGrammar
  );

  // Module 3: 目标生活场景与主题库 (Thematic Real-life Living Chinese)
  // Dynamically reorder based on active target domain & user interests
  const rawThematicConcepts = concepts.filter(
    (c) => !(c.module === 'module1_pinyin' || c.category === 'pinyin' || c.category === 'grammar' || c.isCoreGrammar)
  );

  const themePriorityOrder = activePreset.module2UnitOrder || [
    'dining_food',
    'shopping_prices',
    'travel_directions',
    'numbers_time',
    'greetings_etiquette',
    'identity_family',
    'daily_life',
    'work_study',
    'weather_feelings',
  ];

  const module3Concepts = [...rawThematicConcepts].sort((a, b) => {
    const priorityA = activePreset.priorityThemes.includes(a.theme);
    const priorityB = activePreset.priorityThemes.includes(b.theme);
    if (priorityA && !priorityB) return -1;
    if (!priorityA && priorityB) return 1;

    const idxA = themePriorityOrder.indexOf(a.theme);
    const idxB = themePriorityOrder.indexOf(b.theme);
    const orderA = idxA === -1 ? 999 : idxA;
    const orderB = idxB === -1 ? 999 : idxB;
    if (orderA !== orderB) return orderA - orderB;

    return a.sequenceNo - b.sequenceNo;
  });

  // Learned measures unit completion. Mastered measures retained mastery over time.
  const getNodeProgress = (concept: CurriculumConcept, moduleList: CurriculumConcept[], idx: number) => {
    const progress = learnerState?.conceptProgress?.[concept.conceptId];
    const learnedPercent = progress?.learnedPercent ?? 0;
    const score = progress ? masteredProgressScore(progress) : 0;
    const isMastered = progress?.status === 'mastered';
    const isCompleted = learnedPercent === 100;

    const isUnlocked = true;
    const firstIncompleteIndex = moduleList.findIndex((item) => (learnerState?.conceptProgress?.[item.conceptId]?.learnedPercent ?? 0) < 100);
    const isCurrentActive = idx === firstIncompleteIndex;

    return {
      score,
      isCompleted,
      isMastered,
      isUnlocked,
      isCurrentActive,
      reviewCount: progress?.successfulSpacedRetrievals ?? 0,
      learnedPercent,
    };
  };

  // Compute Module Completion & Mastery Percentages
  const computeModuleStats = (moduleList: CurriculumConcept[]) => {
    if (moduleList.length === 0) return { completedPct: 0, masteredPct: 0, total: 0, completedCount: 0, masteredCount: 0 };
    let completedCount = 0;
    let masteredCount = 0;
    let learnedTotal = 0;
    let readinessTotal = 0;
    let weightTotal = 0;

    for (const c of moduleList) {
      const progress = learnerState?.conceptProgress?.[c.conceptId];
      const learnedPercent = progress?.learnedPercent ?? 0;
      if (learnedPercent === 100) completedCount++;
      if (progress?.status === 'mastered') masteredCount++;
      const weight = c.weight ?? 1;
      learnedTotal += weight * learnedPercent;
      readinessTotal += weight * (progress ? masteredProgressScore(progress) : 0) * 100;
      weightTotal += weight;
    }

    return {
      total: moduleList.length,
      completedCount,
      masteredCount,
      completedPct: Math.round(learnedTotal / Math.max(1, weightTotal)),
      masteredPct: Math.round(readinessTotal / Math.max(1, weightTotal)),
    };
  };

  const m1Stats = computeModuleStats(module1Concepts);
  const m2Stats = computeModuleStats(module2Concepts);
  const m3Stats = computeModuleStats(module3Concepts);

  const isMilestone1Complete = m1Stats.masteredPct === 100 && m2Stats.masteredPct === 100 && m3Stats.masteredPct === 100;
  const isMilestone1Learned = m1Stats.completedPct === 100 && m2Stats.completedPct === 100 && m3Stats.completedPct === 100;

  // Handle switching goal domain
  const handleSelectDomain = (domainId: 'general' | 'travel' | 'dining' | 'work' | 'daily') => {
    const preset = GOAL_PRESETS.find((p) => p.id === domainId);
    if (!preset) return;
    onUpdateGoal({
      title: `${preset.titleEn} (${preset.badge})`,
      targetDomain: preset.id,
      interests: preset.priorityThemes,
      dailyAvailableMinutes: goal?.dailyAvailableMinutes || 20,
    });
  };

  // Serpentine offset for HelloChinese / Duolingo zigzag effect
  const getZigzagOffsetClass = (index: number) => {
    const pattern = [
      'translate-x-0',        // center
      '-translate-x-8 sm:-translate-x-14', // left
      'translate-x-0',        // center
      'translate-x-8 sm:translate-x-14',  // right
    ];
    return pattern[index % pattern.length];
  };

  // Render a module roadmap section
  const renderModuleSection = (
    moduleKey: 'module1' | 'module2' | 'module3',
    titleZh: string,
    titleEn: string,
    badgeText: string,
    themeColor: string,
    conceptsList: CurriculumConcept[],
    stats: { completedPct: number; masteredPct: number; total: number; completedCount: number; masteredCount: number }
  ) => {
    const isPinyin = moduleKey === 'module1';

    return (
      <div className="space-y-6 bg-white rounded-3xl border-2 border-zinc-200 p-5 sm:p-7 shadow-xs">
        {/* Module Header Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b-2 border-zinc-100">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className={`text-[11px] font-black uppercase tracking-wider px-2.5 py-0.5 rounded-full border ${
                themeColor === 'sky' 
                  ? 'bg-sky-100 text-sky-800 border-sky-200' 
                  : themeColor === 'emerald' 
                  ? 'bg-emerald-100 text-emerald-800 border-emerald-200' 
                  : 'bg-amber-100 text-amber-800 border-amber-200'
              }`}>
                {badgeText}
              </span>
            </div>
            <h3 className="text-xl font-black text-zinc-950 font-chinese tracking-tight">
              {titleZh}
            </h3>
            <p className="text-xs font-medium text-zinc-500 mt-0.5">
              {titleEn}
            </p>
          </div>

          {/* Module 2-Tier Progress Pills: Learned vs Mastered */}
          <div className="flex items-center gap-2.5">
            {/* Learned Pill */}
            <div className="px-3.5 py-2 rounded-2xl bg-zinc-50 border border-zinc-200 flex flex-col items-center">
              <span className="text-[10px] font-black text-zinc-400 uppercase tracking-wider">
                Learned
              </span>
              <span className="text-sm font-black text-emerald-600">
                {stats.completedPct}%
              </span>
            </div>

            {/* Mastered Pill */}
            <div className="px-3.5 py-2 rounded-2xl bg-amber-50/70 border border-amber-200 flex flex-col items-center">
              <div className="flex items-center gap-1">
                <Crown className="w-3 h-3 text-amber-500 fill-amber-500" />
                <span className="text-[10px] font-black text-amber-900 uppercase tracking-wider">
                  Mastered
                </span>
              </div>
              <span className="text-sm font-black text-amber-700">
                {stats.masteredPct}%
              </span>
            </div>
          </div>
        </div>

        {/* Serpentine Roadmap Pathway */}
        <div className="py-6 flex flex-col items-center relative">
          <div className="w-full max-w-md space-y-7 relative">
            {conceptsList.map((concept, idx) => {
              const node = getNodeProgress(concept, conceptsList, idx);
              const zigzagClass = getZigzagOffsetClass(idx);
              const isInTodayPlan = learnerState?.activePlan?.items.some((item) =>
                (item.conceptIds ?? (item.conceptId ? [item.conceptId] : [])).includes(concept.conceptId)) ?? false;

              return (
                <div 
                  key={concept.conceptId}
                  className={`flex flex-col items-center transition-all duration-300 ${zigzagClass}`}
                >
                  {/* Stepping Stone Button Node */}
                  <div className="relative group flex flex-col items-center">
                    {/* Active Pulsing Ring */}
                    {node.isCurrentActive && (
                      <div className="absolute -inset-2.5 rounded-full bg-emerald-400/30 animate-ping pointer-events-none" />
                    )}

                    {/* Floating Mascot Badge on Current Active Node */}
                    {node.isCurrentActive && (
                      <div className="absolute -top-11 z-20 flex items-center gap-1.5 bg-zinc-950 text-white text-[11px] font-black px-3 py-1 rounded-full shadow-lg border border-zinc-800 animate-bounce">
                        <PandaMascot mood="cheering" size={20} />
                        <span>Start!</span>
                      </div>
                    )}

                    <button
                      onClick={() => onStartStudy(concept.conceptId, isPinyin)}
                      className={`w-18 h-18 sm:w-20 sm:h-20 rounded-3xl flex flex-col items-center justify-center font-black transition-all duration-200 cursor-pointer select-none ${
                        node.isMastered
                          ? 'bg-gradient-to-b from-amber-400 to-amber-500 text-zinc-950 border-2 border-amber-600 shadow-[0_5px_0_#b45309] hover:shadow-[0_2px_0_#b45309] hover:translate-y-1'
                          : node.isCompleted
                          ? 'bg-gradient-to-b from-emerald-500 to-emerald-600 text-white border-2 border-emerald-700 shadow-[0_5px_0_#047857] hover:shadow-[0_2px_0_#047857] hover:translate-y-1'
                          : 'bg-white text-zinc-950 border-2 border-zinc-950 shadow-[0_5px_0_#09090b] hover:shadow-[0_2px_0_#09090b] hover:translate-y-1 ring-4 ring-emerald-500/20'
                      }`}
                    >
                      {node.isMastered ? <Crown className="w-4 h-4 mb-1 fill-current" /> : node.isCompleted ? <Check className="w-4 h-4 mb-1 stroke-[3]" /> : <Zap className="w-4 h-4 mb-1 text-emerald-600 fill-emerald-600" />}
                      <span className="max-w-[68px] text-center text-[10px] leading-tight">{curriculumShortTitle(concept)}</span>
                    </button>

                    {/* Node Description Text Below */}
                    <div className="mt-2.5 text-center max-w-[210px] space-y-0.5">
                      <h4 className="text-sm font-black text-zinc-900 font-chinese leading-tight">
                        {curriculumChineseSummary(concept)}
                      </h4>
                      {isInTodayPlan && <span className="inline-flex rounded-full bg-sky-100 px-2 py-0.5 text-[9px] font-black uppercase text-sky-800">Today</span>}

                      {/* Micro Status Chip */}
                      <div className="flex items-center justify-center gap-1.5 pt-1">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md ${
                          node.isCompleted 
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' 
                            : 'bg-zinc-100 text-zinc-400'
                        }`}>
                          Learned: {Math.round(node.learnedPercent)}%
                        </span>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md ${
                          node.isMastered 
                            ? 'bg-amber-100 text-amber-800 border border-amber-300 font-black' 
                            : 'bg-zinc-100 text-zinc-400'
                        }`}>
                          Mastered: {Math.round(node.score * 100)}%
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-8 select-none">
      {/* 1. Header & Milestone 1 Grand Tracker */}
      <div className="bg-white rounded-3xl border-2 border-zinc-200 p-6 sm:p-8 shadow-xs space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <PandaMascot mood="studying" size={56} />
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-black uppercase tracking-wider bg-emerald-100 text-emerald-800 px-2.5 py-0.5 rounded-full border border-emerald-200">
                  Curriculum Roadmap
                </span>
                <span className="text-[10px] font-bold text-zinc-500 bg-zinc-100 px-2.5 py-0.5 rounded-full">
                  Skill Path
                </span>
              </div>
              <h2 className="text-2xl font-black text-zinc-950 tracking-tight mt-1">
                HSK 1 Curriculum Roadmap
              </h2>
            </div>
          </div>

          {/* Pedagogy Toggle Button */}
          <button
            onClick={() => setShowPedagogyExplanation(!showPedagogyExplanation)}
            className="px-4 py-2 rounded-2xl border-2 border-zinc-200 hover:border-zinc-950 bg-zinc-50 text-zinc-800 text-xs font-black flex items-center gap-2 cursor-pointer transition-all self-start sm:self-center"
          >
            <Info className="w-4 h-4 text-emerald-600" />
            <span>Learned vs. Mastered</span>
          </button>
        </div>

        {/* Pedagogy Explanation Drawer / Banner */}
        {showPedagogyExplanation && (
          <div className="p-5 rounded-2xl bg-amber-50/80 border-2 border-amber-300 text-xs text-amber-950 space-y-3 animate-in fade-in">
            <div className="flex items-center gap-2 font-black text-sm text-amber-900">
              <span>🎓 Mastery Guide:</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="p-3.5 bg-white rounded-xl border border-amber-200 space-y-1">
                <div className="font-black text-emerald-700 flex items-center gap-1.5 text-xs">
                  <Check className="w-4 h-4" />
                  <span>Learned (Studied & Practiced)</span>
                </div>
                <p className="text-[11px] text-zinc-600 leading-relaxed">
                  You completed the lesson and practice. Spaced reviews help you retain it.
                </p>
              </div>

              <div className="p-3.5 bg-white rounded-xl border border-amber-200 space-y-1">
                <div className="font-black text-amber-700 flex items-center gap-1.5 text-xs">
                  <Crown className="w-4 h-4 fill-amber-500 text-amber-500" />
                  <span>Mastered (Retained via Ebbinghaus)</span>
                </div>
                <p className="text-[11px] text-zinc-600 leading-relaxed">
                  Verified through spaced reviews with 85%+ retention accuracy according to the Ebbinghaus forgetting curve, locking it into long-term reflex memory.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Milestone 1 Triple-Module Progress Card */}
        <div className="p-5 sm:p-6 rounded-3xl bg-slate-900 text-white space-y-5 shadow-[0_6px_0_#0f172a]">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-emerald-500/20 border border-emerald-400/40 flex items-center justify-center text-emerald-400">
                <Trophy className="w-6 h-6" />
              </div>
              <div>
                <span className="text-[10px] font-black text-emerald-400 uppercase tracking-widest">
                  Ultimate Achievement
                </span>
                <h3 className="text-lg font-black text-white">
                  Milestone 1 Goal
                </h3>
              </div>
            </div>

            <div className="text-xs font-bold text-slate-400">
              {isMilestone1Complete ? (
                <span className="text-emerald-400 font-black flex items-center gap-1.5">
                  <Award className="w-4 h-4" /> Milestone Mastered!
                </span>
              ) : isMilestone1Learned ? (
                <span className="text-amber-400 font-black">
                  All lessons learned! Complete reviews to reach 100% mastery.
                </span>
              ) : (
                <span>Learn all 3 modules to unlock.</span>
              )}
            </div>
          </div>

          {/* 3 Modules Checklist Bar */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5 pt-2">
            {/* Module 1 */}
            <div className="p-3.5 bg-slate-800/80 rounded-2xl border border-slate-700 flex flex-col justify-between gap-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-black text-sky-400">Module 1 · Pinyin</span>
                {m1Stats.masteredPct === 100 ? (
                  <Crown className="w-4 h-4 text-amber-400 fill-amber-400" />
                ) : m1Stats.completedPct === 100 ? (
                  <Check className="w-4 h-4 text-emerald-400 stroke-[3]" />
                ) : (
                  <span className="text-[10px] font-bold text-slate-400">{m1Stats.completedCount}/{m1Stats.total}</span>
                )}
              </div>
              <div className="space-y-1">
                <div className="flex justify-between text-[10px] text-slate-400">
                  <span>Learned: {m1Stats.completedPct}%</span>
                  <span className="text-amber-300">Mastered: {m1Stats.masteredPct}%</span>
                </div>
                <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                  <div 
                    style={{ width: `${m1Stats.masteredPct}%` }}
                    className="h-full bg-amber-400 rounded-full transition-all duration-500"
                  />
                </div>
              </div>
            </div>

            {/* Module 2 */}
            <div className="p-3.5 bg-slate-800/80 rounded-2xl border border-slate-700 flex flex-col justify-between gap-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-black text-emerald-400">Module 2 · Grammar</span>
                {m2Stats.masteredPct === 100 ? (
                  <Crown className="w-4 h-4 text-amber-400 fill-amber-400" />
                ) : m2Stats.completedPct === 100 ? (
                  <Check className="w-4 h-4 text-emerald-400 stroke-[3]" />
                ) : (
                  <span className="text-[10px] font-bold text-slate-400">{m2Stats.completedCount}/{m2Stats.total}</span>
                )}
              </div>
              <div className="space-y-1">
                <div className="flex justify-between text-[10px] text-slate-400">
                  <span>Learned: {m2Stats.completedPct}%</span>
                  <span className="text-amber-300">Mastered: {m2Stats.masteredPct}%</span>
                </div>
                <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                  <div 
                    style={{ width: `${m2Stats.masteredPct}%` }}
                    className="h-full bg-amber-400 rounded-full transition-all duration-500"
                  />
                </div>
              </div>
            </div>

            {/* Module 3 */}
            <div className="p-3.5 bg-slate-800/80 rounded-2xl border border-slate-700 flex flex-col justify-between gap-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-black text-amber-400">Module 3 · Communication</span>
                {m3Stats.masteredPct === 100 ? (
                  <Crown className="w-4 h-4 text-amber-400 fill-amber-400" />
                ) : m3Stats.completedPct === 100 ? (
                  <Check className="w-4 h-4 text-emerald-400 stroke-[3]" />
                ) : (
                  <span className="text-[10px] font-bold text-slate-400">{m3Stats.completedCount}/{m3Stats.total}</span>
                )}
              </div>
              <div className="space-y-1">
                <div className="flex justify-between text-[10px] text-slate-400">
                  <span>Learned: {m3Stats.completedPct}%</span>
                  <span className="text-amber-300">Mastered: {m3Stats.masteredPct}%</span>
                </div>
                <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                  <div 
                    style={{ width: `${m3Stats.masteredPct}%` }}
                    className="h-full bg-amber-400 rounded-full transition-all duration-500"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Module Tabs (All vs Module 1 vs Module 2 vs Module 3) */}
        <div className="flex items-center gap-2 pt-2 border-t border-zinc-100 overflow-x-auto pb-1">
          <button
            onClick={() => setActiveModuleTab('all')}
            className={`px-4 py-2 rounded-2xl text-xs font-black transition-all cursor-pointer whitespace-nowrap ${
              activeModuleTab === 'all'
                ? 'bg-emerald-600 text-white shadow-xs'
                : 'text-zinc-600 hover:bg-zinc-100'
            }`}
          >
            🗺️ All Modules ({concepts.length})
          </button>
          <button
            onClick={() => setActiveModuleTab('module1')}
            className={`px-4 py-2 rounded-2xl text-xs font-black transition-all cursor-pointer whitespace-nowrap ${
              activeModuleTab === 'module1'
                ? 'bg-sky-600 text-white shadow-xs'
                : 'text-zinc-600 hover:bg-zinc-100'
            }`}
          >
            🗣️ Module 1: Pinyin ({module1Concepts.length})
          </button>
          <button
            onClick={() => setActiveModuleTab('module2')}
            className={`px-4 py-2 rounded-2xl text-xs font-black transition-all cursor-pointer whitespace-nowrap ${
              activeModuleTab === 'module2'
                ? 'bg-emerald-600 text-white shadow-xs'
                : 'text-zinc-600 hover:bg-zinc-100'
            }`}
          >
            📐 Module 2: Grammar ({module2Concepts.length})
          </button>
          <button
            onClick={() => setActiveModuleTab('module3')}
            className={`px-4 py-2 rounded-2xl text-xs font-black transition-all cursor-pointer whitespace-nowrap ${
              activeModuleTab === 'module3'
                ? 'bg-amber-600 text-white shadow-xs'
                : 'text-zinc-600 hover:bg-zinc-100'
            }`}
          >
            🎯 Module 3: Communication ({module3Concepts.length})
          </button>
        </div>
      </div>

      {/* 2. Render Modules */}
      {(activeModuleTab === 'all' || activeModuleTab === 'module1') &&
        renderModuleSection(
          'module1',
          'Module 1: Pinyin & Pronunciation',
          'Pinyin Phonetics, 4 Tones & Sandhi Rules with Native Audio Demo',
          'Phonetics & Tones',
          'sky',
          module1Concepts,
          m1Stats
        )}

      {(activeModuleTab === 'all' || activeModuleTab === 'module2') &&
        renderModuleSection(
          'module2',
          'Module 2: Core Grammar Foundations',
          'Essential HSK 1 sentence patterns and questions',
          'Grammar Skeleton',
          'emerald',
          module2Concepts,
          m2Stats
        )}

      {(activeModuleTab === 'all' || activeModuleTab === 'module3') &&
        renderModuleSection(
          'module3',
          `Module 3: Communication (${activePreset.badge || 'Focus'})`,
          'Everyday communication with familiar HSK 1 language',
          'Real-Life Application',
          'amber',
          module3Concepts,
          m3Stats
        )}
    </div>
  );
};
