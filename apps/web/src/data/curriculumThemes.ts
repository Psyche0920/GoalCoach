import { CurriculumTheme, ConceptCategory } from '../types.ts';

export interface CategoryMeta {
  id: ConceptCategory;
  titleZh: string;
  titleEn: string;
  icon: string;
  badge: string;
  descriptionZh: string;
}

export const CATEGORY_REGISTRY: Record<ConceptCategory, CategoryMeta> = {
  pinyin: {
    id: 'pinyin',
    titleZh: '音标发音单元',
    titleEn: 'Pinyin & Pronunciation',
    icon: '🗣️',
    badge: '发音基础',
    descriptionZh: '声母、韵母、四声声调与拼读规则，初学中文的发音钥匙。',
  },
  grammar: {
    id: 'grammar',
    titleZh: '核心语法骨架',
    titleEn: 'Core Grammar Foundations',
    icon: '📐',
    badge: '语法必须项',
    descriptionZh: '语言底层逻辑、句式结构、疑问否定与体态助词，所有场景必修支撑。',
  },
  general_knowledge: {
    id: 'general_knowledge',
    titleZh: '生活实用常识',
    titleEn: 'General Knowledge & Tools',
    icon: '💡',
    badge: '必备常识',
    descriptionZh: '日期、日历星期、时钟时间、0-100计数数字、货币与日常高频度量单位。',
  },
  scenario: {
    id: 'scenario',
    titleZh: '主题交际场景',
    titleEn: 'Thematic Scenarios',
    icon: '🎯',
    badge: '情境优先',
    descriptionZh: '围绕旅游出行、职场工作、餐饮美食等真实目标展开的高频会话与词汇。',
  },
};

export interface ThemeMeta {
  id: CurriculumTheme;
  titleZh: string;
  titleEn: string;
  icon: string;
  color: string;
  category: ConceptCategory;
  description: string;
}

export const THEME_REGISTRY: Record<CurriculumTheme, ThemeMeta> = {
  pinyin_basics: {
    id: 'pinyin_basics',
    titleZh: '音标：声母、韵母与声调',
    titleEn: 'Pinyin: Initials, Finals & Tones',
    icon: '🗣️',
    color: 'sky',
    category: 'pinyin',
    description: 'Learn the Chinese phonetic system: tones, initials, finals, and pronunciation rules.',
  },
  core_grammar: {
    id: 'core_grammar',
    titleZh: '核心语法骨架',
    titleEn: 'Core Grammar Structures',
    icon: '📐',
    color: 'emerald',
    category: 'grammar',
    description: 'Essential sentence patterns, copulas, particles and negations required for all paths.',
  },
  numbers_time: {
    id: 'numbers_time',
    titleZh: '常识：数字与时钟日期',
    titleEn: 'General: Numbers, Time & Calendar',
    icon: '📅',
    color: 'amber',
    category: 'general_knowledge',
    description: 'Counting 0-100, clock hours, calendar days, and chronological ordering common sense.',
  },
  shopping_prices: {
    id: 'shopping_prices',
    titleZh: '常识与场景：金钱问价与度量',
    titleEn: 'General & Scenario: Prices & Quantities',
    icon: '🛍️',
    color: 'rose',
    category: 'general_knowledge',
    description: 'Asking prices (多少钱), monetary units (块), demonstratives (这个/那个) and classifiers (个/本/杯).',
  },
  travel_directions: {
    id: 'travel_directions',
    titleZh: '情境：出行、交通与旅游',
    titleEn: 'Scenario: Travel & Navigation',
    icon: '✈️',
    color: 'teal',
    category: 'scenario',
    description: 'Locations (在哪儿), transportation (出租车/飞机/火车站), and orientations.',
  },
  work_study: {
    id: 'work_study',
    titleZh: '情境：职场工作与学习',
    titleEn: 'Scenario: Work & Study',
    icon: '💼',
    color: 'purple',
    category: 'scenario',
    description: 'Office, company, learning Mandarin, reading/writing Chinese characters.',
  },
  dining_food: {
    id: 'dining_food',
    titleZh: '情境：美食与餐饮点餐',
    titleEn: 'Scenario: Dining & Food',
    icon: '🍜',
    color: 'orange',
    category: 'scenario',
    description: 'Ordering food, beverages, Chinese dishes, expressing hunger and taste.',
  },
  greetings_etiquette: {
    id: 'greetings_etiquette',
    titleZh: '情境：问候与礼貌交际',
    titleEn: 'Scenario: Greetings & Etiquette',
    icon: '👋',
    color: 'blue',
    category: 'scenario',
    description: 'Everyday greetings, polite responses, apologies and goodbyes.',
  },
  identity_family: {
    id: 'identity_family',
    titleZh: '情境：身份、称谓与家庭',
    titleEn: 'Scenario: Identity & Family',
    icon: '👨‍👩‍👧',
    color: 'indigo',
    category: 'scenario',
    description: 'Introductions, nationalities, professions, and family members.',
  },
  daily_life: {
    id: 'daily_life',
    titleZh: '情境：日常生活与起居',
    titleEn: 'Scenario: Daily Life & Routine',
    icon: '☕',
    color: 'cyan',
    category: 'scenario',
    description: 'Home routines, reading, watching TV, sleeping, and phone conversations.',
  },
  weather_feelings: {
    id: 'weather_feelings',
    titleZh: '情境：天气、身心与感受',
    titleEn: 'Scenario: Weather & Feelings',
    icon: '🌤️',
    color: 'sky',
    category: 'scenario',
    description: 'Weather (冷/热/下雨), health (身体), and emotional states (高兴/漂亮).',
  },
};

