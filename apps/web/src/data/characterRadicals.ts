export interface ComponentDecomposition {
  char: string;
  pinyin?: string;
  meaningEn: string;
  radicalOrigin?: string; // Etymological origin / mnemonic
  components?: ComponentDecomposition[];
}

export interface CharacterEntry {
  text: string;
  pinyin: string;
  partOfSpeech: 'noun' | 'verb' | 'adjective' | 'pronoun' | 'adverb' | 'preposition' | 'particle' | 'measure_word' | 'numeral' | 'greeting';
  meaningEn: string;
  audioText?: string;
  mnemonicStory?: string;
  breakdown: ComponentDecomposition[];
}

// Comprehensive HSK 1 Character Decomposition Database (matching HelloChinese style)
export const CHARACTER_RADICAL_REGISTRY: Record<string, CharacterEntry> = {
  '老师': {
    text: '老师',
    pinyin: 'lǎoshī',
    partOfSpeech: 'noun',
    meaningEn: 'teacher',
    mnemonicStory: 'An elder (老) with mastery knowledge (师) guiding young minds.',
    breakdown: [
      {
        char: '老',
        pinyin: 'lǎo',
        meaningEn: 'old; venerable',
        radicalOrigin: 'Depicts an elder with long hair leaning forward with walking cane (匕).',
      },
      {
        char: '师',
        pinyin: 'shī',
        meaningEn: 'master; teacher; division leader',
        radicalOrigin: 'Originally an army division flag and banner, evolving into a master of guidance.',
        components: [
          { char: '刂', meaningEn: 'knife / person standing upright' },
          { char: '一', meaningEn: 'stick / horizontal ground boundary' },
          { char: '巾', meaningEn: 'scarf; cloth banner hanging down' },
        ],
      },
    ],
  },
  '是': {
    text: '是',
    pinyin: 'shì',
    partOfSpeech: 'verb',
    meaningEn: 'to be; yes; correct',
    mnemonicStory: 'The sun (日) shines straight down (正/止), showing the true reality without shadow.',
    breakdown: [
      {
        char: '是',
        pinyin: 'shì',
        meaningEn: 'to be; correct; indeed',
        components: [
          { char: '日', meaningEn: 'sun; daylight (clarity and truth)' },
          { char: '疋 / 止', meaningEn: 'foot / straight path (standing firm in truth)' },
        ],
      },
    ],
  },
  '我': {
    text: '我',
    pinyin: 'wǒ',
    partOfSpeech: 'pronoun',
    meaningEn: 'I; me; myself',
    mnemonicStory: 'A hand (手) grasping a ceremonial spear (戈) defending oneself.',
    breakdown: [
      {
        char: '我',
        pinyin: 'wǒ',
        meaningEn: 'I; me',
        components: [
          { char: '扌/手', meaningEn: 'hand' },
          { char: '戈', meaningEn: 'dagger-axe; halberd weapon' },
        ],
      },
    ],
  },
  '你': {
    text: '你',
    pinyin: 'nǐ',
    partOfSpeech: 'pronoun',
    meaningEn: 'you (singular)',
    mnemonicStory: 'A person (亻) standing across facing you (尔).',
    breakdown: [
      {
        char: '你',
        pinyin: 'nǐ',
        meaningEn: 'you',
        components: [
          { char: '亻', meaningEn: 'person (standing person radical)' },
          { char: '尔', meaningEn: 'flowering branches reaching outward / you' },
        ],
      },
    ],
  },
  '他': {
    text: '他',
    pinyin: 'tā',
    partOfSpeech: 'pronoun',
    meaningEn: 'he; him',
    mnemonicStory: 'A person (亻) who is another (也).',
    breakdown: [
      {
        char: '他',
        pinyin: 'tā',
        meaningEn: 'he; him',
        components: [
          { char: '亻', meaningEn: 'person radical' },
          { char: '也', meaningEn: 'also; another snake/basin' },
        ],
      },
    ],
  },
  '她': {
    text: '她',
    pinyin: 'tā',
    partOfSpeech: 'pronoun',
    meaningEn: 'she; her',
    mnemonicStory: 'A woman (女) who is another (也).',
    breakdown: [
      {
        char: '她',
        pinyin: 'tā',
        meaningEn: 'she; her',
        components: [
          { char: '女', meaningEn: 'woman; female radical' },
          { char: '也', meaningEn: 'also; another' },
        ],
      },
    ],
  },
  '好': {
    text: '好',
    pinyin: 'hǎo',
    partOfSpeech: 'adjective',
    meaningEn: 'good; well; fine',
    mnemonicStory: 'A mother/woman (女) holding her beloved child (子) in harmony.',
    breakdown: [
      {
        char: '女',
        pinyin: 'nǚ',
        meaningEn: 'woman; daughter',
        radicalOrigin: 'A kneeling woman with hands crossed respectfully.',
      },
      {
        char: '子',
        pinyin: 'zǐ',
        meaningEn: 'child; son; newborn baby',
        radicalOrigin: 'A baby in swaddling clothes waving two little arms.',
      },
    ],
  },
  '美国': {
    text: '美国',
    pinyin: 'Měiguó',
    partOfSpeech: 'noun',
    meaningEn: 'United States; America',
    mnemonicStory: 'The Beautiful Country: beauty (美) + sovereign nation (国).',
    breakdown: [
      {
        char: '美',
        pinyin: 'měi',
        meaningEn: 'beautiful; pleasing',
        components: [
          { char: '羊', meaningEn: 'sheep / ram with grand horns' },
          { char: '大', meaningEn: 'big person (grand, plump sheep is beautiful)' },
        ],
      },
      {
        char: '国',
        pinyin: 'guó',
        meaningEn: 'country; sovereign nation',
        components: [
          { char: '囗', meaningEn: 'surrounding territorial boundary / enclosure' },
          { char: '玉', meaningEn: 'imperial jade seal / treasure guarded within' },
        ],
      },
    ],
  },
  '中国': {
    text: '中国',
    pinyin: 'Zhōngguó',
    partOfSpeech: 'noun',
    meaningEn: 'China; Middle Kingdom',
    mnemonicStory: 'The nation located at the central sovereign crossroads (中 + 国).',
    breakdown: [
      {
        char: '中',
        pinyin: 'zhōng',
        meaningEn: 'middle; center; target center',
        radicalOrigin: 'A vertical arrow piercing straight through a circular drum center.',
      },
      {
        char: '国',
        pinyin: 'guó',
        meaningEn: 'country; state',
        components: [
          { char: '囗', meaningEn: 'enclosing defensive walls' },
          { char: '玉', meaningEn: 'jade royal heirloom inside' },
        ],
      },
    ],
  },
  '人': {
    text: '人',
    pinyin: 'rén',
    partOfSpeech: 'noun',
    meaningEn: 'person; people; human',
    mnemonicStory: 'Two supportive legs standing firmly upright upon the earth.',
    breakdown: [
      {
        char: '人',
        pinyin: 'rén',
        meaningEn: 'human / upright bipedal being',
        radicalOrigin: 'Pictograph of a side profile of a walking person.',
      },
    ],
  },
  '学生': {
    text: '学生',
    pinyin: 'xuéshēng',
    partOfSpeech: 'noun',
    meaningEn: 'student; pupil',
    mnemonicStory: 'A young child (子) under a schoolhouse roof (冖) nurturing new life (生).',
    breakdown: [
      {
        char: '学',
        pinyin: 'xué',
        meaningEn: 'to learn; study',
        components: [
          { char: '𦥑', meaningEn: 'two hands guiding' },
          { char: '冖', meaningEn: 'roof of academy' },
          { char: '子', meaningEn: 'child learning' },
        ],
      },
      {
        char: '生',
        pinyin: 'shēng',
        meaningEn: 'to be born; life; growth',
        radicalOrigin: 'A fresh young plant bud emerging from the dark soil.',
      },
    ],
  },
  '朋友': {
    text: '朋友',
    pinyin: 'péngyou',
    partOfSpeech: 'noun',
    meaningEn: 'friend; companion',
    mnemonicStory: 'Two strings of precious cowrie shells (朋) and two joined hands (友).',
    breakdown: [
      {
        char: '朋',
        pinyin: 'péng',
        meaningEn: 'peer; companion',
        components: [
          { char: '月/肉', meaningEn: 'two twin strings of currency shells' },
        ],
      },
      {
        char: '友',
        pinyin: 'yǒu',
        meaningEn: 'friend; friendship',
        components: [
          { char: '又', meaningEn: 'right hand reaching out' },
          { char: '𠂇', meaningEn: 'left hand grasping in warmth' },
        ],
      },
    ],
  },
  '吃': {
    text: '吃',
    pinyin: 'chī',
    partOfSpeech: 'verb',
    meaningEn: 'to eat; consume food',
    mnemonicStory: 'Using the mouth (口) to take in sustenance that satisfies a craving (乞).',
    breakdown: [
      {
        char: '吃',
        pinyin: 'chī',
        meaningEn: 'to eat',
        components: [
          { char: '口', meaningEn: 'mouth radical' },
          { char: '乞', meaningEn: 'to beg / desire / swallow steam' },
        ],
      },
    ],
  },
  '喝': {
    text: '喝',
    pinyin: 'hē',
    partOfSpeech: 'verb',
    meaningEn: 'to drink; sip',
    mnemonicStory: 'Opening the mouth (口) when the throat feels parched under the blazing sun (曷).',
    breakdown: [
      {
        char: '喝',
        pinyin: 'hē',
        meaningEn: 'to drink',
        components: [
          { char: '口', meaningEn: 'mouth radical' },
          { char: '日', meaningEn: 'sun' },
          { char: '勹/人', meaningEn: 'bent person' },
          { char: '匃', meaningEn: 'thirsty begging for water' },
        ],
      },
    ],
  },
  '茶': {
    text: '茶',
    pinyin: 'chá',
    partOfSpeech: 'noun',
    meaningEn: 'tea; tea leaves',
    mnemonicStory: 'Herbs and green leaves (艹) harvested by people (人) from wooden trees (木).',
    breakdown: [
      {
        char: '艹',
        pinyin: 'cǎo',
        meaningEn: 'grass; plant; herbal radical',
      },
      {
        char: '人',
        pinyin: 'rén',
        meaningEn: 'human harvester in between',
      },
      {
        char: '木',
        pinyin: 'mù',
        meaningEn: 'wood; tea bush trunk',
      },
    ],
  },
  '水': {
    text: '水',
    pinyin: 'shuǐ',
    partOfSpeech: 'noun',
    meaningEn: 'water; liquid',
    mnemonicStory: 'Wavy central river flow flanked by splashes and drops of water.',
    breakdown: [
      {
        char: '水',
        pinyin: 'shuǐ',
        meaningEn: 'flowing river / water droplets',
      },
    ],
  },
  '想': {
    text: '想',
    pinyin: 'xiǎng',
    partOfSpeech: 'verb',
    meaningEn: 'would like to; to miss; to think',
    mnemonicStory: 'Inspecting with tree (木) and eye (目) while holding feelings deep in the heart (心).',
    breakdown: [
      {
        char: '相',
        pinyin: 'xiāng',
        meaningEn: 'mutual; observing carefully',
        components: [
          { char: '木', meaningEn: 'tree; wood' },
          { char: '目', meaningEn: 'eye observing' },
        ],
      },
      {
        char: '心',
        pinyin: 'xīn',
        meaningEn: 'heart; innermost thought and emotion',
      },
    ],
  },
  '去': {
    text: '去',
    pinyin: 'qù',
    partOfSpeech: 'verb',
    meaningEn: 'to go; depart to',
    mnemonicStory: 'Feet taking steps away from the homeland soil (土 + 厶).',
    breakdown: [
      {
        char: '去',
        pinyin: 'qù',
        meaningEn: 'to go; leave',
        components: [
          { char: '土', meaningEn: 'earth; ground location' },
          { char: '厶', meaningEn: 'departure motion / stepping aside' },
        ],
      },
    ],
  },
  '在': {
    text: '在',
    pinyin: 'zài',
    partOfSpeech: 'preposition',
    meaningEn: 'at; in; on; located at',
    mnemonicStory: 'A young sprout (才) anchored firmly into the soil (土).',
    breakdown: [
      {
        char: '在',
        pinyin: 'zài',
        meaningEn: 'to be located at',
        components: [
          { char: '才', meaningEn: 'sprout / emerging presence' },
          { char: '土', meaningEn: 'soil; earth; ground' },
        ],
      },
    ],
  },
  '有': {
    text: '有',
    pinyin: 'yǒu',
    partOfSpeech: 'verb',
    meaningEn: 'to have; there is/are',
    mnemonicStory: 'A hand (𠂇) holding a piece of dried meat (月/肉) — possession and abundance.',
    breakdown: [
      {
        char: '有',
        pinyin: 'yǒu',
        meaningEn: 'to possess; have',
        components: [
          { char: '𠂇', meaningEn: 'hand grasping' },
          { char: '月', meaningEn: 'meat (肉 radical variant) — prize in hand' },
        ],
      },
    ],
  },
  '没有': {
    text: '没有',
    pinyin: 'méiyǒu',
    partOfSpeech: 'verb',
    meaningEn: 'do not have; there is no',
    mnemonicStory: 'Water (氵) swirling into oblivion (殳) + having (有) = nonexistent.',
    breakdown: [
      {
        char: '没',
        pinyin: 'méi',
        meaningEn: 'not; sink into nothingness',
        components: [
          { char: '氵', meaningEn: 'water droplets' },
          { char: '殳', meaningEn: 'hand striking away' },
        ],
      },
      {
        char: '有',
        pinyin: 'yǒu',
        meaningEn: 'to have',
        components: [
          { char: '𠂇', meaningEn: 'hand' },
          { char: '月', meaningEn: 'meat' },
        ],
      },
    ],
  },
  '谢谢': {
    text: '谢谢',
    pinyin: 'xièxie',
    partOfSpeech: 'greeting',
    meaningEn: 'thank you; thanks',
    mnemonicStory: 'Spoken words (讠) shooting forth like arrows of gratitude (射).',
    breakdown: [
      {
        char: '讠',
        meaningEn: 'speech / spoken words radical',
      },
      {
        char: '身',
        meaningEn: 'body bowing with gratitude',
      },
      {
        char: '寸',
        meaningEn: 'inch / hand gesture of measure',
      },
    ],
  },
  '客气': {
    text: '客气',
    pinyin: 'kèqi',
    partOfSpeech: 'adjective',
    meaningEn: 'polite; courteous; guest-like',
    mnemonicStory: 'A guest arriving under roof (宀) with refined air and attitude (气).',
    breakdown: [
      {
        char: '客',
        pinyin: 'kè',
        meaningEn: 'guest; customer',
        components: [
          { char: '宀', meaningEn: 'roof / guest house' },
          { char: '各', meaningEn: 'each person arriving on foot (夂 + 口)' },
        ],
      },
      {
        char: '气',
        pinyin: 'qì',
        meaningEn: 'energy; demeanor; vapor',
        radicalOrigin: 'Vaporous clouds of warm breath rising peacefully.',
      },
    ],
  },
  '火车站': {
    text: '火车站',
    pinyin: 'huǒchēzhàn',
    partOfSpeech: 'noun',
    meaningEn: 'railway station',
    mnemonicStory: 'Fire (火) + steam engine carriage (车) + stopping depot (站).',
    breakdown: [
      {
        char: '火',
        pinyin: 'huǒ',
        meaningEn: 'fire; flame',
        radicalOrigin: 'Flickering flames leaping upward.',
      },
      {
        char: '车',
        pinyin: 'chē',
        meaningEn: 'cart; vehicle; train',
        radicalOrigin: 'Top view of a horse chariot with two wheels and axle.',
      },
      {
        char: '站',
        pinyin: 'zhàn',
        meaningEn: 'station; stop',
        components: [
          { char: '立', meaningEn: 'person standing upright' },
          { char: '占', meaningEn: 'marker flag / occupying a point' },
        ],
      },
    ],
  },
  '多少钱': {
    text: '多少钱',
    pinyin: 'duōshǎo qián',
    partOfSpeech: 'noun',
    meaningEn: 'how much money? / price',
    mnemonicStory: 'Many (多) + few (少) + bronze coins made of metal (钅).',
    breakdown: [
      {
        char: '多',
        pinyin: 'duō',
        meaningEn: 'many; much',
        components: [
          { char: '夕', meaningEn: 'crescent moon stacked upon moon (many nights)' },
        ],
      },
      {
        char: '少',
        pinyin: 'shǎo',
        meaningEn: 'few; little',
        radicalOrigin: 'Small grains (小) slashed away into tiny bits.',
      },
      {
        char: '钱',
        pinyin: 'qián',
        meaningEn: 'money; coin; currency',
        components: [
          { char: '钅', meaningEn: 'metal; bronze currency radical' },
          { char: '戋', meaningEn: 'two small spears counting weights' },
        ],
      },
    ],
  },
  '块': {
    text: '块',
    pinyin: 'kuài',
    partOfSpeech: 'measure_word',
    meaningEn: 'yuan (colloquial money unit); piece; lump',
    mnemonicStory: 'Earth and silver clods (土) gathered together for transaction (夬).',
    breakdown: [
      {
        char: '土',
        meaningEn: 'earth; soil; solid matter',
      },
      {
        char: '夬',
        meaningEn: 'divided portion / decisive hand',
      },
    ],
  },
};

