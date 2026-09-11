import React, { useState } from 'react';
import { 
  CheckCircle2, 
  Sparkles, 
  BookOpen, 
  Volume2, 
  Layers, 
  Check, 
  ArrowRight, 
  ChevronRight,
  Headphones,
  Compass,
  FileText
} from 'lucide-react';
import { CurriculumConcept, LearnerState } from '../types.ts';
import { audioFeedback } from '../utils/audioFeedback.ts';

interface MasteryDashboardProps {
  concepts: CurriculumConcept[];
  learnerState: LearnerState | null;
  onSelectConcept: (conceptId: string) => void;
}

export const MasteryDashboard: React.FC<MasteryDashboardProps> = ({
  concepts,
  learnerState,
  onSelectConcept,
}) => {
  const [activeModuleTab, setActiveModuleTab] = useState<'all' | 'module1' | 'module2' | 'module3'>('all');

  // Group concepts by module
  const module1Concepts = concepts.filter(c => c.module === 'module1_pinyin' || c.category === 'pinyin');
  const module2Concepts = concepts.filter(c => c.module === 'module2_grammar' || c.category === 'grammar');
  const module3Concepts = concepts.filter(c => c.module === 'module3_themes' || (!c.module && c.category !== 'pinyin' && c.category !== 'grammar'));

  const getConceptMastery = (conceptId: string) => {
    return learnerState?.mastery?.[conceptId];
  };

  const renderConceptCard = (concept: CurriculumConcept) => {
    const mastery = getConceptMastery(concept.conceptId);
    const score = mastery?.masteryScore || 0;
    const isMastered = score >= 0.75;
    const isLearning = score > 0 && score < 0.75;

    return (
      <div 
        key={concept.conceptId}
        onClick={() => onSelectConcept(concept.conceptId)}
        className="group bg-white rounded-3xl border-2 border-zinc-200 hover:border-zinc-950 p-5 shadow-xs hover:shadow-md transition-all cursor-pointer flex flex-col justify-between gap-4"
      >
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-black uppercase tracking-wider text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded-lg border border-emerald-200">
              {concept.module === 'module1_pinyin' ? 'Pinyin' : concept.module === 'module2_grammar' ? 'Grammar' : 'Theme'}
            </span>
            {isMastered ? (
              <span className="flex items-center gap-1 text-[11px] font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-md">
                <Check className="w-3 h-3 stroke-[3]" /> Mastered
              </span>
            ) : isLearning ? (
              <span className="text-[11px] font-bold text-amber-700 bg-amber-100 px-2 py-0.5 rounded-md">
                {Math.round(score * 100)}% In Progress
              </span>
            ) : (
              <span className="text-[11px] font-bold text-zinc-400 bg-zinc-100 px-2 py-0.5 rounded-md">
                Ready to Learn
              </span>
            )}
          </div>

          <h4 className="text-base font-black text-zinc-950 font-chinese group-hover:text-emerald-700 transition-colors">
            {concept.titleZh}
          </h4>
          <p className="text-xs text-zinc-500 font-medium line-clamp-2 leading-relaxed">
            {concept.titleEn}
          </p>
        </div>

        <div className="pt-3 border-t border-zinc-100 flex items-center justify-between text-xs">
          <span className="text-zinc-400 font-bold">
            {concept.vocabularyFocus?.slice(0, 3).join(', ')}
          </span>
          <div className="flex items-center gap-1 font-black text-emerald-700 group-hover:translate-x-0.5 transition-transform">
            <span>Study</span>
            <ChevronRight className="w-4 h-4 stroke-[2.5]" />
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header Banner - Matching Plan Layout */}
      <div className="bg-white rounded-3xl border-2 border-zinc-200 p-6 sm:p-7 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-2xl bg-emerald-100 border-2 border-emerald-300 flex items-center justify-center text-emerald-800 shrink-0">
              <Layers className="w-6 h-6 stroke-[2.5]" />
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-black uppercase tracking-wider text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-lg border border-emerald-200">
                  Full Curriculum
                </span>
                <span className="text-xs font-extrabold text-zinc-500 bg-zinc-100 px-2.5 py-0.5 rounded-lg">
                  3 Modules Structure
                </span>
              </div>
              <h2 className="text-xl font-black text-zinc-950">
                HSK 1 Learning Modules
              </h2>
              <p className="text-xs text-zinc-500 font-medium">
                Structured from beginner phonetics to foundational grammar and real-world thematic scenarios.
              </p>
            </div>
          </div>

          {/* Module Selector Filter */}
          <div className="flex items-center gap-1.5 bg-zinc-100 p-1.5 rounded-2xl border border-zinc-200 self-start sm:self-center">
            <button
              onClick={() => setActiveModuleTab('all')}
              className={`px-3 py-1.5 rounded-xl text-xs font-black transition-all ${
                activeModuleTab === 'all'
                  ? 'bg-white text-zinc-950 shadow-xs'
                  : 'text-zinc-600 hover:text-zinc-900'
              }`}
            >
              All
            </button>
            <button
              onClick={() => setActiveModuleTab('module1')}
              className={`px-3 py-1.5 rounded-xl text-xs font-black transition-all ${
                activeModuleTab === 'module1'
                  ? 'bg-white text-zinc-950 shadow-xs'
                  : 'text-zinc-600 hover:text-zinc-900'
              }`}
            >
              M1: Pinyin
            </button>
            <button
              onClick={() => setActiveModuleTab('module2')}
              className={`px-3 py-1.5 rounded-xl text-xs font-black transition-all ${
                activeModuleTab === 'module2'
                  ? 'bg-white text-zinc-950 shadow-xs'
                  : 'text-zinc-600 hover:text-zinc-900'
              }`}
            >
              M2: Grammar
            </button>
            <button
              onClick={() => setActiveModuleTab('module3')}
              className={`px-3 py-1.5 rounded-xl text-xs font-black transition-all ${
                activeModuleTab === 'module3'
                  ? 'bg-white text-zinc-950 shadow-xs'
                  : 'text-zinc-600 hover:text-zinc-900'
              }`}
            >
              M3: Themes
            </button>
          </div>
        </div>
      </div>

      {/* Module 1: 音标单元 (Pinyin & Pronunciation) */}
      {(activeModuleTab === 'all' || activeModuleTab === 'module1') && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <span className="p-2 rounded-xl bg-emerald-50 text-emerald-700 border border-emerald-200">
                <Headphones className="w-4 h-4" />
              </span>
              <div>
                <span className="text-[11px] font-black uppercase tracking-wider text-emerald-700">Module 1</span>
                <h3 className="text-lg font-black text-zinc-950">Pinyin & Pronunciation</h3>
              </div>
            </div>
            <span className="text-xs font-bold text-zinc-400">
              {module1Concepts.length} Units • Audio phonetics & tone contours
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {module1Concepts.map(renderConceptCard)}
          </div>
        </section>
      )}

      {/* Module 2: Core Grammar Foundations */}
      {(activeModuleTab === 'all' || activeModuleTab === 'module2') && (
        <section className="space-y-4 pt-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <span className="p-2 rounded-xl bg-sky-50 text-sky-700 border border-sky-200">
                <FileText className="w-4 h-4" />
              </span>
              <div>
                <span className="text-[11px] font-black uppercase tracking-wider text-sky-700">Module 2</span>
                <h3 className="text-lg font-black text-zinc-950">Core Grammar</h3>
              </div>
            </div>
            <span className="text-xs font-bold text-zinc-400">
              {module2Concepts.length} Units • Sentence frames & particles
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {module2Concepts.map(renderConceptCard)}
          </div>
        </section>
      )}

      {/* Module 3: Thematic Scenarios */}
      {(activeModuleTab === 'all' || activeModuleTab === 'module3') && (
        <section className="space-y-4 pt-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <span className="p-2 rounded-xl bg-amber-50 text-amber-700 border border-amber-200">
                <Compass className="w-4 h-4" />
              </span>
              <div>
                <span className="text-[11px] font-black uppercase tracking-wider text-amber-700">Module 3</span>
                <h3 className="text-lg font-black text-zinc-950">Thematic Scenarios</h3>
              </div>
            </div>
            <span className="text-xs font-bold text-zinc-400">
              {module3Concepts.length} Units • Coffee, Dining, Travel & Daily Chat
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {module3Concepts.map(renderConceptCard)}
          </div>
        </section>
      )}
    </div>
  );
};
