import React, { useState, useEffect } from 'react';
import { 
  Volume2, 
  Check, 
  X, 
  ArrowRight, 
  RotateCcw, 
  Award, 
  Sparkles,
  HelpCircle
} from 'lucide-react';
import { PinyinQuizQuestion } from '../data/pinyinData.ts';
import { playMandarinAudio } from '../utils/pinyinAudio.ts';
import { audioFeedback } from '../utils/audioFeedback.ts';

interface PinyinQuizProps {
  questions: PinyinQuizQuestion[];
  onComplete: (score: number) => void;
}

export const PinyinQuiz: React.FC<PinyinQuizProps> = ({
  questions,
  onComplete,
}) => {
  const [currentIdx, setCurrentIdx] = useState(0);
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [isAnswerSubmitted, setIsAnswerSubmitted] = useState(false);
  const [correctCount, setCorrectCount] = useState(0);
  const [isFinished, setIsFinished] = useState(false);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);

  const currentQ = questions[currentIdx] || questions[0];

  // Auto-play audio when moving to next question
  useEffect(() => {
    if (currentQ) {
      handlePlayAudio();
    }
    setSelectedOption(null);
    setIsAnswerSubmitted(false);
  }, [currentIdx]);

  const handlePlayAudio = () => {
    if (!currentQ) return;
    setIsPlayingAudio(true);
    playMandarinAudio(currentQ.audioTarget, {
      rate: 0.85,
      onEnd: () => setIsPlayingAudio(false),
    });
  };

  const handleSelectOption = (opt: string) => {
    if (isAnswerSubmitted) return;
    setSelectedOption(opt);
  };

  const handleSubmit = () => {
    if (!selectedOption || isAnswerSubmitted) return;

    const isCorrect = selectedOption === currentQ.correctAnswer;
    setIsAnswerSubmitted(true);

    if (isCorrect) {
      setCorrectCount((prev) => prev + 1);
      audioFeedback.playSuccessSound();
    } else {
      audioFeedback.playFailureSound();
    }
  };

  const handleNext = () => {
    if (currentIdx < questions.length - 1) {
      setCurrentIdx((prev) => prev + 1);
    } else {
      setIsFinished(true);
    }
  };

  const finalScore = questions.length > 0 ? correctCount / questions.length : 1;

  if (isFinished) {
    return (
      <div className="max-w-md mx-auto bg-white border-2 border-zinc-950 rounded-2xl p-8 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] text-center space-y-6 my-4">
        <div className="w-16 h-16 bg-emerald-100 text-emerald-700 rounded-full flex items-center justify-center mx-auto border-2 border-zinc-950 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
          <Award className="w-8 h-8" />
        </div>

        <div>
          <h3 className="text-2xl font-black text-zinc-950 tracking-tight">
            Quiz Completed!
          </h3>
          <p className="text-xs font-bold text-zinc-500 mt-1">
            Pinyin listening & distinction assessment
          </p>
        </div>

        <div className="p-4 bg-zinc-50 border-2 border-zinc-200 rounded-xl">
          <div className="text-3xl font-black text-zinc-950 font-mono">
            {correctCount} / {questions.length}
          </div>
          <div className="text-xs font-black text-emerald-600 uppercase tracking-wider mt-1">
            {Math.round(finalScore * 100)}% Accuracy
          </div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={() => {
              setCurrentIdx(0);
              setCorrectCount(0);
              setIsFinished(false);
            }}
            className="flex-1 py-3 px-4 rounded-xl border-2 border-zinc-950 font-black text-xs bg-white hover:bg-zinc-100 transition-all flex items-center justify-center gap-2 cursor-pointer shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Retry
          </button>

          <button
            onClick={() => onComplete(finalScore)}
            className="flex-1 py-3 px-4 rounded-xl border-2 border-zinc-950 font-black text-xs bg-emerald-500 hover:bg-emerald-400 text-zinc-950 transition-all flex items-center justify-center gap-2 cursor-pointer shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]"
          >
            <Check className="w-4 h-4" />
            Save & Continue
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-xl mx-auto space-y-6 py-2">
      {/* Quiz Header */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-black uppercase tracking-wider px-2.5 py-1 bg-zinc-100 border border-zinc-300 rounded-lg text-zinc-700">
          Question {currentIdx + 1} of {questions.length}
        </span>
        <span className="text-xs font-bold text-zinc-500">
          Score: {correctCount} correct
        </span>
      </div>

      {/* Main Question Card */}
      <div className="bg-white border-2 border-zinc-950 rounded-2xl p-6 sm:p-8 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] space-y-6">
        {/* Audio Prompt */}
        <div className="flex flex-col items-center justify-center p-6 bg-emerald-50 border-2 border-emerald-300 rounded-2xl text-center">
          <span className="text-[11px] font-black uppercase tracking-wider text-emerald-800 mb-3">
            Audio Prompt
          </span>
          <button
            onClick={handlePlayAudio}
            className={`w-16 h-16 rounded-full border-2 border-zinc-950 flex items-center justify-center shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] transition-all cursor-pointer ${
              isPlayingAudio
                ? 'bg-emerald-600 text-white scale-105'
                : 'bg-white text-zinc-950 hover:bg-emerald-100 active:scale-95'
            }`}
          >
            <Volume2 className={`w-7 h-7 ${isPlayingAudio ? 'animate-pulse' : ''}`} />
          </button>
          <span className="text-xs font-bold text-emerald-900 mt-3">
            Tap to listen to the prompt
          </span>
        </div>

        {/* Question Text */}
        <h4 className="text-base font-black text-zinc-950 leading-snug text-center">
          {currentQ.questionText}
        </h4>

        {/* Options */}
        <div className="space-y-2.5">
          {currentQ.options.map((opt, idx) => {
            const isSelected = selectedOption === opt;
            const isCorrect = opt === currentQ.correctAnswer;

            let optionStyle =
              'border-zinc-300 bg-zinc-50 hover:border-zinc-950 hover:bg-white text-zinc-900 shadow-[1px_1px_0px_0px_rgba(0,0,0,0.04)]';

            if (isSelected && !isAnswerSubmitted) {
              optionStyle =
                'border-zinc-950 bg-zinc-950 text-white shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]';
            } else if (isAnswerSubmitted) {
              if (isCorrect) {
                optionStyle =
                  'border-emerald-600 bg-emerald-100 text-emerald-950 font-black shadow-[2px_2px_0px_0px_rgba(16,185,129,1)]';
              } else if (isSelected && !isCorrect) {
                optionStyle =
                  'border-red-600 bg-red-100 text-red-950 shadow-[2px_2px_0px_0px_rgba(220,38,38,1)]';
              } else {
                optionStyle = 'border-zinc-200 bg-zinc-100 opacity-50 text-zinc-400';
              }
            }

            return (
              <button
                key={idx}
                disabled={isAnswerSubmitted}
                onClick={() => handleSelectOption(opt)}
                className={`w-full p-3.5 rounded-xl border-2 text-left text-xs sm:text-sm font-bold transition-all flex items-center justify-between cursor-pointer ${optionStyle}`}
              >
                <span>{opt}</span>
                {isAnswerSubmitted && isCorrect && (
                  <Check className="w-4 h-4 text-emerald-700 stroke-[3]" />
                )}
                {isAnswerSubmitted && isSelected && !isCorrect && (
                  <X className="w-4 h-4 text-red-600 stroke-[3]" />
                )}
              </button>
            );
          })}
        </div>

        {/* Answer Explanation */}
        {isAnswerSubmitted && (
          <div className="p-4 bg-zinc-50 border border-zinc-200 rounded-xl space-y-1">
            <span className="text-[10px] font-black uppercase tracking-wider text-zinc-500">
              Explanation
            </span>
            <p className="text-xs text-zinc-700 leading-relaxed font-medium">
              {currentQ.explanationEn}
            </p>
          </div>
        )}

        {/* Submit or Next Button */}
        {!isAnswerSubmitted ? (
          <button
            disabled={!selectedOption}
            onClick={handleSubmit}
            className="w-full py-3.5 px-6 bg-zinc-950 hover:bg-zinc-800 disabled:opacity-40 disabled:cursor-not-allowed text-white font-black rounded-xl border-2 border-zinc-950 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] active:scale-98 transition-all cursor-pointer text-sm"
          >
            Check Answer
          </button>
        ) : (
          <button
            onClick={handleNext}
            className="w-full py-3.5 px-6 bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-black rounded-xl border-2 border-zinc-950 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] active:scale-98 transition-all flex items-center justify-center gap-2 cursor-pointer text-sm"
          >
            <span>{currentIdx < questions.length - 1 ? 'Next Question' : 'View Results'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
};
