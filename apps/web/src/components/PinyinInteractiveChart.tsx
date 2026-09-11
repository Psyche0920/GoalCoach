import React, { useState, useMemo } from 'react';
import { Volume2, Sparkles, BookOpen, Mic, X, CheckCircle2, ChevronRight, Layers, HelpCircle } from 'lucide-react';
import { CHART_INITIALS, CHART_FINALS, PINYIN_GRID_CELLS, PinyinChartCellData } from '../data/pinyinChartMatrix';
import { PinyinPhonemeCard } from '../data/pinyinUnitsData';
import { playMandarinAudio } from '../utils/pinyinAudio';

interface PinyinInteractiveChartProps {
  onSelectCardForPractice?: (card: PinyinPhonemeCard, mode: 'knowledge' | 'practice') => void;
}

export const PinyinInteractiveChart: React.FC<PinyinInteractiveChartProps> = ({
  onSelectCardForPractice,
}) => {
  const [selectedTone, setSelectedTone] = useState<number | 'all'>('all');
  const [hoveredCell, setHoveredCell] = useState<{ initial: string; final: string } | null>(null);
  const [activeCell, setActiveCell] = useState<PinyinChartCellData | null>(null);
  const [activeToneInModal, setActiveToneInModal] = useState<number>(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentlyPlayingKey, setCurrentlyPlayingKey] = useState<string | null>(null);

  // High quality Mandarin Audio Player with TTS endpoint + SpeechSynthesis fallback
  const playPinyinAudio = (text: string, playKey?: string, rate: number = 0.88) => {
    if (playKey) setCurrentlyPlayingKey(playKey);
    playMandarinAudio(text, {
      rate,
      onEnd: () => setCurrentlyPlayingKey(null),
    });
  };

  const handleCellClick = (cell: PinyinChartCellData) => {
    setActiveCell(cell);
    const toneToPlay = selectedTone === 'all' ? (cell.validTones[0] || 1) : selectedTone;
    setActiveToneInModal(toneToPlay);
    const audioText = cell.audioChars[toneToPlay] || cell.pinyinWithTones[toneToPlay] || cell.syllable;
    const playKey = `${cell.initial}_${cell.final}`;
    playPinyinAudio(audioText, playKey);
  };

  const handleInitialClick = (initial: string) => {
    const soundMap: Record<string, string> = {
      'Ø': '啊', 'b': '波', 'p': '坡', 'm': '摸', 'f': '佛',
      'd': '得', 't': '特', 'n': '呢', 'l': '勒',
      'g': '哥', 'k': '科', 'h': '喝',
      'j': '鸡', 'q': '七', 'x': '西',
      'zh': '知', 'ch': '吃', 'sh': '诗', 'r': '日',
      'z': '资', 'c': '呲', 's': '思',
      'w': '屋', 'y': '衣'
    };
    playPinyinAudio(soundMap[initial] || initial);
  };

  const handleFinalClick = (final: string) => {
    const soundMap: Record<string, string> = {
      'a': '啊', 'ai': '爱', 'ao': '熬', 'an': '安', 'ang': '昂',
      'e': '饿', 'ei': '欸', 'en': '恩', 'eng': '鞥', 'er': '二',
      'o': '喔', 'ou': '欧', 'ong': '轰',
      'i': '衣', 'ia': '呀', 'iao': '要', 'ie': '也', 'iu': '优', 'ian': '烟', 'in': '因', 'iang': '央', 'ing': '英', 'iong': '庸',
      'u': '乌', 'ua': '蛙', 'uo': '窝', 'uai': '歪', 'ui': '威', 'uan': '弯', 'un': '温', 'uang': '汪',
      'ü': '迂', 'üe': '约', 'üan': '冤', 'ün': '晕'
    };
    playPinyinAudio(soundMap[final] || final);
  };

  // Convert active cell to PinyinPhonemeCard for Practice/Knowledge view
  const currentPhonemeCard: PinyinPhonemeCard | null = useMemo(() => {
    if (!activeCell) return null;
    const tone = activeToneInModal;
    const tonePinyin = activeCell.pinyinWithTones[tone] || activeCell.syllable;
    const anchorChar = activeCell.audioChars[tone] || activeCell.anchorWord?.hanzi || activeCell.syllable;

    return {
      id: `chart_${activeCell.initial}_${activeCell.final}_t${tone}`,
      unitNumber: 1,
      pinyin: tonePinyin,
      category: 'chart',
      subCategory: `Initial: ${activeCell.initial === 'Ø' ? 'Zero' : activeCell.initial} | Final: ${activeCell.final}`,
      anchorHanzi: anchorChar,
      hanziPinyin: tonePinyin,
      meaningEn: activeCell.anchorWord?.meaningEn || `Mandarin syllable (${activeCell.syllable}, tone ${tone})`,
      acousticTip: `Formed by Initial "${activeCell.initial === 'Ø' ? 'None' : activeCell.initial}" + Final "${activeCell.final}".`,
      audioTarget: anchorChar,
      acceptableMatches: [anchorChar, tonePinyin, activeCell.syllable],
      exampleWords: activeCell.anchorWord ? [activeCell.anchorWord] : undefined,
    };
  }, [activeCell, activeToneInModal]);

  return (
    <div className="space-y-6">
      {/* Friendly, Non-Academic English Overview Card */}
      <div className="bg-gradient-to-br from-indigo-50 via-white to-sky-50 border border-indigo-100 rounded-2xl p-6 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-800">
                Unit 1 Sound Matrix
              </span>
              <span className="text-xs text-slate-500 font-medium flex items-center gap-1">
                <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                Audio on every single tap
              </span>
            </div>
            <h2 className="text-xl font-bold text-slate-900 tracking-tight">
              Interactive Mandarin Pinyin Chart
            </h2>
            <p className="text-sm text-slate-600 max-w-3xl leading-relaxed">
              Mandarin is beautifully modular! Every single spoken syllable is simply an{' '}
              <strong className="text-indigo-900">Initial (consonant row)</strong> combined with a{' '}
              <strong className="text-indigo-900">Final (vowel column)</strong> and pronounced with one of{' '}
              <strong className="text-indigo-900">4 musical pitch contours</strong>. 
              Click any cell to hear authentic pronunciation.
            </p>
          </div>

          {/* Quick Stats Pill */}
          <div className="flex items-center gap-3 self-start lg:self-center bg-white/80 backdrop-blur border border-indigo-200/60 rounded-xl px-4 py-2.5 shadow-sm">
            <div className="text-center">
              <div className="text-lg font-bold text-indigo-600">23</div>
              <div className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Initials</div>
            </div>
            <div className="h-7 w-px bg-slate-200" />
            <div className="text-center">
              <div className="text-lg font-bold text-sky-600">36</div>
              <div className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Finals</div>
            </div>
            <div className="h-7 w-px bg-slate-200" />
            <div className="text-center">
              <div className="text-lg font-bold text-emerald-600">4</div>
              <div className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Tones</div>
            </div>
          </div>
        </div>

        {/* Tone Filter Controls */}
        <div className="mt-5 pt-4 border-t border-indigo-100 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-700">Display Tone:</span>
            <div className="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200 text-xs">
              <button
                type="button"
                onClick={() => setSelectedTone('all')}
                className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
                  selectedTone === 'all'
                    ? 'bg-white text-indigo-700 shadow-sm font-semibold'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                All (1-4)
              </button>
              <button
                type="button"
                onClick={() => setSelectedTone(1)}
                className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
                  selectedTone === 1
                    ? 'bg-red-500 text-white shadow-sm font-semibold'
                    : 'text-slate-600 hover:text-red-700'
                }`}
              >
                1st (High —)
              </button>
              <button
                type="button"
                onClick={() => setSelectedTone(2)}
                className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
                  selectedTone === 2
                    ? 'bg-amber-500 text-white shadow-sm font-semibold'
                    : 'text-slate-600 hover:text-amber-700'
                }`}
              >
                2nd (Rising /)
              </button>
              <button
                type="button"
                onClick={() => setSelectedTone(3)}
                className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
                  selectedTone === 3
                    ? 'bg-emerald-600 text-white shadow-sm font-semibold'
                    : 'text-slate-600 hover:text-emerald-700'
                }`}
              >
                3rd (Dip ∨)
              </button>
              <button
                type="button"
                onClick={() => setSelectedTone(4)}
                className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
                  selectedTone === 4
                    ? 'bg-blue-600 text-white shadow-sm font-semibold'
                    : 'text-slate-600 hover:text-blue-700'
                }`}
              >
                4th (Drop \)
              </button>
            </div>
          </div>

          <div className="text-xs text-slate-500 flex items-center gap-1.5">
            <span className="inline-block w-2.5 h-2.5 rounded-full bg-indigo-500 animate-pulse" />
            Tip: Click column headers (finals) or row headers (initials) to isolate individual phonemes!
          </div>
        </div>
      </div>

      {/* Interactive Table Container */}
      <div className="relative border border-slate-200 rounded-2xl bg-white shadow-sm overflow-hidden">
        <div className="overflow-x-auto max-h-[580px] scrollbar-thin scrollbar-thumb-slate-300">
          <table className="w-full text-left border-collapse text-xs">
            {/* Sticky Header with Finals */}
            <thead className="sticky top-0 z-20 bg-slate-50 shadow-sm">
              <tr>
                <th className="sticky left-0 z-30 bg-slate-100 p-2.5 font-bold text-slate-700 border-b border-r border-slate-200 min-w-[72px] text-center">
                  <div className="text-[10px] text-slate-400 uppercase tracking-wider">Initials ↓</div>
                  <div className="text-xs text-indigo-700 font-bold">Finals →</div>
                </th>
                {CHART_FINALS.map((final) => {
                  const isHoveredCol = hoveredCell?.final === final;
                  return (
                    <th
                      key={final}
                      onClick={() => handleFinalClick(final)}
                      className={`p-2 font-bold border-b border-r border-slate-200 text-center min-w-[62px] cursor-pointer select-none transition-colors ${
                        isHoveredCol
                          ? 'bg-indigo-100 text-indigo-900 border-indigo-300'
                          : 'text-slate-700 hover:bg-indigo-50 hover:text-indigo-600'
                      }`}
                      title={`Final: ${final} (Click to listen)`}
                    >
                      <div className="flex items-center justify-center gap-1">
                        <span>{final}</span>
                        <Volume2 className="w-2.5 h-2.5 opacity-40 group-hover:opacity-100" />
                      </div>
                    </th>
                  );
                })}
              </tr>
            </thead>

            {/* Rows with Initials */}
            <tbody>
              {CHART_INITIALS.map((initial) => {
                const isHoveredRow = hoveredCell?.initial === initial;
                return (
                  <tr key={initial} className={isHoveredRow ? 'bg-indigo-50/40' : ''}>
                    {/* Sticky Initial Header Column */}
                    <th
                      onClick={() => handleInitialClick(initial)}
                      className={`sticky left-0 z-10 p-2 font-bold border-b border-r border-slate-200 text-center cursor-pointer select-none transition-colors ${
                        isHoveredRow
                          ? 'bg-indigo-100 text-indigo-900 border-indigo-300'
                          : 'bg-slate-50 text-slate-800 hover:bg-indigo-50 hover:text-indigo-600'
                      }`}
                      title={`Initial: ${initial} (Click to listen)`}
                    >
                      <div className="flex items-center justify-center gap-1">
                        <span className="text-sm font-semibold">{initial === 'Ø' ? 'Ø (Zero)' : initial}</span>
                      </div>
                    </th>

                    {/* Syllable Cells */}
                    {CHART_FINALS.map((final) => {
                      const cellKey = `${initial}_${final}`;
                      const cellData = PINYIN_GRID_CELLS[cellKey];
                      const isHovered = hoveredCell?.initial === initial && hoveredCell?.final === final;
                      const isActive = activeCell?.syllable === cellData?.syllable && activeCell?.initial === initial;

                      if (!cellData) {
                        return (
                          <td
                            key={final}
                            onMouseEnter={() => setHoveredCell({ initial, final })}
                            onMouseLeave={() => setHoveredCell(null)}
                            className="p-1 border-b border-r border-slate-100 bg-slate-50/20 text-center text-slate-200 select-none text-[10px]"
                          >
                            ·
                          </td>
                        );
                      }

                      // Determine which text to show based on selected tone
                      let displayPinyin = cellData.syllable;
                      if (selectedTone !== 'all' && cellData.pinyinWithTones[selectedTone]) {
                        displayPinyin = cellData.pinyinWithTones[selectedTone];
                      }

                      const isCellPlaying = currentlyPlayingKey === `${initial}_${final}`;

                      return (
                        <td
                          key={final}
                          onClick={() => handleCellClick(cellData)}
                          onMouseEnter={() => setHoveredCell({ initial, final })}
                          onMouseLeave={() => setHoveredCell(null)}
                          className={`p-2 border-b border-r border-slate-200 text-center cursor-pointer select-none transition-all duration-150 relative ${
                            isActive || isCellPlaying
                              ? 'bg-indigo-600 text-white font-bold shadow-inner ring-2 ring-indigo-400'
                              : isHovered
                              ? 'bg-indigo-200/70 text-indigo-950 font-bold scale-105 z-10 shadow-sm'
                              : 'hover:bg-indigo-100 text-slate-800 font-medium'
                          }`}
                        >
                          <div className="flex items-center justify-center gap-1">
                            <span className="text-xs font-mono font-semibold tracking-tight">{displayPinyin}</span>
                            {isCellPlaying && (
                              <Volume2 className="w-3 h-3 text-amber-300 animate-pulse" />
                            )}
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Cell Detail Inspection Drawer / Modal */}
      {activeCell && (
        <div className="bg-slate-900 text-white rounded-2xl p-6 shadow-xl border border-slate-800 transition-all animate-in fade-in slide-in-from-bottom-3 duration-200">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            {/* Left: Pronunciation Overview */}
            <div className="flex items-start gap-5">
              <div className="w-16 h-16 rounded-2xl bg-indigo-600/30 border border-indigo-500/50 flex flex-col items-center justify-center shrink-0">
                <span className="text-2xl font-black text-indigo-300">
                  {activeCell.pinyinWithTones[activeToneInModal] || activeCell.syllable}
                </span>
                <span className="text-[10px] text-indigo-200/80 font-mono">
                  Tone {activeToneInModal}
                </span>
              </div>

              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-lg font-bold text-white">
                    {activeCell.anchorWord?.hanzi || activeCell.audioChars[activeToneInModal] || activeCell.syllable}
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                    Initial: {activeCell.initial === 'Ø' ? 'None' : activeCell.initial} + Final: {activeCell.final}
                  </span>
                </div>
                <p className="text-xs text-slate-400">
                  {activeCell.anchorWord?.meaningEn || 'Mandarin syllable composition'}
                </p>
                <div className="flex items-center gap-2 pt-1">
                  <button
                    type="button"
                    onClick={() => {
                      const sound = activeCell.audioChars[activeToneInModal] || activeCell.pinyinWithTones[activeToneInModal];
                      playPinyinAudio(sound);
                    }}
                    className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-sm transition-colors"
                  >
                    <Volume2 className="w-3.5 h-3.5" />
                    Play Pronunciation
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      const sound = activeCell.audioChars[activeToneInModal] || activeCell.pinyinWithTones[activeToneInModal];
                      playPinyinAudio(sound, undefined, 0.6);
                    }}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition-colors"
                  >
                    0.6x Slow
                  </button>
                </div>
              </div>
            </div>

            {/* Middle: 4 Tones Quick Selector */}
            <div className="space-y-1.5">
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Audition Tone Variants:
              </div>
              <div className="flex items-center gap-1.5">
                {[1, 2, 3, 4].map((t) => {
                  const hasTone = activeCell.validTones.includes(t);
                  const isCurrent = activeToneInModal === t;
                  const pinyinForTone = activeCell.pinyinWithTones[t] || activeCell.syllable;
                  const charForTone = activeCell.audioChars[t] || '';

                  return (
                    <button
                      key={t}
                      type="button"
                      disabled={!hasTone}
                      onClick={() => {
                        setActiveToneInModal(t);
                        playPinyinAudio(charForTone || pinyinForTone);
                      }}
                      className={`px-3 py-1.5 rounded-xl border text-xs font-medium transition-all flex flex-col items-center min-w-[54px] ${
                        !hasTone
                          ? 'opacity-30 border-slate-800 bg-slate-800/40 cursor-not-allowed text-slate-500'
                          : isCurrent
                          ? 'border-indigo-400 bg-indigo-500/20 text-white font-bold ring-2 ring-indigo-500/50'
                          : 'border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-200'
                      }`}
                    >
                      <span>{pinyinForTone}</span>
                      <span className="text-[10px] text-slate-400">{charForTone || `T${t}`}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Right: Knowledge & Practice Direct Action Buttons */}
            <div className="flex items-center gap-3 pt-2 md:pt-0 border-t md:border-t-0 border-slate-800">
              {currentPhonemeCard && onSelectCardForPractice && (
                <>
                  <button
                    type="button"
                    onClick={() => onSelectCardForPractice(currentPhonemeCard, 'knowledge')}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-white text-xs font-semibold transition-all shadow-sm"
                  >
                    <BookOpen className="w-4 h-4 text-sky-400" />
                    Knowledge Card
                  </button>
                  <button
                    type="button"
                    onClick={() => onSelectCardForPractice(currentPhonemeCard, 'practice')}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-semibold transition-all shadow-md"
                  >
                    <Mic className="w-4 h-4" />
                    Practice Card
                  </button>
                </>
              )}
              <button
                type="button"
                onClick={() => setActiveCell(null)}
                className="p-2 rounded-xl hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
                title="Close"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
