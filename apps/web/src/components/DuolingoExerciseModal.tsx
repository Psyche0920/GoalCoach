import React, { useState, useEffect } from 'react';
import { 
  X, 
  Check, 
  ArrowRight, 
  Volume2, 
  Sparkles, 
  HelpCircle,
  ShieldCheck,
  AlertTriangle,
  RotateCcw,
  BookOpen,
  Layers
} from 'lucide-react';
import { PandaMascot } from './PandaMascot.tsx';
import { GoalCoachLogo } from './GoalCoachLogo.tsx';
import { CurriculumConcept, TeachingCard, Exercise, GradingResult } from '../types.ts';
import { THEME_REGISTRY } from '../data/curriculumThemes.ts';
import { getTailoredExample } from '../utils/tailoredExamples.ts';
import { CharacterEntry, findCharacterBreakdown } from '../data/characterRadicals.ts';
import { CharacterDecompositionModal } from './CharacterDecompositionModal.tsx';
import { audioFeedback } from '../utils/audioFeedback.ts';

interface DuolingoExerciseModalProps {
  conceptId: string;
  targetDomain?: string;
  mode?: 'review' | 'new' | 'remedial' | 'daily_quiz';
  onClose: () => void;
  onSubmitAnswer: (exerciseId: string, answer: string) => Promise<GradingResult | null>;
  onRecordMistake?: (exerciseId: string, conceptId: string) => void;
  onCompleteConcept?: (conceptId: string) => void;
}

// Helper to extract the complete full target sentence in Chinese (not just a single word or answer token)
const getFullTargetSentenceZh = (ex?: Exercise | null): string => {
  if (!ex) return '';

  // 1. Fill-in-the-blank: substitute answer into prompt to produce the full sentence
  if (ex.exerciseType === 'fill_blank') {
    let ans = ex.acceptedAnswers?.[0] || ex.answer || '';
    if (ans.startsWith('[') && ans.endsWith(']')) {
      try {
        const parsed = JSON.parse(ans);
        if (Array.isArray(parsed)) ans = parsed.join('');
      } catch {}
    }
    ans = ans.replace(/[\p{P}\p{S}]+/gu, '').trim();

    if (/[\u4e00-\u9fa5]/.test(ex.prompt)) {
      const filled = ex.prompt.replace(/_{2,}/g, ans);
      // If there are multiple dialogue lines, take the target response line
      const lines = filled.split('\n');
      const targetLine = lines.find(l => l.includes(ans)) || lines[lines.length - 1] || filled;
      return targetLine.replace(/^[AB][:：]\s*/gm, '').replace(/（[^）]+）|\([^)]+\)/g, '').trim();
    }
    return ans;
  }

  // 2. Meaning MCQ: prompt contains the full Chinese word or sentence
  if (ex.exerciseType === 'meaning_mcq') {
    if (/[\u4e00-\u9fa5]/.test(ex.prompt)) {
      return ex.prompt.replace(/^[AB][:：]\s*/gm, '').replace(/（[^）]+）|\([^)]+\)/g, '').trim();
    }
  }

  // 3. Reorder or Translation: acceptedAnswers or answer is the full assembled sentence
  let raw = ex.acceptedAnswers?.find(a => /[\u4e00-\u9fa5]/.test(a)) || ex.acceptedAnswers?.[0] || ex.answer || '';
  if (raw.startsWith('[') && raw.endsWith(']')) {
    try {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) raw = parsed.join('');
    } catch {}
  }
  // Strip inner spaces between Chinese tokens
  raw = raw.replace(/\s+/g, '');
  if (/[\u4e00-\u9fa5]/.test(raw)) {
    return raw.trim();
  }

  // Fallback to prompt if prompt contains Chinese
  if (/[\u4e00-\u9fa5]/.test(ex.prompt)) {
    return ex.prompt.replace(/^[AB][:：]\s*/gm, '').replace(/_{2,}/g, '').trim();
  }

  return raw;
};

// Helper to get pronounceable Chinese text for the exercise prompt
const getPromptAudioText = (ex?: Exercise | null): string => {
  if (!ex) return '';
  if (/[\u4e00-\u9fa5]/.test(ex.prompt)) {
    // Prompt has Chinese: strip blank underscores for clean reading
    return ex.prompt.replace(/_{2,}/g, '');
  }
  // English prompt: speak the complete target Chinese sentence
  return getFullTargetSentenceZh(ex);
};

