import React, { useState, useRef, useEffect } from 'react';
import { 
  Volume2, 
  Mic, 
  Square, 
  Check, 
  ArrowRight, 
  Sparkles, 
  RotateCcw, 
  BookOpen, 
  HelpCircle, 
  Award, 
  X,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import { PinyinUnit, PinyinFlashcard } from '../data/pinyinData.ts';
import { CurriculumConcept, LearnerState } from '../types.ts';
import { extractLearnedVocabPool, matchLearnedVocab, LearnedVocabItem } from '../utils/pinyinVocabMatcher.ts';
import { playMandarinAudio } from '../utils/pinyinAudio.ts';
import { audioFeedback } from '../utils/audioFeedback.ts';

interface PinyinUnitPracticeViewProps {
  unit: PinyinUnit;
  learnerState: LearnerState | null;
  concepts: CurriculumConcept[];
  onCompleteUnit: (score: number) => void;
}

export const PinyinUnitPracticeView: React.FC<PinyinUnitPracticeViewProps> = ({
  unit,
  learnerState,
  concepts,
  onCompleteUnit,
}) => {
  const [practiceMode, setPracticeMode] = useState<'flashcards' | 'quiz'>('flashcards');

  // Flashcards state
  const [cardIndex, setCardIndex] = useState(0);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recordedAudioUrl, setRecordedAudioUrl] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  // Quiz state
  const [quizIndex, setQuizIndex] = useState(0);
  const [selectedQuizOption, setSelectedQuizOption] = useState<string | null>(null);
  const [isQuizSubmitted, setIsQuizSubmitted] = useState(false);
  const [quizScore, setQuizScore] = useState(0);
  const [isQuizFinished, setIsQuizFinished] = useState(false);

  // Extract learner's dynamic real-time vocabulary pool
  const learnedVocabPool = extractLearnedVocabPool(learnerState, concepts);

  const currentFlashcard = unit.flashcards[cardIndex] || unit.flashcards[0];

  // Dynamically match learned vocabulary for the current flashcard
  const matchedVocab: LearnedVocabItem | null = (() => {
    if (!currentFlashcard) return null;
    return matchLearnedVocab(
      {
        targetPinyin: currentFlashcard.targetPinyin,
        sandhiRuleId: unit.unitNumber === 5 ? 'sandhi' : undefined,
      },
      learnedVocabPool
    );
  })();

  // Reset audio & recording on card change
  useEffect(() => {
    setRecordedAudioUrl(null);
    setIsRecording(false);
  }, [cardIndex, unit.id]);

  // Audio playback handler
  const handlePlayAudio = (target: string, slow = false) => {
    setIsPlayingAudio(true);
    playMandarinAudio(target, {
      rate: slow ? 0.68 : 0.88,
      onEnd: () => setIsPlayingAudio(false),
    });
  };

  // Microphone recording
  const handleStartRecording = async () => {
    try {
      if (!navigator.mediaDevices?.getUserMedia) return;
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        const audioUrl = URL.createObjectURL(audioBlob);
        setRecordedAudioUrl(audioUrl);
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch {
      // Audio capture fallback
    }
  };

  const handleStopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      mediaRecorderRef.current.stream.getTracks().forEach((t) => t.stop());
    }
  };

  // Current quiz question
  const currentQuizQ = unit.quizQuestions[quizIndex] || unit.quizQuestions[0];

  const handleSelectQuizOption = (opt: string) => {
    if (isQuizSubmitted) return;
    setSelectedQuizOption(opt);
  };

  const handleSubmitQuizAnswer = () => {
    if (!selectedQuizOption || isQuizSubmitted || !currentQuizQ) return;
    const isCorrect = selectedQuizOption === currentQuizQ.correctAnswer;
    setIsQuizSubmitted(true);

    if (isCorrect) {
      audioFeedback.playSuccessSound();
      setQuizScore((prev) => prev + 1);
    } else {
      audioFeedback.playFailureSound();
    }
  };

  const handleNextQuizQuestion = () => {
    if (quizIndex + 1 < unit.quizQuestions.length) {
      setQuizIndex((prev) => prev + 1);
      setSelectedQuizOption(null);
      setIsQuizSubmitted(false);
    } else {
      setIsQuizFinished(true);
    }
  };

  return (
    <div className="bg-white border-2 border-zinc-950 rounded-2xl p-5 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] space-y-4">
      {/* Subheader with Mode Switcher & Real-time Matching Count */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-zinc-100 pb-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-black uppercase tracking-wider text-emerald-800 bg-emerald-100 px-2.5 py-0.5 rounded-md">
            Unit {unit.unitNumber} Bundled Practice
          </span>
          {matchedVocab ? (
            <span className="text-[11px] font-bold text-emerald-700 flex items-center gap-1">
              <Sparkles className="w-3.5 h-3.5" /> Matched to learned word ({matchedVocab.hanzi})
            </span>
          ) : (
            <span className="text-[11px] font-bold text-zinc-400">
              Pure Sound Practice (No character burden)
            </span>
          )}
        </div>

        <div className="flex items-center gap-1.5 bg-zinc-100 p-1 rounded-xl border border-zinc-200">
          <button
            onClick={() => setPracticeMode('flashcards')}
            className={`px-3 py-1 text-xs font-black rounded-lg transition-all cursor-pointer ${
              practiceMode === 'flashcards'
                ? 'bg-zinc-950 text-white shadow-xs'
                : 'text-zinc-600 hover:text-zinc-950'
            }`}
          >
            Sound Flashcards ({unit.flashcards.length})
          </button>
          <button
            onClick={() => {
              setPracticeMode('quiz');
              setQuizIndex(0);
              setSelectedQuizOption(null);
              setIsQuizSubmitted(false);
              setIsQuizFinished(false);
            }}
            className={`px-3 py-1 text-xs font-black rounded-lg transition-all cursor-pointer ${
              practiceMode === 'quiz'
                ? 'bg-zinc-950 text-white shadow-xs'
                : 'text-zinc-600 hover:text-zinc-950'
            }`}
          >
            Ear Training ({unit.quizQuestions.length})
          </button>
        </div>
      </div>

      {/* Mode 1: Sound Flashcards */}
      {practiceMode === 'flashcards' && currentFlashcard && (
        <div className="space-y-4">
          <div className="bg-zinc-50 border-2 border-zinc-200 rounded-2xl p-5 text-center space-y-3 relative">
            {/* Dynamic Real-Time Vocabulary Status Tag */}
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-black uppercase tracking-wider text-zinc-400">
                Card {cardIndex + 1} of {unit.flashcards.length} · {currentFlashcard.stageLabel}
              </span>

              {matchedVocab ? (
                <span className="text-[10px] font-black px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-300 flex items-center gap-1">
                  <Sparkles className="w-3 h-3" /> Learned from Lessons
                </span>
              ) : (
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-zinc-200 text-zinc-700">
                  Target Sound
                </span>
              )}
            </div>

            {/* Target Display (Character if learned, otherwise pure sound) */}
            <div className="py-2">
              {matchedVocab ? (
                <div className="space-y-1">
                  <div className="text-5xl font-black font-chinese text-zinc-950 tracking-wide">
                    {matchedVocab.hanzi}
                  </div>
                  <div className="text-2xl font-black font-mono text-emerald-700">
                    {matchedVocab.pinyin}
                  </div>
                  <div className="text-sm font-bold text-zinc-600">
                    {matchedVocab.meaningEn}
                  </div>
                </div>
              ) : currentFlashcard.targetHanzi ? (
                <div className="space-y-1">
                  <div className="text-5xl font-black font-chinese text-zinc-950 tracking-wide">
                    {currentFlashcard.targetHanzi}
                  </div>
                  <div className="text-2xl font-black font-mono text-emerald-700">
                    {currentFlashcard.targetPinyin}
                  </div>
                  <div className="text-sm font-bold text-zinc-600">
                    {currentFlashcard.meaningEn}
                  </div>
                </div>
              ) : (
                <div className="space-y-1">
                  <div className="text-5xl font-black font-mono text-zinc-950 tracking-wide">
                    {currentFlashcard.targetPinyin}
                  </div>
                  <div className="text-xs font-bold text-zinc-400 uppercase tracking-wider">
                    Pure Sound Target
                  </div>
                  <div className="text-sm font-medium text-zinc-600">
                    {currentFlashcard.meaningEn}
                  </div>
                </div>
              )}

              {currentFlashcard.acousticTip && (
                <div className="mt-3 text-xs text-zinc-600 bg-white border border-zinc-200 rounded-xl p-2.5 max-w-md mx-auto font-medium">
                  <span className="font-bold text-zinc-900">Acoustic Guide: </span>
                  {currentFlashcard.acousticTip}
                </div>
              )}
            </div>

            {/* Audio & Self-Recording Controls */}
            <div className="flex flex-wrap items-center justify-center gap-2 pt-2">
              <button
                onClick={() => handlePlayAudio(matchedVocab?.hanzi || currentFlashcard.audioTarget, false)}
                className="px-4 py-2 bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-black text-xs rounded-xl border-2 border-zinc-950 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] active:scale-95 transition-all flex items-center gap-1.5 cursor-pointer"
              >
                <Volume2 className="w-4 h-4" />
                Listen (Normal)
              </button>

              <button
                onClick={() => handlePlayAudio(matchedVocab?.hanzi || currentFlashcard.audioTarget, true)}
                className="px-3 py-2 bg-white hover:bg-zinc-100 text-zinc-800 font-bold text-xs rounded-xl border-2 border-zinc-300 transition-all flex items-center gap-1 cursor-pointer"
              >
                <Volume2 className="w-3.5 h-3.5" />
                Slow 0.7x
              </button>

              {/* Record Button */}
              {!isRecording ? (
                <button
                  onClick={handleStartRecording}
                  className="px-3 py-2 bg-white hover:bg-zinc-100 text-zinc-700 font-bold text-xs rounded-xl border-2 border-zinc-300 flex items-center gap-1.5 cursor-pointer"
                >
                  <Mic className="w-3.5 h-3.5 text-rose-500" />
                  Self Record
                </button>
              ) : (
                <button
                  onClick={handleStopRecording}
                  className="px-3 py-2 bg-rose-600 text-white font-black text-xs rounded-xl border-2 border-zinc-950 animate-pulse flex items-center gap-1.5 cursor-pointer"
                >
                  <Square className="w-3.5 h-3.5 fill-white" />
                  Stop Recording
                </button>
              )}

              {recordedAudioUrl && (
                <audio src={recordedAudioUrl} controls className="h-8 max-w-[160px]" />
              )}
            </div>
          </div>

          {/* Flashcard Navigation */}
          <div className="flex items-center justify-between pt-1">
            <button
              disabled={cardIndex === 0}
              onClick={() => setCardIndex((prev) => Math.max(0, prev - 1))}
              className="px-3.5 py-1.5 bg-white disabled:opacity-40 border-2 border-zinc-300 rounded-xl text-xs font-bold text-zinc-700 flex items-center gap-1 cursor-pointer"
            >
              <ChevronLeft className="w-4 h-4" /> Previous
            </button>

            {cardIndex + 1 < unit.flashcards.length ? (
              <button
                onClick={() => setCardIndex((prev) => prev + 1)}
                className="px-4 py-1.5 bg-zinc-950 hover:bg-zinc-800 text-white border-2 border-zinc-950 rounded-xl text-xs font-black flex items-center gap-1.5 cursor-pointer shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] active:scale-95"
              >
                Next Card <ChevronRight className="w-4 h-4" />
              </button>
            ) : (
              <button
                onClick={() => setPracticeMode('quiz')}
                className="px-4 py-1.5 bg-emerald-500 hover:bg-emerald-400 text-zinc-950 border-2 border-zinc-950 rounded-xl text-xs font-black flex items-center gap-1.5 cursor-pointer shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] active:scale-95"
              >
                Start Ear-Training Quiz <ArrowRight className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      )}

      {/* Mode 2: Ear-Training Listening Quiz */}
      {practiceMode === 'quiz' && (
        <div className="space-y-4">
          {!isQuizFinished ? (
            <div className="bg-zinc-50 border-2 border-zinc-200 rounded-2xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-black uppercase tracking-wider text-zinc-400">
                  Question {quizIndex + 1} of {unit.quizQuestions.length}
                </span>
                <span className="text-xs font-black text-emerald-700">
                  Score: {quizScore}
                </span>
              </div>

              {/* Audio Prompt */}
              <div className="text-center space-y-2 py-2">
                <button
                  onClick={() => handlePlayAudio(currentQuizQ.audioTarget)}
                  className="w-16 h-16 rounded-2xl bg-emerald-500 hover:bg-emerald-400 border-2 border-zinc-950 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] active:scale-95 transition-all flex items-center justify-center mx-auto cursor-pointer text-zinc-950"
                  title="Listen again"
                >
                  <Volume2 className="w-8 h-8" />
                </button>
                <div className="text-xs font-bold text-zinc-500">Tap to hear target audio</div>
                <h4 className="text-sm font-black text-zinc-950 max-w-md mx-auto">
                  {currentQuizQ.questionText}
                </h4>
              </div>

              {/* Options */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {currentQuizQ.options.map((opt) => {
                  const isSelected = selectedQuizOption === opt;
                  let btnStyle = 'bg-white border-zinc-200 hover:border-zinc-950 text-zinc-800';

                  if (isQuizSubmitted) {
                    if (opt === currentQuizQ.correctAnswer) {
                      btnStyle = 'bg-emerald-50 border-emerald-500 text-emerald-950 font-black';
                    } else if (isSelected) {
                      btnStyle = 'bg-rose-50 border-rose-500 text-rose-950';
                    }
                  } else if (isSelected) {
                    btnStyle = 'bg-zinc-950 text-white border-zinc-950';
                  }

                  return (
                    <button
                      key={opt}
                      disabled={isQuizSubmitted}
                      onClick={() => handleSelectQuizOption(opt)}
                      className={`p-3 rounded-xl border-2 text-xs font-bold text-left transition-all cursor-pointer ${btnStyle}`}
                    >
                      {opt}
                    </button>
                  );
                })}
              </div>

              {/* Feedback and Explanation */}
              {isQuizSubmitted && (
                <div className="p-3.5 rounded-xl border bg-white border-zinc-200 text-xs space-y-1 font-medium text-zinc-700">
                  <div className="font-black text-zinc-950 flex items-center gap-1.5">
                    {selectedQuizOption === currentQuizQ.correctAnswer ? (
                      <span className="text-emerald-700 flex items-center gap-1">
                        <Check className="w-4 h-4" /> Correct
                      </span>
                    ) : (
                      <span className="text-rose-700 flex items-center gap-1">
                        <X className="w-4 h-4" /> Incorrect
                      </span>
                    )}
                  </div>
                  <p>{currentQuizQ.explanationEn}</p>
                </div>
              )}

              {/* Action */}
              <div className="flex justify-end pt-1">
                {!isQuizSubmitted ? (
                  <button
                    disabled={!selectedQuizOption}
                    onClick={handleSubmitQuizAnswer}
                    className="px-5 py-2 bg-zinc-950 disabled:opacity-40 hover:bg-zinc-800 text-white font-black text-xs rounded-xl border-2 border-zinc-950 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] active:scale-95 transition-all cursor-pointer"
                  >
                    Submit Answer
                  </button>
                ) : (
                  <button
                    onClick={handleNextQuizQuestion}
                    className="px-5 py-2 bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-black text-xs rounded-xl border-2 border-zinc-950 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] active:scale-95 transition-all cursor-pointer flex items-center gap-1.5"
                  >
                    {quizIndex + 1 < unit.quizQuestions.length ? 'Next Question' : 'Complete Unit'}
                    <ArrowRight className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          ) : (
            /* Quiz Completed View */
            <div className="bg-emerald-50/70 border-2 border-emerald-300 rounded-2xl p-6 text-center space-y-3">
              <div className="w-12 h-12 bg-emerald-500 rounded-2xl border-2 border-zinc-950 flex items-center justify-center mx-auto text-zinc-950 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
                <Award className="w-6 h-6" />
              </div>
              <h4 className="text-base font-black text-zinc-950">
                Unit {unit.unitNumber} Practice Completed!
              </h4>
              <p className="text-xs text-zinc-600 font-medium max-w-sm mx-auto">
                You correctly answered {quizScore} of {unit.quizQuestions.length} ear-training questions.
              </p>

              <div className="pt-3">
                <button
                  onClick={() => onCompleteUnit(Math.round((quizScore / unit.quizQuestions.length) * 100))}
                  className="px-6 py-2.5 bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-black text-xs rounded-xl border-2 border-zinc-950 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] active:scale-95 transition-all cursor-pointer"
                >
                  Mark Unit Learned & Save
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
