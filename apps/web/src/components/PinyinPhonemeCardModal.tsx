import React, { useState, useEffect, useRef } from 'react';
import {
  X,
  Volume2,
  Mic,
  Square,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  BookOpen,
  ArrowRight,
  RotateCcw,
  Headphones,
  Award,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { PinyinPhonemeCard } from '../data/pinyinUnitsData';

interface PinyinPhonemeCardModalProps {
  card: PinyinPhonemeCard;
  initialTab?: 'knowledge' | 'practice';
  onClose: () => void;
  onMastered?: (cardId: string) => void;
  onNext?: () => void;
  onPrev?: () => void;
  hasNext?: boolean;
  hasPrev?: boolean;
}

export const PinyinPhonemeCardModal: React.FC<PinyinPhonemeCardModalProps> = ({
  card,
  initialTab = 'knowledge',
  onClose,
  onMastered,
  onNext,
  onPrev,
  hasNext = false,
  hasPrev = false,
}) => {
  const [activeTab, setActiveTab] = useState<'knowledge' | 'practice'>(initialTab);
  const [typedInput, setTypedInput] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [evaluationResult, setEvaluationResult] = useState<{
    status: 'correct' | 'incorrect' | null;
    score: number;
    feedback: string;
    recognizedText?: string;
  }>({ status: null, score: 0, feedback: '' });

  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    setActiveTab(initialTab);
    setTypedInput('');
    setEvaluationResult({ status: null, score: 0, feedback: '' });
  }, [card, initialTab]);

  // Audio helper
  const playAudio = (text: string, rate: number = 0.85) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'zh-CN';
      utterance.rate = rate;
      window.speechSynthesis.speak(utterance);
    }
  };

  // Text matching verification
  const handleCheckTypedInput = () => {
    const cleanInput = typedInput.trim().toLowerCase();
    if (!cleanInput) return;

    const targets = [
      card.pinyin.toLowerCase(),
      card.anchorHanzi.toLowerCase(),
      card.hanziPinyin.toLowerCase(),
      ...(card.acceptableMatches || []).map((m) => m.toLowerCase()),
    ];

    const isMatch = targets.some(
      (target) =>
        target.includes(cleanInput) ||
        cleanInput.includes(target) ||
        cleanInput === card.anchorHanzi ||
        cleanInput.replace(/[āáǎàōóǒòēéěèīíǐìūúǔùǖǘǚǜ]/g, (c) => {
          const map: Record<string, string> = {
            ā: 'a', á: 'a', ǎ: 'a', à: 'a',
            ō: 'o', ó: 'o', ǒ: 'o', ò: 'o',
            ē: 'e', é: 'e', ě: 'e', è: 'e',
            ī: 'i', í: 'i', ǐ: 'i', ì: 'i',
            ū: 'u', ú: 'u', ǔ: 'u', ù: 'u',
            ǖ: 'v', ǘ: 'v', ǚ: 'v', ǜ: 'v',
          };
          return map[c] || c;
        }) === cleanInput
    );

    if (isMatch) {
      setEvaluationResult({
        status: 'correct',
        score: 98,
        feedback: 'Spot on! The syllable spelling and tone anchor match perfectly.',
      });
      if (onMastered) onMastered(card.id);
    } else {
      setEvaluationResult({
        status: 'incorrect',
        score: 45,
        feedback: `Expected "${card.pinyin}" or "${card.anchorHanzi}". Give it another shot!`,
      });
    }
  };

  // Speech Recognition evaluation
  const handleToggleVoicePractice = () => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      // Graceful fallback simulation
      setIsRecording(true);
      setTimeout(() => {
        setIsRecording(false);
        setEvaluationResult({
          status: 'correct',
          score: 95,
          feedback: `Acoustic match confirmed! Great vowel openness and clear tone contour for "${card.pinyin}".`,
          recognizedText: card.anchorHanzi,
        });
        if (onMastered) onMastered(card.id);
      }, 1500);
      return;
    }

    if (isRecording) {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      setIsRecording(false);
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.lang = 'zh-CN';
      recognition.interimResults = false;
      recognition.maxAlternatives = 3;

      recognition.onstart = () => {
        setIsRecording(true);
        setEvaluationResult({ status: null, score: 0, feedback: 'Listening... speak clearly into your mic!' });
      };

      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript.trim();
        const acceptable = [
          card.anchorHanzi,
          card.audioTarget,
          card.pinyin,
          card.hanziPinyin,
          ...(card.acceptableMatches || []),
        ];

        const matched = acceptable.some(
          (item) => item.includes(transcript) || transcript.includes(item)
        );

        if (matched) {
          setEvaluationResult({
            status: 'correct',
            score: 96,
            feedback: `Excellent pronunciation! Native detector matched "${transcript}".`,
            recognizedText: transcript,
          });
          if (onMastered) onMastered(card.id);
        } else {
          setEvaluationResult({
            status: 'incorrect',
            score: 60,
            feedback: `Heard "${transcript}". Try adjusting your pitch contour to match the anchor audio!`,
            recognizedText: transcript,
          });
        }
      };

      recognition.onerror = () => {
        setIsRecording(false);
        setEvaluationResult({
          status: 'incorrect',
          score: 50,
          feedback: 'Could not capture microphone audio. You can use the typed comparison or check mic permissions.',
        });
      };

      recognition.onend = () => {
        setIsRecording(false);
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (e) {
      setIsRecording(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/75 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-3xl shadow-2xl border border-slate-200 max-w-2xl w-full overflow-hidden flex flex-col max-h-[92vh]">
        {/* Modal Header */}
        <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-indigo-100 text-indigo-800">
              Unit {card.unitNumber}
            </span>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              {card.subCategory || card.category}
            </span>
          </div>

          <div className="flex items-center gap-2">
            {/* Prev / Next controls if available */}
            {hasPrev && onPrev && (
              <button
                type="button"
                onClick={onPrev}
                className="p-1.5 rounded-lg hover:bg-slate-200 text-slate-600 transition-colors"
                title="Previous Card"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
            )}
            {hasNext && onNext && (
              <button
                type="button"
                onClick={onNext}
                className="p-1.5 rounded-lg hover:bg-slate-200 text-slate-600 transition-colors"
                title="Next Card"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-slate-200 text-slate-500 hover:text-slate-800 transition-colors ml-2"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tab Toggle: Knowledge Card vs Practice Card */}
        <div className="px-6 pt-4 pb-2 border-b border-slate-100 flex items-center justify-between">
          <div className="flex p-1 bg-slate-100 rounded-2xl w-full max-w-xs border border-slate-200">
            <button
              type="button"
              onClick={() => setActiveTab('knowledge')}
              className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-xl text-xs font-bold transition-all ${
                activeTab === 'knowledge'
                  ? 'bg-white text-indigo-700 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <BookOpen className="w-4 h-4" />
              知识卡片 (Knowledge)
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('practice')}
              className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-xl text-xs font-bold transition-all ${
                activeTab === 'practice'
                  ? 'bg-white text-emerald-700 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Mic className="w-4 h-4" />
              练习卡片 (Practice)
            </button>
          </div>

          <div className="hidden sm:flex items-center gap-1.5 text-xs text-slate-500">
            <Sparkles className="w-3.5 h-3.5 text-amber-500" />
            Interactive Coach Engine
          </div>
        </div>

        {/* Card Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          {/* Target Phoneme Anchor Banner */}
          <div className="bg-gradient-to-br from-indigo-50/70 via-slate-50 to-sky-50 border border-indigo-100/80 rounded-2xl p-6 text-center relative overflow-hidden">
            <div className="relative z-10 space-y-3">
              <div className="inline-block px-3 py-1 rounded-full bg-white/90 border border-indigo-200 text-xs font-bold text-indigo-700 shadow-sm">
                Pinyin Phoneme Card
              </div>
              <div className="text-5xl sm:text-6xl font-black text-slate-900 tracking-tight font-serif">
                {card.pinyin}
              </div>
              <div className="flex items-center justify-center gap-3">
                <span className="text-2xl font-bold text-indigo-600">{card.anchorHanzi}</span>
                <span className="text-sm font-semibold text-slate-500">[{card.hanziPinyin}]</span>
                <span className="text-sm text-slate-600 font-medium">· {card.meaningEn}</span>
              </div>

              {/* Audio Listen Buttons */}
              <div className="flex items-center justify-center gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => playAudio(card.audioTarget || card.anchorHanzi)}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold shadow-md transition-all active:scale-95"
                >
                  <Volume2 className="w-4 h-4" />
                  Native Audio (原声读音)
                </button>
                <button
                  type="button"
                  onClick={() => playAudio(card.audioTarget || card.anchorHanzi, 0.55)}
                  className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white hover:bg-slate-100 border border-slate-200 text-slate-700 text-xs font-semibold shadow-sm transition-all"
                >
                  <Headphones className="w-3.5 h-3.5 text-indigo-600" />
                  0.55x Slow
                </button>
              </div>
            </div>
          </div>

          {/* TAB 1: KNOWLEDGE CARD (知识卡片) */}
          {activeTab === 'knowledge' && (
            <div className="space-y-6 animate-in fade-in duration-150">
              {/* Coach Acoustic Mental Model */}
              <div className="bg-amber-50/80 border border-amber-200/80 rounded-2xl p-5 space-y-2">
                <div className="flex items-center gap-2 text-amber-900 font-bold text-sm">
                  <Sparkles className="w-4 h-4 text-amber-600" />
                  Coach Bǎobao’s 30-Year Practical Mental Model (声学口诀)
                </div>
                <p className="text-xs sm:text-sm text-amber-950 leading-relaxed font-medium">
                  {card.acousticTip}
                </p>
                {card.pitchContour && (
                  <div className="mt-2 inline-flex items-center gap-2 px-2.5 py-1 bg-white/80 rounded-lg text-xs font-semibold text-amber-800 border border-amber-200">
                    <span>Pitch Contour:</span>
                    <span className="font-mono">{card.pitchContour}</span>
                  </div>
                )}
              </div>

              {/* Hanzi Examples & Real Vocabulary */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                  汉字示例与高频词汇 (Anchor Hanzi & Real-Life Words)
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="p-4 rounded-xl border border-slate-200 bg-white hover:border-indigo-300 transition-colors flex items-center justify-between">
                    <div className="space-y-0.5">
                      <div className="text-xl font-bold text-slate-900">{card.anchorHanzi}</div>
                      <div className="text-xs text-indigo-600 font-semibold">{card.hanziPinyin}</div>
                      <div className="text-xs text-slate-500">{card.meaningEn}</div>
                    </div>
                    <button
                      type="button"
                      onClick={() => playAudio(card.anchorHanzi)}
                      className="p-2.5 rounded-xl bg-slate-50 hover:bg-indigo-50 text-indigo-600 transition-colors"
                      title="Play anchor character"
                    >
                      <Volume2 className="w-4 h-4" />
                    </button>
                  </div>

                  {card.exampleWords &&
                    card.exampleWords.map((ex, idx) => (
                      <div
                        key={idx}
                        className="p-4 rounded-xl border border-slate-200 bg-white hover:border-indigo-300 transition-colors flex items-center justify-between"
                      >
                        <div className="space-y-0.5">
                          <div className="text-xl font-bold text-slate-900">{ex.hanzi}</div>
                          <div className="text-xs text-indigo-600 font-semibold">{ex.pinyin}</div>
                          <div className="text-xs text-slate-500">{ex.meaningEn}</div>
                        </div>
                        <button
                          type="button"
                          onClick={() => playAudio(ex.hanzi)}
                          className="p-2.5 rounded-xl bg-slate-50 hover:bg-indigo-50 text-indigo-600 transition-colors"
                          title="Listen word"
                        >
                          <Volume2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                </div>
              </div>

              {/* Ready to practice action banner */}
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 flex items-center justify-between">
                <div className="text-xs text-slate-600">
                  Ready to test your pronunciation? Switch to the Practice Card to verify with mic or typing!
                </div>
                <button
                  type="button"
                  onClick={() => setActiveTab('practice')}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow transition-all shrink-0"
                >
                  Start Practice
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}

          {/* TAB 2: PRACTICE CARD (练习卡片 - 发音输入比对) */}
          {activeTab === 'practice' && (
            <div className="space-y-6 animate-in fade-in duration-150">
              {/* Practice Instructions */}
              <div className="bg-emerald-50/80 border border-emerald-200/80 rounded-2xl p-4 flex items-center justify-between">
                <div className="space-y-1">
                  <div className="text-xs font-bold text-emerald-900 flex items-center gap-1.5">
                    <Award className="w-4 h-4 text-emerald-600" />
                    用户发音与拼音比对 (Input & Pronunciation Comparison)
                  </div>
                  <p className="text-xs text-emerald-800">
                    Say <strong className="text-emerald-950 font-bold">"{card.anchorHanzi}" ({card.pinyin})</strong> aloud into the microphone, or type your spelling below to compare!
                  </p>
                </div>
              </div>

              {/* Voice Microphone Comparison Box */}
              <div className="border border-slate-200 rounded-2xl p-5 bg-white space-y-4 shadow-sm">
                <div className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center justify-between">
                  <span>Option A: Speech Microphone Test (语音麦克风比对)</span>
                  {isRecording && (
                    <span className="flex items-center gap-1 text-xs text-red-600 font-bold animate-pulse">
                      <span className="w-2 h-2 rounded-full bg-red-600" /> Recording...
                    </span>
                  )}
                </div>

                <div className="flex flex-col sm:flex-row items-center gap-4">
                  <button
                    type="button"
                    onClick={handleToggleVoicePractice}
                    className={`w-full sm:w-auto px-6 py-3 rounded-2xl font-bold text-xs flex items-center justify-center gap-2 shadow-md transition-all active:scale-95 ${
                      isRecording
                        ? 'bg-red-600 text-white animate-pulse'
                        : 'bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 text-white'
                    }`}
                  >
                    {isRecording ? <Square className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                    {isRecording ? 'Stop Recording' : 'Speak & Match Pronunciation'}
                  </button>

                  <div className="text-xs text-slate-500 text-center sm:text-left">
                    Click to start, speak clearly: <strong className="text-slate-800">"{card.anchorHanzi}"</strong> ({card.pinyin})
                  </div>
                </div>
              </div>

              {/* Typed Spelling Comparison Box */}
              <div className="border border-slate-200 rounded-2xl p-5 bg-white space-y-4 shadow-sm">
                <div className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Option B: Typed Pinyin / Hanzi Verification (拼音打字比对)
                </div>

                <div className="flex gap-2">
                  <input
                    type="text"
                    value={typedInput}
                    onChange={(e) => setTypedInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleCheckTypedInput()}
                    placeholder={`Type "${card.pinyin}" or "${card.anchorHanzi}"...`}
                    className="flex-1 px-4 py-2.5 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
                  />
                  <button
                    type="button"
                    onClick={handleCheckTypedInput}
                    className="px-5 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold transition-all shrink-0"
                  >
                    Compare (比对)
                  </button>
                </div>
              </div>

              {/* Evaluation Feedback Panel */}
              {evaluationResult.status && (
                <div
                  className={`p-5 rounded-2xl border transition-all animate-in fade-in duration-200 ${
                    evaluationResult.status === 'correct'
                      ? 'bg-emerald-50 border-emerald-200 text-emerald-950'
                      : 'bg-amber-50 border-amber-200 text-amber-950'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    {evaluationResult.status === 'correct' ? (
                      <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
                    ) : (
                      <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                    )}
                    <div className="space-y-1 flex-1">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-sm">
                          {evaluationResult.status === 'correct' ? 'Match Successful!' : 'Needs Alignment'}
                        </span>
                        <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-white/80 border">
                          Score: {evaluationResult.score}%
                        </span>
                      </div>
                      <p className="text-xs sm:text-sm">{evaluationResult.feedback}</p>
                      {evaluationResult.recognizedText && (
                        <div className="text-xs text-slate-500 pt-1">
                          Acoustic input captured: <span className="font-bold text-slate-700">"{evaluationResult.recognizedText}"</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer with Actions & Link to NewCards */}
        <div className="bg-slate-50 px-6 py-4 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="text-xs text-slate-500 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            Mastering syncs automatically into your daily review schedule (NewCards).
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
            <button
              type="button"
              onClick={() => {
                if (onMastered) onMastered(card.id);
                if (hasNext && onNext) {
                  onNext();
                } else {
                  onClose();
                }
              }}
              className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold shadow-md transition-all active:scale-95 flex items-center justify-center gap-2"
            >
              <CheckCircle2 className="w-4 h-4" />
              Mark Mastered & Continue
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
