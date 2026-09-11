// Standard Mandarin Pinyin Database & Pedagogical Reference
// Structured following international CSL standards and interactive pinyin chart systems

export interface PinyinToneInfo {
  toneNumber: number; // 1 to 4, or 0 (neutral)
  toneName: string; // e.g. "1st Tone (High Flat)"
  markSymbol: string; // "ˉ", "ˊ", "ˇ", "ˋ", "·"
  pitchContour: string; // "55", "35", "214", "51", "short/neutral"
  pitchDescription: string;
  anchorSyllables: {
    syllable: string;
    pinyin: string;
    hanzi: string;
    meaningEn: string;
    audioChar: string;
  }[];
}

export interface ToneSandhiRule {
  id: string;
  title: string;
  ruleFormula: string;
  exampleHanzi: string;
  writtenPinyin: string;
  spokenPinyin: string;
  meaningEn: string;
  explanationEn: string;
  audioTarget: string;
}

export interface PinyinTonePair {
  id: string;
  firstTone: number;
  secondTone: number | 'neutral';
  toneLabel: string;
  exampleHanzi: string;
  pinyin: string;
  meaningEn: string;
  audioTarget: string;
}

export interface PinyinSyllableEntry {
  syllable: string; // e.g. "ba", "ma", "lv"
  initial: string;
  final: string;
  validTones: number[]; // e.g. [1, 2, 3, 4]
  pinyinWithTones: { [tone: number]: string }; // 1: "bā", 2: "bá", etc.
  audioChars: { [tone: number]: string }; // 1: "八", 2: "拔", etc.
  exampleWord?: { hanzi: string; pinyin: string; meaningEn: string };
}

export interface PinyinFlashcard {
  id: string;
  stage: 'sound' | 'syllable' | 'word' | 'phrase';
  stageLabel: string;
  targetPinyin: string;
  targetHanzi: string;
  meaningEn: string;
  audioTarget: string;
  toneIndex?: number;
  acousticTip?: string;
}

export interface PinyinQuizQuestion {
  id: string;
  type: 'tone_id' | 'minimal_pair' | 'tone_pair' | 'spelling';
  audioTarget: string;
  questionText: string;
  options: string[];
  correctAnswer: string;
  explanationEn: string;
}

export interface PinyinUnit {
  id: string;
  unitNumber: number;
  conceptId: string;
  slug: string;
  titleEn: string;
  objectiveEn: string;
  estimatedMinutes: number;
  flashcards: PinyinFlashcard[];
  quizQuestions: PinyinQuizQuestion[];
}

export interface PinyinPhonemeCardItem {
  id: string;
  pinyin: string;
  category: 'initial' | 'final' | 'tone' | 'syllable';
  audioTarget?: string;
  anchorHanzi?: string;
  hanziPinyin?: string;
  meaningEn?: string;
  ipa?: string;
  acousticTip?: string;
  acceptableMatches?: string[];
  exampleWords?: { hanzi: string; pinyin: string; meaningEn: string }[];
}

// 1. PINYIN SYSTEM OVERVIEW DATA
export const PINYIN_OVERVIEW = {
  title: 'What is Pinyin?',
  subtitle: 'The Standard Romanization System for Mandarin Chinese',
  definition:
    'Pinyin (拼音, literally "spelled sounds") is the official Romanization system adopted in 1958 to represent standard Mandarin pronunciation using the Latin alphabet.',
  keyDifferences: [
    {
      title: 'Pinyin is Sound, Hanzi is Meaning',
      description:
        'Pinyin shows you how to pronounce a word. Chinese characters (汉字 Hanzi) convey the meaning. Thousands of distinct characters share only ~409 unique Pinyin syllables.',
    },
    {
      title: 'Not Pronounced Like English',
      description:
        'While letters like "m", "f", and "s" sound similar to English, letters like "c", "q", "x", "zh", and "r" represent unique tongue positions that require deliberate muscle training.',
    },
    {
      title: 'Pinyin Keyboard Input (IME)',
      description:
        'To type Chinese on any phone or computer, type the Pinyin letters without tone marks, then select the character. Use the letter "v" to type "ü" (e.g., type "lv" to produce "绿 lǜ").',
    },
  ],
  syllableAnatomy: {
    formula: 'Initial + Final + Tone Mark = Syllable',
    example: {
      initial: 'm',
      initialLabel: 'Initial (Consonant)',
      final: 'a',
      finalLabel: 'Final (Vowel/Glide)',
      tone: '¯',
      toneLabel: 'Tone Mark (1st Tone)',
      resultPinyin: 'mā',
      resultHanzi: '妈',
      meaning: 'Mother',
    },
  },
  tonePitchIntro:
    'Mandarin is a tonal language. The same syllable pronounced with different pitches produces completely different words.',
};

// 2. THE 4 TONES + NEUTRAL TONE
export const PINYIN_TONES: PinyinToneInfo[] = [
  {
    toneNumber: 1,
    toneName: '1st Tone: High Flat',
    markSymbol: 'ˉ',
    pitchContour: '55',
    pitchDescription: 'High, steady, and sustained without dropping. Like saying "ahh" at the doctor.',
    anchorSyllables: [
      { syllable: 'ma', pinyin: 'mā', hanzi: '妈', meaningEn: 'Mother', audioChar: '妈' },
      { syllable: 'ba', pinyin: 'bā', hanzi: '八', meaningEn: 'Eight', audioChar: '八' },
      { syllable: 'ka', pinyin: 'kā', hanzi: '咖', meaningEn: 'Coffee (first syllable)', audioChar: '咖' },
      { syllable: 'tian', pinyin: 'tiān', hanzi: '天', meaningEn: 'Sky / Day', audioChar: '天' },
    ],
  },
  {
    toneNumber: 2,
    toneName: '2nd Tone: Rising',
    markSymbol: 'ˊ',
    pitchContour: '35',
    pitchDescription: 'Starts at middle pitch and rises smoothly to the top. Like asking "What?!" in surprise.',
    anchorSyllables: [
      { syllable: 'ma', pinyin: 'má', hanzi: '麻', meaningEn: 'Hemp / Sesame', audioChar: '麻' },
      { syllable: 'cha', pinyin: 'chá', hanzi: '茶', meaningEn: 'Tea', audioChar: '茶' },
      { syllable: 'guo', pinyin: 'guó', hanzi: '国', meaningEn: 'Country', audioChar: '国' },
      { syllable: 'lai', pinyin: 'lái', hanzi: '来', meaningEn: 'To come', audioChar: '来' },
    ],
  },
  {
    toneNumber: 3,
    toneName: '3rd Tone: Dipping',
    markSymbol: 'ˇ',
    pitchContour: '214',
    pitchDescription: 'Dips down to the lowest vocal register, then slightly recovers. Deep and guttural.',
    anchorSyllables: [
      { syllable: 'ma', pinyin: 'mǎ', hanzi: '马', meaningEn: 'Horse', audioChar: '马' },
      { syllable: 'ni', pinyin: 'nǐ', hanzi: '你', meaningEn: 'You', audioChar: '你' },
      { syllable: 'hao', pinyin: 'hǎo', hanzi: '好', meaningEn: 'Good', audioChar: '好' },
      { syllable: 'shui', pinyin: 'shuǐ', hanzi: '水', meaningEn: 'Water', audioChar: '水' },
    ],
  },
  {
    toneNumber: 4,
    toneName: '4th Tone: Falling',
    markSymbol: 'ˋ',
    pitchContour: '51',
    pitchDescription: 'Sharp, decisive drop from highest pitch to lowest. Like giving a command: "Stop!".',
    anchorSyllables: [
      { syllable: 'ma', pinyin: 'mà', hanzi: '骂', meaningEn: 'To scold', audioChar: '骂' },
      { syllable: 'da', pinyin: 'dà', hanzi: '大', meaningEn: 'Big', audioChar: '大' },
      { syllable: 'shi', pinyin: 'shì', hanzi: '是', meaningEn: 'To be / Yes', audioChar: '是' },
      { syllable: 'kan', pinyin: 'kàn', hanzi: '看', meaningEn: 'To look / See', audioChar: '看' },
    ],
  },
  {
    toneNumber: 0,
    toneName: 'Neutral Tone: Light & Soft',
    markSymbol: '·',
    pitchContour: 'short',
    pitchDescription: 'Unstressed and half-length. Pitch adjusts naturally depending on the preceding syllable.',
    anchorSyllables: [
      { syllable: 'ma', pinyin: 'ma', hanzi: '吗', meaningEn: 'Question particle', audioChar: '吗' },
      { syllable: 'ba', pinyin: 'ba', hanzi: '吧', meaningEn: 'Suggestion particle', audioChar: '吧' },
      { syllable: 'de', pinyin: 'de', hanzi: '的', meaningEn: 'Possessive particle', audioChar: '的' },
    ],
  },
];

