import React, { useState, useMemo } from 'react';
import { 
  Sparkles, 
  Search, 
  ArrowRight, 
  Volume2, 
  Info,
  CheckCircle2,
  ExternalLink
} from 'lucide-react';
import { CurriculumConcept, LearnerState } from '../types';
import { FIVE_PINYIN_UNITS } from '../data/pinyinUnitsData';
import { audioFeedback } from '../utils/audioFeedback';
import { masteredProgressScore } from '../domain/progress.ts';

export type MainBranchType = 'all' | 'pinyin' | 'grammar' | 'scenarios';

const englishOnly = (value: string): string => value
  .replace(/[\p{Script=Han}]/gu, '')
  .replace(/\(\s*\)/g, '')
  .replace(/\s+/g, ' ')
  .trim();

export interface PedagogicalNode {
  id: string;
  conceptId: string;
  isPinyin: boolean;
  branch: 'pinyin' | 'grammar' | 'scenarios';
  subBranch: string;
  shortLabel: string;
  fullTitleEn: string;
  titleZh?: string;
  pinyin?: string;
  rationale: string; // Pedagogical grounding requirement
  x: number;
  y: number;
  rotation: number;
}

// Strictly pedagogical nodes mapped across 3 distinct branches
export const TREE_PEDAGOGICAL_NODES: PedagogicalNode[] = [
  // ================= BRANCH 1: PINYIN (Left Branch) =================
  {
    id: 'node-pinyin-intro',
    conceptId: 'hsk1_p01',
    isPinyin: true,
    branch: 'pinyin',
    subBranch: 'Intro & Anatomy',
    shortLabel: 'Intro',
    fullTitleEn: 'Syllable Anatomy & Tone Marks',
    titleZh: '拼音结构',
    pinyin: 'Pīnyīn Jiégòu',
    rationale: 'HSK 1 Benchmark: Initial + Final + Tone construct foundation for every Mandarin spoken syllable.',
    x: 180,
    y: 420,
    rotation: -14,
  },
  {
    id: 'node-pinyin-tones',
    conceptId: 'hsk1_p02',
    isPinyin: true,
    branch: 'pinyin',
    subBranch: '4 Tones',
    shortLabel: '4 Tones',
    fullTitleEn: '4 Standard Pitch Contours (55, 35, 214, 51)',
    titleZh: '四声调',
    pinyin: 'Sì Shēngdiào',
    rationale: 'Mandarin is tonal: meaning changes completely depending on high flat, rising, dipping, or falling pitch.',
    x: 120,
    y: 340,
    rotation: -22,
  },
  {
    id: 'node-pinyin-initials',
    conceptId: 'hsk1_p03',
    isPinyin: true,
    branch: 'pinyin',
    subBranch: 'Initials (声母)',
    shortLabel: 'Initials',
    fullTitleEn: '21 Initial Consonants (b, p, m, f, d, t, n, l, g, k, h, j, q, x...)',
    titleZh: '21声母',
    pinyin: 'Shēngmǔ',
    rationale: 'Official HSK 1 Phonology: Essential consonant articulatory onsets covering all 400+ syllables.',
    x: 160,
    y: 250,
    rotation: -10,
  },
  {
    id: 'node-pinyin-finals',
    conceptId: 'hsk1_p04',
    isPinyin: true,
    branch: 'pinyin',
    subBranch: 'Finals (韵母)',
    shortLabel: 'Finals',
    fullTitleEn: 'Simple, Compound & Nasal Finals (a, o, e, i, u, ü, ai, ei, an, eng...)',
    titleZh: '36韵母',
    pinyin: 'Yùnmǔ',
    rationale: 'Vowel and resonance targets that dictate syllable clarity and auditory recognition.',
    x: 230,
    y: 200,
    rotation: -8,
  },
  {
    id: 'node-pinyin-sandhi',
    conceptId: 'hsk1_p05',
    isPinyin: true,
    branch: 'pinyin',
    subBranch: 'Tone Rules',
    shortLabel: 'Rules',
    fullTitleEn: 'Tone Sandhi & Spelling Rules (y/w rules, 不 & 一 tone shifts)',
    titleZh: '变调与拼写',
    pinyin: 'Biàndiào Guīzé',
    rationale: 'Fluency rule: 3rd tone sandhi (3+3 -> 2+3) and "y/w" rules prevent common spoken pronunciation errors.',
    x: 270,
    y: 280,
    rotation: -4,
  },

  // ================= BRANCH 2: GRAMMAR (Center / Upward Branch) =================
  {
    id: 'node-grammar-wordorder',
    conceptId: 'hsk1_c04',
    isPinyin: false,
    branch: 'grammar',
    subBranch: 'Sentence Structure',
    shortLabel: 'Word Order',
    fullTitleEn: 'Standard Word Order (Subject + Verb + Object)',
    titleZh: '主谓宾句序',
    pinyin: 'Zhǔ Wèi Bīn',
    rationale: 'Mandarin syntax cornerstone: Time and Location strictly precede the verb; default SVO structure.',
    x: 340,
    y: 350,
    rotation: -6,
  },
  {
    id: 'node-grammar-copula',
    conceptId: 'hsk1_c03',
    isPinyin: false,
    branch: 'grammar',
    subBranch: 'Copula Verbs',
    shortLabel: 'Copula 是',
    fullTitleEn: 'Identity & Definition with 是 (A 是 B)',
    titleZh: '“是”字句',
    pinyin: 'Shì Zì Jù',
    rationale: 'Equative sentences: Used only between nouns/pronouns (never before descriptive adjectives).',
    x: 460,
    y: 340,
    rotation: 8,
  },
  {
    id: 'node-grammar-ma',
    conceptId: 'hsk1_c01',
    isPinyin: false,
    branch: 'grammar',
    subBranch: 'Questions',
    shortLabel: 'Question 吗',
    fullTitleEn: 'Yes/No Questions with Sentence Particle 吗',
    titleZh: '“吗”疑问句',
    pinyin: 'Ma Yíwèn Jù',
    rationale: 'Direct question construction: Turn any declarative statement into a yes/no question without word inversion.',
    x: 320,
    y: 260,
    rotation: -12,
  },
  {
    id: 'node-grammar-wh',
    conceptId: 'hsk1_c08',
    isPinyin: false,
    branch: 'grammar',
    subBranch: 'Questions',
    shortLabel: 'Wh- Words',
    fullTitleEn: 'Question Pronouns (谁, 什么, 哪, 几, 怎么)',
    titleZh: '疑问代词',
    pinyin: 'Yíwèn Dàicí',
    rationale: 'In-situ question words: Question words replace the target answer directly without shifting positions.',
    x: 480,
    y: 260,
    rotation: 12,
  },
  {
    id: 'node-grammar-negation',
    conceptId: 'hsk1_c07',
    isPinyin: false,
    branch: 'grammar',
    subBranch: 'Negation',
    shortLabel: 'Negation',
    fullTitleEn: 'Negation with 不 (habitual/future) and 没 (past/possession)',
    titleZh: '否定词不与没',
    pinyin: 'Fǒudìng Cí',
    rationale: 'Essential contrast: 不 negates adjectives and habitual actions; 没有 negates existence and past completion.',
    x: 350,
    y: 190,
    rotation: -4,
  },
  {
    id: 'node-grammar-de',
    conceptId: 'hsk1_c04',
    isPinyin: false,
    branch: 'grammar',
    subBranch: 'Particles',
    shortLabel: 'Possessive 的',
    fullTitleEn: 'Possessive & Attributive Particle 的 (Noun + 的 + Noun)',
    titleZh: '结构助词“的”',
    pinyin: 'De Zhùcí',
    rationale: 'Connecting modifier and modified noun: Marks possession (我的) and descriptive modification.',
    x: 450,
    y: 190,
    rotation: 6,
  },
  {
    id: 'node-grammar-hen',
    conceptId: 'hsk1_c06',
    isPinyin: false,
    branch: 'grammar',
    subBranch: 'Adverbs',
    shortLabel: 'Degree 很',
    fullTitleEn: 'Adverbs of Degree with Adjectives (很, 太...了)',
    titleZh: '程度副词“很”',
    pinyin: 'Chéngdù Fùcí',
    rationale: 'Adjectival predicate bridge: Stative adjectives in Chinese require 很 as a structural link in place of 是.',
    x: 350,
    y: 120,
    rotation: -8,
  },
  {
    id: 'node-grammar-zai',
    conceptId: 'hsk1_c11',
    isPinyin: false,
    branch: 'grammar',
    subBranch: 'Prepositions',
    shortLabel: 'Location 在',
    fullTitleEn: 'Locative Verb & Preposition 在 (Subject + 在 + Place + Verb)',
    titleZh: '介词“在”',
    pinyin: 'Jiècí Zài',
    rationale: 'Spatial framing: Expresses physical presence and specifies where an action occurs before the verb.',
    x: 400,
    y: 75,
    rotation: 0,
  },
  {
    id: 'node-grammar-modals',
    conceptId: 'hsk1_c05',
    isPinyin: false,
    branch: 'grammar',
    subBranch: 'Auxiliary',
    shortLabel: 'Modals',
    fullTitleEn: 'Modal Verbs of Ability & Desire (会, 想, 能)',
    titleZh: '能愿动词',
    pinyin: 'Néngyuàn Dòngcí',
    rationale: 'Expressing cognitive capacity (会 speak Chinese), intent (想 eat), and physical permission (能).',
    x: 450,
    y: 120,
    rotation: 10,
  },

  // ================= BRANCH 3: SCENARIOS (Right Branch) =================
  {
    id: 'node-scenarios-greetings',
    conceptId: 'hsk1_c01',
    isPinyin: false,
    branch: 'scenarios',
    subBranch: 'Social Exchange',
    shortLabel: 'Greetings',
    fullTitleEn: 'Essential Greetings, Courtesies & Polite Forms',
    titleZh: '问候与礼貌',
    pinyin: 'Wènhòu',
    rationale: 'Core survival interaction: Initiating dialogue (你好), showing gratitude (谢谢), and farewells (再见).',
    x: 570,
    y: 410,
    rotation: 14,
  },
  {
    id: 'node-scenarios-numbers',
    conceptId: 'hsk1_c02',
    isPinyin: false,
    branch: 'scenarios',
    subBranch: 'Numbers & Time',
    shortLabel: 'Numbers',
    fullTitleEn: 'Numbers 1-100, Clocks, Calendar & Dates',
    titleZh: '数字与时间',
    pinyin: 'Shùzì Shíjiān',
    rationale: 'Functional utility: Scheduling meetings, identifying dates (月/号), day of week (星期), and telling time.',
    x: 650,
    y: 350,
    rotation: 20,
  },
  {
    id: 'node-scenarios-family',
    conceptId: 'hsk1_c04',
    isPinyin: false,
    branch: 'scenarios',
    subBranch: 'Identity & Family',
    shortLabel: 'Family',
    fullTitleEn: 'Self-Introduction, Country, Relatives & Kinship',
    titleZh: '家人与国籍',
    pinyin: 'Jiārén Guójí',
    rationale: 'Personal connection: Introducing family members (爸爸, 妈妈) and nationality (中国人, 美国人).',
    x: 680,
    y: 270,
    rotation: 16,
  },
  {
    id: 'node-scenarios-dining',
    conceptId: 'hsk1_c10',
    isPinyin: false,
    branch: 'scenarios',
    subBranch: 'Food & Dining',
    shortLabel: 'Dining',
    fullTitleEn: 'Restaurant Ordering, Food, Tea, Water & Fruit',
    titleZh: '点餐与饮食',
    pinyin: 'Diǎncān Yǐnshí',
    rationale: 'Daily sustenance: Expressing food preferences, ordering staples (米饭, 面条), and drinks (茶, 水).',
    x: 630,
    y: 200,
    rotation: 6,
  },
  {
    id: 'node-scenarios-shopping',
    conceptId: 'hsk1_c08',
    isPinyin: false,
    branch: 'scenarios',
    subBranch: 'Shopping & Money',
    shortLabel: 'Shopping',
    fullTitleEn: 'Asking Prices, Currency 块, and Measure Words 个/本',
    titleZh: '购物与价格',
    pinyin: 'Gòuwù Jiàgé',
    rationale: 'Commercial exchange: Inquiring "How much is this?" (多少钱) and using classifier measure words.',
    x: 560,
    y: 220,
    rotation: -6,
  },
  {
    id: 'node-scenarios-daily',
    conceptId: 'hsk1_c13',
    isPinyin: false,
    branch: 'scenarios',
    subBranch: 'Places & Transit',
    shortLabel: 'Daily Life',
    fullTitleEn: 'Navigating Locations, School, Home & Transport',
    titleZh: '日常与出行',
    pinyin: 'Rìcháng Chūxíng',
    rationale: 'Directional navigation: Moving between home (家), school (学校), hospital (医院), taking taxis (出租车).',
    x: 560,
    y: 140,
    rotation: 8,
  },
  {
    id: 'node-scenarios-weather',
    conceptId: 'hsk1_c14',
    isPinyin: false,
    branch: 'scenarios',
    subBranch: 'Weather & Feelings',
    shortLabel: 'Weather',
    fullTitleEn: 'Weather Conditions, Temperature & Physical Well-being',
    titleZh: '天气与感受',
    pinyin: 'Tiānqì Gǎnshòu',
    rationale: 'Casual rapport: Talking about climate (冷/热), rain (下雨), and physical health status (身体).',
    x: 630,
    y: 110,
    rotation: 12,
  },
];

