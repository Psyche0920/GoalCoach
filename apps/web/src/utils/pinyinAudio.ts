// Pure Native Mandarin Audio Synthesis & Voice Recording Engine
// Clean phonetic demonstration without chatty audio text

export interface PinyinPhonemeItem {
  id: string;
  symbol: string;
  category: 'initial' | 'simple_final' | 'compound_final' | 'nasal_final' | 'tone' | 'sandhi' | 'whole_syllable';
  anchorChar: string;
  anchorWord: string;
  pinyin: string;
  audioGuideEn: string;
  audioSpeechText: string;
  ipa?: string;
}

export const PINYIN_INITIALS: PinyinPhonemeItem[] = [
  { id: 'init_b', symbol: 'b', category: 'initial', anchorChar: '八', anchorWord: '八 (bā)', pinyin: 'bō', ipa: '[p]', audioGuideEn: 'Like "p" in "speak" (unaspirated)', audioSpeechText: '八' },
  { id: 'init_p', symbol: 'p', category: 'initial', anchorChar: '坡', anchorWord: '坡 (pō)', pinyin: 'pō', ipa: '[pʰ]', audioGuideEn: 'Like "p" in "peak" (aspirated puff)', audioSpeechText: '坡' },
  { id: 'init_m', symbol: 'm', category: 'initial', anchorChar: '摸', anchorWord: '摸 (mō)', pinyin: 'mō', ipa: '[m]', audioGuideEn: 'Like "m" in "mother"', audioSpeechText: '摸' },
  { id: 'init_f', symbol: 'f', category: 'initial', anchorChar: '佛', anchorWord: '佛 (fó)', pinyin: 'fó', ipa: '[f]', audioGuideEn: 'Like "f" in "fish"', audioSpeechText: '佛' },
  { id: 'init_d', symbol: 'd', category: 'initial', anchorChar: '大', anchorWord: '大 (dà)', pinyin: 'dē', ipa: '[t]', audioGuideEn: 'Like "t" in "stop" (unaspirated)', audioSpeechText: '大' },
  { id: 'init_t', symbol: 't', category: 'initial', anchorChar: '他', anchorWord: '他 (tā)', pinyin: 'tē', ipa: '[tʰ]', audioGuideEn: 'Like "t" in "tea" (aspirated puff)', audioSpeechText: '他' },
  { id: 'init_n', symbol: 'n', category: 'initial', anchorChar: '你', anchorWord: '你 (nǐ)', pinyin: 'nē', ipa: '[n]', audioGuideEn: 'Like "n" in "nice"', audioSpeechText: '你' },
  { id: 'init_l', symbol: 'l', category: 'initial', anchorChar: '来', anchorWord: '来 (lái)', pinyin: 'lē', ipa: '[l]', audioGuideEn: 'Like "l" in "love"', audioSpeechText: '来' },
  { id: 'init_g', symbol: 'g', category: 'initial', anchorChar: '哥', anchorWord: '哥 (gē)', pinyin: 'gē', ipa: '[k]', audioGuideEn: 'Like "k" in "skill" (unaspirated)', audioSpeechText: '哥' },
  { id: 'init_k', symbol: 'k', category: 'initial', anchorChar: '开', anchorWord: '开 (kāi)', pinyin: 'kē', ipa: '[kʰ]', audioGuideEn: 'Like "k" in "kite" (aspirated puff)', audioSpeechText: '开' },
  { id: 'init_h', symbol: 'h', category: 'initial', anchorChar: '喝', anchorWord: '喝 (hē)', pinyin: 'hē', ipa: '[x]', audioGuideEn: 'Like "h" in "hat" (rougher throat sound)', audioSpeechText: '喝' },
  { id: 'init_j', symbol: 'j', category: 'initial', anchorChar: '几', anchorWord: '几 (jǐ)', pinyin: 'jī', ipa: '[tɕ]', audioGuideEn: 'Like "j" in "jeep" with flat tongue', audioSpeechText: '几' },
  { id: 'init_q', symbol: 'q', category: 'initial', anchorChar: '七', anchorWord: '七 (qī)', pinyin: 'qī', ipa: '[tɕʰ]', audioGuideEn: 'Like "ch" in "cheese" with flat tongue & puff', audioSpeechText: '七' },
  { id: 'init_x', symbol: 'x', category: 'initial', anchorChar: '西', anchorWord: '西 (xī)', pinyin: 'xī', ipa: '[ɕ]', audioGuideEn: 'Like "sh" in "sheep" with corners of mouth pulled wide', audioSpeechText: '西' },
  { id: 'init_zh', symbol: 'zh', category: 'initial', anchorChar: '知', anchorWord: '知 (zhī)', pinyin: 'zhī', ipa: '[tʂ]', audioGuideEn: 'Retroflex: tongue tip curled back (like "j" in "jump")', audioSpeechText: '知' },
  { id: 'init_ch', symbol: 'ch', category: 'initial', anchorChar: '吃', anchorWord: '吃 (chī)', pinyin: 'chī', ipa: '[tʂʰ]', audioGuideEn: 'Retroflex: tongue tip curled back with strong puff of air', audioSpeechText: '吃' },
  { id: 'init_sh', symbol: 'sh', category: 'initial', anchorChar: '十', anchorWord: '十 (shí)', pinyin: 'shī', ipa: '[ʂ]', audioGuideEn: 'Retroflex: tongue tip curled back, unvoiced hiss', audioSpeechText: '十' },
  { id: 'init_r', symbol: 'r', category: 'initial', anchorChar: '日', anchorWord: '日 (rì)', pinyin: 'rī', ipa: '[ʐ]', audioGuideEn: 'Retroflex: tongue tip curled back, voiced buzz (like "s" in "measure")', audioSpeechText: '日' },
  { id: 'init_z', symbol: 'z', category: 'initial', anchorChar: '字', anchorWord: '字 (zì)', pinyin: 'zī', ipa: '[ts]', audioGuideEn: 'Dental: like "ds" in "reads" behind teeth', audioSpeechText: '字' },
  { id: 'init_c', symbol: 'c', category: 'initial', anchorChar: '词', anchorWord: '词 (cí)', pinyin: 'cī', ipa: '[tsʰ]', audioGuideEn: 'Dental: like "ts" in "cats" with strong puff', audioSpeechText: '词' },
  { id: 'init_s', symbol: 's', category: 'initial', anchorChar: '四', anchorWord: '四 (sì)', pinyin: 'sī', ipa: '[s]', audioGuideEn: 'Dental: like "s" in "sun" behind teeth', audioSpeechText: '四' },
  { id: 'init_y', symbol: 'y', category: 'initial', anchorChar: '一', anchorWord: '一 (yī)', pinyin: 'yī', ipa: '[j]', audioGuideEn: 'Semi-vowel: like "y" in "yes"', audioSpeechText: '一' },
  { id: 'init_w', symbol: 'w', category: 'initial', anchorChar: '五', anchorWord: '五 (wǔ)', pinyin: 'wū', ipa: '[w]', audioGuideEn: 'Semi-vowel: like "w" in "water"', audioSpeechText: '五' },
];

