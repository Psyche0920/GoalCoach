import React, { useState, useEffect } from 'react';
import { 
  X, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  ChevronRight, 
  BookOpen, 
  Sparkles, 
  HelpCircle,
  Clock,
  RotateCcw,
  Check
} from 'lucide-react';
import { CurriculumConcept, TeachingCard, Exercise, GradingResult } from '../types.ts';

interface StudySessionModalProps {
  conceptId: string;
  onClose: () => void;
  onSubmitAnswer: (exerciseId: string, answer: string) => Promise<GradingResult | null>;
}

export const StudySessionModal: React.FC<StudySessionModalProps> = ({
  conceptId,
  onClose,
  onSubmitAnswer,
}) => {
  const [loading, setLoading] = useState(true);
  const [concept, setConcept] = useState<CurriculumConcept | null>(null);
  const [cards, setCards] = useState<TeachingCard[]>([]);
  const [exercises, setExercises] = useState<Exercise[]>([]);
  
  // Step in session: 0 = teaching cards overview, 1+ = exercise index
  const [activeTab, setActiveTab] = useState<'card' | 'practice'>('card');
  const [currentCardIndex, setCurrentCardIndex] = useState(0);
  const [currentExerciseIndex, setCurrentExerciseIndex] = useState(0);

  // User input states for exercise
  const [selectedOption, setSelectedOption] = useState<string>('');
  const [textInput, setTextInput] = useState<string>('');
  const [reorderTokens, setReorderTokens] = useState<string[]>([]);
  const [availableTokens, setAvailableTokens] = useState<string[]>([]);

  // Grading state
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [gradingResult, setGradingResult] = useState<GradingResult | null>(null);

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
        console.error('Failed to load concept data:', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [conceptId]);

  const currentExercise = exercises[currentExerciseIndex];

  // Initialize interactive exercise state
  useEffect(() => {
    setSelectedOption('');
    setTextInput('');
    setGradingResult(null);

    if (currentExercise && currentExercise.exerciseType === 'reorder') {
      const tokens = currentExercise.options || currentExercise.prompt.split('/').map((s) => s.trim());
      setAvailableTokens([...tokens]);
      setReorderTokens([]);
    }
  }, [currentExerciseIndex, currentExercise]);

  const handleAddToken = (token: string, index: number) => {
    setReorderTokens([...reorderTokens, token]);
    const newAvail = [...availableTokens];
    newAvail.splice(index, 1);
    setAvailableTokens(newAvail);
  };

  const handleRemoveToken = (token: string, index: number) => {
    setAvailableTokens([...availableTokens, token]);
    const newReorder = [...reorderTokens];
    newReorder.splice(index, 1);
    setReorderTokens(newReorder);
  };

  const handleSubmit = async () => {
    if (!currentExercise) return;
    let answerToSubmit = '';

    if (currentExercise.exerciseType === 'reorder') {
      answerToSubmit = reorderTokens.join('');
    } else if (currentExercise.options && currentExercise.options.length > 0) {
      answerToSubmit = selectedOption;
    } else {
      answerToSubmit = textInput.trim();
    }

    if (!answerToSubmit) return;

    setIsSubmitting(true);
    try {
      const result = await onSubmitAnswer(currentExercise.id, answerToSubmit);
      if (result) {
        setGradingResult(result);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleNextExercise = () => {
    setGradingResult(null);
    if (currentExerciseIndex < exercises.length - 1) {
      setCurrentExerciseIndex(currentExerciseIndex + 1);
    } else {
      // Completed all exercises for this concept
      onClose();
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/40 backdrop-blur-xs p-4">
        <div className="bg-white rounded-2xl p-8 max-w-md w-full text-center shadow-lg border border-stone-200">
          <div className="w-8 h-8 border-3 border-amber-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm font-medium text-stone-600">Loading learning session...</p>
        </div>
      </div>
    );
  }

  const activeCard = cards[currentCardIndex];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/50 backdrop-blur-xs p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl border border-stone-200 max-w-2xl w-full shadow-2xl overflow-hidden my-8">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-stone-100 bg-stone-50/50">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs px-2 py-0.5 bg-amber-100 text-amber-800 rounded font-bold uppercase">
                {concept?.conceptId}
              </span>
              <span className="font-chinese text-base font-bold text-stone-900">
                {concept?.titleZh}
              </span>
            </div>
            <p className="text-xs text-stone-500 mt-0.5">
              {concept?.titleEn} — {concept?.communicativeGoal}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-stone-400 hover:text-stone-700 hover:bg-stone-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Mode Switcher: Teaching Card vs Interactive Practice */}
        <div className="flex border-b border-stone-100 px-6 pt-2 bg-stone-50/30 gap-4 text-xs font-semibold">
          <button
            onClick={() => setActiveTab('card')}
            className={`pb-2.5 flex items-center gap-1.5 transition-all border-b-2 ${
              activeTab === 'card'
                ? 'border-amber-600 text-amber-700'
                : 'border-transparent text-stone-500 hover:text-stone-800'
            }`}
          >
            <BookOpen className="w-4 h-4" />
            <span>Teaching Guide ({cards.length} Cards)</span>
          </button>
          <button
            onClick={() => setActiveTab('practice')}
            className={`pb-2.5 flex items-center gap-1.5 transition-all border-b-2 ${
              activeTab === 'practice'
                ? 'border-amber-600 text-amber-700'
                : 'border-transparent text-stone-500 hover:text-stone-800'
            }`}
          >
            <Sparkles className="w-4 h-4" />
            <span>Interactive Exercises ({exercises.length} Items)</span>
          </button>
        </div>

        {/* Body Content */}
        <div className="p-6 space-y-6">
          {activeTab === 'card' ? (
            /* Teaching Cards View */
            <div className="space-y-6">
              {activeCard ? (
                <div className="bg-stone-50 rounded-2xl p-6 border border-stone-200 space-y-5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-amber-700 uppercase tracking-wider bg-amber-100/60 px-2.5 py-0.5 rounded-full">
                      Card {activeCard.cardOrder} / {cards.length}: {activeCard.cardType}
                    </span>
                  </div>

                  {activeCard.promptZh && (
                    <div className="text-center py-2">
                      <div className="text-xs text-amber-700 font-mono tracking-widest">
                        {activeCard.pinyin}
                      </div>
                      <div className="font-chinese text-3xl font-bold text-stone-900 mt-1">
                        {activeCard.promptZh}
                      </div>
                      {activeCard.meaningEn && (
                        <div className="text-sm text-stone-600 mt-1 font-medium">
                          “{activeCard.meaningEn}”
                        </div>
                      )}
                    </div>
                  )}

                  <div className="bg-white rounded-xl p-4 border border-stone-200 space-y-2 text-xs">
                    <h4 className="font-bold text-stone-800">Grammar & Usage Rule:</h4>
                    <p className="text-stone-600 leading-relaxed">
                      {activeCard.explanationEn}
                    </p>
                  </div>

                  {activeCard.exampleZh && (
                    <div className="bg-amber-50/50 rounded-xl p-4 border border-amber-200/60 space-y-1">
                      <span className="text-[11px] font-bold text-amber-800 uppercase tracking-wider block">
                        Example in Context:
                      </span>
                      {activeCard.examplePinyin && (
                        <div className="text-xs text-amber-700 font-mono">
                          {activeCard.examplePinyin}
                        </div>
                      )}
                      <div className="font-chinese text-base font-bold text-stone-900">
                        {activeCard.exampleZh}
                      </div>
                      <div className="text-xs text-stone-600 italic">
                        {activeCard.exampleEn}
                      </div>
                    </div>
                  )}

                  {/* Card navigation buttons */}
                  <div className="flex items-center justify-between pt-2">
                    <button
                      disabled={currentCardIndex === 0}
                      onClick={() => setCurrentCardIndex(currentCardIndex - 1)}
                      className="text-xs px-3 py-1.5 border border-stone-200 rounded-lg text-stone-600 disabled:opacity-30"
                    >
                      Previous Card
                    </button>
                    {currentCardIndex < cards.length - 1 ? (
                      <button
                        onClick={() => setCurrentCardIndex(currentCardIndex + 1)}
                        className="text-xs px-3.5 py-1.5 bg-amber-600 text-white rounded-lg font-semibold hover:bg-amber-700"
                      >
                        Next Card
                      </button>
                    ) : (
                      <button
                        onClick={() => setActiveTab('practice')}
                        className="text-xs px-4 py-1.5 bg-emerald-600 text-white rounded-lg font-semibold hover:bg-emerald-700 flex items-center gap-1.5 shadow-xs"
                      >
                        <span>Start Exercises</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              ) : (
                <p className="text-sm text-stone-500 text-center py-6">No teaching cards for this concept.</p>
              )}
            </div>
          ) : (
            /* Practice Exercise View */
            <div className="space-y-6">
              {currentExercise ? (
                <div className="space-y-6">
                  {/* Exercise Tracker */}
                  <div className="flex items-center justify-between text-xs text-stone-500 border-b border-stone-100 pb-3">
                    <span className="font-semibold text-stone-700">
                      Exercise {currentExerciseIndex + 1} of {exercises.length}
                    </span>
                    <span className="capitalize px-2 py-0.5 bg-stone-100 rounded text-stone-600 font-medium">
                      {currentExercise.exerciseType.replace(/_/g, ' ')}
                    </span>
                  </div>

                  {/* Instruction & Prompt */}
                  <div className="bg-stone-50 rounded-2xl p-5 border border-stone-200 space-y-2">
                    <span className="text-xs font-bold text-amber-700 uppercase tracking-wider block">
                      {currentExercise.instruction}
                    </span>
                    {currentExercise.promptPinyin && (
                      <div className="text-xs font-mono text-stone-500">
                        {currentExercise.promptPinyin}
                      </div>
                    )}
                    <div className="font-chinese text-xl font-bold text-stone-900">
                      {currentExercise.prompt}
                    </div>
                  </div>

                  {/* Exercise Input Mode */}
                  {!gradingResult && (
                    <div className="space-y-4">
                      {/* MCQ with options */}
                      {currentExercise.options && currentExercise.options.length > 0 && currentExercise.exerciseType !== 'reorder' && (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                          {currentExercise.options.map((opt) => (
                            <button
                              key={opt}
                              id={`option-${opt}`}
                              onClick={() => setSelectedOption(opt)}
                              className={`p-3 rounded-xl border text-sm font-medium text-left transition-all ${
                                selectedOption === opt
                                  ? 'border-amber-600 bg-amber-50 text-amber-900 ring-2 ring-amber-600/20 font-bold'
                                  : 'border-stone-200 bg-white text-stone-800 hover:bg-stone-50'
                              }`}
                            >
                              <span className="font-chinese">{opt}</span>
                            </button>
                          ))}
                        </div>
                      )}

                      {/* Interactive Sentence Reordering */}
                      {currentExercise.exerciseType === 'reorder' && (
                        <div className="space-y-3">
                          <div className="min-h-[50px] p-3 rounded-xl border-2 border-dashed border-stone-300 bg-stone-50 flex flex-wrap gap-2 items-center">
                            {reorderTokens.length === 0 ? (
                              <span className="text-xs text-stone-400">Click tokens below in correct order...</span>
                            ) : (
                              reorderTokens.map((t, idx) => (
                                <button
                                  key={`${t}-${idx}`}
                                  onClick={() => handleRemoveToken(t, idx)}
                                  className="px-3 py-1.5 rounded-lg bg-amber-600 text-white font-chinese text-sm font-bold shadow-xs hover:bg-amber-700 transition-all flex items-center gap-1"
                                >
                                  <span>{t}</span>
                                  <span className="text-[10px] opacity-70">×</span>
                                </button>
                              ))
                            )}
                          </div>

                          <div className="flex flex-wrap gap-2 pt-1">
                            {availableTokens.map((t, idx) => (
                              <button
                                key={`${t}-${idx}`}
                                onClick={() => handleAddToken(t, idx)}
                                className="px-3 py-1.5 rounded-lg border border-stone-300 bg-white font-chinese text-sm font-semibold text-stone-800 hover:border-amber-500 hover:bg-amber-50 shadow-xs transition-all"
                              >
                                {t}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Free Text / Fill Blank Input */}
                      {(!currentExercise.options || currentExercise.options.length === 0) && currentExercise.exerciseType !== 'reorder' && (
                        <div>
                          <input
                            id="input-exercise-answer"
                            type="text"
                            placeholder="Type your answer in Chinese or English..."
                            value={textInput}
                            onChange={(e) => setTextInput(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') handleSubmit();
                            }}
                            className="w-full text-base font-chinese border border-stone-300 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-amber-500"
                          />
                        </div>
                      )}

                      {/* Submit Button */}
                      <div className="flex justify-end pt-2">
                        <button
                          id="btn-submit-answer"
                          disabled={
                            isSubmitting ||
                            (currentExercise.exerciseType === 'reorder'
                              ? reorderTokens.length === 0
                              : currentExercise.options && currentExercise.options.length > 0
                              ? !selectedOption
                              : !textInput.trim())
                          }
                          onClick={handleSubmit}
                          className="px-5 py-2 rounded-xl bg-amber-600 text-white font-semibold text-xs tracking-wide uppercase hover:bg-amber-700 disabled:opacity-40 transition-all shadow-xs"
                        >
                          {isSubmitting ? 'Evaluating...' : 'Submit Answer'}
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Structured Rubric Evaluation Result */}
                  {gradingResult && (
                    <div className="space-y-4 pt-2 border-t border-stone-100">
                      <div
                        className={`p-4 rounded-xl border flex items-start gap-3 ${
                          gradingResult.passedGates
                            ? 'bg-emerald-50/70 border-emerald-200 text-emerald-900'
                            : 'bg-rose-50/70 border-rose-200 text-rose-900'
                        }`}
                      >
                        <div className="mt-0.5">
                          {gradingResult.passedGates ? (
                            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                          ) : (
                            <XCircle className="w-5 h-5 text-rose-600" />
                          )}
                        </div>
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold uppercase tracking-wider">
                              {gradingResult.passedGates ? 'Passed Rubric Gates' : 'Requires Adjustment'}
                            </span>
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/80 border border-current font-mono">
                              Grader {gradingResult.graderVersion}
                            </span>
                          </div>
                          <p className="text-xs font-medium leading-relaxed">
                            {gradingResult.feedback}
                          </p>
                        </div>
                      </div>

                      {/* Rubric Score Bars */}
                      <div className="bg-stone-50 rounded-xl p-4 border border-stone-200 space-y-2.5">
                        <span className="text-xs font-bold text-stone-700 block">
                          Multi-Dimensional Rubric Scores:
                        </span>

                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                          <div className="space-y-1">
                            <div className="flex justify-between text-[11px] text-stone-600">
                              <span>Grammar Correctness</span>
                              <span className="font-bold">
                                {Math.round(gradingResult.scores.grammaticalCorrectness * 100)}%
                              </span>
                            </div>
                            <div className="h-1.5 bg-stone-200 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-emerald-500 rounded-full"
                                style={{
                                  width: `${Math.round(gradingResult.scores.grammaticalCorrectness * 100)}%`,
                                }}
                              />
                            </div>
                          </div>

                          <div className="space-y-1">
                            <div className="flex justify-between text-[11px] text-stone-600">
                              <span>Semantic Precision</span>
                              <span className="font-bold">
                                {Math.round(gradingResult.scores.semanticPrecision * 100)}%
                              </span>
                            </div>
                            <div className="h-1.5 bg-stone-200 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-sky-500 rounded-full"
                                style={{
                                  width: `${Math.round(gradingResult.scores.semanticPrecision * 100)}%`,
                                }}
                              />
                            </div>
                          </div>

                          <div className="space-y-1">
                            <div className="flex justify-between text-[11px] text-stone-600">
                              <span>Pragmatics</span>
                              <span className="font-bold">
                                {Math.round(gradingResult.scores.pragmaticAppropriateness * 100)}%
                              </span>
                            </div>
                            <div className="h-1.5 bg-stone-200 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-amber-500 rounded-full"
                                style={{
                                  width: `${Math.round(gradingResult.scores.pragmaticAppropriateness * 100)}%`,
                                }}
                              />
                            </div>
                          </div>
                        </div>

                        {gradingResult.detectedErrors.length > 0 && (
                          <div className="mt-2 pt-2 border-t border-stone-200/80 flex items-center gap-2">
                            <span className="text-[11px] font-bold text-rose-700 flex items-center gap-1">
                              <AlertTriangle className="w-3 h-3" />
                              Errors Cataloged:
                            </span>
                            {gradingResult.detectedErrors.map((code) => (
                              <span
                                key={code}
                                className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-rose-100 text-rose-800 border border-rose-200"
                              >
                                {code}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Next Exercise button */}
                      <div className="flex justify-end pt-2">
                        <button
                          id="btn-next-exercise"
                          onClick={handleNextExercise}
                          className="flex items-center gap-1 px-5 py-2 bg-stone-900 hover:bg-stone-800 text-white rounded-xl text-xs font-bold transition-all shadow-xs"
                        >
                          <span>{currentExerciseIndex < exercises.length - 1 ? 'Next Exercise' : 'Finish Session'}</span>
                          <ChevronRight className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-sm text-stone-500 text-center py-6">No exercises found for this concept.</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