// Minimal contrast demonstration (mā, má, mǎ, mà, ma)
export const TONE_CONTRAST_SET = [
  { tone: 1, pinyin: 'mā', hanzi: '妈', meaningEn: 'Mother', audioChar: '妈', mark: 'High Flat (55)' },
  { tone: 2, pinyin: 'má', hanzi: '麻', meaningEn: 'Hemp', audioChar: '麻', mark: 'Rising (35)' },
  { tone: 3, pinyin: 'mǎ', hanzi: '马', meaningEn: 'Horse', audioChar: '马', mark: 'Dipping (214)' },
  { tone: 4, pinyin: 'mà', hanzi: '骂', meaningEn: 'To scold', audioChar: '骂', mark: 'Falling (51)' },
  { tone: 0, pinyin: 'ma', hanzi: '吗', meaningEn: 'Question particle', audioChar: '吗', mark: 'Neutral (short)' },
];

// 3. THE 20 BI-SYLLABIC TONE PAIRS (4x5 COMBINATIONS)
export const TONE_PAIRS_20: PinyinTonePair[] = [
  // 1st Tone Starts
  { id: 'tp_1_1', firstTone: 1, secondTone: 1, toneLabel: '1st + 1st', exampleHanzi: '咖啡', pinyin: 'kāfēi', meaningEn: 'Coffee', audioTarget: '咖啡' },
  { id: 'tp_1_2', firstTone: 1, secondTone: 2, toneLabel: '1st + 2nd', exampleHanzi: '中国', pinyin: 'Zhōngguó', meaningEn: 'China', audioTarget: '中国' },
  { id: 'tp_1_3', firstTone: 1, secondTone: 3, toneLabel: '1st + 3rd', exampleHanzi: '机场', pinyin: 'jīchǎng', meaningEn: 'Airport', audioTarget: '机场' },
  { id: 'tp_1_4', firstTone: 1, secondTone: 4, toneLabel: '1st + 4th', exampleHanzi: '面包', pinyin: 'miànbāo', meaningEn: 'Bread', audioTarget: '面包' },
  { id: 'tp_1_0', firstTone: 1, secondTone: 'neutral', toneLabel: '1st + Neutral', exampleHanzi: '妈妈', pinyin: 'māma', meaningEn: 'Mother', audioTarget: '妈妈' },

  // 2nd Tone Starts
  { id: 'tp_2_1', firstTone: 2, secondTone: 1, toneLabel: '2nd + 1st', exampleHanzi: '时间', pinyin: 'shíjiān', meaningEn: 'Time', audioTarget: '时间' },
  { id: 'tp_2_2', firstTone: 2, secondTone: 2, toneLabel: '2nd + 2nd', exampleHanzi: '银行', pinyin: 'yínháng', meaningEn: 'Bank', audioTarget: '银行' },
  { id: 'tp_2_3', firstTone: 2, secondTone: 3, toneLabel: '2nd + 3rd', exampleHanzi: '苹果', pinyin: 'píngguǒ', meaningEn: 'Apple', audioTarget: '苹果' },
  { id: 'tp_2_4', firstTone: 2, secondTone: 4, toneLabel: '2nd + 4th', exampleHanzi: '决定', pinyin: 'juédìng', meaningEn: 'Decide', audioTarget: '决定' },
  { id: 'tp_2_0', firstTone: 2, secondTone: 'neutral', toneLabel: '2nd + Neutral', exampleHanzi: '学生', pinyin: 'xuésheng', meaningEn: 'Student', audioTarget: '学生' },

  // 3rd Tone Starts
  { id: 'tp_3_1', firstTone: 3, secondTone: 1, toneLabel: '3rd + 1st', exampleHanzi: '北京', pinyin: 'Běijīng', meaningEn: 'Beijing', audioTarget: '北京' },
  { id: 'tp_3_2', firstTone: 3, secondTone: 2, toneLabel: '3rd + 2nd', exampleHanzi: '旅游', pinyin: 'lǚyóu', meaningEn: 'Travel', audioTarget: '旅游' },
  { id: 'tp_3_3', firstTone: 3, secondTone: 3, toneLabel: '3rd + 3rd (Sandhi)', exampleHanzi: '你好', pinyin: 'ní hǎo', meaningEn: 'Hello (3+3 -> 2+3)', audioTarget: '你好' },
  { id: 'tp_3_4', firstTone: 3, secondTone: 4, toneLabel: '3rd + 4th', exampleHanzi: '准备', pinyin: 'zhǔnbèi', meaningEn: 'Prepare', audioTarget: '准备' },
  { id: 'tp_3_0', firstTone: 3, secondTone: 'neutral', toneLabel: '3rd + Neutral', exampleHanzi: '喜欢', pinyin: 'xǐhuan', meaningEn: 'To like', audioTarget: '喜欢' },

  // 4th Tone Starts
  { id: 'tp_4_1', firstTone: 4, secondTone: 1, toneLabel: '4th + 1st', exampleHanzi: '飞机', pinyin: 'fēijī', meaningEn: 'Airplane', audioTarget: '飞机' },
  { id: 'tp_4_2', firstTone: 4, secondTone: 2, toneLabel: '4th + 2nd', exampleHanzi: '去年', pinyin: 'qùnián', meaningEn: 'Last year', audioTarget: '去年' },
  { id: 'tp_4_3', firstTone: 4, secondTone: 3, toneLabel: '4th + 3rd', exampleHanzi: '电影', pinyin: 'diànyǐng', meaningEn: 'Movie', audioTarget: '电影' },
  { id: 'tp_4_4', firstTone: 4, secondTone: 4, toneLabel: '4th + 4th', exampleHanzi: '再见', pinyin: 'zàijiàn', meaningEn: 'Goodbye', audioTarget: '再见' },
  { id: 'tp_4_0', firstTone: 4, secondTone: 'neutral', toneLabel: '4th + Neutral', exampleHanzi: '谢谢', pinyin: 'xièxie', meaningEn: 'Thank you', audioTarget: '谢谢' },
];

// Tone Sandhi Rules
export const TONE_SANDHI_RULES: ToneSandhiRule[] = [
  {
    id: 'sandhi_3_3',
    title: 'Two 3rd Tones Sandhi (3 + 3 → 2 + 3)',
    ruleFormula: '3rd tone + 3rd tone → 2nd tone + 3rd tone',
    exampleHanzi: '你好',
    writtenPinyin: 'nǐ hǎo',
    spokenPinyin: 'ní hǎo',
    meaningEn: 'Hello',
    explanationEn: 'When two 3rd tones appear consecutively, the first tone automatically turns into a 2nd tone.',
    audioTarget: '你好',
  },
  {
    id: 'sandhi_bu',
    title: 'Tone Change of "不" (bù + 4th → bú)',
    ruleFormula: 'bù (4th) + 4th tone → bú (2nd) + 4th tone',
    exampleHanzi: '不是',
    writtenPinyin: 'bù shì',
    spokenPinyin: 'bú shì',
    meaningEn: 'Is not',
    explanationEn: '"bù" is naturally 4th tone, but shifts to 2nd tone "bú" immediately before another 4th tone word.',
    audioTarget: '不是',
  },
  {
    id: 'sandhi_yi',
    title: 'Tone Change of "一" (yī sandhi)',
    ruleFormula: 'yī + 4th → yí (2nd) | yī + 1st/2nd/3rd → yì (4th)',
    exampleHanzi: '一个 / 一天',
    writtenPinyin: 'yī gè / yī tiān',
    spokenPinyin: 'yí gè / yì tiān',
    meaningEn: 'One / One day',
    explanationEn: '"yī" shifts to 2nd tone before a 4th tone (yí gè), and to 4th tone before 1st, 2nd, or 3rd tones (yì tiān).',
    audioTarget: '一个',
  },
];