// Common Radical Dictionary for fallback single-character breakdowns
export const COMMON_RADICALS: Record<string, { name: string; meaningEn: string; explanation: string }> = {
  '亻': { name: '单人旁', meaningEn: 'person', explanation: 'Relates to human beings, behaviors, or personal pronouns.' },
  '女': { name: '女字旁', meaningEn: 'female / woman', explanation: 'Relates to women, family members, or beauty.' },
  '口': { name: '口字旁', meaningEn: 'mouth', explanation: 'Relates to eating, drinking, speaking, shouting, or tasting.' },
  '氵': { name: '三点水', meaningEn: 'water', explanation: 'Relates to liquids, rivers, washing, or oceans.' },
  '艹': { name: '草字头', meaningEn: 'plants / herbs', explanation: 'Relates to vegetables, flowers, tea, and botanical remedies.' },
  '宀': { name: '宝盖头', meaningEn: 'roof / house', explanation: 'Relates to homes, rooms, families, shelter, or settling.' },
  '扌': { name: '提手旁', meaningEn: 'hand', explanation: 'Relates to manual actions: grasping, throwing, pushing, striking.' },
  '木': { name: '木字旁', meaningEn: 'tree / wood', explanation: 'Relates to trees, timber, forestry, wooden furniture, or nature.' },
  '钅': { name: '金字旁', meaningEn: 'metal / gold', explanation: 'Relates to metals, bronze bells, coins, knives, and sharp tools.' },
  '讠': { name: '言字旁', meaningEn: 'speech / words', explanation: 'Relates to language, talking, reading, thanking, or reciting.' },
  '日': { name: '日字旁', meaningEn: 'sun / time', explanation: 'Relates to sunlight, daytime, brightness, hours, or calendar days.' },
  '月': { name: '月字旁 / 肉月旁', meaningEn: 'moon / body flesh', explanation: 'Relates to time cycles or anatomical body organs and meat.' },
  '火': { name: '火字旁', meaningEn: 'fire', explanation: 'Relates to heat, flames, cooking, burning, and light.' },
  '土': { name: '土字底 / 旁', meaningEn: 'earth / soil', explanation: 'Relates to ground, land, building bricks, and dust.' },
  '心': { name: '心字底 / 竖心旁(忄)', meaningEn: 'heart / mind', explanation: 'Relates to feelings, thoughts, intentions, emotions, and memory.' },
  '走': { name: '走字底', meaningEn: 'walking / running', explanation: 'Relates to traveling on foot, starting off, and movement.' },
  '纟': { name: '绞丝旁', meaningEn: 'silk / thread', explanation: 'Relates to cords, weaving, connections, ropes, and lines.' },
  '目': { name: '目字旁', meaningEn: 'eye', explanation: 'Relates to vision, sight, eyes, looking, and gazing.' },
};