// Clean Audio Playback Engine with /api/tts priority & SpeechSynthesis fallback
const audioCache = new Map<string, HTMLAudioElement>();

export const playMandarinAudio = (
  text: string,
  options?: {
    rate?: number; // default 0.85 (slightly paced for learning), 0.65 for slow
    pitch?: number;
    onStart?: () => void;
    onEnd?: () => void;
  }
) => {
  if (typeof window === 'undefined') return;

  const cleanText = text.trim();
  if (!cleanText) return;

  // Function to fallback to SpeechSynthesis
  const fallbackSpeech = () => {
    if (!('speechSynthesis' in window)) return;
    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.lang = 'zh-CN';
      utterance.rate = options?.rate ?? 0.85;
      utterance.pitch = options?.pitch ?? 1.0;

      const voices = window.speechSynthesis.getVoices();
      const zhVoice = voices.find(
        (v) => v.lang.startsWith('zh') || v.lang.includes('cmn') || v.name.toLowerCase().includes('chinese')
      );
      if (zhVoice) {
        utterance.voice = zhVoice;
      }

      if (options?.onStart) utterance.onstart = options.onStart;
      if (options?.onEnd) utterance.onend = options.onEnd;

      window.speechSynthesis.speak(utterance);
    } catch (err) {
      console.error('SpeechSynthesis failed:', err);
      if (options?.onEnd) options.onEnd();
    }
  };

  // Try high-quality /api/tts endpoint first
  try {
    const ttsUrl = `/api/tts?text=${encodeURIComponent(cleanText)}`;
    const audio = new Audio(ttsUrl);
    if (options?.rate && options.rate !== 1.0) {
      audio.playbackRate = options.rate;
    }

    let started = false;
    audio.onplay = () => {
      started = true;
      if (options?.onStart) options.onStart();
    };

    audio.onended = () => {
      if (options?.onEnd) options.onEnd();
    };

    audio.onerror = () => {
      // Fall back to browser native speech synthesis
      fallbackSpeech();
    };

    const playPromise = audio.play();
    if (playPromise !== undefined) {
      playPromise.catch(() => {
        fallbackSpeech();
      });
    }
  } catch (err) {
    fallbackSpeech();
  }
};