// 4. INTERACTIVE PINYIN CHART MATRIX (YOYO CHINESE INSPIRED)
export const PINYIN_INITIALS_LIST = [
  'b', 'p', 'm', 'f',
  'd', 't', 'n', 'l',
  'g', 'k', 'h',
  'j', 'q', 'x',
  'zh', 'ch', 'sh', 'r',
  'z', 'c', 's',
  'y', 'w',
  '', // zero-initial
];

export const PINYIN_FINALS_CATEGORIES = {
  simple: ['a', 'o', 'e', 'i', 'u', 'ü'],
  compound: ['ai', 'ei', 'ao', 'ou', 'ia', 'ie', 'ua', 'uo', 'üe'],
  nasal: ['an', 'en', 'in', 'un', 'ün', 'ang', 'eng', 'ing', 'ong', 'iong'],
  special: ['er'],
};

// High-frequency curated syllable table with pure audio anchor characters
export const PINYIN_CHART_SYLLABLES: PinyinSyllableEntry[] = [
  // b
  { syllable: 'ba', initial: 'b', final: 'a', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'bā', 2: 'bá', 3: 'bǎ', 4: 'bà' }, audioChars: { 1: '八', 2: '拔', 3: '把', 4: '爸' }, exampleWord: { hanzi: '爸爸', pinyin: 'bàba', meaningEn: 'Dad' } },
  { syllable: 'bo', initial: 'b', final: 'o', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'bō', 2: 'bó', 3: 'bǒ', 4: 'bò' }, audioChars: { 1: '波', 2: '伯', 3: '跛', 4: '薄' }, exampleWord: { hanzi: '波浪', pinyin: 'bōlàng', meaningEn: 'Wave' } },
  { syllable: 'bai', initial: 'b', final: 'ai', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'bāi', 2: 'bái', 3: 'bǎi', 4: 'bài' }, audioChars: { 1: '掰', 2: '白', 3: '百', 4: '败' }, exampleWord: { hanzi: '白色', pinyin: 'báisè', meaningEn: 'White' } },
  { syllable: 'bei', initial: 'b', final: 'ei', validTones: [1, 3, 4], pinyinWithTones: { 1: 'bēi', 3: 'běi', 4: 'bèi' }, audioChars: { 1: '杯', 3: '北', 4: '被' }, exampleWord: { hanzi: '北京', pinyin: 'Běijīng', meaningEn: 'Beijing' } },
  { syllable: 'bao', initial: 'b', final: 'ao', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'bāo', 2: 'báo', 3: 'bǎo', 4: 'bào' }, audioChars: { 1: '包', 2: '薄', 3: '饱', 4: '报' }, exampleWord: { hanzi: '面包', pinyin: 'miànbāo', meaningEn: 'Bread' } },
  { syllable: 'ban', initial: 'b', final: 'an', validTones: [1, 3, 4], pinyinWithTones: { 1: 'bān', 3: 'bǎn', 4: 'bàn' }, audioChars: { 1: '班', 3: '板', 4: '半' }, exampleWord: { hanzi: '上班', pinyin: 'shàngbān', meaningEn: 'Go to work' } },
  { syllable: 'ben', initial: 'b', final: 'en', validTones: [1, 3, 4], pinyinWithTones: { 1: 'bēn', 3: 'běn', 4: 'bèn' }, audioChars: { 1: '奔', 3: '本', 4: '笨' }, exampleWord: { hanzi: '一本', pinyin: 'yī běn', meaningEn: 'One volume' } },
  { syllable: 'bang', initial: 'b', final: 'ang', validTones: [1, 3, 4], pinyinWithTones: { 1: 'bāng', 3: 'bǎng', 4: 'bàng' }, audioChars: { 1: '帮', 3: '榜', 4: '棒' }, exampleWord: { hanzi: '帮忙', pinyin: 'bāngmáng', meaningEn: 'Help' } },
  { syllable: 'beng', initial: 'b', final: 'eng', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'bēng', 2: 'béng', 3: 'běng', 4: 'bèng' }, audioChars: { 1: '崩', 2: '甭', 3: '绷', 4: '蹦' } },
  { syllable: 'bi', initial: 'b', final: 'i', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'bī', 2: 'bí', 3: 'bǐ', 4: 'bì' }, audioChars: { 1: '逼', 2: '鼻', 3: '比', 4: '必' }, exampleWord: { hanzi: '比较', pinyin: 'bǐjiào', meaningEn: 'Compare' } },
  { syllable: 'bian', initial: 'b', final: 'an', validTones: [1, 3, 4], pinyinWithTones: { 1: 'biān', 3: 'biǎn', 4: 'biàn' }, audioChars: { 1: '边', 3: '扁', 4: '变' }, exampleWord: { hanzi: '左边', pinyin: 'zuǒbian', meaningEn: 'Left side' } },
  { syllable: 'biao', initial: 'b', final: 'ao', validTones: [1, 3, 4], pinyinWithTones: { 1: 'biāo', 3: 'biǎo', 4: 'biào' }, audioChars: { 1: '标', 3: '表', 4: '鳔' }, exampleWord: { hanzi: '手表', pinyin: 'shǒubiǎo', meaningEn: 'Watch' } },
  { syllable: 'bie', initial: 'b', final: 'ie', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'biē', 2: 'bié', 3: 'biě', 4: 'biè' }, audioChars: { 1: '憋', 2: '别', 3: '瘪', 4: '别' }, exampleWord: { hanzi: '别人', pinyin: 'biérén', meaningEn: 'Other people' } },
  { syllable: 'bin', initial: 'b', final: 'in', validTones: [1, 4], pinyinWithTones: { 1: 'bīn', 4: 'bìn' }, audioChars: { 1: '宾', 4: '鬓' }, exampleWord: { hanzi: '宾馆', pinyin: 'bīnguǎn', meaningEn: 'Hotel' } },
  { syllable: 'bing', initial: 'b', final: 'ing', validTones: [1, 3, 4], pinyinWithTones: { 1: 'bīng', 3: 'bǐng', 4: 'bìng' }, audioChars: { 1: '冰', 3: '饼', 4: '病' }, exampleWord: { hanzi: '冰水', pinyin: 'bīngshuǐ', meaningEn: 'Ice water' } },
  { syllable: 'bu', initial: 'b', final: 'u', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'bū', 2: 'bú', 3: 'bǔ', 4: 'bù' }, audioChars: { 1: '逋', 2: '不', 3: '补', 4: '不' }, exampleWord: { hanzi: '不是', pinyin: 'bú shì', meaningEn: 'Is not' } },

  // p
  { syllable: 'pa', initial: 'p', final: 'a', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'pā', 2: 'pá', 3: 'pǎ', 4: 'pà' }, audioChars: { 1: '趴', 2: '爬', 3: '跑', 4: '怕' }, exampleWord: { hanzi: '害怕', pinyin: 'hàipà', meaningEn: 'Fear' } },
  { syllable: 'po', initial: 'p', final: 'o', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'pō', 2: 'pó', 3: 'pǒ', 4: 'pò' }, audioChars: { 1: '坡', 2: '婆', 3: '叵', 4: '破' }, exampleWord: { hanzi: '山坡', pinyin: 'shānpō', meaningEn: 'Hill slope' } },
  { syllable: 'pai', initial: 'p', final: 'ai', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'pāi', 2: 'pái', 3: 'pǎi', 4: 'pài' }, audioChars: { 1: '拍', 2: '排', 3: '迫', 4: '派' }, exampleWord: { hanzi: '拍照', pinyin: 'pāizhào', meaningEn: 'Take a photo' } },
  { syllable: 'pao', initial: 'p', final: 'ao', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'pāo', 2: 'páo', 3: 'pǎo', 4: 'pào' }, audioChars: { 1: '抛', 2: '袍', 3: '跑', 4: '泡' }, exampleWord: { hanzi: '跑步', pinyin: 'pǎobù', meaningEn: 'Run' } },
  { syllable: 'pan', initial: 'p', final: 'an', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'pān', 2: 'pán', 3: 'pǎn', 4: 'pàn' }, audioChars: { 1: '攀', 2: '盘', 3: '蹒', 4: '盼' }, exampleWord: { hanzi: '盘子', pinyin: 'pánzi', meaningEn: 'Plate' } },
  { syllable: 'peng', initial: 'p', final: 'eng', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'pēng', 2: 'péng', 3: 'pěng', 4: 'pèng' }, audioChars: { 1: '烹', 2: '朋', 3: '捧', 4: '碰' }, exampleWord: { hanzi: '朋友', pinyin: 'péngyou', meaningEn: 'Friend' } },
  { syllable: 'pi', initial: 'p', final: 'i', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'pī', 2: 'pí', 3: 'pǐ', 4: 'pì' }, audioChars: { 1: '批', 2: '皮', 3: '匹', 4: '屁' }, exampleWord: { hanzi: '皮肤', pinyin: 'pífū', meaningEn: 'Skin' } },
  { syllable: 'piao', initial: 'p', final: 'ao', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'piāo', 2: 'piáo', 3: 'piǎo', 4: 'piào' }, audioChars: { 1: '飘', 2: '瓢', 3: '漂', 4: '票' }, exampleWord: { hanzi: '门票', pinyin: 'ménpiào', meaningEn: 'Ticket' } },
  { syllable: 'ping', initial: 'p', final: 'ing', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'pīng', 2: 'píng', 3: 'pǐng', 4: 'pìng' }, audioChars: { 1: '乒', 2: '平', 3: '品', 4: '聘' }, exampleWord: { hanzi: '苹果', pinyin: 'píngguǒ', meaningEn: 'Apple' } },
  { syllable: 'pu', initial: 'p', final: 'u', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'pū', 2: 'pú', 3: 'pǔ', 4: 'pù' }, audioChars: { 1: '铺', 2: '葡', 3: '普', 4: '瀑' }, exampleWord: { hanzi: '普通话', pinyin: 'pǔtōnghuà', meaningEn: 'Mandarin' } },

  // m
  { syllable: 'ma', initial: 'm', final: 'a', validTones: [1, 2, 3, 4, 0], pinyinWithTones: { 1: 'mā', 2: 'má', 3: 'mǎ', 4: 'mà', 0: 'ma' }, audioChars: { 1: '妈', 2: '麻', 3: '马', 4: '骂', 0: '吗' }, exampleWord: { hanzi: '妈妈', pinyin: 'māma', meaningEn: 'Mom' } },
  { syllable: 'mo', initial: 'm', final: 'o', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'mō', 2: 'mó', 3: 'mǒ', 4: 'mò' }, audioChars: { 1: '摸', 2: '磨', 3: '抹', 4: '墨' }, exampleWord: { hanzi: '周末', pinyin: 'zhōumò', meaningEn: 'Weekend' } },
  { syllable: 'me', initial: 'm', final: 'e', validTones: [0], pinyinWithTones: { 0: 'me' }, audioChars: { 0: '么' }, exampleWord: { hanzi: '什么', pinyin: 'shénme', meaningEn: 'What' } },
  { syllable: 'mai', initial: 'm', final: 'ai', validTones: [2, 3, 4], pinyinWithTones: { 2: 'mái', 3: 'mǎi', 4: 'mài' }, audioChars: { 2: '埋', 3: '买', 4: '卖' }, exampleWord: { hanzi: '买单', pinyin: 'mǎidān', meaningEn: 'Pay the bill' } },
  { syllable: 'man', initial: 'm', final: 'an', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'mān', 2: 'mán', 3: 'mǎn', 4: 'màn' }, audioChars: { 1: '蛮', 2: '瞒', 3: '满', 4: '慢' }, exampleWord: { hanzi: '慢慢', pinyin: 'mànmàn', meaningEn: 'Slowly' } },
  { syllable: 'men', initial: 'm', final: 'en', validTones: [2, 0], pinyinWithTones: { 2: 'mén', 0: 'men' }, audioChars: { 2: '门', 0: '们' }, exampleWord: { hanzi: '我们', pinyin: 'wǒmen', meaningEn: 'We / Us' } },
  { syllable: 'mang', initial: 'm', final: 'ang', validTones: [2, 3], pinyinWithTones: { 2: 'máng', 3: 'mǎng' }, audioChars: { 2: '忙', 3: '莽' }, exampleWord: { hanzi: '很忙', pinyin: 'hěn máng', meaningEn: 'Very busy' } },
  { syllable: 'mi', initial: 'm', final: 'i', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'mī', 2: 'mí', 3: 'mǐ', 4: 'mì' }, audioChars: { 1: '咪', 2: '迷', 3: '米', 4: '密' }, exampleWord: { hanzi: '米饭', pinyin: 'mǐfàn', meaningEn: 'Cooked rice' } },
  { syllable: 'mian', initial: 'm', final: 'an', validTones: [3, 4], pinyinWithTones: { 3: 'miǎn', 4: 'miàn' }, audioChars: { 3: '免', 4: '面' }, exampleWord: { hanzi: '面条', pinyin: 'miàntiáo', meaningEn: 'Noodles' } },
  { syllable: 'ming', initial: 'm', final: 'ing', validTones: [2, 4], pinyinWithTones: { 2: 'míng', 4: 'mìng' }, audioChars: { 2: '明', 4: '命' }, exampleWord: { hanzi: '明天', pinyin: 'míngtiān', meaningEn: 'Tomorrow' } },
  { syllable: 'mu', initial: 'm', final: 'u', validTones: [3, 4], pinyinWithTones: { 3: 'mǔ', 4: 'mù' }, audioChars: { 3: '母', 4: '木' }, exampleWord: { hanzi: '目光', pinyin: 'mùguāng', meaningEn: 'Sight' } },

  // f
  { syllable: 'fa', initial: 'f', final: 'a', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'fā', 2: 'fá', 3: 'fǎ', 4: 'fà' }, audioChars: { 1: '发', 2: '罚', 3: '法', 4: '发' }, exampleWord: { hanzi: '方法', pinyin: 'fāngfǎ', meaningEn: 'Method' } },
  { syllable: 'fo', initial: 'f', final: 'o', validTones: [2], pinyinWithTones: { 2: 'fó' }, audioChars: { 2: '佛' } },
  { syllable: 'fei', initial: 'f', final: 'ei', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'fēi', 2: 'féi', 3: 'fěi', 4: 'fèi' }, audioChars: { 1: '飞', 2: '肥', 3: '匪', 4: '费' }, exampleWord: { hanzi: '飞机', pinyin: 'fēijī', meaningEn: 'Airplane' } },
  { syllable: 'fan', initial: 'f', final: 'an', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'fān', 2: 'fán', 3: 'fǎn', 4: 'fàn' }, audioChars: { 1: '番', 2: '烦', 3: '反', 4: '饭' }, exampleWord: { hanzi: '吃饭', pinyin: 'chīfàn', meaningEn: 'Eat a meal' } },
  { syllable: 'fang', initial: 'f', final: 'ang', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'fāng', 2: 'fáng', 3: 'fǎng', 4: 'fàng' }, audioChars: { 1: '方', 2: '房', 3: '访', 4: '放' }, exampleWord: { hanzi: '房子', pinyin: 'fángzi', meaningEn: 'House' } },
  { syllable: 'fu', initial: 'f', final: 'u', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'fū', 2: 'fú', 3: 'fǔ', 4: 'fù' }, audioChars: { 1: '夫', 2: '服', 3: '府', 4: '父' }, exampleWord: { hanzi: '服务员', pinyin: 'fúwùyuán', meaningEn: 'Waiter' } },

  // d, t, n, l
  { syllable: 'da', initial: 'd', final: 'a', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'dā', 2: 'dá', 3: 'dǎ', 4: 'dà' }, audioChars: { 1: '搭', 2: '达', 3: '打', 4: '大' }, exampleWord: { hanzi: '大学', pinyin: 'dàxué', meaningEn: 'University' } },
  { syllable: 'de', initial: 'd', final: 'e', validTones: [2, 0], pinyinWithTones: { 2: 'dé', 0: 'de' }, audioChars: { 2: '得', 0: '的' }, exampleWord: { hanzi: '我的', pinyin: 'wǒ de', meaningEn: 'My / Mine' } },
  { syllable: 'di', initial: 'd', final: 'i', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'dī', 2: 'dí', 3: 'dǐ', 4: 'dì' }, audioChars: { 1: '低', 2: '敌', 3: '底', 4: '地' }, exampleWord: { hanzi: '地方', pinyin: 'dìfang', meaningEn: 'Place' } },
  { syllable: 'duo', initial: 'd', final: 'uo', validTones: [1, 3, 4], pinyinWithTones: { 1: 'duō', 3: 'duǒ', 4: 'duò' }, audioChars: { 1: '多', 3: '朵', 4: '剁' }, exampleWord: { hanzi: '多少', pinyin: 'duōshao', meaningEn: 'How much' } },
  { syllable: 'ta', initial: 't', final: 'a', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'tā', 2: 'tá', 3: 'tǎ', 4: 'tà' }, audioChars: { 1: '他', 2: '塔', 3: '踏', 4: '踏' }, exampleWord: { hanzi: '他们', pinyin: 'tāmen', meaningEn: 'They' } },
  { syllable: 'tian', initial: 't', final: 'an', validTones: [1, 2, 3], pinyinWithTones: { 1: 'tiān', 2: 'tián', 3: 'tiǎn' }, audioChars: { 1: '天', 2: '田', 3: '舔' }, exampleWord: { hanzi: '今天', pinyin: 'jīntiān', meaningEn: 'Today' } },
  { syllable: 'na', initial: 'n', final: 'a', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'nā', 2: 'ná', 3: 'nǎ', 4: 'nà' }, audioChars: { 1: '南', 2: '拿', 3: '哪', 4: '那' }, exampleWord: { hanzi: '哪里', pinyin: 'nǎlǐ', meaningEn: 'Where' } },
  { syllable: 'ni', initial: 'n', final: 'i', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'nī', 2: 'ní', 3: 'nǐ', 4: 'nì' }, audioChars: { 1: '妮', 2: '泥', 3: '你', 4: '逆' }, exampleWord: { hanzi: '你好', pinyin: 'nǐ hǎo', meaningEn: 'Hello' } },
  { syllable: 'lv', initial: 'l', final: 'ü', validTones: [2, 3, 4], pinyinWithTones: { 2: 'lǘ', 3: 'lǚ', 4: 'lǜ' }, audioChars: { 2: '驴', 3: '旅', 4: '绿' }, exampleWord: { hanzi: '旅游', pinyin: 'lǚyóu', meaningEn: 'Travel (type lv)' } },
  { syllable: 'lai', initial: 'l', final: 'ai', validTones: [2], pinyinWithTones: { 2: 'lái' }, audioChars: { 2: '来' }, exampleWord: { hanzi: '来这里', pinyin: 'lái zhèlǐ', meaningEn: 'Come here' } },

  // g, k, h
  { syllable: 'ge', initial: 'g', final: 'e', validTones: [1, 2, 3, 4, 0], pinyinWithTones: { 1: 'gē', 2: 'gé', 3: 'gě', 4: 'gè', 0: 'ge' }, audioChars: { 1: '哥', 2: '格', 3: '葛', 4: '个', 0: '个' }, exampleWord: { hanzi: '一个', pinyin: 'yí gè', meaningEn: 'One item' } },
  { syllable: 'gao', initial: 'g', final: 'ao', validTones: [1, 3, 4], pinyinWithTones: { 1: 'gāo', 3: 'gǎo', 4: 'gào' }, audioChars: { 1: '高', 3: '搞', 4: '告' }, exampleWord: { hanzi: '高兴', pinyin: 'gāoxìng', meaningEn: 'Happy' } },
  { syllable: 'kai', initial: 'k', final: 'ai', validTones: [1, 3, 4], pinyinWithTones: { 1: 'kāi', 3: 'kǎi', 4: 'kài' }, audioChars: { 1: '开', 3: '铠', 4: '慨' }, exampleWord: { hanzi: '开门', pinyin: 'kāimén', meaningEn: 'Open the door' } },
  { syllable: 'kan', initial: 'k', final: 'an', validTones: [1, 3, 4], pinyinWithTones: { 1: 'kān', 3: 'kǎn', 4: 'kàn' }, audioChars: { 1: '看', 3: '砍', 4: '看' }, exampleWord: { hanzi: '看书', pinyin: 'kànshū', meaningEn: 'Read a book' } },
  { syllable: 'hao', initial: 'h', final: 'ao', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'hāo', 2: 'háo', 3: 'hǎo', 4: 'hào' }, audioChars: { 1: '蒿', 2: '豪', 3: '好', 4: '号' }, exampleWord: { hanzi: '很好', pinyin: 'hěn hǎo', meaningEn: 'Very good' } },
  { syllable: 'he', initial: 'h', final: 'e', validTones: [1, 2, 4], pinyinWithTones: { 1: 'hē', 2: 'hé', 4: 'hè' }, audioChars: { 1: '喝', 2: '和', 4: '贺' }, exampleWord: { hanzi: '喝水', pinyin: 'hē shuǐ', meaningEn: 'Drink water' } },

  // j, q, x (Notice: ü written as u)
  { syllable: 'ji', initial: 'j', final: 'i', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'jī', 2: 'jí', 3: 'jǐ', 4: 'jì' }, audioChars: { 1: '鸡', 2: '极', 3: '几', 4: '记' }, exampleWord: { hanzi: '飞机', pinyin: 'fēijī', meaningEn: 'Airplane' } },
  { syllable: 'jia', initial: 'j', final: 'a', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'jiā', 2: 'jiá', 3: 'jiǎ', 4: 'jià' }, audioChars: { 1: '家', 2: '夹', 3: '假', 4: '价' }, exampleWord: { hanzi: '大家', pinyin: 'dàjiā', meaningEn: 'Everyone' } },
  { syllable: 'ju', initial: 'j', final: 'ü', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'jū', 2: 'jú', 3: 'jǔ', 4: 'jù' }, audioChars: { 1: '居', 2: '橘', 3: '举', 4: '句' }, exampleWord: { hanzi: '句子', pinyin: 'jùzi', meaningEn: 'Sentence (j+ü -> ju)' } },
  { syllable: 'qi', initial: 'q', final: 'i', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'qī', 2: 'qí', 3: 'qǐ', 4: 'qì' }, audioChars: { 1: '七', 2: '骑', 3: '起', 4: '气' }, exampleWord: { hanzi: '对不起', pinyin: 'duìbuqǐ', meaningEn: 'Sorry' } },
  { syllable: 'qian', initial: 'q', final: 'an', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'qiān', 2: 'qián', 3: 'qiǎn', 4: 'qiàn' }, audioChars: { 1: '千', 2: '钱', 3: '浅', 4: '欠' }, exampleWord: { hanzi: '多少钱', pinyin: 'duōshao qián', meaningEn: 'How much money' } },
  { syllable: 'qu', initial: 'q', final: 'ü', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'qū', 2: 'qú', 3: 'qǔ', 4: 'qù' }, audioChars: { 1: '区', 2: '渠', 3: '取', 4: '去' }, exampleWord: { hanzi: '去商店', pinyin: 'qù shāngdiàn', meaningEn: 'Go to store' } },
  { syllable: 'xi', initial: 'x', final: 'i', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'xī', 2: 'xí', 3: 'xǐ', 4: 'xì' }, audioChars: { 1: '西', 2: '习', 3: '喜', 4: '细' }, exampleWord: { hanzi: '喜欢', pinyin: 'xǐhuan', meaningEn: 'To like' } },
  { syllable: 'xie', initial: 'x', final: 'ie', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'xiē', 2: 'xié', 3: 'xiě', 4: 'xiè' }, audioChars: { 1: '些', 2: '鞋', 3: '写', 4: '谢' }, exampleWord: { hanzi: '谢谢', pinyin: 'xièxie', meaningEn: 'Thank you' } },
  { syllable: 'xu', initial: 'x', final: 'ü', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'xū', 2: 'xú', 3: 'xǔ', 4: 'xù' }, audioChars: { 1: '需', 2: '徐', 3: '许', 4: '序' }, exampleWord: { hanzi: '学习', pinyin: 'xuéxí', meaningEn: 'Study' } },

  // zh, ch, sh, r (Retroflex sounds)
  { syllable: 'zhi', initial: 'zh', final: 'i', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'zhī', 2: 'zhí', 3: 'zhǐ', 4: 'zhì' }, audioChars: { 1: '知', 2: '直', 3: '只', 4: '志' }, exampleWord: { hanzi: '知道', pinyin: 'zhīdào', meaningEn: 'To know' } },
  { syllable: 'zhong', initial: 'zh', final: 'ong', validTones: [1, 3, 4], pinyinWithTones: { 1: 'zhōng', 3: 'zhǒng', 4: 'zhòng' }, audioChars: { 1: '中', 3: '种', 4: '重' }, exampleWord: { hanzi: '中国', pinyin: 'Zhōngguó', meaningEn: 'China' } },
  { syllable: 'chi', initial: 'ch', final: 'i', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'chī', 2: 'chí', 3: 'chǐ', 4: 'chì' }, audioChars: { 1: '吃', 2: '迟', 3: '齿', 4: '翅' }, exampleWord: { hanzi: '吃饭', pinyin: 'chīfàn', meaningEn: 'To eat' } },
  { syllable: 'cha', initial: 'ch', final: 'a', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'chā', 2: 'chá', 3: 'chǎ', 4: 'chà' }, audioChars: { 1: '插', 2: '茶', 3: '汊', 4: '差' }, exampleWord: { hanzi: '喝茶', pinyin: 'hē chá', meaningEn: 'Drink tea' } },
  { syllable: 'shi', initial: 'sh', final: 'i', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'shī', 2: 'shí', 3: 'shǐ', 4: 'shì' }, audioChars: { 1: '师', 2: '十', 3: '使', 4: '是' }, exampleWord: { hanzi: '老师', pinyin: 'lǎoshī', meaningEn: 'Teacher' } },
  { syllable: 'shui', initial: 'sh', final: 'ui', validTones: [3, 4], pinyinWithTones: { 3: 'shuǐ', 4: 'shuì' }, audioChars: { 3: '水', 4: '睡' }, exampleWord: { hanzi: '喝水', pinyin: 'hē shuǐ', meaningEn: 'Water' } },
  { syllable: 'ren', initial: 'r', final: 'en', validTones: [2, 3, 4], pinyinWithTones: { 2: 'rén', 3: 'rěn', 4: 'rèn' }, audioChars: { 2: '人', 3: '忍', 4: '认' }, exampleWord: { hanzi: '中国人', pinyin: 'Zhōngguórén', meaningEn: 'Person' } },
  { syllable: 'ri', initial: 'r', final: 'i', validTones: [4], pinyinWithTones: { 4: 'rì' }, audioChars: { 4: '日' }, exampleWord: { hanzi: '星期日', pinyin: 'xīngqīrì', meaningEn: 'Sunday' } },

  // z, c, s (Dental sibilants)
  { syllable: 'zi', initial: 'z', final: 'i', validTones: [1, 3, 4, 0], pinyinWithTones: { 1: 'zī', 3: 'zǐ', 4: 'zì', 0: 'zi' }, audioChars: { 1: '资', 3: '子', 4: '字', 0: '子' }, exampleWord: { hanzi: '汉字', pinyin: 'Hànzì', meaningEn: 'Chinese character' } },
  { syllable: 'zai', initial: 'z', final: 'ai', validTones: [3, 4], pinyinWithTones: { 3: 'zǎi', 4: 'zài' }, audioChars: { 3: '崽', 4: '在' }, exampleWord: { hanzi: '再见', pinyin: 'zàijiàn', meaningEn: 'Goodbye' } },
  { syllable: 'ci', initial: 'c', final: 'i', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'cī', 2: 'cí', 3: 'cǐ', 4: 'cì' }, audioChars: { 1: '呲', 2: '词', 3: '此', 4: '次' }, exampleWord: { hanzi: '生词', pinyin: 'shēngcí', meaningEn: 'Vocabulary' } },
  { syllable: 'si', initial: 's', final: 'i', validTones: [1, 3, 4], pinyinWithTones: { 1: 'sī', 3: 'sǐ', 4: 'sì' }, audioChars: { 1: '司', 3: '死', 4: '四' }, exampleWord: { hanzi: '四', pinyin: 'sì', meaningEn: 'Four' } },

  // y, w
  { syllable: 'yi', initial: 'y', final: 'i', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'yī', 2: 'yí', 3: 'yǐ', 4: 'yì' }, audioChars: { 1: '一', 2: '姨', 3: '以', 4: '意' }, exampleWord: { hanzi: '一', pinyin: 'yī', meaningEn: 'One' } },
  { syllable: 'wu', initial: 'w', final: 'u', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'wū', 2: 'wú', 3: 'wǔ', 4: 'wù' }, audioChars: { 1: '屋', 2: '无', 3: '五', 4: '物' }, exampleWord: { hanzi: '五', pinyin: 'wǔ', meaningEn: 'Five' } },
  { syllable: 'yu', initial: 'y', final: 'ü', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'yū', 2: 'yú', 3: 'yǔ', 4: 'yù' }, audioChars: { 1: '迂', 2: '鱼', 3: '雨', 4: '遇' }, exampleWord: { hanzi: '下雨', pinyin: 'xià yǔ', meaningEn: 'Rain' } },
];

