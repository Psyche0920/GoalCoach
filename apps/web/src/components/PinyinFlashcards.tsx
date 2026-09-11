import React, { useState, useRef, useEffect } from 'react';
import { 
  Volume2, 
  Mic, 
  Square, 
  RotateCcw, 
  Check, 
  ArrowRight, 
  Sparkles, 
  Play, 
  Eye, 
  Info,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import { PinyinFlashcard } from '../data/pinyinData.ts';
import { playMandarinAudio } from '../utils/pinyinAudio.ts';

interface PinyinFlashcardsProps {
  cards: PinyinFlashcard[];
  onComplete: () => void;
}

export const PinyinFlashcards: React.FC<PinyinFlashcardsProps> = ({
  cards,
  onComplete,
}) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlayingModel, setIsPlayingModel] = useState(false);
  const [audioSpeed, setAudioSpeed] = useState<'normal' | 'slow'>('normal');
  const [revealed, setRevealed] = useState(false);
  
  // Voice Recording State for Self-Correction
  const [isRecording, setIsRecording] = useState(false);
  const [recordedAudioUrl, setRecordedAudioUrl] = useState<string | null>(null);
  const [isPlayingUserAudio, setIsPlayingUserAudio] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const userAudioElementRef = useRef<HTMLAudioElement | null>(null);

  const currentCard = cards[currentIndex] || cards[0];

  // Reset audio & reveal on card change
  useEffect(() => {
    setRevealed(false);
    setRecordedAudioUrl(null);
    setIsRecording(false);
  }, [currentIndex]);

  // Play standard native audio model
  const handlePlayModelAudio = (slow = false) => {
    if (!currentCard) return;
    setIsPlayingModel(true);
    const rate = slow ? 0.65 : 0.88;
    playMandarinAudio(currentCard.audioTarget, {
      rate,
      onEnd: () => setIsPlayingModel(false),
    });
  };

  // Start recording user's voice
  const handleStartRecording = async () => {
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert('Microphone access is not supported in this environment.');
        return;
      }
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        const url = URL.createObjectURL(audioBlob);
        setRecordedAudioUrl(url);
        // Stop all tracks to release mic
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      console.warn('Microphone error:', err);
    }
  };

  const handleStopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const handlePlayUserAudio = () => {
    if (!recordedAudioUrl) return;
    if (!userAudioElementRef.current) {
      userAudioElementRef.current = new Audio(recordedAudioUrl);
    } else {
      userAudioElementRef.current.src = recordedAudioUrl;
    }
    setIsPlayingUserAudio(true);
    userAudioElementRef.current.onended = () => setIsPlayingUserAudio(false);
    userAudioElementRef.current.play().catch(() => setIsPlayingUserAudio(false));
  };

  const handleNext = () => {
    if (currentIndex < cards.length - 1) {
      setCurrentIndex((prev) => prev + 1);
    } else {
      onComplete();
    }
  };

  const handlePrev = () => {
    if (currentIndex > 0) {
      setCurrentIndex((prev) => prev - 1);
    }
  };

  return (
    <div className="max-w-xl mx-auto space-y-6 py-2">
      {/* Step Indicator & Progression Stage */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-black uppercase tracking-wider px-2.5 py-1 bg-zinc-100 border border-zinc-300 rounded-lg text-zinc-700">
            Card {currentIndex + 1} of {cards.length}
          </span>
          <span className="text-xs font-bold text-emerald-700 bg-emerald-50 border border-emerald-300 px-2 py-0.5 rounded">
            Stage: {currentCard.stageLabel}
          </span>
        </div>

        {/* Speed Toggle */}
        <div className="flex items-center gap-1 bg-zinc-100 p-0.5 rounded-lg border border-zinc-300">
          <button
            onClick={() => setAudioSpeed('normal')}
            className={`px-2 py-0.5 rounded text-[10px] font-black transition-all cursor-pointer ${
              audioSpeed === 'normal'
                ? 'bg-zinc-950 text-white'
                : 'text-zinc-600 hover:text-zinc-900'
            }`}
          >
            1.0x
          </button>
          <button
            onClick={() => setAudioSpeed('slow')}
            className={`px-2 py-0.5 rounded text-[10px] font-black transition-all cursor-pointer ${
              audioSpeed === 'slow'
                ? 'bg-zinc-950 text-white'
                : 'text-zinc-600 hover:text-zinc-900'
            }`}
          >
            0.75x
          </button>
        </div>
      </div>

      {/* Main Flashcard */}
      <div className="bg-white border-2 border-zinc-950 rounded-2xl p-8 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] text-center relative overflow-hidden">
        {/* Progress line */}
        <div
          className="absolute top-0 left-0 h-1.5 bg-emerald-500 transition-all duration-300"
          style={{ width: `${((currentIndex + 1) / cards.length) * 100}%` }}
        />

        {/* Main Pinyin Display */}
        <div className="my-6">
          <span className="text-5xl sm:text-6xl font-black text-zinc-950 font-mono tracking-wide block">
            {currentCard.targetPinyin}
          </span>
          {currentCard.targetHanzi && (
            <span className="text-2xl font-black text-zinc-400 mt-2 block">
              {currentCard.targetHanzi}
            </span>
          )}
        </div>

        {/* Listen Standard Model Audio Button */}
        <div className="flex justify-center mb-6">
          <button
            onClick={() => handlePlayModelAudio(audioSpeed === 'slow')}
            className={`px-6 py-3 rounded-2xl border-2 border-zinc-950 font-black text-sm flex items-center gap-2.5 transition-all shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] cursor-pointer ${
              isPlayingModel
                ? 'bg-emerald-600 text-white scale-105'
                : 'bg-emerald-500 hover:bg-emerald-400 text-zinc-950 active:scale-95'
            }`}
          >
            <Volume2 className={`w-5 h-5 ${isPlayingModel ? 'animate-pulse' : ''}`} />
            <span>{isPlayingModel ? 'Playing Audio...' : 'Listen Native Audio'}</span>
          </button>
        </div>

        {/* Acoustic Tip & Translation */}
        <div className="p-4 bg-zinc-50 border border-zinc-200 rounded-xl text-left space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-black uppercase tracking-wider text-zinc-500">
              Meaning & Context
            </span>
            <button
              onClick={() => setRevealed(!revealed)}
              className="text-xs font-black text-emerald-600 hover:text-emerald-700 flex items-center gap-1 cursor-pointer"
            >
              <Eye className="w-3.5 h-3.5" />
              {revealed ? 'Hide Notes' : 'Show Notes'}
            </button>
          </div>

          <p className="text-sm font-black text-zinc-900">
            {currentCard.meaningEn}
          </p>

          {revealed && currentCard.acousticTip && (
            <div className="pt-2 border-t border-zinc-200">
              <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block">
                Pronunciation Tip:
              </span>
              <p className="text-xs text-zinc-700 font-medium mt-0.5">
                {currentCard.acousticTip}
              </p>
            </div>
          )}
        </div>

        {/* Voice Recording & Self-Comparison Section */}
        <div className="mt-6 pt-6 border-t-2 border-dashed border-zinc-200">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-black text-zinc-950">
              Self-Correction Studio
            </span>
            <span className="text-[11px] font-bold text-zinc-400">
              Record & compare with model
            </span>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-3">
            {!isRecording ? (
              <button
                onClick={handleStartRecording}
                className="px-4 py-2.5 bg-white hover:bg-red-50 text-red-600 border-2 border-red-600 rounded-xl font-black text-xs flex items-center gap-2 transition-all shadow-[2px_2px_0px_0px_rgba(220,38,38,0.3)] active:scale-95 cursor-pointer"
              >
                <Mic className="w-4 h-4" />
                Record My Voice
              </button>
            ) : (
              <button
                onClick={handleStopRecording}
                className="px-4 py-2.5 bg-red-600 text-white border-2 border-zinc-950 rounded-xl font-black text-xs flex items-center gap-2 animate-pulse shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] active:scale-95 cursor-pointer"
              >
                <Square className="w-4 h-4 fill-white" />
                Stop Recording
              </button>
            )}

            {recordedAudioUrl && (
              <button
                onClick={handlePlayUserAudio}
                className={`px-4 py-2.5 rounded-xl border-2 border-zinc-950 font-black text-xs flex items-center gap-2 transition-all shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] cursor-pointer ${
                  isPlayingUserAudio
                    ? 'bg-sky-600 text-white'
                    : 'bg-sky-50 text-sky-950 hover:bg-sky-100 active:scale-95'
                }`}
              >
                <Play className="w-4 h-4 fill-current" />
                {isPlayingUserAudio ? 'Playing Yours...' : 'Playback My Voice'}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Navigation Controls */}
      <div className="flex items-center justify-between gap-3">
        <button
          onClick={handlePrev}
          disabled={currentIndex === 0}
          className="px-4 py-3 rounded-xl border-2 border-zinc-950 font-black text-xs flex items-center gap-1.5 transition-all bg-white hover:bg-zinc-100 disabled:opacity-40 disabled:cursor-not-allowed shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] cursor-pointer"
        >
          <ChevronLeft className="w-4 h-4" />
          Previous
        </button>

        <button
          onClick={handleNext}
          className="flex-1 py-3 px-6 rounded-xl border-2 border-zinc-950 font-black text-sm flex items-center justify-center gap-2 transition-all bg-zinc-950 text-white hover:bg-zinc-800 active:scale-98 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] cursor-pointer"
        >
          <span>{currentIndex === cards.length - 1 ? 'Finish Flashcards' : 'Next Card'}</span>
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