// Global Distractor pool for building dynamic Word Banks without manual typing
const COMMON_DISTRACTOR_TOKENS = [
  '我', '你', '他', '她', '是', '不', '很', '好', '老师', '学生', 
  '中国', '美国', '吃', '喝', '茶', '水', '买', '多少钱', '块', 
  '去', '火车站', '想', '在', '有', '没有', '客气', '谢谢', '对不起', '大'
];

export const DuolingoExerciseModal: React.FC<DuolingoExerciseModalProps> = ({
  conceptId,
  targetDomain = 'general',
  mode = 'new',
  onClose,
  onSubmitAnswer,
  onRecordMistake,
  onCompleteConcept,
}) => {
  const [loading, setLoading] = useState(true);
  const [concept, setConcept] = useState<CurriculumConcept | null>(null);
  const [cards, setCards] = useState<TeachingCard[]>([]);
  const [exercises, setExercises] = useState<Exercise[]>([]);

  // Flow: For 'review' and 'remedial', jump straight into practice cards!
  // For 'new', show knowledge concept card first, then practice.
  const [phase, setPhase] = useState<'card' | 'practice'>(
    mode === 'review' || mode === 'remedial' ? 'practice' : 'card'
  );
  const [currentCardIndex, setCurrentCardIndex] = useState(0);
  const [currentExerciseIndex, setCurrentExerciseIndex] = useState(0);

  // Forced concept popup when answer is wrong in review/remedial mode, or user clicks "View Concept"
  const [showConceptExplainer, setShowConceptExplainer] = useState(false);
  const [forcedByMistake, setForcedByMistake] = useState(false);

  // Input states
  const [selectedOption, setSelectedOption] = useState<string>('');
  const [slotTokens, setSlotTokens] = useState<string[]>([]);
  const [wordBankTokens, setWordBankTokens] = useState<{ id: string; text: string }[]>([]);

  // Evaluation
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [gradingResult, setGradingResult] = useState<GradingResult | null>(null);

  // Character Radical Inspector Modal state (Image 1 feature)
  const [inspectedEntry, setInspectedEntry] = useState<CharacterEntry | null>(null);

  // Audio Pronunciation using audioFeedback utility
  const playAudio = (text: string) => {
    audioFeedback.speakChinese(text);
  };

  useEffect(() => {
    async function loadData() {
      try {
        const res = await fetch(`/api/v1/curriculum/concepts/${conceptId}`);
        if (res.ok) {
          const data = await res.json();
          setConcept(data.concept);
          setCards(data.cards || []);
          setExercises(data.exercises || []);
        }
      } catch (err) {
        console.error('Failed to load concept exercises:', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [conceptId]);

  const currentExercise = exercises[currentExerciseIndex];

  // Helper to initialize interactive word bank for the current exercise
  useEffect(() => {
    setSelectedOption('');
    setSlotTokens([]);
    setGradingResult(null);

    if (!currentExercise) return;

    // Check if exercise uses Word Bank (reorder, fill_blank, translate, or no options)
    const needsWordBank = 
      currentExercise.exerciseType === 'reorder' ||
      currentExercise.exerciseType === 'fill_blank' ||
      currentExercise.exerciseType === 'translate_to_zh' ||
      !currentExercise.options ||
      currentExercise.options.length === 0;

    if (needsWordBank) {
      let coreTokens: string[] = [];

      if (currentExercise.options && currentExercise.options.length > 0) {
        coreTokens = [...currentExercise.options];
      } else {
        // Derive tokens from target answer
        const rawAns = currentExercise.acceptedAnswers?.[0] || currentExercise.answer || '';
        // If JSON array
        if (rawAns.startsWith('[') && rawAns.endsWith(']')) {
          try {
            coreTokens = JSON.parse(rawAns);
          } catch {
            coreTokens = [rawAns];
          }
        } else {
          // Tokenize Chinese characters / words
          // If short word like "客气", keep it whole
          if (rawAns.length <= 3) {
            coreTokens = [rawAns];
          } else {
            // Split into 1-2 char chunks
            const chars = rawAns.split('');
            coreTokens = chars;
          }
        }

        // Add 2-3 random distractors from vocabulary focus or common pool
        const availableDistractors = (concept?.vocabularyFocus || [])
          .concat(COMMON_DISTRACTOR_TOKENS)
          .filter((t) => !coreTokens.includes(t) && t.length > 0);

        // Pick 2-3 distractors
        const picked = availableDistractors.slice(0, 3);
        coreTokens = [...coreTokens, ...picked];
      }

      // Shuffle tokens
      const shuffled = coreTokens
        .map((t, idx) => ({ id: `token-${t}-${idx}-${Math.random()}`, text: t }))
        .sort(() => Math.random() - 0.5);

      setWordBankTokens(shuffled);
    }
  }, [currentExerciseIndex, currentExercise, concept]);

  // Click word in word bank to add to slots (点什么发什么音)
  const handleBankTokenClick = (tokenId: string, text: string) => {
    if (gradingResult) return;
    audioFeedback.playPopSound();
    audioFeedback.speakChinese(text);
    setSlotTokens([...slotTokens, text]);
    setWordBankTokens(wordBankTokens.filter((t) => t.id !== tokenId));
  };

  // Click token in slot to return it to word bank (退回也点什么发什么音)
  const handleSlotTokenClick = (index: number, text: string) => {
    if (gradingResult) return;
    audioFeedback.playPopSound();
    audioFeedback.speakChinese(text);
    const newSlots = [...slotTokens];
    newSlots.splice(index, 1);
    setSlotTokens(newSlots);
    setWordBankTokens([...wordBankTokens, { id: `token-return-${Date.now()}-${Math.random()}`, text }]);
  };

  // Clear all slotted tokens
  const handleResetSlots = () => {
    if (gradingResult) return;
    audioFeedback.playPopSound();
    const returned = slotTokens.map((t) => ({ id: `token-reset-${Math.random()}`, text: t }));
    setWordBankTokens([...wordBankTokens, ...returned]);
    setSlotTokens([]);
  };

  // Click option card in MCQ
  const handleOptionClick = (opt: string) => {
    if (gradingResult) return;
    setSelectedOption(opt);
    audioFeedback.playPopSound();
    // 仅当选项为中文时才发音，英文选项点击时不发音
    if (/[\u4e00-\u9fa5]/.test(opt)) {
      audioFeedback.speakChinese(opt);
    }
  };

  // Inspect character radicals (Image 1 Feature)
  const handleInspectCharacter = (text: string) => {
    const entry = findCharacterBreakdown(text);
    if (entry) {
      setInspectedEntry(entry);
    }
  };

  // Submit Answer & Play Grading Sound & Pronounce Full Correct Sentence
  const handleSubmit = async () => {
    if (!currentExercise) return;
    let answerToSubmit = '';

    const isMultipleChoice = currentExercise.options && currentExercise.options.length > 0 && currentExercise.exerciseType !== 'reorder' && currentExercise.exerciseType !== 'fill_blank';

    if (isMultipleChoice) {
      answerToSubmit = selectedOption;
    } else {
      // From slotted tokens
      answerToSubmit = slotTokens.join('');
    }

    if (!answerToSubmit) return;

    setIsSubmitting(true);
    try {
      const result = await onSubmitAnswer(currentExercise.id, answerToSubmit);
      if (result) {
        setGradingResult(result);

        if (!result.passedGates) {
          if (onRecordMistake) {
            onRecordMistake(currentExercise.id, conceptId);
          }
          // For review and remedial modes: force open concept explainer on wrong answer!
          if (mode === 'review' || mode === 'remedial') {
            setForcedByMistake(true);
            setShowConceptExplainer(true);
          }
        }

        // 获取完整正确句子（保证完整朗读全句，而非单纯重复单一字词）
        const fullCorrectSentence = getFullTargetSentenceZh(currentExercise);

        // 成功发出成功提示音，失败发出失败提示音，然后再完整朗读正确答案的完整句子
        audioFeedback.playGradingFeedbackAndSentence(result.passedGates, fullCorrectSentence);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    audioFeedback.stopSpeech();
    onClose();
  };

  const handleNextExercise = () => {
    // 切换进入下一题时停止上一题的发音
    audioFeedback.stopSpeech();
    setGradingResult(null);
    if (currentExerciseIndex < exercises.length - 1) {
      setCurrentExerciseIndex(currentExerciseIndex + 1);
    } else {
      if (onCompleteConcept) {
        onCompleteConcept(conceptId);
      }
      handleClose();
    }
  };

  // Progress computation
  const totalSteps = cards.length + exercises.length;
  const currentStep = phase === 'card' ? currentCardIndex : cards.length + currentExerciseIndex;
  const progressPercent = totalSteps > 0 ? Math.round(((currentStep + 1) / totalSteps) * 100) : 0;

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
        <div className="bg-white rounded-3xl p-8 max-w-sm w-full text-center space-y-4 shadow-2xl border-2 border-zinc-950">
          <div className="w-12 h-12 border-4 border-zinc-950 border-t-emerald-500 rounded-full animate-spin mx-auto" />
          <h3 className="font-black text-lg text-zinc-950">Preparing Interactive Lesson...</h3>
          <p className="text-xs text-zinc-500 font-bold">Loading HelloChinese radical components & word bank</p>
        </div>
      </div>
    );
  }

  const activeCard = cards[currentCardIndex];

  // Helper to render Chinese sentence with clickable character radicals (Image 1 & 2 Feature)
  // 点什么发什么音，点击汉字朗读发音并查看偏旁
  const renderInteractiveChineseText = (text: string, className = "text-2xl font-black font-chinese text-zinc-950") => {
    // Break into characters and punctuation
    const chars = text.split(/([^\u4e00-\u9fa5]+)/).filter(Boolean);

    return (
      <div className={`flex items-center flex-wrap gap-1.5 ${className}`}>
        {chars.map((segment, idx) => {
          const isChinese = /[\u4e00-\u9fa5]/.test(segment);
          if (!isChinese) {
            return <span key={idx} className="text-zinc-500 font-medium">{segment}</span>;
          }

          // Check if this word or character has radical breakdown
          const breakdown = findCharacterBreakdown(segment);

          return (
            <span
              key={idx}
              onClick={(e) => {
                e.stopPropagation();
                // 点什么发什么音
                audioFeedback.playPopSound();
                audioFeedback.speakChinese(segment);
                if (breakdown) {
                  setInspectedEntry(breakdown);
                }
              }}
              className={`
                relative inline-block transition-all select-none
                ${breakdown ? 'border-b-2 border-dashed border-indigo-500 text-indigo-950 hover:bg-indigo-100/60 rounded px-1 cursor-pointer' : 'hover:bg-zinc-100 rounded px-1 cursor-pointer'}
              `}
              title={breakdown ? 'Listen & view radicals' : 'Listen'}
            >
              {segment}
            </span>
          );
        })}
      </div>
    );
  };

  const isCurrentExerciseMCQ = currentExercise?.options && currentExercise.options.length > 0 && currentExercise.exerciseType !== 'reorder' && currentExercise.exerciseType !== 'fill_blank';

  const isCheckReady = isCurrentExerciseMCQ ? Boolean(selectedOption) : slotTokens.length > 0;

  return (
    <div className="fixed inset-0 bg-white z-50 flex flex-col justify-between overflow-y-auto select-none">
      {/* 1. Header (HelloChinese Style Top Navigation) */}
      <header className="px-4 sm:px-8 py-3.5 border-b-2 border-zinc-200 flex items-center gap-4 max-w-3xl mx-auto w-full">
        <button
          onClick={handleClose}
          className="text-zinc-400 hover:text-zinc-800 p-1.5 rounded-xl transition-colors cursor-pointer"
          title="Exit"
        >
          <X className="w-5 h-5 stroke-[3]" />
        </button>

        {/* Clean Top Tag */}
        <div className="text-xs font-bold text-emerald-800 bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200">
          {phase === 'card' 
            ? (concept?.isCoreGrammar ? 'Grammar' : 'Vocabulary') 
            : 'Practice'}
        </div>

        {/* Progress Bar Container */}
        <div className="flex-1 bg-zinc-100 h-3 rounded-full overflow-hidden p-0.5 border border-zinc-200">
          <div
            className="bg-emerald-500 h-full rounded-full transition-all duration-300"
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        <div className="text-xs font-black uppercase text-zinc-500 tracking-wider">
          {currentStep + 1}/{totalSteps}
        </div>
      </header>

      {/* 2. Main Container */}
      <main className="flex-1 max-w-2xl mx-auto w-full p-4 sm:p-8 flex flex-col justify-center">
        {phase === 'card' && activeCard ? (
          /* ======================================================== */
          /* Teaching Cards Phase (HelloChinese Teaching Card)         */
          /* ======================================================== */
          <div className="space-y-6">
            <div className="flex items-center gap-4">
              <PandaMascot mood="idle" size={72} />
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-zinc-500">
                    Card {currentCardIndex + 1} / {cards.length}
                  </span>
                </div>

                {/* Pronunciation & Interactive Chinese Text */}
                <div className="flex items-center gap-3 pt-1">
                  <button
                    onClick={() => playAudio(activeCard.promptZh || concept?.titleZh || '')}
                    className="p-2.5 rounded-full bg-emerald-500 hover:bg-emerald-400 text-white shadow-[0_3px_0_#059669] transition-all cursor-pointer"
                    title="Play"
                  >
                    <Volume2 className="w-5 h-5 stroke-[2.5]" />
                  </button>
                  {renderInteractiveChineseText(
                    activeCard.promptZh || concept?.titleZh || '', 
                    'text-3xl font-black font-chinese text-zinc-950'
                  )}
                </div>

                {activeCard.pinyin && (
                  <p className="text-sm font-mono font-black text-emerald-700 mt-0.5">
                    {activeCard.pinyin}
                  </p>
                )}
              </div>
            </div>

            {/* Explanation box */}
            <div className="bg-zinc-50 rounded-3xl p-6 border-2 border-zinc-900 shadow-[0_4px_0_#18181b] space-y-4">
              <div className="text-sm font-bold text-zinc-800 leading-relaxed">
                {activeCard.explanationEn}
              </div>

              {(() => {
                const tailored = getTailoredExample(concept || undefined, activeCard, targetDomain);
                return (
                  <div className="bg-emerald-50 rounded-2xl p-4 border-2 border-emerald-500 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-black uppercase text-emerald-800 flex items-center gap-1.5">
                        <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                        {tailored.scenarioTag}
                      </span>
                      <button
                        onClick={() => playAudio(tailored.zh)}
                        className="text-emerald-700 hover:text-emerald-900 flex items-center gap-1 text-xs font-bold cursor-pointer"
                        title="Play tailored example"
                      >
                        <Volume2 className="w-3.5 h-3.5" />
                        Listen
                      </button>
                    </div>

                    {renderInteractiveChineseText(tailored.zh, 'text-xl font-black font-chinese text-zinc-950')}

                    {tailored.pinyin && (
                      <div className="text-xs font-mono text-emerald-700 font-bold">
                        {tailored.pinyin}
                      </div>
                    )}
                    <div className="text-xs font-bold text-zinc-600 italic">
                      {tailored.en}
                    </div>
                  </div>
                );
              })()}
            </div>

            {/* Card Navigation */}
            <div className="flex justify-end pt-2">
              <button
                id="btn-card-next"
                onClick={() => {
                  if (currentCardIndex < cards.length - 1) {
                    setCurrentCardIndex(currentCardIndex + 1);
                  } else {
                    setPhase('practice');
                  }
                }}
                className="px-8 py-3.5 rounded-2xl bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-black text-sm uppercase tracking-wide border-2 border-zinc-950 shadow-[0_4px_0_#15803d] flex items-center gap-2 active:translate-y-1 active:shadow-none transition-all cursor-pointer"
              >
                <span>{currentCardIndex < cards.length - 1 ? 'NEXT' : 'CONTINUE'}</span>
                <ArrowRight className="w-4 h-4 stroke-[3]" />
              </button>
            </div>
          </div>
        ) : (
          /* ======================================================== */
          /* Practice Phase (Zero-typing Word Bank & Visual Cards)     */
          /* ======================================================== */
          currentExercise && (
            <div className="space-y-6">
              {/* Exercise Header & Instruction with View Concept link */}
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <h3 className="text-lg font-black text-zinc-950">
                    {currentExercise.instruction}
                  </h3>
                  <button
                    id="btn-view-concept"
                    onClick={() => {
                      setForcedByMistake(false);
                      setShowConceptExplainer(true);
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-50 hover:bg-emerald-100 text-emerald-800 text-xs font-bold border border-emerald-300 transition-colors shrink-0 shadow-xs"
                    title="View Concept Explanation"
                  >
                    <BookOpen className="w-3.5 h-3.5" />
                    <span>View Concept</span>
                  </button>
                </div>

                {/* Prompt Card with Audio Speaker & Clickable Radicals */}
                <div className="bg-zinc-50 rounded-2xl p-4 border-2 border-zinc-200 flex items-center gap-4">
                  {/* Speaker Button */}
                  <button
                    onClick={() => audioFeedback.speakChinese(getPromptAudioText(currentExercise))}
                    className="p-3 rounded-2xl bg-emerald-500 hover:bg-emerald-400 text-white shadow-[0_3px_0_#059669] shrink-0 cursor-pointer"
                    title="Play"
                  >
                    <Volume2 className="w-5 h-5 stroke-[2.5]" />
                  </button>

                  <div className="space-y-1">
                    {currentExercise.promptPinyin && (
                      <div className="text-xs font-mono font-bold text-emerald-600">
                        {currentExercise.promptPinyin}
                      </div>
                    )}
                    {renderInteractiveChineseText(currentExercise.prompt, 'text-2xl font-black font-chinese text-zinc-950')}
                  </div>
                </div>
              </div>

              {/* Interaction Modes (100% Click-based, No Manual Typing!) */}
              {!gradingResult && (
                <div className="space-y-5 pt-2">
                  {/* Mode A: Visual Cards / Multiple Choice (Matching Image 1) */}
                  {isCurrentExerciseMCQ && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {currentExercise.options?.map((opt) => {
                        const isSelected = selectedOption === opt;
                        // Give visual icon hints based on common vocab
                        let icon = '📖';
                        if (opt.includes('Teacher') || opt.includes('老师')) icon = '👩‍🏫';
                        else if (opt.includes('Student') || opt.includes('学生')) icon = '🧑‍🎓';
                        else if (opt.includes('America') || opt.includes('美国')) icon = '🗽';
                        else if (opt.includes('China') || opt.includes('中国')) icon = '🏮';
                        else if (opt.includes('Tea') || opt.includes('茶')) icon = '🍵';
                        else if (opt.includes('Water') || opt.includes('水')) icon = '💧';
                        else if (opt.includes('Eat') || opt.includes('吃')) icon = '🥢';
                        else if (opt.includes('Drink') || opt.includes('喝')) icon = '🥤';
                        else if (opt.includes('Hello') || opt.includes('你好')) icon = '👋';

                        return (
                          <button
                            key={opt}
                            id={`btn-opt-${opt}`}
                            onClick={() => handleOptionClick(opt)}
                            className={`p-4 rounded-2xl border-2 text-left font-black transition-all flex items-center justify-between cursor-pointer ${
                              isSelected
                                ? 'bg-emerald-50 border-emerald-600 text-emerald-950 shadow-[0_4px_0_#059669] -translate-y-0.5'
                                : 'bg-white border-zinc-300 text-zinc-900 hover:bg-zinc-50 shadow-[0_4px_0_#d4d4d8] active:translate-y-1 active:shadow-none'
                            }`}
                          >
                            <div className="flex items-center gap-3">
                              <span className="text-2xl">{icon}</span>
                              <span className="font-chinese text-base">{opt}</span>
                            </div>
                            <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                              isSelected ? 'border-emerald-600 bg-emerald-600 text-white' : 'border-zinc-300'
                            }`}>
                              {isSelected && <Check className="w-3 h-3 stroke-[3]" />}
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  )}

                  {/* Mode B: Word Bank Pill Tap-to-Fill (Matching Image 2 Complete the Translation) */}
                  {!isCurrentExerciseMCQ && (
                    <div className="space-y-4">
                      {/* Target Answer Slot (Dashed Drop Zone) */}
                      <div className="min-h-[84px] p-3.5 rounded-2xl border-2 border-dashed border-emerald-400 bg-emerald-50/40 flex flex-wrap gap-2.5 items-center justify-start">
                        {slotTokens.length === 0 ? (
                          <span className="text-sm font-medium text-zinc-400 pl-2">
                            Tap words below to form your sentence...
                          </span>
                        ) : (
                          slotTokens.map((tok, idx) => (
                            <button
                              key={`slot-${tok}-${idx}`}
                              onClick={() => handleSlotTokenClick(idx, tok)}
                              className="px-4 py-2.5 rounded-xl bg-zinc-950 text-white font-chinese text-lg font-black border-2 border-zinc-950 shadow-[0_3px_0_#27272a] active:translate-y-0.5 cursor-pointer hover:bg-zinc-800 transition-transform flex items-center gap-1"
                              title="Tap to remove"
                            >
                              <span>{tok}</span>
                            </button>
                          ))
                        )}
                      </div>

                      {/* Controls (Reset) */}
                      {slotTokens.length > 0 && (
                        <div className="flex justify-end">
                          <button
                            onClick={handleResetSlots}
                            className="text-xs font-bold text-zinc-500 hover:text-zinc-800 flex items-center gap-1 cursor-pointer"
                          >
                            <RotateCcw className="w-3 h-3" />
                            <span>Reset</span>
                          </button>
                        </div>
                      )}

                      {/* Available Word Bank (Chunky 3D Pills like HelloChinese) */}
                      <div className="flex flex-wrap gap-2.5 pt-1">
                        {wordBankTokens.map((token) => (
                          <button
                            key={token.id}
                            onClick={() => handleBankTokenClick(token.id, token.text)}
                            className="px-4 py-2.5 rounded-xl bg-white border-2 border-zinc-300 hover:border-zinc-900 font-chinese text-lg font-black text-zinc-900 shadow-[0_3px_0_#d4d4d8] active:translate-y-1 active:shadow-none transition-all cursor-pointer hover:scale-105"
                          >
                            {token.text}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        )}
      </main>

      {/* 3. Bottom Drawer for Evaluation Feedback & Big CHECK Button (Image 1 & 2 Style) */}
      <footer
        className={`px-4 sm:px-8 py-5 border-t-2 transition-colors ${
          gradingResult
            ? gradingResult.passedGates
              ? 'bg-emerald-100 border-emerald-300 text-emerald-950'
              : 'bg-rose-100 border-rose-300 text-rose-950'
            : 'bg-white border-zinc-200'
        }`}
      >
        <div className="max-w-2xl mx-auto flex flex-col sm:flex-row sm:items-center justify-between gap-5">
          {gradingResult ? (
            <div className="space-y-1.5 flex-1">
              <div className="flex items-center gap-2">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center font-black ${
                  gradingResult.passedGates ? 'bg-emerald-600 text-white' : 'bg-rose-600 text-white'
                }`}>
                  {gradingResult.passedGates ? <Check className="w-4 h-4 stroke-[3]" /> : <X className="w-4 h-4 stroke-[3]" />}
                </div>
                <span className={`font-black text-base ${gradingResult.passedGates ? 'text-emerald-900' : 'text-rose-900'}`}>
                  {gradingResult.passedGates ? 'Nice catch!' : 'Correct solution:'}
                </span>
              </div>

              {/* Complete target sentence pronunciation */}
              {currentExercise && (
                <div className="flex items-center gap-2 pt-0.5">
                  <span className="font-chinese text-base font-black text-slate-900">
                    {getFullTargetSentenceZh(currentExercise)}
                  </span>
                  <button
                    onClick={() => audioFeedback.speakChinese(getFullTargetSentenceZh(currentExercise))}
                    className="p-1.5 rounded-full bg-emerald-200/70 hover:bg-emerald-300 text-emerald-900 cursor-pointer shadow-xs transition-colors"
                    title="Play Audio"
                  >
                    <Volume2 className="w-4 h-4" />
                  </button>
                </div>
              )}

              <p className="text-xs font-medium leading-relaxed text-slate-700 bg-white/70 p-2.5 rounded-xl border border-emerald-200/60 max-w-lg">
                {gradingResult.feedback}
              </p>
            </div>
          ) : null}

          {/* Action Button (Big CHECK / CONTINUE button matching Duolingo & HelloChinese) */}
          {gradingResult ? (
            <button
              id="btn-duo-continue"
              onClick={handleNextExercise}
              className={`w-full sm:w-auto px-10 py-4 rounded-2xl font-black text-base uppercase tracking-wider border-2 border-slate-900 transition-all shrink-0 cursor-pointer ${
                gradingResult.passedGates
                  ? 'bg-emerald-500 hover:bg-emerald-400 text-white shadow-[0_5px_0_#059669]'
                  : 'bg-rose-600 hover:bg-rose-500 text-white shadow-[0_5px_0_#9f1239]'
              } active:translate-y-1 active:shadow-none`}
            >
              CONTINUE
            </button>
          ) : (
            <button
              id="btn-duo-check"
              disabled={isSubmitting || !isCheckReady}
              onClick={handleSubmit}
              className={`w-full sm:w-auto px-12 py-4 rounded-2xl font-black text-base uppercase tracking-wider transition-all cursor-pointer select-none ${
                isCheckReady && !isSubmitting
                  ? 'bg-emerald-500 hover:bg-emerald-400 text-white border-2 border-emerald-700 shadow-[0_5px_0_#059669] active:translate-y-1 active:shadow-none'
                  : 'bg-zinc-200 text-zinc-400 border-2 border-zinc-300 cursor-not-allowed'
              }`}
            >
              {isSubmitting ? 'CHECKING...' : 'CHECK'}
            </button>
          )}
        </div>
      </footer>

      {/* Forced / Optional Concept Explainer Modal (User requirement: review/remedial wrong answer forced popup) */}
      {showConceptExplainer && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 z-60 animate-in fade-in duration-200">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 sm:p-8 space-y-5 border-2 border-zinc-950 shadow-2xl relative">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="p-2 bg-emerald-50 text-emerald-700 rounded-xl border border-emerald-200">
                  <BookOpen className="w-5 h-5" />
                </span>
                <div>
                  <div className="text-[11px] font-black uppercase text-emerald-700">
                    {forcedByMistake ? 'Review Required Concept' : 'Concept Explanation'}
                  </div>
                  <h3 className="text-lg font-black text-zinc-950 font-chinese">
                    {concept?.titleZh || 'Concept'}
                  </h3>
                </div>
              </div>
              <button
                onClick={() => {
                  setShowConceptExplainer(false);
                  setForcedByMistake(false);
                }}
                className="p-1 text-zinc-400 hover:text-zinc-900 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {forcedByMistake && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-2xl text-xs font-bold text-amber-900 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                <span>Let's review this concept first so you can master it!</span>
              </div>
            )}

            <div className="space-y-3 bg-zinc-50 p-4 rounded-2xl border border-zinc-200 text-sm">
              <div className="font-bold text-zinc-800">
                {concept?.titleEn}
              </div>
              <div className="text-xs text-zinc-600 leading-relaxed">
                {concept?.communicativeGoal}
              </div>
              {concept?.grammarFocus && concept.grammarFocus.length > 0 && (
                <div className="pt-2 border-t border-zinc-200 space-y-1">
                  <span className="text-[11px] font-extrabold uppercase text-zinc-400 block">Focus Rules</span>
                  {concept.grammarFocus.map((gf, idx) => (
                    <div key={idx} className="text-xs font-mono font-bold text-emerald-800 bg-emerald-50/70 px-2.5 py-1 rounded-lg">
                      • {gf}
                    </div>
                  ))}
                </div>
              )}

              {/* Teaching Card sample */}
              {cards[0] && (
                <div className="mt-3 p-3 bg-white rounded-xl border border-zinc-200 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-zinc-400">Example</span>
                    <button
                      onClick={() => audioFeedback.speakChinese(cards[0].exampleZh)}
                      className="text-xs font-bold text-emerald-700 flex items-center gap-1 hover:underline"
                    >
                      <Volume2 className="w-3.5 h-3.5" /> Play
                    </button>
                  </div>
                  <div className="font-chinese text-base font-black text-zinc-900">
                    {cards[0].exampleZh}
                  </div>
                  <div className="text-xs font-mono text-emerald-600 font-bold">
                    {cards[0].examplePinyin}
                  </div>
                  <div className="text-xs text-zinc-500 italic">
                    {cards[0].exampleEn}
                  </div>
                </div>
              )}
            </div>

            <button
              id="btn-close-concept-explainer"
              onClick={() => {
                setShowConceptExplainer(false);
                setForcedByMistake(false);
              }}
              className="w-full py-3.5 rounded-2xl bg-emerald-500 hover:bg-emerald-400 text-white font-black text-sm uppercase tracking-wider border-2 border-emerald-700 shadow-[0_4px_0_#059669] active:translate-y-1 active:shadow-none transition-all cursor-pointer"
            >
              I GOT IT, CONTINUE
            </button>
          </div>
        </div>
      )}

      {/* 4. Character Radical Decomposition Popover Modal (Image 1 Feature) */}
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