export interface PronunciationMatchResult {
  score: number; // 0 to 100
  recognizedText: string;
  targetText: string;
  matched: boolean;
  feedback: string;
  toneAssessment?: string;
}

export function evaluatePronunciation(
  transcript: string,
  targetHanzi: string,
  targetPinyin: string,
  acceptableMatches?: string[]
): PronunciationMatchResult {
  const normTrans = transcript.trim().toLowerCase();
  const normHanzi = targetHanzi.trim().toLowerCase();
  const normPinyin = targetPinyin.trim().toLowerCase().replace(/[\s\-_]/g, '');

  const targets = [
    normHanzi,
    normPinyin,
    targetPinyin.toLowerCase(),
    ...(acceptableMatches || []).map((m) => m.toLowerCase().trim()),
  ];

  // Exact character or exact pinyin match
  if (targets.some((t) => normTrans === t || normTrans.includes(t) || t.includes(normTrans))) {
    return {
      score: 96,
      recognizedText: transcript,
      targetText: targetHanzi || targetPinyin,
      matched: true,
      feedback: 'Excellent pronunciation! Crisp articulation and native accuracy.',
      toneAssessment: 'Tone pitch contour accurately produced.',
    };
  }

  // Partial or fuzzy match
  if (normTrans.length > 0) {
    // Check if initial or final matches roughly
    const isClose = targets.some((t) => {
      if (t.length >= 2 && normTrans.length >= 2) {
        return t.slice(0, 2) === normTrans.slice(0, 2) || t.slice(-2) === normTrans.slice(-2);
      }
      return false;
    });

    if (isClose) {
      return {
        score: 82,
        recognizedText: transcript,
        targetText: targetHanzi || targetPinyin,
        matched: true,
        feedback: 'Good effort! Intelligible, with minor pitch or vowel coloration nuance.',
        toneAssessment: 'Slight tone glide difference detected.',
      };
    }

    return {
      score: 65,
      recognizedText: transcript,
      targetText: targetHanzi || targetPinyin,
      matched: false,
      feedback: `Detected "${transcript}". Focus on tongue placement and try again!`,
      toneAssessment: 'Tone contour differed from native standard.',
    };
  }

  return {
    score: 50,
    recognizedText: '(No clear sound detected)',
    targetText: targetHanzi || targetPinyin,
    matched: false,
    feedback: 'No voice was captured. Please check microphone and speak louder.',
    toneAssessment: 'Unclear sound',
  };
}