// Helper to look up decomposition for a word or character
export function findCharacterBreakdown(chineseText: string): CharacterEntry | null {
  const clean = chineseText.replace(/[^\u4e00-\u9fa5]/g, '');
  if (!clean) return null;

  // 1. Direct multi-character match
  if (CHARACTER_RADICAL_REGISTRY[clean]) {
    return CHARACTER_RADICAL_REGISTRY[clean];
  }

  // 2. Look for substring match in keys
  for (const [key, val] of Object.entries(CHARACTER_RADICAL_REGISTRY)) {
    if (clean.includes(key) || key.includes(clean)) {
      return val;
    }
  }

  // 3. Fallback: Take first character and build single-character breakdown
  const firstChar = clean[0];
  for (const [key, val] of Object.entries(CHARACTER_RADICAL_REGISTRY)) {
    if (key.includes(firstChar)) {
      const charPart = val.breakdown.find((b) => b.char === firstChar);
      if (charPart) {
        return {
          text: firstChar,
          pinyin: charPart.pinyin || val.pinyin,
          partOfSpeech: val.partOfSpeech,
          meaningEn: charPart.meaningEn || val.meaningEn,
          breakdown: [charPart],
        };
      }
    }
  }

  // 4. Heuristic radical detection
  for (const [rad, radMeta] of Object.entries(COMMON_RADICALS)) {
    if (firstChar.includes(rad) || clean.includes(rad)) {
      return {
        text: clean,
        pinyin: '',
        partOfSpeech: 'noun',
        meaningEn: clean,
        breakdown: [
          {
            char: firstChar,
            meaningEn: 'Chinese character',
            components: [
              {
                char: rad,
                meaningEn: radMeta.meaningEn,
                radicalOrigin: radMeta.explanation,
              },
            ],
          },
        ],
      };
    }
  }

  return null;
}
