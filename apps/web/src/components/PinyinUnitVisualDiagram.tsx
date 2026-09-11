import React, { useState } from 'react';
import { Volume2, Play, Sparkles, Check, ArrowRight, Info, Music2 } from 'lucide-react';
import { playMandarinAudio } from '../utils/pinyinAudio.ts';

interface PinyinUnitVisualDiagramProps {
  unitNumber: number;
}

export const PinyinUnitVisualDiagram: React.FC<PinyinUnitVisualDiagramProps> = ({ unitNumber }) => {
  const [playingAudio, setPlayingAudio] = useState<string | null>(null);

  const handlePlay = (text: string) => {
    setPlayingAudio(text);
    playMandarinAudio(text, {
      rate: 0.85,
      onEnd: () => setPlayingAudio(null),
    });
  };

  // Unit 1: Overview & Syllable Anatomy
  if (unitNumber === 1) {
    return (
      <div className="bg-white border-2 border-zinc-950 rounded-2xl p-5 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-sm font-black uppercase tracking-wider text-emerald-700">
              Visual Diagram: Syllable Anatomy
            </h4>
            <p className="text-xs text-zinc-500 font-medium">
              Every Mandarin syllable is constructed from 3 modular building blocks.
            </p>
          </div>
          <span className="text-[10px] font-black px-2.5 py-1 bg-zinc-100 border border-zinc-300 rounded-lg text-zinc-700">
            Formula: Initial + Final + Tone
          </span>
        </div>

        {/* Syllable Assembly Equation */}
        <div className="grid grid-cols-1 sm:grid-cols-7 gap-2 items-center text-center">
          {/* Initial */}
          <div className="sm:col-span-2 bg-sky-50 border-2 border-sky-300 rounded-xl p-3">
            <span className="text-[10px] font-black uppercase tracking-wider text-sky-700 block">
              1. Initial (Consonant)
            </span>
            <span className="text-3xl font-black text-sky-950 font-mono block my-1">
              m
            </span>
            <span className="text-[11px] font-medium text-sky-850 block">
              21 distinct consonants
            </span>
            <button
              onClick={() => handlePlay('摸')}
              className="mt-2 text-[10px] font-black text-sky-700 hover:text-sky-900 flex items-center justify-center gap-1 mx-auto cursor-pointer"
            >
              <Volume2 className="w-3 h-3" /> Listen 'm'
            </button>
          </div>

          <div className="text-xl font-black text-zinc-400 hidden sm:block">+</div>

          {/* Final */}
          <div className="sm:col-span-2 bg-amber-50 border-2 border-amber-300 rounded-xl p-3">
            <span className="text-[10px] font-black uppercase tracking-wider text-amber-700 block">
              2. Final (Vowel/Nasal)
            </span>
            <span className="text-3xl font-black text-amber-950 font-mono block my-1">
              a
            </span>
            <span className="text-[11px] font-medium text-amber-850 block">
              36 simple/compound finals
            </span>
            <button
              onClick={() => handlePlay('啊')}
              className="mt-2 text-[10px] font-black text-amber-700 hover:text-amber-900 flex items-center justify-center gap-1 mx-auto cursor-pointer"
            >
              <Volume2 className="w-3 h-3" /> Listen 'a'
            </button>
          </div>

          <div className="text-xl font-black text-zinc-400 hidden sm:block">+</div>

          {/* Tone */}
          <div className="sm:col-span-2 bg-emerald-50 border-2 border-emerald-300 rounded-xl p-3">
            <span className="text-[10px] font-black uppercase tracking-wider text-emerald-700 block">
              3. Tone Mark
            </span>
            <span className="text-3xl font-black text-emerald-950 font-mono block my-1">
              ¯ (1st)
            </span>
            <span className="text-[11px] font-medium text-emerald-850 block">
              High flat pitch (55)
            </span>
            <button
              onClick={() => handlePlay('妈')}
              className="mt-2 text-[10px] font-black text-emerald-700 hover:text-emerald-900 flex items-center justify-center gap-1 mx-auto cursor-pointer"
            >
              <Volume2 className="w-3 h-3" /> Result: mā (妈)
            </button>
          </div>
        </div>

        {/* Essential Rule Callout: Keyboard 'v' rule */}
        <div className="bg-zinc-50 border border-zinc-200 rounded-xl p-3 flex items-start gap-2.5 text-xs text-zinc-700 font-medium">
          <Info className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
          <div>
            <span className="font-black text-zinc-950">Keyboard Input Rule: </span>
            Since standard keyboards lack the umlaut <span className="font-mono font-bold text-emerald-700">ü</span>, it is universally typed as <span className="font-mono font-bold text-emerald-700 bg-emerald-100 px-1 rounded">v</span> in Pinyin input systems (e.g. type <span className="font-mono font-bold">lv</span> for <span className="font-mono">lǜ</span> 绿, <span className="font-mono font-bold">nv</span> for <span className="font-mono">nǚ</span> 女).
          </div>
        </div>
      </div>
    );
  }

  // Unit 2: Initials & Consonant Articulation Zones
  if (unitNumber === 2) {
    return (
      <div className="bg-white border-2 border-zinc-950 rounded-2xl p-5 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-sm font-black uppercase tracking-wider text-sky-700">
              Visual Diagram: Tongue & Mouth Articulation Zones
            </h4>
            <p className="text-xs text-zinc-500 font-medium">
              Contrast between Retroflex (curled tongue), Dental (flat tongue), and Palatal (wide smile).
            </p>
          </div>
          <span className="text-[10px] font-black px-2.5 py-1 bg-sky-100 border border-sky-300 rounded-lg text-sky-800">
            21 Initials System
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {/* Retroflex */}
          <div className="bg-rose-50/70 border-2 border-rose-200 rounded-xl p-3.5 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-black uppercase tracking-wider text-rose-800">
                Retroflex (Curled)
              </span>
              <button
                onClick={() => handlePlay('知')}
                className="text-[10px] font-black text-rose-700 hover:text-rose-900 flex items-center gap-1 cursor-pointer"
              >
                <Volume2 className="w-3 h-3" /> Audio
              </button>
            </div>
            <div className="text-2xl font-black text-zinc-900 font-mono">
              zh · ch · sh · r
            </div>
            <p className="text-xs text-zinc-600 font-medium leading-relaxed">
              <span className="font-bold text-zinc-900">Tongue action:</span> Curl tip backward toward the roof of your mouth (hard palate). No contact with front teeth.
            </p>
            <div className="text-[11px] font-bold text-rose-800 bg-rose-100/60 p-2 rounded-lg">
              Contrast: <span className="font-mono">zhī</span> (知) vs <span className="font-mono">shì</span> (是)
            </div>
          </div>

          {/* Dental Sibilants */}
          <div className="bg-amber-50/70 border-2 border-amber-200 rounded-xl p-3.5 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-black uppercase tracking-wider text-amber-800">
                Dental (Flat)
              </span>
              <button
                onClick={() => handlePlay('字')}
                className="text-[10px] font-black text-amber-700 hover:text-amber-900 flex items-center gap-1 cursor-pointer"
              >
                <Volume2 className="w-3 h-3" /> Audio
              </button>
            </div>
            <div className="text-2xl font-black text-zinc-900 font-mono">
              z · c · s
            </div>
            <p className="text-xs text-zinc-600 font-medium leading-relaxed">
              <span className="font-bold text-zinc-900">Tongue action:</span> Keep tongue tip strictly flat and pressed against the back of upper front teeth.
            </p>
            <div className="text-[11px] font-bold text-amber-800 bg-amber-100/60 p-2 rounded-lg">
              Contrast: <span className="font-mono">sì</span> (四 - four) vs <span className="font-mono">shì</span> (是 - is)
            </div>
          </div>

          {/* Palatals */}
          <div className="bg-indigo-50/70 border-2 border-indigo-200 rounded-xl p-3.5 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-black uppercase tracking-wider text-indigo-800">
                Palatal (Smile)
              </span>
              <button
                onClick={() => handlePlay('七')}
                className="text-[10px] font-black text-indigo-700 hover:text-indigo-900 flex items-center gap-1 cursor-pointer"
              >
                <Volume2 className="w-3 h-3" /> Audio
              </button>
            </div>
            <div className="text-2xl font-black text-zinc-900 font-mono">
              j · q · x
            </div>
            <p className="text-xs text-zinc-600 font-medium leading-relaxed">
              <span className="font-bold text-zinc-900">Tongue action:</span> Pull mouth corners into a wide smile. Flat surface of tongue touches hard palate.
            </p>
            <div className="text-[11px] font-bold text-indigo-800 bg-indigo-100/60 p-2 rounded-lg">
              Contrast: <span className="font-mono">qī</span> (七 - seven) with puff of air
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Unit 3: Finals & Nasal Airflow
  if (unitNumber === 3) {
    return (
      <div className="bg-white border-2 border-zinc-950 rounded-2xl p-5 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-sm font-black uppercase tracking-wider text-amber-700">
              Visual Diagram: Vowel Aperture & Nasal Resonators
            </h4>
            <p className="text-xs text-zinc-500 font-medium">
              Vowel openness order + acoustic discrimination between Front (-n) and Back (-ng) nasals.
            </p>
          </div>
          <span className="text-[10px] font-black px-2.5 py-1 bg-amber-100 border border-amber-300 rounded-lg text-amber-800">
            36 Finals System
          </span>
        </div>

        {/* Vowel Aperture Scale */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-[11px] font-bold text-zinc-500">
            <span>Widest Mouth Opening</span>
            <span>Tightest Rounded Lips</span>
          </div>
          <div className="grid grid-cols-6 gap-2 text-center">
            {[
              { char: 'a', sound: '啊', label: 'Wide Open' },
              { char: 'o', sound: '喔', label: 'Rounded' },
              { char: 'e', sound: '鹅', label: 'Neutral' },
              { char: 'i', sound: '衣', label: 'Spread' },
              { char: 'u', sound: '乌', label: 'Round Pucker' },
              { char: 'ü', sound: '迂', label: 'Tight Whistle' },
            ].map((v) => (
              <button
                key={v.char}
                onClick={() => handlePlay(v.sound)}
                className="p-2 rounded-xl border-2 border-zinc-200 hover:border-zinc-950 bg-zinc-50 hover:bg-white transition-all cursor-pointer group"
              >
                <span className="text-xl font-black text-zinc-950 font-mono block group-hover:text-emerald-700">
                  {v.char}
                </span>
                <span className="text-[9px] font-bold text-zinc-400 block mt-0.5">
                  {v.label}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Nasal Airflow Comparison */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
          {/* Front Nasal -n */}
          <div className="bg-sky-50 border-2 border-sky-200 rounded-xl p-3.5 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-black text-sky-950">Front Nasal Ending: -n</span>
              <button
                onClick={() => handlePlay('饭')}
                className="text-[10px] font-black text-sky-700 hover:text-sky-900 flex items-center gap-1 cursor-pointer"
              >
                <Volume2 className="w-3 h-3" /> Audio (fàn 饭)
              </button>
            </div>
            <p className="text-xs text-zinc-600 font-medium leading-relaxed">
              Tongue tip seals firmly against the alveolar ridge (behind top teeth). Airflow exits purely through the nose with front closure.
            </p>
          </div>

          {/* Back Nasal -ng */}
          <div className="bg-indigo-50 border-2 border-indigo-200 rounded-xl p-3.5 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-black text-indigo-950">Back Nasal Ending: -ng</span>
              <button
                onClick={() => handlePlay('房')}
                className="text-[10px] font-black text-indigo-700 hover:text-indigo-900 flex items-center gap-1 cursor-pointer"
              >
                <Volume2 className="w-3 h-3" /> Audio (fáng 房)
              </button>
            </div>
            <p className="text-xs text-zinc-600 font-medium leading-relaxed">
              Tongue back elevates against the soft palate. Creates a rich, hollow reverberation in the nasal and throat cavity.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Unit 4: The 4 Mandarin Tones (Chao 5-Level Pitch Contours)
  if (unitNumber === 4) {
    return (
      <div className="bg-white border-2 border-zinc-950 rounded-2xl p-5 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-sm font-black uppercase tracking-wider text-purple-700">
              Visual Diagram: Chao 5-Level Pitch Contour Chart
            </h4>
            <p className="text-xs text-zinc-500 font-medium">
              Mandarin is tonal: changing the musical pitch contour completely changes the word meaning.
            </p>
          </div>
          <span className="text-[10px] font-black px-2.5 py-1 bg-purple-100 border border-purple-300 rounded-lg text-purple-800">
            5-Level Tone Scale
          </span>
        </div>

        {/* 4 Tones Grid with Audio Triggers */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            {
              tone: 1,
              name: '1st Tone: High Flat',
              contour: '5 — 5',
              pinyin: 'mā',
              hanzi: '妈',
              meaning: 'Mother',
              audioChar: '妈',
              desc: 'High, steady, singing pitch. Keep pitch unwavering.',
              bg: 'bg-emerald-50 border-emerald-300 text-emerald-950',
            },
            {
              tone: 2,
              name: '2nd Tone: Rising',
              contour: '3 ↗ 5',
              pinyin: 'má',
              hanzi: '麻',
              meaning: 'Hemp',
              audioChar: '麻',
              desc: 'Rises smoothly like asking "What?!" in surprise.',
              bg: 'bg-sky-50 border-sky-300 text-sky-950',
            },
            {
              tone: 3,
              name: '3rd Tone: Dipping',
              contour: '2 ↘ 1 ↗ 4',
              pinyin: 'mǎ',
              hanzi: '马',
              meaning: 'Horse',
              audioChar: '马',
              desc: 'Dips low into vocal fry, then recovers slightly.',
              bg: 'bg-amber-50 border-amber-300 text-amber-950',
            },
            {
              tone: 4,
              name: '4th Tone: Sharp Falling',
              contour: '5 ↘ 1',
              pinyin: 'mà',
              hanzi: '骂',
              meaning: 'To Scold',
              audioChar: '骂',
              desc: 'Drops swiftly and decisively like an emphatic "No!".',
              bg: 'bg-rose-50 border-rose-300 text-rose-950',
            },
          ].map((t) => (
            <div
              key={t.tone}
              onClick={() => handlePlay(t.audioChar)}
              className={`border-2 rounded-2xl p-4 transition-all cursor-pointer shadow-xs hover:shadow-md flex flex-col justify-between gap-2.5 ${t.bg}`}
            >
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-black uppercase tracking-wider">
                    Tone {t.tone}
                  </span>
                  <span className="text-[10px] font-mono font-black px-1.5 py-0.5 rounded bg-white/80 border border-zinc-200">
                    Pitch {t.contour}
                  </span>
                </div>
                <div className="flex items-baseline gap-2 pt-1">
                  <span className="text-3xl font-black font-chinese">{t.hanzi}</span>
                  <span className="text-lg font-mono font-black">{t.pinyin}</span>
                </div>
                <div className="text-xs font-bold">{t.meaning}</div>
                <p className="text-[11px] opacity-80 leading-relaxed font-medium">
                  {t.desc}
                </p>
              </div>

              <div className="pt-2 border-t border-zinc-200/60 flex items-center justify-between text-xs font-black">
                <span className="flex items-center gap-1">
                  <Volume2 className="w-3.5 h-3.5" /> Tap to Hear
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Unit 5: Tone Sandhi & Neutral Tone
  if (unitNumber === 5) {
    return (
      <div className="bg-white border-2 border-zinc-950 rounded-2xl p-5 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-sm font-black uppercase tracking-wider text-rose-700">
              Visual Diagram: Spoken Tone Sandhi Rules
            </h4>
            <p className="text-xs text-zinc-500 font-medium">
              In real connected speech, certain adjacent tones automatically morph for natural fluid articulation.
            </p>
          </div>
          <span className="text-[10px] font-black px-2.5 py-1 bg-rose-100 border border-rose-300 rounded-lg text-rose-800">
            Natural Sound Shifts
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {/* Rule 1: 3+3 */}
          <div className="bg-zinc-50 border-2 border-zinc-200 rounded-xl p-3.5 space-y-2">
            <span className="text-[10px] font-black uppercase tracking-wider text-zinc-500 block">
              Rule 1: 3rd + 3rd Tone Sandhi
            </span>
            <div className="flex items-center gap-2 text-sm font-mono font-black">
              <span className="px-2 py-1 bg-amber-100 text-amber-900 rounded border border-amber-300">
                3rd (ˇ) + 3rd (ˇ)
              </span>
              <ArrowRight className="w-3.5 h-3.5 text-zinc-400" />
              <span className="px-2 py-1 bg-emerald-100 text-emerald-900 rounded border border-emerald-300">
                2nd (ˊ) + 3rd (ˇ)
              </span>
            </div>
            <p className="text-xs text-zinc-600 font-medium">
              Pronounced <span className="font-mono font-bold text-zinc-950">"ní hǎo"</span>, written <span className="font-mono font-bold text-zinc-950">"nǐ hǎo"</span> (你好).
            </p>
            <button
              onClick={() => handlePlay('你好')}
              className="text-[10px] font-black text-emerald-700 hover:text-emerald-900 flex items-center gap-1 cursor-pointer pt-1"
            >
              <Volume2 className="w-3 h-3" /> Hear: nǐ hǎo (你好)
            </button>
          </div>

          {/* Rule 2: Bu Sandhi */}
          <div className="bg-zinc-50 border-2 border-zinc-200 rounded-xl p-3.5 space-y-2">
            <span className="text-[10px] font-black uppercase tracking-wider text-zinc-500 block">
              Rule 2: "bù" (不) Sandhi
            </span>
            <div className="flex items-center gap-2 text-sm font-mono font-black">
              <span className="px-2 py-1 bg-rose-100 text-rose-900 rounded border border-rose-300">
                bù (4th) + 4th (ˋ)
              </span>
              <ArrowRight className="w-3.5 h-3.5 text-zinc-400" />
              <span className="px-2 py-1 bg-emerald-100 text-emerald-900 rounded border border-emerald-300">
                bú (2nd) + 4th
              </span>
            </div>
            <p className="text-xs text-zinc-600 font-medium">
              "bù" changes to 2nd tone before any 4th tone word (e.g. <span className="font-mono font-bold text-zinc-950">bú shì</span> 不是).
            </p>
            <button
              onClick={() => handlePlay('不是')}
              className="text-[10px] font-black text-emerald-700 hover:text-emerald-900 flex items-center gap-1 cursor-pointer pt-1"
            >
              <Volume2 className="w-3 h-3" /> Hear: bú shì (不是)
            </button>
          </div>

          {/* Rule 3: Yi Sandhi */}
          <div className="bg-zinc-50 border-2 border-zinc-200 rounded-xl p-3.5 space-y-2">
            <span className="text-[10px] font-black uppercase tracking-wider text-zinc-500 block">
              Rule 3: "yī" (一) Sandhi
            </span>
            <div className="flex items-center gap-2 text-sm font-mono font-black">
              <span className="px-2 py-1 bg-sky-100 text-sky-900 rounded border border-sky-300">
                yī + 4th (ˋ)
              </span>
              <ArrowRight className="w-3.5 h-3.5 text-zinc-400" />
              <span className="px-2 py-1 bg-emerald-100 text-emerald-900 rounded border border-emerald-300">
                yí (2nd) + 4th
              </span>
            </div>
            <p className="text-xs text-zinc-600 font-medium">
              "yī" becomes 2nd tone before 4th tone (<span className="font-mono font-bold text-zinc-950">yí gè</span> 一个), and 4th before others (<span className="font-mono font-bold text-zinc-950">yì tiān</span> 一天).
            </p>
            <button
              onClick={() => handlePlay('一个')}
              className="text-[10px] font-black text-emerald-700 hover:text-emerald-900 flex items-center gap-1 cursor-pointer pt-1"
            >
              <Volume2 className="w-3 h-3" /> Hear: yí gè (一个)
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Unit 6: Connected Speech & Rhythm
  return (
    <div className="bg-white border-2 border-zinc-950 rounded-2xl p-5 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-sm font-black uppercase tracking-wider text-teal-700">
            Visual Diagram: Connected Speech & Natural Cadence
          </h4>
          <p className="text-xs text-zinc-500 font-medium">
            Speaking Chinese naturally is about phrasing chunks, not robotic syllable-by-syllable delivery.
          </p>
        </div>
        <span className="text-[10px] font-black px-2.5 py-1 bg-teal-100 border border-teal-300 rounded-lg text-teal-800">
          Spoken Cadence
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
        {[
          { textZh: '你好', pinyin: 'nǐ hǎo', en: 'Hello' },
          { textZh: '谢谢', pinyin: 'xièxie', en: 'Thank you' },
          { textZh: '不客气', pinyin: 'bú kèqi', en: "You're welcome" },
          { textZh: '对不起', pinyin: 'duìbuqǐ', en: 'Sorry' },
          { textZh: '再见', pinyin: 'zàijiàn', en: 'Goodbye' },
          { textZh: '请问', pinyin: 'qǐngwèn', en: 'Excuse me, may I ask' },
        ].map((item) => (
          <div
            key={item.textZh}
            onClick={() => handlePlay(item.textZh)}
            className="p-3 bg-zinc-50 border-2 border-zinc-200 hover:border-zinc-950 rounded-xl transition-all cursor-pointer flex items-center justify-between gap-2"
          >
            <div>
              <div className="flex items-baseline gap-2">
                <span className="text-base font-black font-chinese text-zinc-950">{item.textZh}</span>
                <span className="text-xs font-mono font-bold text-zinc-500">{item.pinyin}</span>
              </div>
              <span className="text-[11px] font-medium text-zinc-600">{item.en}</span>
            </div>
            <Volume2 className="w-4 h-4 text-emerald-600 shrink-0" />
          </div>
        ))}
      </div>
    </div>
  );
};