export interface GoalPreset {
  id: 'general' | 'travel' | 'dining' | 'work' | 'daily';
  titleZh: string;
  titleEn: string;
  icon: string;
  badge: string;
  descriptionZh: string;
  descriptionEn: string;
  priorityThemes: CurriculumTheme[];
  module2UnitOrder: CurriculumTheme[];
}

export const GOAL_PRESETS: GoalPreset[] = [
  {
    id: 'travel',
    titleZh: '中国旅游与自由行',
    titleEn: 'Travel & Tourism in China',
    icon: '✈️',
    badge: 'Travel Focus',
    descriptionZh: '语法必须全通！Module 2 优先突破出行交通、问路导游、买票问价及旅游急用表达。',
    descriptionEn: 'Grammar mandatory. Module 2 prioritizes transit, flight/train, wayfinding, and shopping.',
    priorityThemes: [
      'core_grammar',
      'travel_directions',
      'shopping_prices',
      'dining_food',
      'numbers_time',
      'greetings_etiquette',
    ],
    module2UnitOrder: [
      'travel_directions', // Unit 1: 旅游交通 (Priority 1)
      'shopping_prices',   // Unit 2: 购物问价金钱 (Priority 2)
      'dining_food',       // Unit 3: 餐饮美食
      'numbers_time',      // Unit 4: 常识：数字与时刻
      'greetings_etiquette',// Unit 5: 问候礼貌
      'identity_family',   // Unit 6: 身份朋友
      'work_study',        // Unit 7: 职场
      'daily_life',        // Unit 8: 起居
      'weather_feelings',  // Unit 9: 天气感受
    ],
  },
  {
    id: 'work',
    titleZh: '商务交流与职场工作',
    titleEn: 'Business & Workplace Chinese',
    icon: '💼',
    badge: 'Career Focus',
    descriptionZh: '语法必须全通！Module 2 优先突破公司开会、职位称谓、商务日程与日常办公用语。',
    descriptionEn: 'Grammar mandatory. Module 2 prioritizes office, meetings, schedules, and colleagues.',
    priorityThemes: [
      'core_grammar',
      'work_study',
      'identity_family',
      'numbers_time',
      'greetings_etiquette',
      'travel_directions',
    ],
    module2UnitOrder: [
      'work_study',        // Unit 1: 职场工作与学习 (Priority 1)
      'identity_family',   // Unit 2: 身份称谓与同事 (Priority 2)
      'numbers_time',      // Unit 3: 常识：日程时间与数字 (Priority 3)
      'greetings_etiquette',// Unit 4: 商务问候礼仪
      'travel_directions', // Unit 5: 出差通勤与交通
      'dining_food',       // Unit 6: 商务宴请点餐
      'shopping_prices',   // Unit 7: 购物开支
      'daily_life',        // Unit 8: 日常起居
      'weather_feelings',  // Unit 9: 天气身心
    ],
  },
  {
    id: 'dining',
    titleZh: '地道美食与餐馆点餐',
    titleEn: 'Dining & Culinary Explorer',
    icon: '🍜',
    badge: 'Foodie Focus',
    descriptionZh: '语法必须全通！Module 2 优先突破地道菜名、茶水点单、结账问价及美味评价。',
    descriptionEn: 'Grammar mandatory. Module 2 prioritizes dishes, drinks, asking checks, and compliments.',
    priorityThemes: [
      'core_grammar',
      'dining_food',
      'shopping_prices',
      'numbers_time',
      'greetings_etiquette',
    ],
    module2UnitOrder: [
      'dining_food',       // Unit 1: 餐饮美食点餐 (Priority 1)
      'shopping_prices',   // Unit 2: 结账金钱与问价 (Priority 2)
      'numbers_time',      // Unit 3: 常识：数字与时间
      'greetings_etiquette',// Unit 4: 问候礼节
      'daily_life',        // Unit 5: 日常起居
      'identity_family',   // Unit 6: 家庭朋友
      'travel_directions', // Unit 7: 出行路线
      'work_study',        // Unit 8: 职场
      'weather_feelings',  // Unit 9: 天气感受
    ],
  },
  {
    id: 'daily',
    titleZh: '日常生活与社交闲聊',
    titleEn: 'Daily Life & Social Chat',
    icon: '☕',
    badge: 'Social Life',
    descriptionZh: '语法必须全通！Module 2 优先聚焦起居作息、家庭亲友、日常闲聊与身心状态。',
    descriptionEn: 'Grammar mandatory. Module 2 prioritizes home routine, family, casual chat, and health.',
    priorityThemes: [
      'core_grammar',
      'daily_life',
      'identity_family',
      'greetings_etiquette',
      'weather_feelings',
      'numbers_time',
    ],
    module2UnitOrder: [
      'daily_life',        // Unit 1: 日常起居与闲聊 (Priority 1)
      'identity_family',   // Unit 2: 亲友称谓与家庭 (Priority 2)
      'greetings_etiquette',// Unit 3: 社交问候
      'weather_feelings',  // Unit 4: 天气与身心感受
      'numbers_time',      // Unit 5: 常识：时间日期
      'dining_food',       // Unit 6: 餐饮美食
      'shopping_prices',   // Unit 7: 购物花费
      'travel_directions', // Unit 8: 交通出行
      'work_study',        // Unit 9: 职场学习
    ],
  },
];
