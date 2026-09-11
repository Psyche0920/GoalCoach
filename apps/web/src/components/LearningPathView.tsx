import React, { useState } from 'react';
import { 
  Check, 
  Star, 
  Sparkles, 
  Clock, 
  ArrowRight, 
  Filter, 
  Compass, 
  Volume2, 
  BookOpen, 
  Flame, 
  Trophy, 
  Gift, 
  Lock, 
  HelpCircle,
  Tag,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { PandaMascot } from './PandaMascot.tsx';
import { CurriculumConcept, DailyPlan, LearningGoal, LearnerState, CurriculumTheme, ConceptCategory } from '../types.ts';
import { isConceptReviewDue } from '../domain/retention.ts';
import { GOAL_PRESETS, THEME_REGISTRY, CATEGORY_REGISTRY } from '../data/curriculumThemes.ts';
import { getTailoredExample } from '../utils/tailoredExamples.ts';
import { CharacterEntry, findCharacterBreakdown } from '../data/characterRadicals.ts';
import { CharacterDecompositionModal } from './CharacterDecompositionModal.tsx';

interface LearningPathViewProps {
  concepts: CurriculumConcept[];
  plan: DailyPlan | null;
  goal: LearningGoal | null;
  learnerState: LearnerState | null;
  onStartStudy: (conceptId: string) => void;
  onUpdateGoal: (goal: Partial<LearningGoal>) => void;
}

export const LearningPathView: React.FC<LearningPathViewProps> = ({
  concepts,
  plan,
  goal,
  learnerState,
  onStartStudy,
  onUpdateGoal,
}) => {
  const [selectedConcept, setSelectedConcept] = useState<CurriculumConcept | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<'all' | ConceptCategory>('all');
  const [showTaxonomy, setShowTaxonomy] = useState(false);
  const [inspectedEntry, setInspectedEntry] = useState<CharacterEntry | null>(null);

  const now = new Date();
  const activeTargetDomain = goal?.targetDomain || 'general';
  const activePreset = GOAL_PRESETS.find((p) => p.id === activeTargetDomain) || GOAL_PRESETS[0];

  // Speech helper
  const playAudio = (text: string) => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'zh-CN';
      utterance.rate = 0.85;
      window.speechSynthesis.speak(utterance);
    }
  };

  const handleSelectPreset = (presetId: 'general' | 'travel' | 'dining' | 'work' | 'daily') => {
    const preset = GOAL_PRESETS.find((p) => p.id === presetId);
    if (!preset) return;

    onUpdateGoal({
      title: `${preset.titleZh} (${preset.badge})`,
      targetDomain: preset.id,
      interests: preset.priorityThemes,
      dailyAvailableMinutes: goal?.dailyAvailableMinutes || 20,
    });
  };

  // 1. Separate concepts into MODULE 1 (Grammar) and MODULE 2 (Vocabulary & General Knowledge)
  const grammarConcepts = concepts.filter(
    (c) => c.category === 'grammar' || c.module === 'module1_grammar' || c.isCoreGrammar
  );

  const nonGrammarConcepts = concepts.filter(
    (c) => !(c.category === 'grammar' || c.module === 'module1_grammar' || c.isCoreGrammar)
  );

  // Group Module 2 concepts according to the active goal's unit ordering!
  // E.g. If travel: travel_directions -> shopping_prices -> dining_food -> numbers_time ...
  const themeOrder = activePreset.module2UnitOrder || [
    'greetings_etiquette',
    'identity_family',
    'numbers_time',
    'dining_food',
    'shopping_prices',
    'travel_directions',
    'daily_life',
    'work_study',
    'weather_feelings',
  ];

  interface PathUnit {
    id: string;
    unitNumber: number;
    module: 'module1_grammar' | 'module2_vocabulary';
    theme?: CurriculumTheme;
    titleZh: string;
    titleEn: string;
    badge: string;
    color: string;
    icon: string;
    isPriority: boolean;
    concepts: CurriculumConcept[];
  }

  // Build Module 1 Units (Subdivided into foundational steps)
  const module1Units: PathUnit[] = [
    {
      id: 'm1_u1',
      unitNumber: 1,
      module: 'module1_grammar',
      theme: 'core_grammar',
      titleZh: '语法单元 1: 人称代词与判断句体系',
      titleEn: 'Copula & Sentence Basics (是 / 吗 / 呢)',
      badge: '必须掌握 · 核心语法',
      color: 'emerald',
      icon: '📐',
      isPriority: true,
      concepts: grammarConcepts.slice(0, 5),
    },
    {
      id: 'm1_u2',
      unitNumber: 2,
      module: 'module1_grammar',
      theme: 'core_grammar',
      titleZh: '语法单元 2: 领属、存在与意愿能愿动词',
      titleEn: 'Possession, Existence & Wishes (的 / 有 / 想)',
      badge: '必须掌握 · 核心语法',
      color: 'teal',
      icon: '🧠',
      isPriority: true,
      concepts: grammarConcepts.slice(5, 10),
    },
    {
      id: 'm1_u3',
      unitNumber: 3,
      module: 'module1_grammar',
      theme: 'core_grammar',
      titleZh: '语法单元 3: 连动句、体态助词与副词精通',
      titleEn: 'Action, Aspect & Degree (在 / 去 / 了 / 太)',
      badge: '必须掌握 · 核心语法',
      color: 'cyan',
      icon: '⚡',
      isPriority: true,
      concepts: grammarConcepts.slice(10),
    },
  ];

  // Build Module 2 Units dynamically based on active preset's unit order
  const module2Units: PathUnit[] = themeOrder
    .map((th, idx) => {
      const meta = THEME_REGISTRY[th];
      const matchingConcepts = nonGrammarConcepts.filter((c) => c.theme === th);
      if (matchingConcepts.length === 0) return null;

      const isFirstTwo = idx < 3;
      const isPriorityTheme = activePreset.priorityThemes.includes(th);

      let badge = '情境场景';
      if (meta?.category === 'general_knowledge') {
        badge = '💡 生活必备常识';
      } else if (isPriorityTheme) {
        badge = `🎯 ${activePreset.badge} 优先`;
      }

      return {
        id: `m2_u${idx + 1}_${th}`,
        unitNumber: idx + 1,
        module: 'module2_vocabulary' as const,
        theme: th,
        titleZh: `单元 ${idx + 1}: ${meta?.titleZh || th}`,
        titleEn: meta?.titleEn || th,
        badge,
        color: meta?.color || 'blue',
        icon: meta?.icon || '🌟',
        isPriority: isPriorityTheme,
        concepts: matchingConcepts,
      };
    })
    .filter(Boolean) as PathUnit[];

  // Find the current active step in path for Mascot placement & pulse
  const findCurrentActiveConcept = (): string => {
    // 1. Look in active plan
    const planIncomplete = plan?.items.find((i) => !i.completed);
    if (planIncomplete) return planIncomplete.conceptId;

    // 2. Look for first unmastered concept in sequence
    for (const c of [...grammarConcepts, ...nonGrammarConcepts]) {
      const mastery = learnerState?.mastery?.[c.conceptId];
      if (!mastery || mastery.masteryScore < 0.7) {
        return c.conceptId;
      }
    }
    return grammarConcepts[0]?.conceptId || 'hsk1_c03';
  };

  const currentActiveConceptId = findCurrentActiveConcept();

  // Concept status resolver
  const getConceptState = (conceptId: string) => {
    const mastery = learnerState?.mastery?.[conceptId];
    const isCompleted = (mastery?.masteryScore || 0) >= 0.7;
    const isDue = mastery ? isConceptReviewDue(mastery.nextReviewAt, now) : false;
    const isCurrent = conceptId === currentActiveConceptId;
    const isLocked = !isCompleted && !isCurrent && (!mastery || mastery.masteryScore === 0);

    return { isCompleted, isDue, isCurrent, isLocked, score: mastery?.masteryScore || 0 };
  };

  // Helper to render winding S-curve connecting path ribbon for a list of concepts
  const renderSerpentinePath = (unitConcepts: CurriculumConcept[], unitBgColor: string) => {
    // Serpentine horizontal offset positions (percentage from center-ish: -42px, -20px, 0px, 20px, 42px)
    const offsets = [0, 48, 80, 48, 0, -48, -80, -48];
    const stepHeight = 110;
    const totalHeight = unitConcepts.length * stepHeight;

    return (
      <div 
        className="relative flex flex-col items-center select-none" 
        style={{ minHeight: `${totalHeight + 40}px` }}
      >
        {/* SVG Bezier connecting ribbon background track */}
        <svg
          className="absolute inset-0 w-full h-full pointer-events-none overflow-visible"
          style={{ zIndex: 0 }}
        >
          <defs>
            <linearGradient id={`gradient-done-${unitBgColor}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10b981" />
              <stop offset="100%" stopColor="#059669" />
            </linearGradient>
            <linearGradient id="gradient-gold" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#fbbf24" />
              <stop offset="100%" stopColor="#d97706" />
            </linearGradient>
          </defs>

          {unitConcepts.map((currConcept, idx) => {
            if (idx === unitConcepts.length - 1) return null;
            const nextConcept = unitConcepts[idx + 1];

            const xOffset1 = offsets[idx % offsets.length];
            const xOffset2 = offsets[(idx + 1) % offsets.length];

            const y1 = idx * stepHeight + 40;
            const y2 = (idx + 1) * stepHeight + 40;

            const st1 = getConceptState(currConcept.conceptId);
            const st2 = getConceptState(nextConcept.conceptId);
            const isSegmentLit = st1.isCompleted;

            // Cubic Bezier curve control points
            const d = `M calc(50% + ${xOffset1}px) ${y1} C calc(50% + ${xOffset1}px) ${(y1 + y2) / 2}, calc(50% + ${xOffset2}px) ${(y1 + y2) / 2}, calc(50% + ${xOffset2}px) ${y2}`;

            return (
              <g key={`path-${currConcept.conceptId}-${nextConcept.conceptId}`}>
                {/* Outer shadow / 3D base */}
                <path
                  d={d}
                  fill="none"
                  stroke="#cbd5e1"
                  strokeWidth="14"
                  strokeLinecap="round"
                />
                {/* Inner track */}
                <path
                  d={d}
                  fill="none"
                  stroke="#f1f5f9"
                  strokeWidth="10"
                  strokeLinecap="round"
                />
                {/* Progress lit line if current/completed */}
                {isSegmentLit && (
                  <path
                    d={d}
                    fill="none"
                    stroke={st2.isCompleted ? '#10b981' : '#f59e0b'}
                    strokeWidth="10"
                    strokeLinecap="round"
                    strokeDasharray={st2.isCompleted ? 'none' : '6 6'}
                    className="transition-all duration-500"
                  />
                )}
              </g>
            );
          })}
        </svg>

        {/* Stepping Stones (Chunky 3D Duolingo Buttons) */}
        {unitConcepts.map((concept, idx) => {
          const xOffset = offsets[idx % offsets.length];
          const { isCompleted, isDue, isCurrent, isLocked, score } = getConceptState(concept.conceptId);
          const meta = THEME_REGISTRY[concept.theme];

          // Tailored example for active target domain
          const tailored = getTailoredExample(concept, undefined, activeTargetDomain);

          return (
            <div
              key={concept.conceptId}
              style={{
                transform: `translateX(${xOffset}px)`,
                height: `${stepHeight}px`,
                zIndex: 10,
              }}
              className="relative flex flex-col items-center justify-center"
            >
              {/* Floating Start Badge for Current Step */}
              {isCurrent && (
                <div className="absolute -top-7 z-20 animate-bounce">
                  <div className="bg-emerald-600 text-white font-black text-[11px] uppercase tracking-wider px-3 py-1 rounded-xl shadow-[0_3px_0_#064e3b] border border-emerald-400 flex items-center gap-1">
                    <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                    <span>START 开始</span>
                  </div>
                </div>
              )}

              {/* Review Due Alert Badge */}
              {isDue && !isCurrent && (
                <div className="absolute -top-6 z-20">
                  <div className="bg-amber-500 text-white font-black text-[10px] px-2.5 py-0.5 rounded-full shadow-[0_2px_0_#92400e] border border-amber-300 flex items-center gap-1 animate-pulse">
                    <Flame className="w-3 h-3 text-amber-200" />
                    <span>待复习</span>
                  </div>
                </div>
              )}

              {/* Chunky 3D Duolingo Stepping Stone Button */}
              <button
                onClick={() => setSelectedConcept(concept)}
                className={`
                  relative group w-18 h-18 rounded-full flex items-center justify-center
                  transition-all duration-150 cursor-pointer select-none
                  active:translate-y-1.5
                  ${
                    isCompleted
                      ? 'bg-emerald-500 border-b-[6px] border-emerald-700 shadow-[0_6px_0_#047857] hover:bg-emerald-400 text-white'
                      : isCurrent
                      ? 'bg-amber-400 border-b-[6px] border-amber-600 shadow-[0_6px_0_#b45309] hover:bg-amber-300 text-zinc-950 ring-4 ring-amber-400/40 ring-offset-2'
                      : isDue
                      ? 'bg-amber-500 border-b-[6px] border-amber-700 shadow-[0_6px_0_#92400e] hover:bg-amber-400 text-white'
                      : isLocked
                      ? 'bg-slate-200 border-b-[6px] border-slate-400 shadow-[0_6px_0_#94a3b8] text-slate-400 hover:bg-slate-300'
                      : 'bg-white border-b-[6px] border-slate-300 shadow-[0_6px_0_#cbd5e1] text-slate-800 hover:bg-slate-100'
                  }
                `}
                title={`${concept.titleZh} (${concept.titleEn})`}
              >
                {/* Top highlight glare on button */}
                <div className="absolute top-1.5 w-10 h-3 rounded-full bg-white/30 pointer-events-none" />

                {/* Node Center Icon */}
                <div className="flex flex-col items-center justify-center">
                  {isCompleted ? (
                    <Check className="w-8 h-8 stroke-[3.5] text-white drop-shadow-sm" />
                  ) : isCurrent ? (
                    <Star className="w-8 h-8 fill-zinc-950 text-zinc-950 drop-shadow-sm animate-spin-slow" />
                  ) : isDue ? (
                    <Flame className="w-8 h-8 text-white fill-white drop-shadow-sm" />
                  ) : isLocked ? (
                    <Lock className="w-6 h-6 stroke-[2.5] text-slate-400" />
                  ) : (
                    <span className="text-2xl">{meta?.icon || '📖'}</span>
                  )}
                </div>

                {/* Tiny mastery percentage ring if partly learned */}
                {score > 0 && score < 0.7 && !isCompleted && (
                  <div className="absolute -bottom-1 -right-1 bg-white text-zinc-900 font-mono text-[9px] font-black px-1.5 py-0.5 rounded-full border border-slate-300 shadow-sm">
                    {Math.round(score * 100)}%
                  </div>
                )}
              </button>

              {/* Node Title Label under button */}
              <div className="mt-1.5 text-center max-w-[130px]">
                <div className="text-xs font-black text-zinc-800 line-clamp-1 font-chinese">
                  {concept.titleZh}
                </div>
                <div className="text-[10px] font-bold text-zinc-500 line-clamp-1">
                  {concept.titleEn}
                </div>
              </div>

              {/* Panda Mascot hovering beside Current Node */}
              {isCurrent && (
                <div className="absolute left-24 sm:left-28 -top-3 flex items-center gap-2 pointer-events-none z-30">
                  <PandaMascot mood="cheering" size={68} />
                  <div className="hidden sm:block bg-white border-2 border-zinc-900 rounded-2xl px-3 py-1.5 text-xs font-bold text-zinc-800 shadow-[0_3px_0_#18181b] relative">
                    <div className="text-[10px] font-black text-emerald-600 uppercase">
                      {activePreset.badge}
                    </div>
                    <div>点击开始这一关！</div>
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {/* Unit Completion Treasure Chest */}
        <div className="relative mt-4 flex flex-col items-center z-10">
          <div className="w-14 h-14 rounded-2xl bg-amber-100 border-2 border-amber-500 shadow-[0_4px_0_#d97706] flex items-center justify-center text-2xl hover:scale-105 transition-transform cursor-pointer">
            <Trophy className="w-7 h-7 text-amber-600 fill-amber-300" />
          </div>
          <span className="text-[10px] font-black uppercase tracking-wider text-amber-700 mt-1">
            Unit Checkpoint
          </span>
        </div>
      </div>
    );
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8 pb-20 select-none">
      {/* 1. Target & Interest Goal Selector Banner (Adaptive Curriculum Engine) */}
      <div className="bg-white rounded-3xl p-6 border-2 border-zinc-900 shadow-[0_6px_0_#18181b] space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <PandaMascot mood="happy" size={56} />
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-black uppercase text-emerald-700 tracking-wider">
                  多邻国路线 · 智能场景优先级排课
                </span>
                <span className="text-[10px] font-black bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full border border-emerald-300">
                  {activePreset.badge}
                </span>
              </div>
              <h2 className="text-xl font-black text-zinc-950 font-chinese mt-0.5">
                {activePreset.titleZh}
              </h2>
            </div>
          </div>

          <button
            onClick={() => setShowTaxonomy(!showTaxonomy)}
            className="flex items-center gap-1.5 text-xs font-black text-zinc-700 hover:text-zinc-950 bg-zinc-100 hover:bg-zinc-200 px-3 py-2 rounded-xl border border-zinc-300 transition-colors self-start sm:self-auto cursor-pointer"
          >
            <Tag className="w-3.5 h-3.5 text-emerald-600" />
            <span>知识点与常识分类看板</span>
            {showTaxonomy ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>

        {/* Preset Pills */}
        <div className="space-y-2">
          <div className="text-xs font-bold text-zinc-500">
            切换学习目标场景（课程路线与例句将自动根据所选场景重排定制）：
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
            {GOAL_PRESETS.map((p) => {
              const isSelected = p.id === activeTargetDomain;
              return (
                <button
                  key={p.id}
                  onClick={() => handleSelectPreset(p.id)}
                  className={`
                    p-3 rounded-2xl text-left border-2 transition-all flex flex-col justify-between cursor-pointer
                    ${
                      isSelected
                        ? 'bg-emerald-50 border-emerald-600 shadow-[0_3px_0_#059669]'
                        : 'bg-zinc-50 border-zinc-200 hover:border-zinc-400 text-zinc-700'
                    }
                  `}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xl">{p.icon}</span>
                    {isSelected && <Check className="w-3.5 h-3.5 text-emerald-600 stroke-[3]" />}
                  </div>
                  <div className="mt-2">
                    <div className="text-xs font-black text-zinc-900 line-clamp-1">{p.titleZh}</div>
                    <div className="text-[10px] text-zinc-500 font-bold">{p.badge}</div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Priority Rule Indicator */}
        <div className="bg-amber-50 rounded-2xl p-3 border border-amber-200 flex items-start gap-2.5 text-xs text-amber-900">
          <Sparkles className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          <div>
            <span className="font-black">排课与例句逻辑已生效：</span>
            <span>
              严格遵循 <strong className="text-amber-950">核心语法必须项 + 【{activePreset.titleZh}】优先场景 &gt; 生活常识 &gt; 其他场景</strong>。
              所有教学卡片与关卡例句均已动态定制为针对当前场景的最佳表达！
            </span>
          </div>
        </div>
      </div>

      {/* 2. Full HSK 1 Taxonomy & Common Sense Showcase (Collapsible) */}
      {showTaxonomy && (
        <div className="bg-white rounded-3xl p-6 border-2 border-zinc-900 shadow-[0_6px_0_#18181b] space-y-4">
          <div className="flex items-center justify-between border-b pb-3">
            <div>
              <h3 className="text-base font-black text-zinc-950 font-chinese">
                HSK 1 完整标签与知识体系归类看板
              </h3>
              <p className="text-xs text-zinc-500 font-bold">
                涵盖语言底层语法、生活实用常识与丰富主题情境（共36个微概念）
              </p>
            </div>
            <div className="flex items-center gap-1">
              {(['all', 'grammar', 'general_knowledge', 'scenario'] as const).map((cat) => (
                <button
                  key={cat}
                  onClick={() => setCategoryFilter(cat)}
                  className={`text-xs font-bold px-2.5 py-1 rounded-xl transition-colors cursor-pointer ${
                    categoryFilter === cat
                      ? 'bg-zinc-900 text-white'
                      : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200'
                  }`}
                >
                  {cat === 'all'
                    ? '全部'
                    : cat === 'grammar'
                    ? '📐 核心语法'
                    : cat === 'general_knowledge'
                    ? '💡 生活常识'
                    : '🎯 交际情境'}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {/* Category 1: Grammar */}
            {(categoryFilter === 'all' || categoryFilter === 'grammar') && (
              <div className="p-4 rounded-2xl bg-emerald-50/70 border border-emerald-200 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xl">📐</span>
                    <h4 className="text-xs font-black text-emerald-950 uppercase">核心语法 (15个)</h4>
                  </div>
                  <span className="text-[10px] font-black bg-emerald-200 text-emerald-900 px-2 py-0.5 rounded-full">
                    必须项
                  </span>
                </div>
                <p className="text-[11px] text-emerald-800 font-medium">
                  是判断句、吗/谁/什么/呢疑问句、不/没有否定、领属的、想/会能愿动词、在方位、连动句、了完成体、太/也/都副词。
                </p>
                <div className="flex flex-wrap gap-1 pt-1">
                  {['是字句', '吗疑问', '不否定', '有/没有', '助词的', '了完成体', '能愿动词'].map((t) => (
                    <span key={t} className="text-[9px] font-bold bg-white text-emerald-800 px-1.5 py-0.5 rounded border border-emerald-200">
                      #{t}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Category 2: General Knowledge */}
            {(categoryFilter === 'all' || categoryFilter === 'general_knowledge') && (
              <div className="p-4 rounded-2xl bg-amber-50/70 border border-amber-200 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xl">💡</span>
                    <h4 className="text-xs font-black text-amber-950 uppercase">生活实用常识 (5大类)</h4>
                  </div>
                  <span className="text-[10px] font-black bg-amber-200 text-amber-900 px-2 py-0.5 rounded-full">
                    基础工具
                  </span>
                </div>
                <p className="text-[11px] text-amber-800 font-medium">
                  0-100计数数字、时钟点分表达、日历年月日星期、人民币金钱问价（多少钱/块）、基础生活通用量词（个/本/杯/岁）。
                </p>
                <div className="flex flex-wrap gap-1 pt-1">
                  {['数字0-100', '几点几分', '年月日星期', '金钱问价', '高频量词'].map((t) => (
                    <span key={t} className="text-[9px] font-bold bg-white text-amber-800 px-1.5 py-0.5 rounded border border-amber-200">
                      #{t}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Category 3: Scenarios */}
            {(categoryFilter === 'all' || categoryFilter === 'scenario') && (
              <div className="p-4 rounded-2xl bg-indigo-50/70 border border-indigo-200 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xl">🎯</span>
                    <h4 className="text-xs font-black text-indigo-950 uppercase">交际情境场景 (16个)</h4>
                  </div>
                  <span className="text-[10px] font-black bg-indigo-200 text-indigo-900 px-2 py-0.5 rounded-full">
                    动态优先
                  </span>
                </div>
                <p className="text-[11px] text-indigo-800 font-medium">
                  旅游交通、职场工作、餐饮美食、商场购物、社交问候、家庭人际、日常作息与天气身心。
                </p>
                <div className="flex flex-wrap gap-1 pt-1">
                  {['旅游交通', '商务工作', '美食点餐', '购物问价', '问候社交'].map((t) => (
                    <span key={t} className="text-[9px] font-bold bg-white text-indigo-800 px-1.5 py-0.5 rounded border border-indigo-200">
                      #{t}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* MODULE 1: 核心语法骨架 (Core Grammar - 必须项) */}
      {/* ======================================================== */}
      <div className="space-y-6">
        <div className="bg-emerald-600 text-white rounded-3xl p-6 shadow-[0_6px_0_#065f46] flex items-center justify-between border-2 border-emerald-800">
          <div className="space-y-1">
            <div className="text-xs font-black uppercase tracking-wider text-emerald-200 flex items-center gap-2">
              <span>MODULE 1</span>
              <span>•</span>
              <span className="bg-emerald-700/80 px-2 py-0.5 rounded-full text-[10px]">所有目标必须修习</span>
            </div>
            <h3 className="text-2xl font-black font-chinese">
              核心语法骨架 (Core Grammar Foundations)
            </h3>
            <p className="text-xs text-emerald-100 font-bold max-w-xl">
              汇集 HSK 1 全量 15 大核心语法体系，构建牢不可破的中文句式支撑，为所有场景赋能。
            </p>
          </div>
          <div className="text-4xl hidden sm:block">📐</div>
        </div>

        {/* Render Module 1 Units */}
        <div className="space-y-12">
          {module1Units.map((unit) => (
            <div key={unit.id} className="space-y-4">
              <div className="flex items-center gap-3 justify-center text-center">
                <div className="h-[2px] bg-slate-300 flex-1 max-w-[100px]" />
                <div className="inline-flex items-center gap-2 bg-white px-4 py-1.5 rounded-full border-2 border-slate-900 shadow-[0_2px_0_#0f172a]">
                  <span className="text-base">{unit.icon}</span>
                  <span className="text-xs font-black text-slate-900">{unit.titleZh}</span>
                  <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.2 rounded-full">
                    {unit.badge}
                  </span>
                </div>
                <div className="h-[2px] bg-slate-300 flex-1 max-w-[100px]" />
              </div>

              {renderSerpentinePath(unit.concepts, unit.color)}
            </div>
          ))}
        </div>
      </div>

      {/* Module Separator Bridge */}
      <div className="relative flex items-center justify-center py-6">
        <div className="h-[3px] bg-gradient-to-r from-emerald-500 via-amber-500 to-indigo-500 w-full rounded-full" />
        <div className="absolute bg-white px-4 py-1 rounded-full border-2 border-zinc-900 shadow-md flex items-center gap-2 text-xs font-black">
          <Trophy className="w-4 h-4 text-amber-500 fill-amber-300" />
          <span>进阶：场景词汇与生活常识模块</span>
        </div>
      </div>

      {/* ======================================================== */}
      {/* MODULE 2: 场景词汇与生活常识 (Thematic Scenarios & General Knowledge) */}
      {/* 根据当前兴趣动态排序！ */}
      {/* ======================================================== */}
      <div className="space-y-6">
        <div className="bg-indigo-600 text-white rounded-3xl p-6 shadow-[0_6px_0_#3730a3] flex items-center justify-between border-2 border-indigo-800">
          <div className="space-y-1">
            <div className="text-xs font-black uppercase tracking-wider text-indigo-200 flex items-center gap-2">
              <span>MODULE 2</span>
              <span>•</span>
              <span className="bg-indigo-700/80 px-2 py-0.5 rounded-full text-[10px]">
                自适应优先：{activePreset.titleZh}
              </span>
            </div>
            <h3 className="text-2xl font-black font-chinese">
              场景词汇与生活常识 (Scenarios & General Knowledge)
            </h3>
            <p className="text-xs text-indigo-100 font-bold max-w-xl">
              Unit 排序根据您所选的【{activePreset.titleZh}】目标重组，优先攻克最急需的场景与常识词汇！
            </p>
          </div>
          <div className="text-4xl hidden sm:block">{activePreset.icon}</div>
        </div>

        {/* Render Module 2 Units */}
        <div className="space-y-12">
          {module2Units.map((unit) => (
            <div key={unit.id} className="space-y-4">
              <div className="flex items-center gap-3 justify-center text-center">
                <div className="h-[2px] bg-slate-300 flex-1 max-w-[100px]" />
                <div className={`inline-flex items-center gap-2 bg-white px-4 py-1.5 rounded-full border-2 border-slate-900 shadow-[0_2px_0_#0f172a] ${
                  unit.isPriority ? 'ring-2 ring-amber-400' : ''
                }`}>
                  <span className="text-base">{unit.icon}</span>
                  <span className="text-xs font-black text-slate-900">{unit.titleZh}</span>
                  <span className={`text-[10px] font-bold px-2 py-0.2 rounded-full ${
                    unit.isPriority 
                      ? 'bg-amber-100 text-amber-900' 
                      : unit.theme === 'numbers_time' || unit.theme === 'shopping_prices'
                      ? 'bg-blue-100 text-blue-900'
                      : 'bg-slate-100 text-slate-700'
                  }`}>
                    {unit.badge}
                  </span>
                </div>
                <div className="h-[2px] bg-slate-300 flex-1 max-w-[100px]" />
              </div>

              {renderSerpentinePath(unit.concepts, unit.color)}
            </div>
          ))}
        </div>
      </div>

      {/* 3. Concept Detail Drawer / Popover Modal */}
      {selectedConcept && (
        <div className="fixed inset-0 bg-zinc-950/60 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 border-2 border-zinc-900 shadow-[0_8px_0_#18181b] space-y-5 animate-in fade-in zoom-in-95 duration-150">
            {/* Header */}
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-black uppercase tracking-wider text-emerald-600">
                    {selectedConcept.category === 'grammar'
                      ? '📐 核心通用语法'
                      : selectedConcept.category === 'general_knowledge'
                      ? '💡 必备生活常识'
                      : '🎯 主题交际情境'}
                  </span>
                  <span className="text-[10px] font-black bg-zinc-100 text-zinc-700 px-2 py-0.5 rounded-full">
                    {THEME_REGISTRY[selectedConcept.theme]?.titleZh}
                  </span>
                  <span className="text-[10px] font-bold bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full">
                    难度 Lv.{selectedConcept.difficulty}
                  </span>
                </div>
                <h3 className="text-2xl font-black text-zinc-950 font-chinese">
                  {selectedConcept.titleZh}
                </h3>
                <p className="text-xs font-bold text-zinc-500">
                  {selectedConcept.titleEn}
                </p>
              </div>

              <button
                onClick={() => setSelectedConcept(null)}
                className="text-zinc-400 hover:text-zinc-800 p-1.5 rounded-xl transition-colors cursor-pointer"
              >
                ✕
              </button>
            </div>

            {/* Communicative Goal */}
            <div className="bg-zinc-50 rounded-2xl p-4 border border-zinc-200 space-y-1.5">
              <div className="text-xs font-black uppercase text-zinc-500">交际应用目标</div>
              <p className="text-xs font-bold text-zinc-800 leading-relaxed">
                {selectedConcept.communicativeGoal}
              </p>
            </div>

            {/* Dynamic Tailored Example based on user interest! */}
            {(() => {
              const tailored = getTailoredExample(selectedConcept, undefined, activeTargetDomain);
              return (
                <div className="bg-emerald-50 rounded-2xl p-4 border-2 border-emerald-500 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-black uppercase text-emerald-900 flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                      {tailored.scenarioTag}
                    </span>
                    <button
                      onClick={() => playAudio(tailored.zh)}
                      className="text-emerald-700 hover:text-emerald-900 flex items-center gap-1 text-xs font-bold cursor-pointer"
                    >
                      <Volume2 className="w-3.5 h-3.5" />
                      朗读例句
                    </button>
                  </div>
                  <div className="font-chinese text-lg font-black text-zinc-950">
                    {tailored.zh}
                  </div>
                  <div className="text-xs font-mono font-bold text-emerald-700">
                    {tailored.pinyin}
                  </div>
                  <div className="text-xs font-bold text-zinc-600 italic">
                    {tailored.en}
                  </div>
                </div>
              );
            })()}

            {/* Focus Items */}
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 bg-zinc-50 rounded-xl border border-zinc-200">
                <div className="font-black text-zinc-700 mb-1 flex items-center justify-between">
                  <span>重点词汇 (可点查偏旁)</span>
                  <Sparkles className="w-3 h-3 text-amber-500" />
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {selectedConcept.vocabularyFocus.map((v) => {
                    const breakdown = findCharacterBreakdown(v);
                    return (
                      <button
                        key={v}
                        onClick={() => breakdown && setInspectedEntry(breakdown)}
                        className={`px-2 py-0.5 rounded border font-bold font-chinese transition-colors cursor-pointer text-xs ${
                          breakdown
                            ? 'bg-indigo-50 border-indigo-300 text-indigo-950 hover:bg-indigo-100 border-b-2 border-dashed'
                            : 'bg-white border-zinc-300 text-zinc-800'
                        }`}
                        title={breakdown ? '点击探索偏旁部首树形解构' : undefined}
                      >
                        {v}
                      </button>
                    );
                  })}
                </div>
              </div>
              <div className="p-3 bg-zinc-50 rounded-xl border border-zinc-200">
                <div className="font-black text-zinc-700 mb-1">句型骨架</div>
                <div className="space-y-0.5">
                  {selectedConcept.grammarFocus.map((g) => (
                    <div key={g} className="font-bold text-zinc-800 line-clamp-1">
                      • {g}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center gap-3 pt-2">
              <button
                onClick={() => setSelectedConcept(null)}
                className="flex-1 py-3 text-xs font-black text-zinc-600 hover:bg-zinc-100 rounded-2xl border border-zinc-300 cursor-pointer"
              >
                稍后学习
              </button>
              <button
                onClick={() => {
                  const id = selectedConcept.conceptId;
                  setSelectedConcept(null);
                  onStartStudy(id);
                }}
                className="flex-2 py-3 bg-emerald-500 hover:bg-emerald-400 text-white font-black text-sm rounded-2xl border-b-4 border-emerald-700 shadow-[0_4px_0_#047857] flex items-center justify-center gap-2 active:translate-y-1 transition-all cursor-pointer"
              >
                <span>进入关卡挑战</span>
                <ArrowRight className="w-4 h-4 stroke-[3]" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Character Radical Decomposition Popover Modal (Image 1 Feature) */}
      {inspectedEntry && (
        <CharacterDecompositionModal
          entry={inspectedEntry}
          onClose={() => setInspectedEntry(null)}
          onPlayAudio={playAudio}
        />
      )}
    </div>
  );
};
