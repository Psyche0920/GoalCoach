import React, { useState, useMemo } from 'react';
import { Search, Volume2, X, Play, Info, Check, Filter } from 'lucide-react';
import { 
  PINYIN_INITIALS_LIST, 
  PINYIN_FINALS_CATEGORIES, 
  PINYIN_CHART_SYLLABLES, 
  PinyinSyllableEntry 
} from '../data/pinyinData.ts';
import { playMandarinAudio } from '../utils/pinyinAudio.ts';

interface PinyinChartTableProps {
  onSelectSyllable?: (syllable: PinyinSyllableEntry) => void;
}

export const PinyinChartTable: React.FC<PinyinChartTableProps> = ({ onSelectSyllable }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<'all' | 'simple' | 'compound' | 'nasal'>('all');
  const [activeTone, setActiveTone] = useState<number | 'all'>('all');
  const [inspectingSyllable, setInspectingSyllable] = useState<PinyinSyllableEntry | null>(
    PINYIN_CHART_SYLLABLES[0]
  );
  const [playingTone, setPlayingTone] = useState<number | null>(null);

  // Normalize search for 'v' -> 'ü' or direct match
  const filteredSyllables = useMemo(() => {
    let list = PINYIN_CHART_SYLLABLES;
    const query = searchQuery.trim().toLowerCase();

    if (query) {
      const normalizedQuery = query.replace(/v/g, 'v');
      list = list.filter((item) => {
        const matchesSyllable = item.syllable.toLowerCase().includes(normalizedQuery) ||
          (query.includes('v') && item.final.includes('ü'));
        const matchesExample = item.exampleWord?.pinyin.toLowerCase().includes(query) ||
          item.exampleWord?.meaningEn.toLowerCase().includes(query);
        return matchesSyllable || matchesExample;
      });
    }

    if (selectedCategory !== 'all') {
      const allowedFinals = PINYIN_FINALS_CATEGORIES[selectedCategory];
      list = list.filter((item) => allowedFinals.includes(item.final));
    }

    return list;
  }, [searchQuery, selectedCategory]);

  // Audio player for specific tone of a syllable
  const handlePlayTone = (entry: PinyinSyllableEntry, tone: number) => {
    const audioChar = entry.audioChars[tone];
    if (!audioChar) return;

    setPlayingTone(tone);
    playMandarinAudio(audioChar, {
      rate: 0.85,
      onEnd: () => setPlayingTone(null),
    });
  };

  const handleCellClick = (entry: PinyinSyllableEntry) => {
    setInspectingSyllable(entry);
    if (onSelectSyllable) onSelectSyllable(entry);
    // Play default tone (1st if available, or first valid)
    const toneToPlay = entry.validTones[0] ?? 1;
    handlePlayTone(entry, toneToPlay);
  };

  return (
    <div className="space-y-6">
      {/* Search & Filter Toolbar */}
      <div className="bg-white border-2 border-zinc-950 rounded-2xl p-4 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] flex flex-col md:flex-row gap-3 items-center justify-between">
        {/* Search Bar */}
        <div className="relative w-full md:w-72">
          <Search className="w-4 h-4 text-zinc-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search syllable (e.g., ma, lv, chi)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-8 py-2 text-xs font-bold bg-zinc-50 border-2 border-zinc-300 rounded-xl focus:border-zinc-950 focus:bg-white focus:outline-none transition-all placeholder:text-zinc-400"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-700 cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Finals Category Filters */}
        <div className="flex flex-wrap items-center gap-1.5 w-full md:w-auto">
          {(
            [
              { id: 'all', label: 'All Finals' },
              { id: 'simple', label: 'Simple (a, o, e...)' },
              { id: 'compound', label: 'Compound (ai, ao...)' },
              { id: 'nasal', label: 'Nasal (an, ang...)' },
            ] as const
          ).map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-black transition-all cursor-pointer ${
                selectedCategory === cat.id
                  ? 'bg-zinc-950 text-white shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]'
                  : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200 border border-zinc-300'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* Tone Filter */}
        <div className="flex items-center gap-1 w-full md:w-auto justify-end border-t md:border-t-0 pt-2 md:pt-0 border-zinc-100">
          <span className="text-[11px] font-bold text-zinc-500 mr-1">Tone:</span>
          {(['all', 1, 2, 3, 4] as const).map((t) => (
            <button
              key={t}
              onClick={() => setActiveTone(t)}
              className={`w-7 h-7 rounded-lg text-xs font-black flex items-center justify-center transition-all cursor-pointer ${
                activeTone === t
                  ? 'bg-emerald-600 text-white font-mono'
                  : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200'
              }`}
            >
              {t === 'all' ? 'All' : `${t}`}
            </button>
          ))}
        </div>
      </div>

      {/* Syllable Inspector Card (Fixed Preview for Clicked Syllable) */}
      {inspectingSyllable && (
        <div className="bg-white border-2 border-zinc-950 rounded-2xl p-5 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] flex flex-col md:flex-row items-center justify-between gap-5">
          <div className="flex items-center gap-5 w-full md:w-auto">
            {/* Big Syllable Display */}
            <div className="w-20 h-20 bg-zinc-950 text-white rounded-2xl flex flex-col items-center justify-center border-2 border-zinc-950 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
              <span className="text-2xl font-black font-mono tracking-tight">
                {inspectingSyllable.syllable}
              </span>
              <span className="text-[10px] text-zinc-400 font-bold uppercase tracking-wider mt-0.5">
                {inspectingSyllable.initial || 'Ø'} + {inspectingSyllable.final}
              </span>
            </div>

            {/* Syllable Details */}
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-black text-zinc-950">
                  Mandarin Syllable Audio
                </span>
                <span className="text-[10px] font-bold px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded">
                  Tap Tone to Listen
                </span>
              </div>
              {inspectingSyllable.exampleWord ? (
                <div className="flex items-center gap-2 mt-1.5 text-xs text-zinc-600">
                  <span className="font-bold">Example:</span>
                  <span className="font-black text-zinc-900">
                    {inspectingSyllable.exampleWord.hanzi}
                  </span>
                  <span className="font-mono text-zinc-700">
                    ({inspectingSyllable.exampleWord.pinyin})
                  </span>
                  <span className="text-zinc-500">
                    — {inspectingSyllable.exampleWord.meaningEn}
                  </span>
                </div>
              ) : (
                <p className="text-xs text-zinc-500 font-medium mt-1">
                  Click any of the 4 tones below to hear the native pronunciation.
                </p>
              )}
            </div>
          </div>

          {/* Tone Audio Buttons */}
          <div className="flex flex-wrap items-center gap-2 w-full md:w-auto justify-start md:justify-end">
            {[1, 2, 3, 4].map((t) => {
              const pinyinStr = inspectingSyllable.pinyinWithTones[t];
              const isValid = inspectingSyllable.validTones.includes(t);
              const isPlaying = playingTone === t;

              if (!isValid || !pinyinStr) {
                return (
                  <div
                    key={t}
                    className="px-3 py-2 bg-zinc-100 border border-zinc-200 rounded-xl text-zinc-300 font-mono text-xs cursor-not-allowed select-none"
                  >
                    Tone {t} —
                  </div>
                );
              }

              return (
                <button
                  key={t}
                  onClick={() => handlePlayTone(inspectingSyllable, t)}
                  className={`px-3.5 py-2 rounded-xl border-2 font-mono text-sm font-black flex items-center gap-2 transition-all cursor-pointer ${
                    isPlaying
                      ? 'bg-emerald-600 text-white border-zinc-950 scale-105 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]'
                      : 'bg-white hover:bg-zinc-50 text-zinc-950 border-zinc-950 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] active:scale-95'
                  }`}
                >
                  <Volume2 className={`w-3.5 h-3.5 ${isPlaying ? 'animate-pulse' : ''}`} />
                  <span>{pinyinStr}</span>
                  <span className="text-[10px] font-sans font-bold text-zinc-500">
                    (T{t})
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Syllable Grid Matrix */}
      <div className="bg-white border-2 border-zinc-950 rounded-2xl p-5 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)]">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <span className="text-sm font-black text-zinc-950">
              Interactive Syllables
            </span>
            <span className="text-xs font-bold text-zinc-500">
              ({filteredSyllables.length} matches)
            </span>
          </div>
          <span className="text-[11px] font-bold text-zinc-400">
            Tip: Click any cell to hear pronunciation
          </span>
        </div>

        {filteredSyllables.length === 0 ? (
          <div className="text-center py-12 text-zinc-400">
            <p className="text-sm font-bold">No syllables match your search filter.</p>
            <button
              onClick={() => {
                setSearchQuery('');
                setSelectedCategory('all');
              }}
              className="mt-3 text-xs font-black text-emerald-600 underline cursor-pointer"
            >
              Reset filters
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-2.5 max-h-[500px] overflow-y-auto pr-1">
            {filteredSyllables.map((entry) => {
              const isSelected = inspectingSyllable?.syllable === entry.syllable;
              // Determine display pinyin depending on activeTone
              const displayPinyin =
                activeTone !== 'all' && entry.pinyinWithTones[activeTone]
                  ? entry.pinyinWithTones[activeTone]
                  : entry.pinyinWithTones[entry.validTones[0]] || entry.syllable;

              return (
                <button
                  key={entry.syllable}
                  onClick={() => handleCellClick(entry)}
                  className={`p-2.5 rounded-xl border-2 text-left transition-all cursor-pointer flex flex-col justify-between ${
                    isSelected
                      ? 'border-emerald-600 bg-emerald-50 shadow-[2px_2px_0px_0px_rgba(16,185,129,1)]'
                      : 'border-zinc-200 bg-zinc-50 hover:border-zinc-950 hover:bg-white shadow-[1px_1px_0px_0px_rgba(0,0,0,0.04)]'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-base font-black text-zinc-950 font-mono">
                      {displayPinyin}
                    </span>
                    <Volume2 className="w-3 h-3 text-zinc-400" />
                  </div>

                  <div className="flex items-center gap-1 mt-1">
                    <span className="text-[10px] font-bold text-zinc-400">
                      tones:
                    </span>
                    <div className="flex gap-0.5">
                      {[1, 2, 3, 4].map((t) => (
                        <span
                          key={t}
                          className={`text-[9px] font-bold px-1 rounded ${
                            entry.validTones.includes(t)
                              ? 'bg-zinc-200 text-zinc-700'
                              : 'text-zinc-300'
                          }`}
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
