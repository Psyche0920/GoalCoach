import React, { useState } from 'react';
import { Volume2, ArrowRight, Play, Sparkles, BookOpen } from 'lucide-react';
import { PINYIN_OVERVIEW, TONE_CONTRAST_SET } from '../data/pinyinData.ts';
import { playMandarinAudio } from '../utils/pinyinAudio.ts';

interface PinyinOverviewViewProps {
  onStartUnit: (unitNumber: number) => void;
  onOpenChart: () => void;
}

export const PinyinOverviewView: React.FC<PinyinOverviewViewProps> = ({
  onStartUnit,
  onOpenChart,
}) => {
  const [playingTone, setPlayingTone] = useState<number | null>(null);

  const handlePlayContrast = (tone: number, audioChar: string) => {
    setPlayingTone(tone);
    playMandarinAudio(audioChar, {
      rate: 0.8,
      onEnd: () => setPlayingTone(null),
    });
  };

  return (
    <div className="space-y-8 max-w-3xl mx-auto py-2">
      {/* Introduction Card */}
      <div className="bg-white border-2 border-zinc-950 rounded-2xl p-6 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)]">
        <h2 className="text-2xl font-black text-zinc-950 tracking-tight">
          {PINYIN_OVERVIEW.title}
        </h2>
        <p className="text-xs font-bold uppercase tracking-wider text-emerald-600 mt-1">
          {PINYIN_OVERVIEW.subtitle}
        </p>
        <p className="text-sm text-zinc-700 leading-relaxed mt-3">
          {PINYIN_OVERVIEW.definition}
        </p>

        {/* 3 Foundational Pillars */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-6">
          {PINYIN_OVERVIEW.keyDifferences.map((item, idx) => (
            <div
              key={idx}
              className="bg-zinc-50 border border-zinc-200 rounded-xl p-3.5 flex flex-col justify-between"
            >
              <div>
                <span className="text-[10px] font-black text-zinc-500 uppercase tracking-wider">
                  0{idx + 1}
                </span>
                <h3 className="text-sm font-black text-zinc-950 mt-1">
                  {item.title}
                </h3>
                <p className="text-xs text-zinc-600 leading-relaxed mt-1.5">
                  {item.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Anatomy Diagram: Initial + Final + Tone */}
      <div className="bg-white border-2 border-zinc-950 rounded-2xl p-6 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)]">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-black text-zinc-950 tracking-tight">
              Anatomy of a Mandarin Syllable
            </h3>
            <p className="text-xs text-zinc-500 font-bold">
              Formula: Initial + Final + Tone Mark
            </p>
          </div>
          <span className="text-xs font-black px-2.5 py-1 bg-zinc-100 border border-zinc-300 rounded-lg text-zinc-700">
            ~409 Valid Syllables
          </span>
        </div>

        {/* Visual Anatomy Breakdown Blocks */}
        <div className="grid grid-cols-3 sm:grid-cols-4 gap-3 items-center text-center">
          {/* Initial */}
          <div className="bg-sky-50 border-2 border-sky-300 rounded-xl p-3.5">
            <span className="text-[10px] font-black uppercase tracking-wider text-sky-700 block">
              Initial
            </span>
            <span className="text-3xl font-black text-sky-950 block my-1 font-mono">
              m
            </span>
            <span className="text-[11px] font-medium text-sky-800">
              Consonant sound
            </span>
          </div>

          <div className="text-xl font-black text-zinc-400 hidden sm:block">+</div>

          {/* Final */}
          <div className="bg-amber-50 border-2 border-amber-300 rounded-xl p-3.5">
            <span className="text-[10px] font-black uppercase tracking-wider text-amber-700 block">
              Final
            </span>
            <span className="text-3xl font-black text-amber-950 block my-1 font-mono">
              a
            </span>
            <span className="text-[11px] font-medium text-amber-800">
              Vowel / Glide
            </span>
          </div>

          {/* Tone */}
          <div className="bg-purple-50 border-2 border-purple-300 rounded-xl p-3.5">
            <span className="text-[10px] font-black uppercase tracking-wider text-purple-700 block">
              Tone Mark
            </span>
            <span className="text-3xl font-black text-purple-950 block my-1 font-mono">
              ˉ
            </span>
            <span className="text-[11px] font-medium text-purple-800">
              Pitch level 55
            </span>
          </div>
        </div>

        {/* Resulting Word Card */}
        <div className="mt-5 bg-emerald-50 border-2 border-emerald-500 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 bg-white border-2 border-emerald-600 rounded-xl flex items-center justify-center text-2xl font-black text-zinc-950">
              妈
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-2xl font-black text-emerald-950 font-mono tracking-wide">
                  mā
                </span>
                <span className="text-xs font-bold px-2 py-0.5 bg-emerald-200 text-emerald-900 rounded">
                  1st Tone
                </span>
              </div>
              <p className="text-xs text-zinc-600 font-bold mt-0.5">
                Meaning: Mother / Mom
              </p>
            </div>
          </div>

          <button
            onClick={() => handlePlayContrast(1, '妈')}
            className="w-full sm:w-auto px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 active:scale-95 text-white font-black rounded-xl border-2 border-zinc-950 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] text-xs flex items-center justify-center gap-2 transition-all cursor-pointer"
          >
            <Volume2 className="w-4 h-4" />
            Listen "mā"
          </button>
        </div>
      </div>

      {/* The 4 Tones & Pitch Pitch Contours Interactive Demo */}
      <div className="bg-white border-2 border-zinc-950 rounded-2xl p-6 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)]">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-black text-zinc-950 tracking-tight">
              The 4 Tones & Pitch Contours
            </h3>
            <p className="text-xs text-zinc-500 font-bold">
              Tone changes the entire meaning of a word
            </p>
          </div>
          <span className="text-xs font-black text-zinc-600 bg-zinc-100 border border-zinc-300 px-2.5 py-1 rounded-lg">
            5-Level Pitch Scale
          </span>
        </div>

        {/* Minimal Contrast Table */}
        <div className="grid grid-cols-1 sm:grid-cols-5 gap-2.5">
          {TONE_CONTRAST_SET.map((item) => {
            const isPlaying = playingTone === item.tone;
            return (
              <button
                key={item.tone}
                onClick={() => handlePlayContrast(item.tone, item.audioChar)}
                className={`p-3 rounded-xl border-2 text-left transition-all cursor-pointer flex flex-col justify-between ${
                  isPlaying
                    ? 'border-emerald-600 bg-emerald-50 shadow-[2px_2px_0px_0px_rgba(16,185,129,1)]'
                    : 'border-zinc-300 bg-white hover:border-zinc-950 shadow-[2px_2px_0px_0px_rgba(0,0,0,0.06)]'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-black uppercase tracking-wider text-zinc-500">
                    {item.tone === 0 ? 'Neutral' : `Tone ${item.tone}`}
                  </span>
                  <Volume2
                    className={`w-3.5 h-3.5 ${
                      isPlaying ? 'text-emerald-600 animate-pulse' : 'text-zinc-400'
                    }`}
                  />
                </div>

                <div className="my-2">
                  <div className="text-2xl font-black text-zinc-950 font-mono">
                    {item.pinyin}
                  </div>
                  <div className="text-sm font-bold text-zinc-500">{item.hanzi}</div>
                </div>

                <div>
                  <div className="text-[11px] font-black text-zinc-800 truncate">
                    {item.meaningEn}
                  </div>
                  <div className="text-[10px] font-bold text-zinc-400 mt-0.5">
                    {item.mark}
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        {/* Pitch Curve Visual Scale */}
        <div className="mt-5 p-4 bg-zinc-50 border border-zinc-200 rounded-xl">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-black text-zinc-700">
              Chao 5-Level Pitch Scale
            </span>
            <span className="text-[11px] font-bold text-zinc-500">
              5 (High) → 1 (Low)
            </span>
          </div>

          <svg viewBox="0 0 400 120" className="w-full h-28 bg-white border border-zinc-200 rounded-lg">
            {/* Grid lines */}
            <line x1="40" y1="20" x2="380" y2="20" stroke="#e4e4e7" strokeDasharray="3 3" />
            <line x1="40" y1="42" x2="380" y2="42" stroke="#e4e4e7" strokeDasharray="3 3" />
            <line x1="40" y1="65" x2="380" y2="65" stroke="#e4e4e7" strokeDasharray="3 3" />
            <line x1="40" y1="88" x2="380" y2="88" stroke="#e4e4e7" strokeDasharray="3 3" />
            <line x1="40" y1="110" x2="380" y2="110" stroke="#e4e4e7" strokeDasharray="3 3" />

            {/* Pitch numbers */}
            <text x="20" y="24" fontSize="10" fontWeight="bold" fill="#a1a1aa">5</text>
            <text x="20" y="46" fontSize="10" fontWeight="bold" fill="#a1a1aa">4</text>
            <text x="20" y="69" fontSize="10" fontWeight="bold" fill="#a1a1aa">3</text>
            <text x="20" y="92" fontSize="10" fontWeight="bold" fill="#a1a1aa">2</text>
            <text x="20" y="113" fontSize="10" fontWeight="bold" fill="#a1a1aa">1</text>

            {/* Tone 1: High flat (55) */}
            <path d="M 60 20 L 110 20" stroke="#059669" strokeWidth="4" strokeLinecap="round" />
            <text x="75" y="14" fontSize="10" fontWeight="900" fill="#059669">1st (55)</text>

            {/* Tone 2: Rising (35) */}
            <path d="M 135 65 L 185 20" stroke="#0284c7" strokeWidth="4" strokeLinecap="round" />
            <text x="150" y="14" fontSize="10" fontWeight="900" fill="#0284c7">2nd (35)</text>

            {/* Tone 3: Dipping (214) */}
            <path d="M 210 88 Q 235 110 260 42" fill="none" stroke="#d97706" strokeWidth="4" strokeLinecap="round" />
            <text x="225" y="14" fontSize="10" fontWeight="900" fill="#d97706">3rd (214)</text>

            {/* Tone 4: Falling (51) */}
            <path d="M 285 20 L 335 110" stroke="#dc2626" strokeWidth="4" strokeLinecap="round" />
            <text x="300" y="14" fontSize="10" fontWeight="900" fill="#dc2626">4th (51)</text>

            {/* Neutral */}
            <circle cx="365" cy="65" r="4" fill="#71717a" />
            <text x="350" y="52" fontSize="9" fontWeight="bold" fill="#71717a">Neutral</text>
          </svg>
        </div>
      </div>

      {/* Action Footer */}
      <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
        <button
          onClick={() => onStartUnit(1)}
          className="w-full sm:flex-1 py-3.5 px-6 bg-zinc-950 hover:bg-zinc-800 text-white font-black rounded-xl border-2 border-zinc-950 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] active:scale-98 transition-all flex items-center justify-center gap-2 cursor-pointer text-sm"
        >
          <Play className="w-4 h-4 fill-white" />
          Start Unit 1: Pinyin Overview & Initials
        </button>

        <button
          onClick={onOpenChart}
          className="w-full sm:w-auto py-3.5 px-6 bg-white hover:bg-zinc-100 text-zinc-950 font-black rounded-xl border-2 border-zinc-950 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] active:scale-98 transition-all flex items-center justify-center gap-2 cursor-pointer text-sm"
        >
          <BookOpen className="w-4 h-4" />
          Open Full Pinyin Chart
        </button>
      </div>
    </div>
  );
};