// 5. 6 PEDAGOGICALLY ORDERED UNITS (MODULE 1)
export const PINYIN_CURRICULUM_UNITS: PinyinUnit[] = [
  {
    id: 'unit_1',
    unitNumber: 1,
    conceptId: 'hsk1_p01',
    slug: 'pinyin_overview_anatomy',
    titleEn: 'Unit 1: Pinyin Overview & Syllable Anatomy',
    objectiveEn: 'Understand syllable structure (Initial + Final + Tone) and how Pinyin maps to Mandarin sounds.',
    estimatedMinutes: 5,
    flashcards: [
      { id: 'fc_1_1', stage: 'sound', stageLabel: 'Initial', targetPinyin: 'b', targetHanzi: '玻', meaningEn: 'Unaspirated voiceless stop (like "p" in "speak")', audioTarget: '八', acousticTip: 'Do not blow air. Feel your lips pop cleanly.' },
      { id: 'fc_1_2', stage: 'sound', stageLabel: 'Initial', targetPinyin: 'p', targetHanzi: '坡', meaningEn: 'Aspirated voiceless stop (like "p" in "peak")', audioTarget: '坡', acousticTip: 'Strong puff of air. Hold your hand in front of your lips to feel the breeze.' },
      { id: 'fc_1_3', stage: 'syllable', stageLabel: 'Simple Syllable', targetPinyin: 'bā', targetHanzi: '八', meaningEn: 'Eight (Number 8)', audioTarget: '八', toneIndex: 1 },
      { id: 'fc_1_4', stage: 'word', stageLabel: 'Core Word', targetPinyin: 'māma', targetHanzi: '妈妈', meaningEn: 'Mom / Mother', audioTarget: '妈妈' },
      { id: 'fc_1_5', stage: 'phrase', stageLabel: 'Real Context', targetPinyin: 'bā gè', targetHanzi: '八个', meaningEn: 'Eight items', audioTarget: '八个' },
    ],
    quizQuestions: [
      {
        id: 'q_1_1',
        type: 'minimal_pair',
        audioTarget: '八',
        questionText: 'Listen to the audio. Which syllable was pronounced?',
        options: ['bā (unaspirated)', 'pā (aspirated puff)'],
        correctAnswer: 'bā (unaspirated)',
        explanationEn: '"bā" starts with unvoiced, unaspirated "b", sounding like the "p" in "sport".',
      },
      {
        id: 'q_1_2',
        type: 'spelling',
        audioTarget: '妈妈',
        questionText: 'Listen and identify the correct Pinyin transcription for this word:',
        options: ['māma (1st tone + neutral)', 'bàba (4th tone + neutral)', 'gēge (1st tone + neutral)'],
        correctAnswer: 'māma (1st tone + neutral)',
        explanationEn: '"māma" consists of 1st tone "mā" followed by a short unstressed neutral tone.',
      },
      {
        id: 'q_1_3',
        type: 'spelling',
        audioTarget: '马',
        questionText: 'How do you type the character "绿 lǜ" on a standard English keyboard?',
        options: ['Type "lv"', 'Type "lu"', 'Type "lyu"'],
        correctAnswer: 'Type "lv"',
        explanationEn: 'The letter "v" represents "ü" in all Pinyin input methods (IME).',
      },
    ],
  },
  {
    id: 'unit_2',
    unitNumber: 2,
    conceptId: 'hsk1_p02',
    slug: 'four_tones_mastery',
    titleEn: 'Unit 2: The 4 Mandarin Tones',
    objectiveEn: 'Distinguish and produce the 4 pitch contours (55, 35, 214, 51) and neutral tone accurately.',
    estimatedMinutes: 5,
    flashcards: [
      { id: 'fc_2_1', stage: 'sound', stageLabel: '1st Tone', targetPinyin: 'mā', targetHanzi: '妈', meaningEn: 'Mother (High Flat 55)', audioTarget: '妈', toneIndex: 1, acousticTip: 'Keep pitch steadily high without waivering.' },
      { id: 'fc_2_2', stage: 'sound', stageLabel: '2nd Tone', targetPinyin: 'má', targetHanzi: '麻', meaningEn: 'Hemp / Numb (Rising 35)', audioTarget: '麻', toneIndex: 2, acousticTip: 'Glide smoothly upward like asking "What?".' },
      { id: 'fc_2_3', stage: 'sound', stageLabel: '3rd Tone', targetPinyin: 'mǎ', targetHanzi: '马', meaningEn: 'Horse (Dipping 214)', audioTarget: '马', toneIndex: 3, acousticTip: 'Dip low into your vocal register before slight recovery.' },
      { id: 'fc_2_4', stage: 'sound', stageLabel: '4th Tone', targetPinyin: 'mà', targetHanzi: '骂', meaningEn: 'To scold (Falling 51)', audioTarget: '骂', toneIndex: 4, acousticTip: 'Sharp, decisive drop. Do not drag it out.' },
      { id: 'fc_2_5', stage: 'sound', stageLabel: 'Neutral', targetPinyin: 'ma', targetHanzi: '吗', meaningEn: 'Question particle (Light)', audioTarget: '吗', toneIndex: 0, acousticTip: 'Half-length and soft.' },
    ],
    quizQuestions: [
      {
        id: 'q_2_1',
        type: 'tone_id',
        audioTarget: '妈',
        questionText: 'Listen to the audio. Which tone was pronounced?',
        options: ['1st Tone (High Flat 55)', '2nd Tone (Rising 35)', '3rd Tone (Dipping 214)', '4th Tone (Falling 51)'],
        correctAnswer: '1st Tone (High Flat 55)',
        explanationEn: 'This sound stays high and flat at pitch level 5, characteristic of the 1st tone.',
      },
      {
        id: 'q_2_2',
        type: 'tone_id',
        audioTarget: '马',
        questionText: 'Listen to the audio. Which tone was pronounced?',
        options: ['3rd Tone (Dipping 214)', '2nd Tone (Rising 35)', '4th Tone (Falling 51)', '1st Tone (High Flat 55)'],
        correctAnswer: '3rd Tone (Dipping 214)',
        explanationEn: '"mǎ" (马) dips down into the lowest vocal register, marking the 3rd tone.',
      },
      {
        id: 'q_2_3',
        type: 'tone_id',
        audioTarget: '骂',
        questionText: 'Listen to the audio. Which tone was pronounced?',
        options: ['4th Tone (Falling 51)', '1st Tone (High Flat 55)', '2nd Tone (Rising 35)', '3rd Tone (Dipping 214)'],
        correctAnswer: '4th Tone (Falling 51)',
        explanationEn: '"mà" (骂) drops sharply and decisively from pitch level 5 down to 1.',
      },
    ],
  },
  {
    id: 'unit_3',
    unitNumber: 3,
    conceptId: 'hsk1_p03',
    slug: 'distinctive_consonants',
    titleEn: 'Unit 3: Difficult Consonants (zh/ch/sh vs z/c/s vs j/q/x)',
    objectiveEn: 'Master retroflex, dental sibilant, and palatal sounds that differ critically from English.',
    estimatedMinutes: 5,
    flashcards: [
      { id: 'fc_3_1', stage: 'sound', stageLabel: 'Retroflex', targetPinyin: 'zhī', targetHanzi: '知', meaningEn: 'To know (Tongue tip curled back)', audioTarget: '知', acousticTip: 'Curl tongue tip toward the hard palate without touching teeth.' },
      { id: 'fc_3_2', stage: 'sound', stageLabel: 'Dental', targetPinyin: 'zī', targetHanzi: '字', meaningEn: 'Character (Tongue flat behind teeth)', audioTarget: '字', acousticTip: 'Tongue tip presses flat against back of upper front teeth.' },
      { id: 'fc_3_3', stage: 'sound', stageLabel: 'Palatal', targetPinyin: 'qī', targetHanzi: '七', meaningEn: 'Seven (Air through tongue-palate)', audioTarget: '七', acousticTip: 'Smile wide, puff air through flat tongue surface.' },
      { id: 'fc_3_4', stage: 'word', stageLabel: 'Retroflex Word', targetPinyin: 'Zhōngguó', targetHanzi: '中国', meaningEn: 'China', audioTarget: '中国' },
      { id: 'fc_3_5', stage: 'word', stageLabel: 'Essential Word', targetPinyin: 'lǎoshī', targetHanzi: '老师', meaningEn: 'Teacher (sh retroflex)', audioTarget: '老师' },
    ],
    quizQuestions: [
      {
        id: 'q_3_1',
        type: 'minimal_pair',
        audioTarget: '中国',
        questionText: 'Listen to the audio. Does the first syllable use retroflex "zh" or dental "z"?',
        options: ['zh (Zhōngguó - tongue curled)', 'z (Zōngguó - tongue flat)'],
        correctAnswer: 'zh (Zhōngguó - tongue curled)',
        explanationEn: '"zh" in "Zhōngguó" is retroflex, pronounced with the tongue tip slightly curled back.',
      },
      {
        id: 'q_3_2',
        type: 'minimal_pair',
        audioTarget: '四',
        questionText: 'Listen to the audio. Was that "sì" (four) or "shì" (is/to be)?',
        options: ['sì (Dental sibilant)', 'shì (Retroflex)'],
        correctAnswer: 'sì (Dental sibilant)',
        explanationEn: '"sì" (四) uses dental "s" with flat tongue, unlike retroflex "shì" (是).',
      },
      {
        id: 'q_3_3',
        type: 'minimal_pair',
        audioTarget: '七',
        questionText: 'Listen to the audio. Which sound was produced?',
        options: ['qī (Number 7)', 'xī (West)'],
        correctAnswer: 'qī (Number 7)',
        explanationEn: '"q" is aspirated with a burst of air, whereas "x" is an unburst fricative.',
      },
    ],
  },
  {
    id: 'unit_4',
    unitNumber: 4,
    conceptId: 'hsk1_p04',
    slug: 'compound_finals_glides',
    titleEn: 'Unit 4: Compound & Nasal Finals (ai, ao, an, ang, ü)',
    objectiveEn: 'Execute smooth vowel glides and distinguish front nasal (-n) from back nasal (-ng).',
    estimatedMinutes: 5,
    flashcards: [
      { id: 'fc_4_1', stage: 'sound', stageLabel: 'Compound Final', targetPinyin: 'kāi', targetHanzi: '开', meaningEn: 'Open (a -> i glide)', audioTarget: '开', acousticTip: 'Start with wide open "a", glide seamlessly into high "i".' },
      { id: 'fc_4_2', stage: 'sound', stageLabel: 'Front Nasal', targetPinyin: 'fàn', targetHanzi: '饭', meaningEn: 'Rice / Meal (-n ending)', audioTarget: '饭', acousticTip: 'Tongue tip closes against the alveolar ridge (behind teeth).' },
      { id: 'fc_4_3', stage: 'sound', stageLabel: 'Back Nasal', targetPinyin: 'fáng', targetHanzi: '房', meaningEn: 'House / Room (-ng ending)', audioTarget: '房', acousticTip: 'Back of tongue lifts against soft palate (nasal resonance).' },
      { id: 'fc_4_4', stage: 'word', stageLabel: 'High-Frequency Word', targetPinyin: 'kāfēi', targetHanzi: '咖啡', meaningEn: 'Coffee', audioTarget: '咖啡' },
      { id: 'fc_4_5', stage: 'phrase', stageLabel: 'Dining Phrase', targetPinyin: 'chī fàn', targetHanzi: '吃饭', meaningEn: 'Eat a meal', audioTarget: '吃饭' },
    ],
    quizQuestions: [
      {
        id: 'q_4_1',
        type: 'minimal_pair',
        audioTarget: '饭',
        questionText: 'Listen to the audio. Does it end in front nasal (-n) or back nasal (-ng)?',
        options: ['-n (fàn)', '-ng (fàng)'],
        correctAnswer: '-n (fàn)',
        explanationEn: '"fàn" ends in alveolar nasal -n, closing the airflow behind the front teeth.',
      },
      {
        id: 'q_4_2',
        type: 'spelling',
        audioTarget: '咖啡',
        questionText: 'Listen and select the correct Pinyin spelling:',
        options: ['kāfēi', 'kāifēi', 'kēfēi'],
        correctAnswer: 'kāfēi',
        explanationEn: 'The first syllable is "kā" (simple final "a"), not "kāi".',
      },
    ],
  },
  {
    id: 'unit_5',
    unitNumber: 5,
    conceptId: 'hsk1_p05',
    slug: 'tone_pairs_sandhi',
    titleEn: 'Unit 5: Bi-Syllabic Tone Pairs & Tone Sandhi',
    objectiveEn: 'Master the 20 natural two-syllable tone combinations and essential sandhi (3+3 -> 2+3, bù, yī).',
    estimatedMinutes: 5,
    flashcards: [
      { id: 'fc_5_1', stage: 'word', stageLabel: '3+3 Sandhi', targetPinyin: 'ní hǎo', targetHanzi: '你好', meaningEn: 'Hello (Spelled nǐ hǎo, spoken ní hǎo)', audioTarget: '你好', acousticTip: 'First syllable rises as a 2nd tone automatically.' },
      { id: 'fc_5_2', stage: 'word', stageLabel: 'bù Sandhi', targetPinyin: 'bú shì', targetHanzi: '不是', meaningEn: 'Is not (bù + 4th -> bú)', audioTarget: '不是', acousticTip: '"bù" changes to 2nd tone before another 4th tone.' },
      { id: 'fc_5_3', stage: 'word', stageLabel: 'Tone Pair (1+2)', targetPinyin: 'Zhōngguó', targetHanzi: '中国', meaningEn: 'China (1st flat + 2nd rising)', audioTarget: '中国' },
      { id: 'fc_5_4', stage: 'word', stageLabel: 'Tone Pair (4+4)', targetPinyin: 'zàijiàn', targetHanzi: '再见', meaningEn: 'Goodbye (4th drop + 4th drop)', audioTarget: '再见' },
      { id: 'fc_5_5', stage: 'phrase', stageLabel: 'High Frequency', targetPinyin: 'yí gè', targetHanzi: '一个', meaningEn: 'One item (yī + 4th -> yí)', audioTarget: '一个' },
    ],
    quizQuestions: [
      {
        id: 'q_5_1',
        type: 'tone_pair',
        audioTarget: '咖啡',
        questionText: 'Listen to the tone combination in "kāfēi". Which pair is this?',
        options: ['1st Tone + 1st Tone', '1st Tone + 2nd Tone', '2nd Tone + 1st Tone', '4th Tone + 4th Tone'],
        correctAnswer: '1st Tone + 1st Tone',
        explanationEn: 'Both "kā" and "fēi" sustain a high, steady 1st tone (55-55).',
      },
      {
        id: 'q_5_2',
        type: 'tone_pair',
        audioTarget: '你好',
        questionText: 'In natural speech, what happens to the two 3rd tones in "nǐ hǎo"?',
        options: ['The first turns into a 2nd tone (ní hǎo)', 'Both remain low dipping tones', 'The second turns into a 4th tone'],
        correctAnswer: 'The first turns into a 2nd tone (ní hǎo)',
        explanationEn: 'Rule: 3rd tone + 3rd tone -> 2nd tone + 3rd tone.',
      },
      {
        id: 'q_5_3',
        type: 'tone_pair',
        audioTarget: '再见',
        questionText: 'Listen to "zàijiàn". Which tone pair was pronounced?',
        options: ['4th Tone + 4th Tone (falling + falling)', '1st Tone + 4th Tone', '3rd Tone + 4th Tone'],
        correctAnswer: '4th Tone + 4th Tone (falling + falling)',
        explanationEn: 'Both "zài" and "jiàn" drop sharply and decisively from pitch level 5 to 1.',
      },
    ],
  },
  {
    id: 'unit_6',
    unitNumber: 6,
    conceptId: 'hsk1_p06',
    slug: 'connected_speech_fluency',
    titleEn: 'Unit 6: Connected Speech & Real Everyday Phrases',
    objectiveEn: 'Pronounce foundational daily greetings and interactions with authentic Mandarin rhythm.',
    estimatedMinutes: 5,
    flashcards: [
      { id: 'fc_6_1', stage: 'phrase', stageLabel: 'Daily Greeting', targetPinyin: 'Nǐ hǎo!', targetHanzi: '你好！', meaningEn: 'Hello!', audioTarget: '你好' },
      { id: 'fc_6_2', stage: 'phrase', stageLabel: 'Polite Expression', targetPinyin: 'Xièxie!', targetHanzi: '谢谢！', meaningEn: 'Thank you!', audioTarget: '谢谢' },
      { id: 'fc_6_3', stage: 'phrase', stageLabel: 'Polite Reply', targetPinyin: 'Bú kèqi!', targetHanzi: '不客气！', meaningEn: "You're welcome!", audioTarget: '不客气' },
      { id: 'fc_6_4', stage: 'phrase', stageLabel: 'Apology', targetPinyin: 'Duìbuqǐ!', targetHanzi: '对不起！', meaningEn: "I'm sorry!", audioTarget: '对不起' },
      { id: 'fc_6_5', stage: 'phrase', stageLabel: 'Farewell', targetPinyin: 'Zàijiàn!', targetHanzi: '再见！', meaningEn: 'Goodbye!', audioTarget: '再见' },
    ],
    quizQuestions: [
      {
        id: 'q_6_1',
        type: 'spelling',
        audioTarget: '谢谢',
        questionText: 'Listen to the audio. What is the English meaning?',
        options: ['Thank you', 'Hello', 'Goodbye', "You're welcome"],
        correctAnswer: 'Thank you',
        explanationEn: '"Xièxie" (谢谢) is the universal Mandarin phrase for "Thank you".',
      },
      {
        id: 'q_6_2',
        type: 'spelling',
        audioTarget: '对不起',
        questionText: 'Listen to the audio. Which expression was pronounced?',
        options: ['Duìbuqǐ (Sorry)', 'Bú kèqi (You are welcome)', 'Zàijiàn (Goodbye)'],
        correctAnswer: 'Duìbuqǐ (Sorry)',
        explanationEn: '"Duìbuqǐ" (对不起) means "Sorry" or "Excuse me".',
      },
    ],
  },
];