interface KnowledgeTreeProps {
  learnerState: LearnerState | null;
  concepts: CurriculumConcept[];
  onSelectConcept: (conceptId: string, isPinyin?: boolean) => void;
}

export const KnowledgeTree: React.FC<KnowledgeTreeProps> = ({
  learnerState,
  onSelectConcept,
}) => {
  const [selectedBranch, setSelectedBranch] = useState<MainBranchType>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [hoveredNode, setHoveredNode] = useState<{
    node: PedagogicalNode;
    stateType: 'leaf' | 'green_apple' | 'red_apple';
    score: number;
    evidence: number;
  } | null>(null);

  // Compute node lifecycle states according to exact user criteria:
  // - unstudied: Green leaf (🍃)
  // - completed / studied unit: Green apple (🍏)
  // - mastered (score >= 0.8 && evidence > 0): Red apple (🍎)
  const evaluatedNodes = useMemo(() => {
    return TREE_PEDAGOGICAL_NODES.map((node) => {
      const mastery = learnerState?.mastery?.[node.conceptId];
      const progress = learnerState?.conceptProgress?.[node.conceptId];
      const evidence = progress?.evidenceDays ?? mastery?.evidenceCount ?? 0;
      const score = progress
        ? masteredProgressScore(progress)
        : (evidence > 0 ? mastery?.masteryScore ?? 0 : 0);

      let stateType: 'leaf' | 'green_apple' | 'red_apple' = 'leaf';
      if (progress?.status === 'mastered') {
        stateType = 'red_apple';
      } else if ((progress?.learnedPercent ?? 0) > 0 || evidence > 0 || score > 0) {
        stateType = 'green_apple';
      } else {
        stateType = 'leaf';
      }

      const matchesBranch = selectedBranch === 'all' || node.branch === selectedBranch;
      const q = searchQuery.trim().toLowerCase();
      const matchesSearch =
        q === '' ||
        node.shortLabel.toLowerCase().includes(q) ||
        node.fullTitleEn.toLowerCase().includes(q) ||
        node.subBranch.toLowerCase().includes(q);

      const isDimmed = !(matchesBranch && matchesSearch);

      return {
        ...node,
        stateType,
        score,
        evidence,
        isDimmed,
      };
    });
  }, [learnerState, selectedBranch, searchQuery]);

  // Aggregate metrics
  const stats = useMemo(() => {
    let redCount = 0;
    let greenCount = 0;
    let leafCount = 0;

    evaluatedNodes.forEach((n) => {
      if (n.stateType === 'red_apple') redCount++;
      else if (n.stateType === 'green_apple') greenCount++;
      else leafCount++;
    });

    return {
      total: evaluatedNodes.length,
      redApples: redCount,
      greenApples: greenCount,
      leaves: leafCount,
      completionRate: Math.round(((redCount + greenCount) / Math.max(1, evaluatedNodes.length)) * 100),
    };
  }, [evaluatedNodes]);

  return (
    <section className="bg-white rounded-3xl border-2 border-zinc-950 p-4 sm:p-7 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] space-y-6">
      {/* Header & Controls Bar (Strictly English & Visual Icons) */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-zinc-100 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">🌳</span>
            <h2 className="text-xl sm:text-2xl font-black text-zinc-950 tracking-tight">
              Knowledge Tree
            </h2>
          </div>
          <p className="text-xs font-semibold text-zinc-500 mt-1">
            HSK 1 Stem branching into Pinyin, Grammar, and Communicative Scenarios.
          </p>
        </div>

        {/* Growth Lifecycle Legend Pills */}
        <div className="flex flex-wrap items-center gap-2 sm:gap-3 text-xs font-black select-none">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800">
            <span>🍎</span>
            <span>Mastered ({stats.redApples})</span>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-lime-50 border border-lime-200 text-lime-800">
            <span>🍏</span>
            <span>Studied Unit ({stats.greenApples})</span>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800">
            <span>🍃</span>
            <span>Unstudied Leaf ({stats.leaves})</span>
          </div>
        </div>
      </div>

      {/* Filter & Search Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        {/* 3 Main Branch Filters */}
        <div className="flex items-center gap-1.5 overflow-x-auto text-xs font-black">
          <button
            type="button"
            onClick={() => setSelectedBranch('all')}
            className={`px-3 py-1.5 rounded-xl transition-all cursor-pointer ${
              selectedBranch === 'all'
                ? 'bg-zinc-950 text-white shadow-xs'
                : 'bg-zinc-100 hover:bg-zinc-200 text-zinc-700'
            }`}
          >
            All Branches ({evaluatedNodes.length})
          </button>
          <button
            type="button"
            onClick={() => setSelectedBranch('pinyin')}
            className={`px-3 py-1.5 rounded-xl transition-all cursor-pointer ${
              selectedBranch === 'pinyin'
                ? 'bg-zinc-950 text-white shadow-xs'
                : 'bg-zinc-100 hover:bg-zinc-200 text-zinc-700'
            }`}
          >
            Branch 1: Pinyin
          </button>
          <button
            type="button"
            onClick={() => setSelectedBranch('grammar')}
            className={`px-3 py-1.5 rounded-xl transition-all cursor-pointer ${
              selectedBranch === 'grammar'
                ? 'bg-zinc-950 text-white shadow-xs'
                : 'bg-zinc-100 hover:bg-zinc-200 text-zinc-700'
            }`}
          >
            Branch 2: Grammar
          </button>
          <button
            type="button"
            onClick={() => setSelectedBranch('scenarios')}
            className={`px-3 py-1.5 rounded-xl transition-all cursor-pointer ${
              selectedBranch === 'scenarios'
                ? 'bg-zinc-950 text-white shadow-xs'
                : 'bg-zinc-100 hover:bg-zinc-200 text-zinc-700'
            }`}
          >
            Branch 3: Scenarios
          </button>
        </div>

        {/* Search Input */}
        <div className="relative w-full sm:w-60">
          <Search className="w-3.5 h-3.5 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search concepts on tree..."
            className="w-full pl-8 pr-3 py-1.5 rounded-xl border border-zinc-200 text-xs font-semibold focus:outline-none focus:border-zinc-950"
          />
        </div>
      </div>

      {/* Main Illustrative Tree Canvas */}
      <div 
        className="relative w-full bg-radial from-amber-50/40 via-emerald-50/20 to-zinc-50 border-2 border-zinc-950 rounded-3xl p-2 sm:p-6 overflow-hidden shadow-inner min-h-[580px] flex items-center justify-center select-none"
        onMouseLeave={() => setHoveredNode(null)}
      >
        {/* Dynamic Detail Popover on Hover (Closes instantly on mouse leave) */}
        {hoveredNode && (
          <div 
            className="absolute z-30 max-w-sm w-80 bg-zinc-950/95 backdrop-blur-md text-white rounded-2xl p-4 shadow-2xl border-2 border-zinc-700 animate-in fade-in zoom-in-95 duration-150 space-y-3 pointer-events-auto"
            style={{
              left: `${Math.min(72, Math.max(8, (hoveredNode.node.x / 800) * 100))}%`,
              top: `${Math.min(65, Math.max(6, (hoveredNode.node.y / 700) * 100 - 15))}%`,
            }}
            onMouseEnter={() => {
              // Keep active while hovering popover
            }}
            onMouseLeave={() => {
              // Disappear immediately when mouse leaves
              setHoveredNode(null);
            }}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="space-y-0.5">
                <span className="text-[10px] font-black uppercase tracking-wider text-emerald-400">
                  {hoveredNode.node.branch.toUpperCase()} · {englishOnly(hoveredNode.node.subBranch)}
                </span>
                <h4 className="text-sm font-black text-white leading-tight">
                  {englishOnly(hoveredNode.node.fullTitleEn)}
                </h4>
              </div>

              {/* Status Badge */}
              <div className="shrink-0">
                {hoveredNode.stateType === 'red_apple' ? (
                  <span className="text-[11px] font-black px-2.5 py-1 rounded-xl bg-rose-500 text-white flex items-center gap-1 shadow-sm">
                    🍎 Mastered
                  </span>
                ) : hoveredNode.stateType === 'green_apple' ? (
                  <span className="text-[11px] font-black px-2.5 py-1 rounded-xl bg-lime-500 text-zinc-950 flex items-center gap-1 shadow-sm">
                    🍏 Studied
                  </span>
                ) : (
                  <span className="text-[11px] font-black px-2.5 py-1 rounded-xl bg-zinc-800 text-zinc-400 flex items-center gap-1">
                    🍃 Unstudied
                  </span>
                )}
              </div>
            </div>

            {/* Pedagogical Grounding / Rationale */}
            <div className="bg-zinc-900/80 p-2.5 rounded-xl border border-zinc-800 text-[11px] text-zinc-300 leading-relaxed font-medium">
              <div className="font-bold text-zinc-400 mb-0.5 flex items-center gap-1">
                <Info className="w-3 h-3 text-emerald-400" /> Pedagogical Grounding:
              </div>
              {englishOnly(hoveredNode.node.rationale)}
            </div>

            {/* Mastery & Review Stat */}
            <div className="flex items-center justify-between text-[11px] text-zinc-400 border-t border-zinc-800 pt-2 font-semibold">
              <span>Mastery: {Math.round(hoveredNode.score * 100)}%</span>
              <span>{hoveredNode.evidence} completed sessions</span>
            </div>

            {/* Practice Action Link */}
            <button
              type="button"
              onClick={() => {
                const n = hoveredNode.node;
                setHoveredNode(null);
                onSelectConcept(n.conceptId, n.isPinyin);
              }}
              className="w-full py-2 bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-black text-xs rounded-xl transition-all flex items-center justify-center gap-1.5 cursor-pointer shadow-md"
            >
              <span>Practice Concept</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Scalable SVG Canvas */}
        <svg
          viewBox="0 0 800 700"
          className="w-full max-w-3xl h-auto max-h-[700px] select-none"
        >
          <defs>
            {/* Organic Bark Gradients */}
            <linearGradient id="trunkBarkGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#2c1407" />
              <stop offset="40%" stopColor="#451e0b" />
              <stop offset="70%" stopColor="#301508" />
              <stop offset="100%" stopColor="#200d04" />
            </linearGradient>

            <linearGradient id="branchBarkGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#3d1b09" />
              <stop offset="50%" stopColor="#54260d" />
              <stop offset="100%" stopColor="#261005" />
            </linearGradient>

            {/* Red Apple Ripe Radial Gradient */}
            <radialGradient id="redAppleGrad" cx="35%" cy="30%" r="70%">
              <stop offset="0%" stopColor="#f87171" />
              <stop offset="45%" stopColor="#dc2626" />
              <stop offset="100%" stopColor="#881337" />
            </radialGradient>

            {/* Green Apple Fresh Radial Gradient */}
            <radialGradient id="greenAppleGrad" cx="35%" cy="30%" r="70%">
              <stop offset="0%" stopColor="#bef264" />
              <stop offset="45%" stopColor="#84cc16" />
              <stop offset="100%" stopColor="#3f6212" />
            </radialGradient>

            {/* Leaf Gradient */}
            <linearGradient id="leafGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#4ade80" />
              <stop offset="60%" stopColor="#16a34a" />
              <stop offset="100%" stopColor="#14532d" />
            </linearGradient>

            {/* Drop Shadow */}
            <filter id="shadowFilter" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="1.5" dy="2.5" stdDeviation="2" floodOpacity="0.25" />
            </filter>
          </defs>

          {/* Ground Soil & Soft Roots Shadow */}
          <ellipse cx="400" cy="670" rx="260" ry="18" fill="#e2e8f0" opacity="0.6" />
          <ellipse cx="400" cy="672" rx="180" ry="10" fill="#cbd5e1" opacity="0.7" />

          {/* ================= MAIN TRUNK & 3 BRANCHES ================= */}
          <g id="tree_trunk_branches">
            {/* Trunk Base ascending to main 3-way branch division point at (400, 440) */}
            <path
              d="M340,670 
                 C350,600 365,540 370,470
                 C375,440 360,420 340,390
                 C300,340 240,300 180,280
                 C220,300 270,330 310,380
                 C345,420 360,450 380,440
                 C390,400 385,320 370,260
                 C360,200 350,150 345,110
                 C360,140 380,190 395,250
                 C405,290 405,370 415,380
                 C430,320 440,240 455,180
                 C465,140 480,100 495,80
                 C480,120 465,180 455,240
                 C445,300 440,380 435,440
                 C460,440 500,410 540,370
                 C600,310 650,270 690,240
                 C640,270 580,330 520,390
                 C470,440 440,470 435,490
                 C440,540 455,600 465,670
                 Z"
              fill="url(#trunkBarkGrad)"
              filter="url(#shadowFilter)"
            />

            {/* Left Branch: PINYIN sub-branches */}
            <path
              d="M330,400 C270,370 200,340 130,320 C180,335 240,360 295,395 Z"
              fill="url(#branchBarkGrad)"
            />
            <path
              d="M250,345 C210,300 170,250 140,210 C165,245 200,285 235,325 Z"
              fill="url(#branchBarkGrad)"
            />
            <path
              d="M200,280 C220,240 250,200 280,165 C255,195 230,235 210,270 Z"
              fill="url(#branchBarkGrad)"
            />

            {/* Center Branch: GRAMMAR sub-branches */}
            <path
              d="M390,320 C360,270 330,220 310,170 C330,210 360,255 385,295 Z"
              fill="url(#branchBarkGrad)"
            />
            <path
              d="M420,310 C450,260 480,210 500,160 C480,200 450,250 425,290 Z"
              fill="url(#branchBarkGrad)"
            />
            <path
              d="M400,220 C395,170 395,120 400,75 C405,120 405,170 405,220 Z"
              fill="url(#branchBarkGrad)"
            />

            {/* Right Branch: SCENARIOS sub-branches */}
            <path
              d="M470,410 C530,380 600,340 660,320 C610,335 550,370 495,405 Z"
              fill="url(#branchBarkGrad)"
            />
            <path
              d="M550,360 C590,300 630,250 670,210 C635,245 600,290 565,335 Z"
              fill="url(#branchBarkGrad)"
            />
            <path
              d="M600,280 C580,230 570,180 565,135 C575,175 585,220 600,260 Z"
              fill="url(#branchBarkGrad)"
            />
          </g>

          {/* ================= STEM PLAQUE: HSK 1 ================= */}
          <g id="hsk1_stem_plaque" transform="translate(400, 570)">
            {/* Wooden Plaque Body */}
            <rect
              x="-65"
              y="-24"
              width="130"
              height="48"
              rx="12"
              fill="#fed7aa"
              stroke="#451e0b"
              strokeWidth="3.5"
              filter="url(#shadowFilter)"
            />
            <rect
              x="-59"
              y="-18"
              width="118"
              height="36"
              rx="8"
              fill="#ffedd5"
              stroke="#9a3412"
              strokeWidth="1.2"
              strokeDasharray="3 2"
            />
            {/* Engraved HSK 1 Text */}
            <text
              x="0"
              y="1"
              textAnchor="middle"
              fontSize="18"
              fontWeight="900"
              fill="#431407"
              fontFamily="sans-serif"
              letterSpacing="0.08em"
            >
              HSK 1
            </text>
            <text
              x="0"
              y="13"
              textAnchor="middle"
              fontSize="7.5"
              fontWeight="800"
              fill="#9a3412"
              letterSpacing="0.12em"
              className="uppercase"
            >
              STEM FOUNDATION
            </text>
            {/* Screws */}
            <circle cx="-52" cy="0" r="2.5" fill="#78350f" />
            <circle cx="52" cy="0" r="2.5" fill="#78350f" />
          </g>

          {/* ================= 3 MAIN BRANCH LABELS ================= */}
          {/* Branch 1: Pinyin Label */}
          <g transform="translate(190, 460)">
            <rect
              x="-45"
              y="-12"
              width="90"
              height="24"
              rx="12"
              fill="#ffffff"
              stroke="#18181b"
              strokeWidth="2"
              filter="url(#shadowFilter)"
            />
            <text
              x="0"
              y="4.5"
              textAnchor="middle"
              fontSize="10"
              fontWeight="900"
              fill="#09090b"
              letterSpacing="0.04em"
            >
              1. Pinyin
            </text>
          </g>

          {/* Branch 2: Grammar Label */}
          <g transform="translate(400, 395)">
            <rect
              x="-50"
              y="-12"
              width="100"
              height="24"
              rx="12"
              fill="#ffffff"
              stroke="#18181b"
              strokeWidth="2"
              filter="url(#shadowFilter)"
            />
            <text
              x="0"
              y="4.5"
              textAnchor="middle"
              fontSize="10"
              fontWeight="900"
              fill="#09090b"
              letterSpacing="0.04em"
            >
              2. Grammar
            </text>
          </g>

          {/* Branch 3: Scenarios Label */}
          <g transform="translate(610, 460)">
            <rect
              x="-50"
              y="-12"
              width="100"
              height="24"
              rx="12"
              fill="#ffffff"
              stroke="#18181b"
              strokeWidth="2"
              filter="url(#shadowFilter)"
            />
            <text
              x="0"
              y="4.5"
              textAnchor="middle"
              fontSize="10"
              fontWeight="900"
              fill="#09090b"
              letterSpacing="0.04em"
            >
              3. Scenarios
            </text>
          </g>

          {/* ================= INTERACTIVE PEDAGOGICAL NODES ================= */}
          <g id="tree_pedagogical_nodes">
            {evaluatedNodes.map((node) => {
              const isHovered = hoveredNode?.node.id === node.id;

              return (
                <g
                  key={node.id}
                  transform={`translate(${node.x}, ${node.y}) rotate(${node.rotation})`}
                  className={`transition-all duration-200 cursor-pointer ${
                    node.isDimmed ? 'opacity-25 grayscale' : 'opacity-100'
                  }`}
                  onMouseEnter={() => {
                    setHoveredNode({
                      node,
                      stateType: node.stateType,
                      score: node.score,
                      evidence: node.evidence,
                    });
                  }}
                  onClick={() => {
                    setHoveredNode(null);
                    onSelectConcept(node.conceptId, node.isPinyin);
                  }}
                >
                  {/* Subtle Twig connecting to branch */}
                  <line
                    x1="0"
                    y1="18"
                    x2="0"
                    y2="28"
                    stroke="#54260d"
                    strokeWidth="2"
                    strokeLinecap="round"
                  />

                  {/* ================= STATE 1: GREEN LEAF (Unstudied) ================= */}
                  {node.stateType === 'leaf' && (
                    <g transform="scale(1.15)">
                      {/* Leaf Shape */}
                      <path
                        d="M0,-18 
                           C14,-10 18,6 0,16 
                           C-18,6 -14,-10 0,-18 Z"
                        fill="url(#leafGrad)"
                        stroke="#14532d"
                        strokeWidth="1.5"
                        filter="url(#shadowFilter)"
                      />
                      {/* Leaf Center Vein */}
                      <path
                        d="M0,-14 L0,12"
                        stroke="#bbf7d0"
                        strokeWidth="1"
                        strokeLinecap="round"
                        opacity="0.8"
                      />
                      {/* Side Veins */}
                      <line x1="0" y1="-6" x2="6" y2="-2" stroke="#bbf7d0" strokeWidth="0.8" opacity="0.6" />
                      <line x1="0" y1="-1" x2="-6" y2="3" stroke="#bbf7d0" strokeWidth="0.8" opacity="0.6" />
                      <line x1="0" y1="4" x2="5" y2="8" stroke="#bbf7d0" strokeWidth="0.8" opacity="0.6" />
                    </g>
                  )}

                  {/* ================= STATE 2: GREEN APPLE (Studied Unit) ================= */}
                  {node.stateType === 'green_apple' && (
                    <g transform="scale(1.2)">
                      {/* Stem */}
                      <path
                        d="M0,-15 C-2,-20 -5,-22 -7,-24"
                        fill="none"
                        stroke="#451e0b"
                        strokeWidth="2"
                        strokeLinecap="round"
                      />
                      {/* Mini Leaf on Stem */}
                      <path
                        d="M-2,-19 C2,-23 7,-22 8,-18 C7,-15 1,-16 -2,-19 Z"
                        fill="#65a30d"
                        stroke="#365314"
                        strokeWidth="0.8"
                      />
                      {/* Fresh Green Apple Body */}
                      <path
                        d="M0,-13 
                           C6,-16 16,-10 16,1 
                           C16,12 8,18 2,17 
                           C1,17 0,16 -2,17 
                           C-8,18 -16,12 -16,1 
                           C-16,-10 -6,-16 0,-13 Z"
                        fill="url(#greenAppleGrad)"
                        stroke="#365314"
                        strokeWidth="1.6"
                        filter="url(#shadowFilter)"
                      />
                      {/* Glossy Specular Highlight */}
                      <path
                        d="M-9,-6 C-12,-1 -11,5 -8,8"
                        fill="none"
                        stroke="#ffffff"
                        strokeWidth="1.8"
                        strokeLinecap="round"
                        opacity="0.6"
                      />
                    </g>
                  )}

                  {/* ================= STATE 3: RED APPLE (Mastered) ================= */}
                  {node.stateType === 'red_apple' && (
                    <g transform="scale(1.25)">
                      {/* Apple Stem */}
                      <path
                        d="M0,-15 C-2,-20 -5,-22 -7,-25"
                        fill="none"
                        stroke="#451e0b"
                        strokeWidth="2.2"
                        strokeLinecap="round"
                      />
                      {/* Little Leaf on Stem */}
                      <path
                        d="M-2,-19 C2,-24 8,-23 9,-19 C8,-16 2,-16 -2,-19 Z"
                        fill="#22c55e"
                        stroke="#14532d"
                        strokeWidth="0.9"
                      />
                      {/* Plump Ripe Red Apple Body */}
                      <path
                        d="M0,-13 
                           C7,-17 18,-11 18,2 
                           C18,14 9,20 2,19 
                           C1,19 0,18 -2,19 
                           C-9,20 -18,14 -18,2 
                           C-18,-11 -7,-17 0,-13 Z"
                        fill="url(#redAppleGrad)"
                        stroke="#4c0519"
                        strokeWidth="1.8"
                        filter="url(#shadowFilter)"
                      />
                      {/* Glossy Specular Reflection Highlight */}
                      <path
                        d="M-10,-6 C-13,0 -12,7 -9,10"
                        fill="none"
                        stroke="#ffffff"
                        strokeWidth="2.2"
                        strokeLinecap="round"
                        opacity="0.8"
                      />
                      {/* Top indentation dimple */}
                      <circle cx="0" cy="-12" r="1.5" fill="#4c0519" opacity="0.7" />
                    </g>
                  )}

                  {/* Dynamic Hover Ring */}
                  {isHovered && (
                    <circle
                      cx="0"
                      cy="0"
                      r="28"
                      fill="none"
                      stroke="#10b981"
                      strokeWidth="2.5"
                      strokeDasharray="4 3"
                      className="animate-spin"
                    />
                  )}

                  {/* Short English Label Pill Directly Underneath Node */}
                  <g transform={`translate(0, 30) rotate(${-node.rotation})`}>
                    <rect
                      x="-36"
                      y="-8"
                      width="72"
                      height="16"
                      rx="8"
                      fill="#ffffff"
                      stroke="#18181b"
                      strokeWidth="1.4"
                      filter="url(#shadowFilter)"
                    />
                    <text
                      x="0"
                      y="3.5"
                      textAnchor="middle"
                      fontSize="7.5"
                      fontWeight="900"
                      fill="#09090b"
                      className="select-none tracking-tight font-sans"
                    >
                      {englishOnly(node.shortLabel)}
                    </text>
                  </g>
                </g>
              );
            })}
          </g>
        </svg>
      </div>

      {/* Footer Info / Direct Concept Directory Shortcut */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-zinc-500 font-semibold px-2">
        <div className="flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-amber-500" />
          <span>Hover over any leaf or apple to inspect its pedagogical rationale. Click to practice.</span>
        </div>
        <div className="font-mono text-zinc-700 font-black">
          HSK 1 Progress: {stats.completionRate}% ({stats.redApples} Mastered · {stats.greenApples} Studied)
        </div>
      </div>
    </section>
  );
};
