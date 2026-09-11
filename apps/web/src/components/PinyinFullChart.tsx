import React, { useState, useMemo } from 'react';
import { 
  Search, 
  Volume2, 
  X, 
  Play, 
  Info, 
  ChevronDown, 
  ChevronUp, 
  Layers, 
  Sparkles,
  BookOpen,
  Mic,
  ArrowRight
} from 'lucide-react';
import { 
  PINYIN_INITIALS_LIST, 
  PINYIN_FINALS_CATEGORIES, 
  PINYIN_CHART_SYLLABLES, 
  PinyinSyllableEntry,
  PinyinPhonemeCardItem
} from '../data/pinyinData.ts';
import { playMandarinAudio } from '../utils/pinyinAudio.ts';

interface PinyinFullChartProps {
  onOpenCard?: (item: PinyinPhonemeCardItem, mode: 'knowledge' | 'practice') => void;
}

export const PinyinFullChart: React.FC<PinyinFullChartProps> = ({ onOpenCard }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedInitialGroup, setSelectedInitialGroup] = useState<string>('all');
  const [selectedFinalCategory, setSelectedFinalCategory] = useState<'all' | 'simple' | 'compound' | 'nasal'>('all');
  const [selectedSyllable, setSelectedSyllable] = useState<PinyinSyllableEntry | null>(
    PINYIN_CHART_SYLLABLES[0]
  );
  const [showIntroGuide, setShowIntroGuide] = useState(true);
  const [playingKey, setPlayingKey] = useState<string | null>(null);

  // Play audio with visual playing indicator
  const playAudio = (text: string, key: string, rate: number = 0.85) => {
    setPlayingKey(key);
    playMandarinAudio(text, {
      rate,
      onEnd: () => setPlayingKey(null),
    });
  };

  // Initial sound mappings for standalone initial clicks
  const initialAudios: Record<string, { audio: string; label: string; tip: string }> = {
    'b': { audio: '八', label: 'b (bō)', tip: 'Unaspirated voiceless stop (like "p" in "speak")' },
    'p': { audio: '坡', label: 'p (pō)', tip: 'Aspirated burst of air (like "p" in "peak")' },
    'm': { audio: '摸', label: 'm (mō)', tip: 'Nasal voiced bilabial (like "m" in "mother")' },
    'f': { audio: '佛', label: 'f (fó)', tip: 'Labiodental fricative (like "f" in "fish")' },
    'd': { audio: '大', label: 'd (dē)', tip: 'Unaspirated dental stop (like "t" in "stop")' },
    't': { audio: '他', label: 't (tē)', tip: 'Aspirated burst (like "t" in "tea")' },
    'n': { audio: '你', label: 'n (nē)', tip: 'Alveolar nasal (like "n" in "nice")' },
    'l': { audio: '来', label: 'l (lē)', tip: 'Alveolar lateral (like "l" in "love")' },
    'g': { audio: '哥', label: 'g (gē)', tip: 'Velar stop (like "k" in "skill")' },
    'k': { audio: '开', label: 'k (kē)', tip: 'Aspirated velar stop (like "k" in "kite")' },
    'h': { audio: '喝', label: 'h (hē)', tip: 'Velar fricative (rougher "h" in "hat")' },
    'j': { audio: '几', label: 'j (jī)', tip: 'Palatal with flat tongue (like "j" in "jeep")' },
    'q': { audio: '七', label: 'q (qī)', tip: 'Palatal with flat tongue and strong air puff' },
    'x': { audio: '西', label: 'x (xī)', tip: 'Palatal fricative with corners of mouth pulled wide' },
    'zh': { audio: '知', label: 'zh (zhī)', tip: 'Retroflex: tongue tip curled back toward hard palate' },
    'ch': { audio: '吃', label: 'ch (chī)', tip: 'Retroflex: tongue tip curled back with strong puff' },
    'sh': { audio: '十', label: 'sh (shí)', tip: 'Retroflex: tongue tip curled back, unvoiced hiss' },
    'r': { audio: '日', label: 'r (rì)', tip: 'Retroflex: tongue tip curled back, voiced buzz' },
    'z': { audio: '字', label: 'z (zī)', tip: 'Dental sibilant: tongue flat against back of front teeth' },
    'c': { audio: '词', label: 'c (cī)', tip: 'Dental sibilant with strong air puff (like "ts" in "cats")' },
    's': { audio: '四', label: 's (sī)', tip: 'Dental sibilant unvoiced hiss (like "s" in "sun")' },
    'y': { audio: '一', label: 'y (yī)', tip: 'Semi-vowel glide (like "y" in "yes")' },
    'w': { audio: '五', label: 'w (wū)', tip: 'Semi-vowel glide (like "w" in "water")' },
  };

  // Final sound mappings for standalone final clicks
  const finalAudios: Record<string, { audio: string; label: string; tip: string }> = {
    'a': { audio: '啊', label: 'a (ā)', tip: 'Open wide mouth, tongue relaxed in center' },
    'o': { audio: '哦', label: 'o (ō)', tip: 'Rounded lips, back vowel' },
    'e': { audio: '鹅', label: 'e (é)', tip: 'Corners of mouth pulled back, unrounded' },
    'i': { audio: '衣', label: 'i (yī)', tip: 'High front vowel, wide smile' },
    'u': { audio: '屋', label: 'u (wū)', tip: 'High back vowel, tight rounded lips' },
    'ü': { audio: '鱼', label: 'ü (yú)', tip: 'Make "ee" sound with mouth, then round lips tight like "oo"' },
    'ai': { audio: '爱', label: 'ai (ài)', tip: 'Glide from open "a" to high "i"' },
    'ei': { audio: '杯', label: 'ei (bēi)', tip: 'Glide from "e" to high "i"' },
    'ao': { audio: '包', label: 'ao (bāo)', tip: 'Glide from open "a" to rounded "o"' },
    'ou': { audio: '狗', label: 'ou (gǒu)', tip: 'Glide from "o" to rounded "u"' },
    'an': { audio: '安', label: 'an (ān)', tip: 'Front nasal: tongue tip hits ridge behind front teeth' },
    'en': { audio: '恩', label: 'en (ēn)', tip: 'Front nasal: neutral vowel into -n' },
    'ang': { audio: '昂', label: 'ang (áng)', tip: 'Back nasal: back of tongue lifts against soft palate' },
    'eng': { audio: '鞥', label: 'eng (ēng)', tip: 'Back nasal resonance' },
    'ing': { audio: '英', label: 'ing (yīng)', tip: 'High front vowel into back nasal -ng' },
    'ong': { audio: '轰', label: 'ong (hōng)', tip: 'Rounded back nasal' },
    'er': { audio: '二', label: 'er (èr)', tip: 'Retroflex vowel: curl tongue tip while vocalizing' },
  };

  // Initial Groups Filter Options
  const initialGroups = [
    { id: 'all', label: 'All Initials' },
    { id: 'labial', label: 'Labial (b, p, m, f)', list: ['b', 'p', 'm', 'f'] },
    { id: 'alveolar', label: 'Alveolar (d, t, n, l)', list: ['d', 't', 'n', 'l'] },
    { id: 'velar', label: 'Velar (g, k, h)', list: ['g', 'k', 'h'] },
    { id: 'palatal', label: 'Palatal (j, q, x)', list: ['j', 'q', 'x'] },
    { id: 'retroflex', label: 'Retroflex (zh, ch, sh, r)', list: ['zh', 'ch', 'sh', 'r'] },
    { id: 'dental', label: 'Dental (z, c, s)', list: ['z', 'c', 's'] },
    { id: 'glides', label: 'Glides (y, w)', list: ['y', 'w'] },
  ];

  // Finals list for table columns
  const finalsList = useMemo(() => {
    if (selectedFinalCategory === 'all') {
      return [
        'a', 'o', 'e', 'i', 'u', 'ü',
        'ai', 'ei', 'ao', 'ou', 'ia', 'ie', 'ua', 'uo', 'üe',
        'an', 'en', 'in', 'un', 'ün', 'ang', 'eng', 'ing', 'ong',
        'er'
      ];
    }
    return PINYIN_FINALS_CATEGORIES[selectedFinalCategory] || [];
  }, [selectedFinalCategory]);

  // Syllable Matrix Map for instant lookup: `matrix[initial][final] = entry`
  const syllableMatrix = useMemo(() => {
    const map: Record<string, Record<string, PinyinSyllableEntry>> = {};
    for (const entry of PINYIN_CHART_SYLLABLES) {
      if (!map[entry.initial]) {
        map[entry.initial] = {};
      }
      map[entry.initial][entry.final] = entry;
    }
    return map;
  }, []);

  // Filtered initials list
  const filteredInitials = useMemo(() => {
    if (selectedInitialGroup === 'all') return PINYIN_INITIALS_LIST;
    const group = initialGroups.find((g) => g.id === selectedInitialGroup);
    return group?.list || PINYIN_INITIALS_LIST;
  }, [selectedInitialGroup]);

  // Filtered syllables for search card view
  const searchResults = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return null;
    return PINYIN_CHART_SYLLABLES.filter((item) => {
      const matchSyllable = item.syllable.toLowerCase().includes(q) ||
        (q.includes('v') && item.final.includes('ü'));
      const matchExample = item.exampleWord?.hanzi.includes(q) ||
        item.exampleWord?.pinyin.toLowerCase().includes(q) ||
        item.exampleWord?.meaningEn.toLowerCase().includes(q);
      return matchSyllable || matchExample;
    });
  }, [searchQuery]);

  // Convert syllable to card item for Knowledge/Practice modal
  const openSyllableInCard = (entry: PinyinSyllableEntry, mode: 'knowledge' | 'practice') => {
    if (!onOpenCard) return;
    const cardItem: PinyinPhonemeCardItem = {
      id: `syl_${entry.syllable}`,
      pinyin: entry.pinyinWithTones[1] || entry.pinyinWithTones[entry.validTones[0]] || entry.syllable,
      category: 'syllable',
      audioTarget: entry.audioChars[1] || entry.audioChars[entry.validTones[0]] || entry.syllable,
      anchorHanzi: entry.exampleWord?.hanzi || entry.audioChars[1] || entry.audioChars[entry.validTones[0]] || '字',
      hanziPinyin: entry.exampleWord?.pinyin || entry.pinyinWithTones[1] || entry.syllable,
      meaningEn: entry.exampleWord?.meaningEn || 'Mandarin syllable',
      acousticTip: `Formed by Initial "${entry.initial || 'zero'}" + Final "${entry.final}".`,
      exampleWords: entry.exampleWord ? [entry.exampleWord] : [],
    };
    onOpenCard(cardItem, mode);
  };

  return (
    <div className="space-y-6">
      {/* ========================================================= */}
      {/* 1. COMPREHENSIVE INTRODUCTORY ENGLISH OVERVIEW               */}
      {/* ========================================================= */}
      <div className="bg-white border-2 border-zinc-950 rounded-3xl p-6 sm:p-7 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] transition-all">
        <div className="flex items-center justify-between pb-3 border-b-2 border-zinc-100">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-black uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-sky-100 text-sky-800 border border-sky-200">
              Interactive Guide & Pinyin System
            </span>
            <span className="text-xs font-bold text-zinc-400">AllSet Learning Reference</span>
          </div>

          <button
            onClick={() => setShowIntroGuide(!showIntroGuide)}
            className="flex items-center gap-1 text-xs font-black text-zinc-600 hover:text-zinc-950 cursor-pointer"
          >
            <span>{showIntroGuide ? 'Hide Overview' : 'Show Overview (介绍)'}</span>
            {showIntroGuide ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>

        {showIntroGuide && (
          <div className="pt-4 space-y-4 animate-fadeIn">
            <div>
              <h2 className="text-xl sm:text-2xl font-black text-zinc-950 tracking-tight">
                How Mandarin Chinese Pronunciation Works
              </h2>
              <p className="text-xs sm:text-sm font-medium text-zinc-600 mt-1 leading-relaxed">
                Mandarin syllables are constructed like Lego blocks. There are only <strong className="text-zinc-900">21 Initials</strong> (consonants) and <strong className="text-zinc-900">36+ Finals</strong> (vowels & nasals). When multiplied by the <strong className="text-zinc-900">4 Tones</strong>, they produce exactly <strong className="text-zinc-900">~409 unique syllables</strong> that express every Chinese character in existence!
              </p>
            </div>

            {/* 3 Key Structural Principles */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1">
              <div className="p-4 rounded-2xl bg-zinc-50 border border-zinc-200">
                <div className="w-7 h-7 rounded-xl bg-sky-100 text-sky-800 font-black text-xs flex items-center justify-center mb-2">
                  1
                </div>
                <h4 className="text-xs font-black text-zinc-900 uppercase tracking-wide">
                  Every Box is a Real Sound
                </h4>
                <p className="text-xs font-medium text-zinc-600 mt-1 leading-relaxed">
                  In this interactive chart, every clickable box represents a valid syllable. If a slot is blank, that combination does not exist in Mandarin.
                </p>
              </div>

              <div className="p-4 rounded-2xl bg-zinc-50 border border-zinc-200">
                <div className="w-7 h-7 rounded-xl bg-emerald-100 text-emerald-800 font-black text-xs flex items-center justify-center mb-2">
                  2
                </div>
                <h4 className="text-xs font-black text-zinc-900 uppercase tracking-wide">
                  Click Anything to Hear Audio
                </h4>
                <p className="text-xs font-medium text-zinc-600 mt-1 leading-relaxed">
                  Click any initial header, final header, or syllable cell to hear authentic native pronunciation immediately.
                </p>
              </div>

              <div className="p-4 rounded-2xl bg-zinc-50 border border-zinc-200">
                <div className="w-7 h-7 rounded-xl bg-amber-100 text-amber-800 font-black text-xs flex items-center justify-center mb-2">
                  3
                </div>
                <h4 className="text-xs font-black text-zinc-900 uppercase tracking-wide">
                  Typing Trick: Use "v" for "ü"
                </h4>
                <p className="text-xs font-medium text-zinc-600 mt-1 leading-relaxed">
                  Standard keyboards lack "ü". To type characters like <strong className="text-zinc-900">绿 (lǜ)</strong> or <strong className="text-zinc-900">女 (nǚ)</strong>, type <strong className="text-zinc-900">lv</strong> or <strong className="text-zinc-900">nv</strong>!
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ========================================================= */}
      {/* 2. SEARCH, FILTER, & FAST TONE AUDITION TOOLBAR             */}
      {/* ========================================================= */}
      <div className="bg-white border-2 border-zinc-950 rounded-2xl p-4 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] flex flex-col gap-3">
        <div className="flex flex-col md:flex-row gap-3 items-center justify-between">
          {/* Live Search Bar */}
          <div className="relative w-full md:w-80">
            <Search className="w-4 h-4 text-zinc-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search syllable or hanzi (e.g., ma, lv, chi, 茶)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-8 py-2 text-xs font-bold bg-zinc-50 border-2 border-zinc-200 rounded-xl focus:border-zinc-950 focus:bg-white focus:outline-none transition-all placeholder:text-zinc-400"
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

          {/* Finals Category Selector */}
          <div className="flex flex-wrap items-center gap-1.5 w-full md:w-auto">
            {(
              [
                { id: 'all', label: 'All Finals (全部韵母)' },
                { id: 'simple', label: 'Simple (单韵母 a, o, e...)' },
                { id: 'compound', label: 'Compound (复韵母 ai, ao...)' },
                { id: 'nasal', label: 'Nasal (鼻韵母 an, ang...)' },
              ] as const
            ).map((cat) => (
              <button
                key={cat.id}
                onClick={() => setSelectedFinalCategory(cat.id)}
                className={`px-3 py-1.5 rounded-xl text-xs font-black transition-all cursor-pointer ${
                  selectedFinalCategory === cat.id
                    ? 'bg-zinc-950 text-white shadow-xs'
                    : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200'
                }`}
              >
                {cat.label}
              </button>
            ))}
          </div>
        </div>

        {/* Initial Groups Filter Row */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 pt-1 scrollbar-none">
          <span className="text-[11px] font-black uppercase text-zinc-400 shrink-0 mr-1">
            Initials Group:
          </span>
          {initialGroups.map((group) => (
            <button
              key={group.id}
              onClick={() => setSelectedInitialGroup(group.id)}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-bold shrink-0 transition-all cursor-pointer ${
                selectedInitialGroup === group.id
                  ? 'bg-sky-500 text-white font-black'
                  : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200'
              }`}
            >
              {group.label}
            </button>
          ))}
        </div>
      </div>

      {/* ========================================================= */}
      {/* 3. SEARCH RESULTS QUICK CARD VIEW (WHEN SEARCHING)        */}
      {/* ========================================================= */}
      {searchResults ? (
        <div className="bg-white border-2 border-zinc-950 rounded-3xl p-6 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)]">
          <div className="flex items-center justify-between mb-4 pb-2 border-b border-zinc-100">
            <h3 className="text-sm font-black text-zinc-900">
              Matching Syllables ({searchResults.length} found)
            </h3>
            <button
              onClick={() => setSearchQuery('')}
              className="text-xs text-zinc-500 font-bold hover:text-zinc-900 cursor-pointer"
            >
              Clear Search
            </button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2.5">
            {searchResults.map((entry) => {
              const isSelected = selectedSyllable?.syllable === entry.syllable;
              return (
                <button
                  key={entry.syllable}
                  onClick={() => {
                    setSelectedSyllable(entry);
                    const defaultTone = entry.validTones[0] || 1;
                    playAudio(entry.audioChars[defaultTone] || entry.syllable, `syl_${entry.syllable}`);
                  }}
                  className={`p-3 rounded-2xl border-2 text-left transition-all cursor-pointer flex flex-col justify-between ${
                    isSelected
                      ? 'border-zinc-950 bg-emerald-50 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]'
                      : 'border-zinc-200 bg-zinc-50 hover:bg-white hover:border-zinc-400'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-base font-black text-zinc-900">{entry.syllable}</span>
                    <Volume2 className="w-3.5 h-3.5 text-zinc-400" />
                  </div>
                  {entry.exampleWord && (
                    <div className="mt-2 text-[11px] text-zinc-500 font-medium truncate">
                      <span className="font-chinese font-bold text-zinc-800">{entry.exampleWord.hanzi}</span> {entry.exampleWord.meaningEn}
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      ) : null}

      {/* ========================================================= */}
      {/* 4. THE INTERACTIVE 2D FULL PINYIN CHART MATRIX            */}
      {/* ========================================================= */}
      <div className="bg-white border-2 border-zinc-950 rounded-3xl p-4 sm:p-6 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] overflow-hidden">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-black uppercase text-zinc-900 tracking-wider">
              2D Pronunciation Matrix (Click any item to listen)
            </span>
          </div>
          <span className="text-[11px] font-bold text-zinc-400">
            Scroll horizontally to explore all finals →
          </span>
        </div>

        {/* Scrollable Matrix Table */}
        <div className="overflow-x-auto border-2 border-zinc-950 rounded-2xl max-h-[520px] overflow-y-auto scrollbar-thin">
          <table className="w-full text-center border-collapse">
            {/* Header Row: Finals */}
            <thead className="sticky top-0 z-20 bg-zinc-950 text-white shadow-md">
              <tr>
                <th className="p-2.5 text-xs font-black uppercase tracking-wider bg-zinc-900 sticky left-0 z-30 border-r border-zinc-800 w-16">
                  Initial
                </th>
                {finalsList.map((final) => (
                  <th key={final} className="p-2 text-xs font-black border-r border-zinc-800 min-w-[56px]">
                    <button
                      onClick={() => {
                        const target = finalAudios[final]?.audio || final;
                        playAudio(target, `final_${final}`);
                      }}
                      className={`w-full py-1 rounded-md transition-all flex items-center justify-center gap-1 cursor-pointer ${
                        playingKey === `final_${final}` ? 'bg-emerald-400 text-zinc-950 font-black' : 'hover:bg-zinc-800'
                      }`}
                      title={finalAudios[final]?.tip || `Final: ${final}`}
                    >
                      <span>{final}</span>
                      <Volume2 className="w-2.5 h-2.5 opacity-60" />
                    </button>
                  </th>
                ))}
              </tr>
            </thead>

            {/* Matrix Body: Rows of Initials */}
            <tbody>
              {filteredInitials.map((initial, rowIdx) => {
                const initialInfo = initialAudios[initial];
                return (
                  <tr key={initial || 'zero'} className={rowIdx % 2 === 0 ? 'bg-white' : 'bg-zinc-50/70'}>
                    {/* Sticky Initial Row Header */}
                    <th className="p-2 text-xs font-black bg-zinc-100 sticky left-0 z-10 border-r-2 border-zinc-300 shadow-xs">
                      {initial ? (
                        <button
                          onClick={() => {
                            if (initialInfo) {
                              playAudio(initialInfo.audio, `init_${initial}`);
                            }
                          }}
                          className={`w-full py-1.5 px-2 rounded-lg transition-all flex items-center justify-between cursor-pointer ${
                            playingKey === `init_${initial}`
                              ? 'bg-sky-400 text-zinc-950 font-black'
                              : 'hover:bg-zinc-200 text-zinc-900'
                          }`}
                          title={initialInfo?.tip || `Initial: ${initial}`}
                        >
                          <span>{initial}</span>
                          <Volume2 className="w-3 h-3 text-zinc-400" />
                        </button>
                      ) : (
                        <span className="text-[11px] text-zinc-400 font-bold">∅ (Zero)</span>
                      )}
                    </th>

                    {/* Syllable Cells */}
                    {finalsList.map((final) => {
                      const entry = syllableMatrix[initial]?.[final];
                      if (!entry) {
                        return (
                          <td key={final} className="p-1 border-r border-b border-zinc-100 bg-zinc-100/40 text-zinc-200 text-xs select-none">
                            -
                          </td>
                        );
                      }

                      const isSelected = selectedSyllable?.syllable === entry.syllable;
                      const isPlaying = playingKey === `cell_${entry.syllable}`;

                      return (
                        <td key={final} className="p-1 border-r border-b border-zinc-200">
                          <button
                            onClick={() => {
                              setSelectedSyllable(entry);
                              const toneToPlay = entry.validTones[0] || 1;
                              const audioTarget = entry.audioChars[toneToPlay] || entry.syllable;
                              playAudio(audioTarget, `cell_${entry.syllable}`);
                            }}
                            className={`w-full py-2 px-1 rounded-xl text-xs font-black transition-all cursor-pointer ${
                              isPlaying
                                ? 'bg-emerald-400 text-zinc-950 scale-105 shadow-md'
                                : isSelected
                                ? 'bg-emerald-500 text-white shadow-sm'
                                : 'bg-white hover:bg-emerald-50 hover:text-emerald-700 text-zinc-900 border border-zinc-200/80 shadow-2xs'
                            }`}
                          >
                            {entry.syllable}
                          </button>
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

      {/* ========================================================= */}
      {/* 5. SYLLABLE INSPECTOR DRAWER (4 TONES & PRACTICE JUMP)     */}
      {/* ========================================================= */}
      {selectedSyllable && (
        <div className="bg-white border-2 border-zinc-950 rounded-3xl p-6 sm:p-7 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] transition-all animate-fadeIn">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-4 border-b-2 border-zinc-100">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[11px] font-black uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200">
                  Selected Syllable (音节检测)
                </span>
                <span className="text-xs text-zinc-400 font-bold">
                  Initial: <strong>{selectedSyllable.initial || 'zero'}</strong> + Final: <strong>{selectedSyllable.final}</strong>
                </span>
              </div>
              <h3 className="text-3xl font-black text-zinc-950 tracking-tight font-chinese">
                {selectedSyllable.syllable}
              </h3>
            </div>

            {/* Jump to Knowledge / Practice Card */}
            <div className="flex items-center gap-2 w-full md:w-auto">
              <button
                onClick={() => openSyllableInCard(selectedSyllable, 'knowledge')}
                className="flex-1 md:flex-initial px-4 py-2.5 rounded-xl border-2 border-zinc-950 text-xs font-black text-zinc-900 bg-zinc-50 hover:bg-zinc-100 flex items-center justify-center gap-1.5 transition-all cursor-pointer"
              >
                <BookOpen className="w-3.5 h-3.5" />
                <span>知识卡片 (Card)</span>
              </button>
              <button
                onClick={() => openSyllableInCard(selectedSyllable, 'practice')}
                className="flex-1 md:flex-initial px-4 py-2.5 rounded-xl border-2 border-zinc-950 text-xs font-black text-white bg-zinc-950 hover:bg-zinc-800 flex items-center justify-center gap-1.5 transition-all cursor-pointer shadow-xs"
              >
                <Mic className="w-3.5 h-3.5 text-emerald-400" />
                <span>发音比对 (Voice Practice)</span>
              </button>
            </div>
          </div>

          {/* Tone Variations Buttons */}
          <div className="mt-5 space-y-2">
            <h4 className="text-xs font-black text-zinc-400 uppercase tracking-wider">
              Audition All 4 Tones (点击听各个声调发音):
            </h4>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              {[1, 2, 3, 4].map((tone) => {
                const pinyinWithTone = selectedSyllable.pinyinWithTones[tone];
                const audioChar = selectedSyllable.audioChars[tone];
                const isValid = selectedSyllable.validTones.includes(tone);

                if (!isValid || !pinyinWithTone) {
                  return (
                    <div
                      key={tone}
                      className="p-3 rounded-2xl bg-zinc-50 border border-zinc-200 text-center opacity-40 select-none"
                    >
                      <span className="text-xs font-bold text-zinc-400">Tone {tone} (N/A)</span>
                    </div>
                  );
                }

                const isPlayingTone = playingKey === `tone_${tone}_${selectedSyllable.syllable}`;

                return (
                  <button
                    key={tone}
                    onClick={() => {
                      if (audioChar) {
                        playAudio(audioChar, `tone_${tone}_${selectedSyllable.syllable}`);
                      }
                    }}
                    className={`p-3.5 rounded-2xl border-2 transition-all cursor-pointer text-center flex flex-col items-center justify-center ${
                      isPlayingTone
                        ? 'border-emerald-500 bg-emerald-50 shadow-md scale-102'
                        : 'border-zinc-200 bg-zinc-50 hover:bg-white hover:border-zinc-900'
                    }`}
                  >
                    <div className="text-lg font-black text-zinc-900 font-chinese mb-0.5">
                      {pinyinWithTone}
                    </div>
                    <div className="flex items-center gap-1.5 text-xs text-zinc-500 font-bold">
                      <span className="font-chinese text-sm text-emerald-700 font-black">{audioChar}</span>
                      <span>• Tone {tone}</span>
                      <Volume2 className="w-3.5 h-3.5 text-zinc-400" />
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Example Word if available */}
          {selectedSyllable.exampleWord && (
            <div className="mt-5 p-4 rounded-2xl bg-zinc-50 border border-zinc-200 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="text-xl font-black font-chinese text-zinc-900">
                  {selectedSyllable.exampleWord.hanzi}
                </div>
                <div>
                  <div className="text-xs font-black text-zinc-800">
                    {selectedSyllable.exampleWord.pinyin}
                  </div>
                  <div className="text-[11px] font-medium text-zinc-500">
                    {selectedSyllable.exampleWord.meaningEn}
                  </div>
                </div>
              </div>
              <button
                onClick={() => playAudio(selectedSyllable.exampleWord!.hanzi, 'example_word')}
                className="p-2 rounded-xl bg-white border border-zinc-300 hover:border-zinc-900 text-zinc-700 transition-all cursor-pointer"
              >
                <Volume2 className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
