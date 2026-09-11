import React, { useState, useMemo } from 'react';
import {
  X,
  Sparkles,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  GraduationCap,
  Award,
} from 'lucide-react';
import {
  FIVE_PINYIN_UNITS,
  PinyinCurriculumUnitDef,
  PinyinPhonemeCard,
} from '../data/pinyinUnitsData';
import { PinyinInteractiveChart } from './PinyinInteractiveChart';
import { PinyinPhonemeCardModal } from './PinyinPhonemeCardModal';
import { CurriculumConcept, LearnerState } from '../types';
import { PINYIN_CURRICULUM_UNITS } from '../data/pinyinData';
import { PinyinUnitPracticeView } from './PinyinUnitPracticeView';
import { ToneContourVisualizer } from './ToneContourVisualizer';
import { PinyinInteractivePhonemeCard } from './PinyinInteractivePhonemeCard';
import { CATEGORY_VISUAL_GUIDES } from '../data/categoryVisualGuides';

interface PinyinLessonModalProps {
  conceptId: string;
  onClose: () => void;
  onComplete: (score: number) => void;
  learnerState?: LearnerState | null;
  concepts?: CurriculumConcept[];
  onUpdateLearnerState?: (updater: (prev: LearnerState) => LearnerState) => void;
}

export const PinyinLessonModal: React.FC<PinyinLessonModalProps> = ({
  conceptId,
  onClose,
  onComplete,
  learnerState,
  concepts = [],
  onUpdateLearnerState,
}) => {
  // Find initial unit matching the conceptId or default to unit 1
  const initialUnitDef =
    FIVE_PINYIN_UNITS.find((u) => u.conceptId === conceptId) || FIVE_PINYIN_UNITS[0];

  const [currentUnit, setCurrentUnit] = useState<PinyinCurriculumUnitDef>(initialUnitDef);
  const [activePhonemeModal, setActivePhonemeModal] = useState<{
    card: PinyinPhonemeCard;
    tab: 'knowledge' | 'practice';
  } | null>(null);
  const [selectedSubCategory, setSelectedSubCategory] = useState<string>('all');
  const [showUnitQuiz, setShowUnitQuiz] = useState<boolean>(false);
  const [completedUnitScore, setCompletedUnitScore] = useState<number | null>(null);

  // Local state for phonemes marked mastered in this session
  const [masteredPhonemeIds, setMasteredPhonemeIds] = useState<Set<string>>(() => {
    const saved = learnerState?.coachPreferences?.masteredPinyinIds;
    return new Set(Array.isArray(saved) ? saved : []);
  });

  // Check if a unit is completed in learnerState
  const isUnitCompleted = (unitDef: PinyinCurriculumUnitDef) => {
    if (!learnerState?.mastery) return false;
    const m = learnerState.mastery[unitDef.conceptId];
    return Boolean(m && (m.masteryScore >= 0.7 || (m.evidenceCount || 0) > 0));
  };

  // Mark phoneme as mastered and sync with learnerState
  const handleMarkMastered = (phonemeId: string) => {
    setMasteredPhonemeIds((prev) => {
      const next = new Set(prev);
      next.add(phonemeId);
      return next;
    });
  };

  // Subcategories in current unit
  const subCategories = useMemo(() => {
    const set = new Set<string>();
    currentUnit.items.forEach((item) => {
      if (item.subCategory) set.add(item.subCategory);
    });
    return Array.from(set);
  }, [currentUnit]);

  // Active Category Guide
  const activeCategoryGuide = useMemo(() => {
    if (selectedSubCategory !== 'all' && CATEGORY_VISUAL_GUIDES[selectedSubCategory]) {
      return CATEGORY_VISUAL_GUIDES[selectedSubCategory];
    }
    const firstCat = subCategories[0];
    return firstCat && CATEGORY_VISUAL_GUIDES[firstCat] ? CATEGORY_VISUAL_GUIDES[firstCat] : null;
  }, [selectedSubCategory, subCategories]);

  // Filtered phoneme items
  const filteredItems = useMemo(() => {
    if (selectedSubCategory === 'all') return currentUnit.items;
    return currentUnit.items.filter((item) => item.subCategory === selectedSubCategory);
  }, [currentUnit, selectedSubCategory]);

  // Navigate stations
  const currentUnitIndex = FIVE_PINYIN_UNITS.findIndex((u) => u.id === currentUnit.id);
  const hasPrevStation = currentUnitIndex > 0;
  const hasNextStation = currentUnitIndex < FIVE_PINYIN_UNITS.length - 1;

  const handlePrevStation = () => {
    if (hasPrevStation) {
      setCurrentUnit(FIVE_PINYIN_UNITS[currentUnitIndex - 1]);
      setShowUnitQuiz(false);
      setSelectedSubCategory('all');
    }
  };

  const handleNextStation = () => {
    if (hasNextStation && completedUnitScore !== null) {
      setCurrentUnit(FIVE_PINYIN_UNITS[currentUnitIndex + 1]);
      setShowUnitQuiz(false);
      setCompletedUnitScore(null);
      setSelectedSubCategory('all');
    }
  };

  // Handle unit quiz completion
  const handleCompleteUnitPractice = (score: number) => {
    onComplete(score);
    setCompletedUnitScore(score);
  };

  // Find corresponding legacy unit for quiz if available
  const legacyUnit =
    PINYIN_CURRICULUM_UNITS.find((u) => u.unitNumber === currentUnit.unitNumber) ||
    PINYIN_CURRICULUM_UNITS[0];

  return (
    <div className="fixed inset-0 z-50 bg-zinc-950/80 backdrop-blur-md flex items-center justify-center p-2 sm:p-4 md:p-6 select-none animate-in fade-in duration-200">
      <div className="bg-zinc-50 border-2 border-zinc-950 rounded-3xl w-full max-w-6xl h-[94vh] max-h-[950px] flex flex-col overflow-hidden shadow-[6px_6px_0px_0px_rgba(0,0,0,1)]">
        
        {/* Top Header Bar: Clean Station Focus */}
        <div className="bg-white border-b-2 border-zinc-950 px-5 py-3.5 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-emerald-500 text-zinc-950 border-2 border-zinc-950 rounded-2xl flex items-center justify-center font-black text-sm shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
              {currentUnit.unitNumber}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded-md bg-zinc-100 text-zinc-800 border border-zinc-300">
                  Station {currentUnit.unitNumber} of 5
                </span>
                {isUnitCompleted(currentUnit) && (
                  <span className="text-[10px] font-black px-2 py-0.5 rounded-md bg-emerald-100 text-emerald-800 border border-emerald-300 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" /> Mastered
                  </span>
                )}
              </div>
              <h1 className="text-base sm:text-lg font-black text-zinc-950 tracking-tight">
                {currentUnit.titleEn}
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Station Stepper (Prev / Next) */}
            <div className="hidden sm:flex items-center gap-1 bg-zinc-100 p-1 rounded-2xl border border-zinc-200">
              <button
                type="button"
                onClick={handlePrevStation}
                disabled={!hasPrevStation}
                className="p-1.5 rounded-xl text-zinc-700 hover:text-zinc-950 hover:bg-white disabled:opacity-30 disabled:hover:bg-transparent transition-all cursor-pointer"
                title="Previous Station"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-[11px] font-bold text-zinc-600 px-1">
                {currentUnit.unitNumber}/5
              </span>
              <button
                type="button"
                onClick={handleNextStation}
                disabled={!hasNextStation || completedUnitScore === null}
                className="p-1.5 rounded-xl text-zinc-700 hover:text-zinc-950 hover:bg-white disabled:opacity-30 disabled:hover:bg-transparent transition-all cursor-pointer"
                title={completedUnitScore === null ? 'Complete this unit first' : 'Next Station'}
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>

            {/* Practice / Cards Switcher */}
            <button
              type="button"
              onClick={() => setShowUnitQuiz((prev) => !prev)}
              className={`px-3 py-1.5 rounded-xl text-xs font-black flex items-center gap-1.5 transition-all border-2 border-zinc-950 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] cursor-pointer ${
                showUnitQuiz
                  ? 'bg-zinc-950 text-white'
                  : 'bg-white hover:bg-zinc-100 text-zinc-950'
              }`}
            >
              <GraduationCap className="w-4 h-4 text-emerald-600" />
              <span>{showUnitQuiz ? 'Cards' : 'Quiz'}</span>
            </button>

            {/* Close Button */}
            <button
              type="button"
              onClick={onClose}
              className="w-9 h-9 rounded-xl border-2 border-zinc-950 bg-white hover:bg-zinc-100 flex items-center justify-center text-zinc-950 transition-colors shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] cursor-pointer"
              title="Close"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Main Body Area */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
          {completedUnitScore !== null ? (
            <div className="bg-white border-2 border-zinc-950 rounded-3xl p-8 text-center shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] space-y-5">
              <Award className="w-12 h-12 mx-auto text-emerald-600" />
              <div>
                <h3 className="text-xl font-black">Unit {currentUnit.unitNumber} complete</h3>
                <p className="text-sm text-zinc-600 mt-2">Learning evidence saved. Score: {completedUnitScore}%.</p>
                <p className="text-xs text-zinc-500 mt-1">Mastery requires successful reviews across separate intervals.</p>
              </div>
              <div className="flex justify-center gap-3">
                <button type="button" onClick={onClose} className="px-5 py-2.5 rounded-xl border-2 border-zinc-950 bg-white font-black">
                  Back to roadmap
                </button>
                {hasNextStation && (
                  <button type="button" onClick={handleNextStation} className="px-5 py-2.5 rounded-xl border-2 border-zinc-950 bg-emerald-500 font-black">
                    Next unit
                  </button>
                )}
              </div>
            </div>
          ) : showUnitQuiz ? (
            /* Cumulative Unit Practice View with Real-Time Vocab Match */
            <div className="bg-white border-2 border-zinc-950 rounded-3xl p-6 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
              <PinyinUnitPracticeView
                unit={legacyUnit}
                learnerState={learnerState || null}
                concepts={concepts}
                onCompleteUnit={handleCompleteUnitPractice}
              />
            </div>
          ) : currentUnit.unitNumber === 1 ? (
            /* UNIT 1: Full Interactive Pinyin Chart (no Hanzi in cells, full audio coverage!) */
            <PinyinInteractiveChart
              onSelectCardForPractice={(card, mode) => {
                setActivePhonemeModal({ card, tab: mode });
              }}
            />
          ) : currentUnit.unitNumber === 2 ? (
            /* UNIT 2: Visual Pitch Curves (1-4) + Neutral Tone Annotation + Syllable Anatomy */
            <div className="space-y-6">
              {/* Pitch Contour Visualizer */}
              <ToneContourVisualizer
                onTonePracticeComplete={(toneNum) => {
                  handleMarkMastered(`u2_tone_${toneNum}`);
                }}
              />

              {/* Syllable Anatomy & Spelling Rules Cards */}
              <div className="space-y-3 pt-2">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-black text-zinc-700 uppercase tracking-wider flex items-center gap-1.5">
                    <Sparkles className="w-4 h-4 text-amber-500" />
                    Syllable & Tone Placement Cards
                  </h3>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {currentUnit.items
                    .filter((item) => item.category === 'syllable')
                    .map((item) => (
                      <PinyinInteractivePhonemeCard
                        key={item.id}
                        item={item}
                        isMastered={masteredPhonemeIds.has(item.id)}
                        onOpenKnowledge={() => setActivePhonemeModal({ card: item, tab: 'knowledge' })}
                        onMarkMastered={handleMarkMastered}
                      />
                    ))}
                </div>
              </div>
            </div>
          ) : (
            /* UNITS 3, 4, 5: Visual Category Explanations + Interactive Phoneme Cards */
            <div className="space-y-6">
              {/* Category Filter Pills */}
              {subCategories.length > 1 && (
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setSelectedSubCategory('all')}
                    className={`px-3 py-1.5 rounded-xl text-xs font-black transition-all border-2 border-zinc-950 cursor-pointer ${
                      selectedSubCategory === 'all'
                        ? 'bg-zinc-950 text-white shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]'
                        : 'bg-white hover:bg-zinc-100 text-zinc-800'
                    }`}
                  >
                    All ({currentUnit.items.length})
                  </button>
                  {subCategories.map((cat) => {
                    const guide = CATEGORY_VISUAL_GUIDES[cat];
                    const isSelected = selectedSubCategory === cat;
                    return (
                      <button
                        key={cat}
                        type="button"
                        onClick={() => setSelectedSubCategory(cat)}
                        className={`px-3 py-1.5 rounded-xl text-xs font-black transition-all border-2 border-zinc-950 flex items-center gap-1.5 cursor-pointer ${
                          isSelected
                            ? 'bg-emerald-500 text-zinc-950 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] scale-102'
                            : 'bg-white hover:bg-zinc-100 text-zinc-800'
                        }`}
                      >
                        {guide && <span>{guide.icon}</span>}
                        <span>{cat}</span>
                      </button>
                    );
                  })}
                </div>
              )}

              {/* Elementary-Level Kid-Friendly Category Visual Guide Card */}
              {activeCategoryGuide && (
                <div className={`p-5 rounded-3xl border-2 border-zinc-950 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] ${activeCategoryGuide.badgeBg} flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 animate-in fade-in`}>
                  <div className="flex items-center gap-3.5">
                    <div className="w-12 h-12 rounded-2xl bg-white border-2 border-zinc-950 flex items-center justify-center text-2xl shadow-xs shrink-0">
                      {activeCategoryGuide.icon}
                    </div>
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <h4 className="text-sm font-black text-zinc-950">
                          {activeCategoryGuide.simpleTitleEn}
                        </h4>
                      </div>
                      <p className="text-xs font-bold text-zinc-700">
                        {activeCategoryGuide.kidExplanation}
                      </p>
                      <p className="text-[11px] font-medium text-zinc-600">
                        💡 {activeCategoryGuide.actionTip}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Grid of Individual Phoneme Knowledge & Practice Cards */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-black text-zinc-600 uppercase tracking-wider">
                    Phoneme Cards ({filteredItems.length})
                  </span>
                  <div className="text-xs font-bold text-emerald-800 bg-emerald-50 px-2.5 py-1 rounded-lg border border-emerald-200">
                    Mastered: {masteredPhonemeIds.size} sounds
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {filteredItems.map((item) => (
                    <PinyinInteractivePhonemeCard
                      key={item.id}
                      item={item}
                      isMastered={masteredPhonemeIds.has(item.id)}
                      onOpenKnowledge={() => setActivePhonemeModal({ card: item, tab: 'knowledge' })}
                      onMarkMastered={handleMarkMastered}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Dedicated Phoneme Knowledge & Practice Modal */}
        {activePhonemeModal && (
          <PinyinPhonemeCardModal
            card={activePhonemeModal.card}
            initialTab={activePhonemeModal.tab}
            onClose={() => setActivePhonemeModal(null)}
            onMastered={(cardId) => handleMarkMastered(cardId)}
            onNext={() => {
              const currentIdx = currentUnit.items.findIndex(
                (i) => i.id === activePhonemeModal.card.id
              );
              if (currentIdx + 1 < currentUnit.items.length) {
                setActivePhonemeModal({
                  card: currentUnit.items[currentIdx + 1],
                  tab: activePhonemeModal.tab,
                });
              }
            }}
            onPrev={() => {
              const currentIdx = currentUnit.items.findIndex(
                (i) => i.id === activePhonemeModal.card.id
              );
              if (currentIdx > 0) {
                setActivePhonemeModal({
                  card: currentUnit.items[currentIdx - 1],
                  tab: activePhonemeModal.tab,
                });
              }
            }}
            hasNext={
              currentUnit.items.findIndex((i) => i.id === activePhonemeModal.card.id) + 1 <
              currentUnit.items.length
            }
            hasPrev={
              currentUnit.items.findIndex((i) => i.id === activePhonemeModal.card.id) > 0
            }
          />
        )}
      </div>
    </div>
  );
};
