// Full AllSet Learning Inspired Pinyin Chart Matrix
// Features full row/column crosshair grid, tone selectors 1, 2, 3, 4, 1234,
// and audio anchor Hanzi characters for every tone variant.

export interface PinyinChartCellData {
  syllable: string; // Base without tone marks, e.g. "ba", "ma"
  initial: string; // "b", "m", or "Ø"
  final: string; // "a", "ai", etc.
  validTones: number[]; // e.g. [1, 2, 3, 4]
  pinyinWithTones: { [tone: number]: string };
  audioChars: { [tone: number]: string };
  anchorWord?: {
    hanzi: string;
    pinyin: string;
    meaningEn: string;
  };
}

export const CHART_INITIALS = [
  'Ø', 'b', 'p', 'm', 'f', 
  'd', 't', 'n', 'l', 
  'g', 'k', 'h', 
  'j', 'q', 'x', 
  'zh', 'ch', 'sh', 'r', 
  'z', 'c', 's', 
  'w', 'y'
] as const;

export const CHART_FINALS = [
  'a', 'ai', 'ao', 'an', 'ang',
  'e', 'ei', 'en', 'eng', 'er',
  'o', 'ou', 'ong',
  'i', 'ia', 'iao', 'ie', 'iu', 'ian', 'in', 'iang', 'ing', 'iong',
  'u', 'ua', 'uo', 'uai', 'ui', 'uan', 'un', 'uang',
  'ü', 'üe', 'üan', 'ün'
] as const;

// Curated comprehensive syllable lookup map (key: `${initial}_${final}`)
export const PINYIN_GRID_CELLS: Record<string, PinyinChartCellData> = {
  // Ø (Zero-initial)
  'Ø_a': { syllable: 'a', initial: 'Ø', final: 'a', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'ā', 2: 'á', 3: 'ǎ', 4: 'à' }, audioChars: { 1: '啊', 2: '啊', 3: '啊', 4: '啊' }, anchorWord: { hanzi: '啊', pinyin: 'ā', meaningEn: 'Ah / expression' } },
  'Ø_ai': { syllable: 'ai', initial: 'Ø', final: 'ai', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'āi', 2: 'ái', 3: 'ǎi', 4: 'ài' }, audioChars: { 1: '哎', 2: '挨', 3: '矮', 4: '爱' }, anchorWord: { hanzi: '爱', pinyin: 'ài', meaningEn: 'Love' } },
  'Ø_ao': { syllable: 'ao', initial: 'Ø', final: 'ao', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'āo', 2: 'áo', 3: 'ǎo', 4: 'ào' }, audioChars: { 1: '凹', 2: '熬', 3: '袄', 4: '傲' }, anchorWord: { hanzi: '熬夜', pinyin: 'áoyè', meaningEn: 'Stay up late' } },
  'Ø_an': { syllable: 'an', initial: 'Ø', final: 'an', validTones: [1, 3, 4], pinyinWithTones: { 1: 'ān', 3: 'ǎn', 4: 'àn' }, audioChars: { 1: '安', 3: '俺', 4: '按' }, anchorWord: { hanzi: '安全', pinyin: 'ānquán', meaningEn: 'Safe' } },
  'Ø_ang': { syllable: 'ang', initial: 'Ø', final: 'ang', validTones: [1, 2, 4], pinyinWithTones: { 1: 'āng', 2: 'áng', 4: 'àng' }, audioChars: { 1: '腌', 2: '昂', 4: '盎' }, anchorWord: { hanzi: '昂贵', pinyin: 'ángguì', meaningEn: 'Expensive' } },
  'Ø_e': { syllable: 'e', initial: 'Ø', final: 'e', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'ē', 2: 'é', 3: 'ě', 4: 'è' }, audioChars: { 1: '阿', 2: '鹅', 3: '恶', 4: '饿' }, anchorWord: { hanzi: '肚子饿', pinyin: 'dùzi è', meaningEn: 'Hungry' } },
  'Ø_er': { syllable: 'er', initial: 'Ø', final: 'er', validTones: [2, 3, 4], pinyinWithTones: { 2: 'ér', 3: 'ěr', 4: 'èr' }, audioChars: { 2: '儿', 3: '耳', 4: '二' }, anchorWord: { hanzi: '二', pinyin: 'èr', meaningEn: 'Two (2)' } },
  'Ø_ou': { syllable: 'ou', initial: 'Ø', final: 'ou', validTones: [1, 3, 4], pinyinWithTones: { 1: 'ōu', 3: 'ǒu', 4: 'òu' }, audioChars: { 1: '欧', 3: '偶', 4: '呕' }, anchorWord: { hanzi: '欧洲', pinyin: 'Ōuzhōu', meaningEn: 'Europe' } },

  // b-
  'b_a': { syllable: 'ba', initial: 'b', final: 'a', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'bā', 2: 'bá', 3: 'bǎ', 4: 'bà' }, audioChars: { 1: '八', 2: '拔', 3: '把', 4: '爸' }, anchorWord: { hanzi: '爸爸', pinyin: 'bàba', meaningEn: 'Dad' } },
  'b_ai': { syllable: 'bai', initial: 'b', final: 'ai', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'bāi', 2: 'bái', 3: 'bǎi', 4: 'bài' }, audioChars: { 1: '掰', 2: '白', 3: '百', 4: '败' }, anchorWord: { hanzi: '白色', pinyin: 'báisè', meaningEn: 'White' } },
  'b_ao': { syllable: 'bao', initial: 'b', final: 'ao', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'bāo', 2: 'báo', 3: 'bǎo', 4: 'bào' }, audioChars: { 1: '包', 2: '雹', 3: '饱', 4: '报' }, anchorWord: { hanzi: '面包', pinyin: 'miànbāo', meaningEn: 'Bread' } },
  'b_an': { syllable: 'ban', initial: 'b', final: 'an', validTones: [1, 3, 4], pinyinWithTones: { 1: 'bān', 3: 'bǎn', 4: 'bàn' }, audioChars: { 1: '班', 3: '板', 4: '半' }, anchorWord: { hanzi: '上班', pinyin: 'shàngbān', meaningEn: 'Work' } },
  'b_ang': { syllable: 'bang', initial: 'b', final: 'ang', validTones: [1, 3, 4], pinyinWithTones: { 1: 'bāng', 3: 'bǎng', 4: 'bàng' }, audioChars: { 1: '帮', 3: '榜', 4: '棒' }, anchorWord: { hanzi: '帮忙', pinyin: 'bāngmáng', meaningEn: 'Help' } },
  'b_ei': { syllable: 'bei', initial: 'b', final: 'ei', validTones: [1, 3, 4], pinyinWithTones: { 1: 'bēi', 3: 'běi', 4: 'bèi' }, audioChars: { 1: '杯', 3: '北', 4: '被' }, anchorWord: { hanzi: '北京', pinyin: 'Běijīng', meaningEn: 'Beijing' } },
  'b_en': { syllable: 'ben', initial: 'b', final: 'en', validTones: [1, 3, 4], pinyinWithTones: { 1: 'bēn', 3: 'běn', 4: 'bèn' }, audioChars: { 1: '奔', 3: '本', 4: '笨' }, anchorWord: { hanzi: '一本书', pinyin: 'yī běn shū', meaningEn: 'A book' } },
  'b_eng': { syllable: 'beng', initial: 'b', final: 'eng', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'bēng', 2: 'béng', 3: 'běng', 4: 'bèng' }, audioChars: { 1: '崩', 2: '甭', 3: '绷', 4: '蹦' }, anchorWord: { hanzi: '蹦跳', pinyin: 'bèngtiào', meaningEn: 'Hop' } },
  'b_o': { syllable: 'bo', initial: 'b', final: 'o', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'bō', 2: 'bó', 3: 'bǒ', 4: 'bò' }, audioChars: { 1: '波', 2: '伯', 3: '跛', 4: '薄' }, anchorWord: { hanzi: '波浪', pinyin: 'bōlàng', meaningEn: 'Wave' } },
  'b_i': { syllable: 'bi', initial: 'b', final: 'i', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'bī', 2: 'bí', 3: 'bǐ', 4: 'bì' }, audioChars: { 1: '逼', 2: '鼻', 3: '比', 4: '必' }, anchorWord: { hanzi: '比较', pinyin: 'bǐjiào', meaningEn: 'Compare' } },
  'b_ian': { syllable: 'bian', initial: 'b', final: 'ian', validTones: [1, 3, 4], pinyinWithTones: { 1: 'biān', 3: 'biǎn', 4: 'biàn' }, audioChars: { 1: '边', 3: '扁', 4: '便' }, anchorWord: { hanzi: '左边', pinyin: 'zuǒbian', meaningEn: 'Left side' } },
  'b_iao': { syllable: 'biao', initial: 'b', final: 'iao', validTones: [1, 3, 4], pinyinWithTones: { 1: 'biāo', 3: 'biǎo', 4: 'biào' }, audioChars: { 1: '标', 3: '表', 4: '鳔' }, anchorWord: { hanzi: '手表', pinyin: 'shǒubiǎo', meaningEn: 'Watch' } },
  'b_ie': { syllable: 'bie', initial: 'b', final: 'ie', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'biē', 2: 'bié', 3: 'biě', 4: 'biè' }, audioChars: { 1: '憋', 2: '别', 3: '瘪', 4: '别' }, anchorWord: { hanzi: '别人', pinyin: 'biérén', meaningEn: 'Other person' } },
  'b_in': { syllable: 'bin', initial: 'b', final: 'in', validTones: [1, 4], pinyinWithTones: { 1: 'bīn', 4: 'bìn' }, audioChars: { 1: '宾', 4: '鬓' }, anchorWord: { hanzi: '宾馆', pinyin: 'bīnguǎn', meaningEn: 'Hotel' } },
  'b_ing': { syllable: 'bing', initial: 'b', final: 'ing', validTones: [1, 3, 4], pinyinWithTones: { 1: 'bīng', 3: 'bǐng', 4: 'bìng' }, audioChars: { 1: '冰', 3: '饼', 4: '病' }, anchorWord: { hanzi: '冰水', pinyin: 'bīngshuǐ', meaningEn: 'Ice water' } },
  'b_u': { syllable: 'bu', initial: 'b', final: 'u', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'bū', 2: 'bú', 3: 'bǔ', 4: 'bù' }, audioChars: { 1: '逋', 2: '不', 3: '补', 4: '不' }, anchorWord: { hanzi: '不是', pinyin: 'bú shì', meaningEn: 'Is not' } },

  // p-
  'p_a': { syllable: 'pa', initial: 'p', final: 'a', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'pā', 2: 'pá', 3: 'pǎ', 4: 'pà' }, audioChars: { 1: '趴', 2: '爬', 3: '跑', 4: '怕' }, anchorWord: { hanzi: '害怕', pinyin: 'hàipà', meaningEn: 'Scared' } },
  'p_ai': { syllable: 'pai', initial: 'p', final: 'ai', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'pāi', 2: 'pái', 3: 'pǎi', 4: 'pài' }, audioChars: { 1: '拍', 2: '排', 3: '迫', 4: '派' }, anchorWord: { hanzi: '拍照', pinyin: 'pāizhào', meaningEn: 'Take photos' } },
  'p_ao': { syllable: 'pao', initial: 'p', final: 'ao', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'pāo', 2: 'páo', 3: 'pǎo', 4: 'pào' }, audioChars: { 1: '抛', 2: '袍', 3: '跑', 4: '泡' }, anchorWord: { hanzi: '跑步', pinyin: 'pǎobù', meaningEn: 'Running' } },
  'p_an': { syllable: 'pan', initial: 'p', final: 'an', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'pān', 2: 'pán', 3: 'pǎn', 4: 'pàn' }, audioChars: { 1: '攀', 2: '盘', 3: '蹒', 4: '盼' }, anchorWord: { hanzi: '盘子', pinyin: 'pánzi', meaningEn: 'Plate' } },
  'p_ang': { syllable: 'pang', initial: 'p', final: 'ang', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'pāng', 2: 'páng', 3: 'pǎng', 4: 'pàng' }, audioChars: { 1: '滂', 2: '旁', 3: '彷', 4: '胖' }, anchorWord: { hanzi: '旁边', pinyin: 'pángbiān', meaningEn: 'Beside' } },
  'p_ei': { syllable: 'pei', initial: 'p', final: 'ei', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'pēi', 2: 'péi', 3: 'pěi', 4: 'pèi' }, audioChars: { 1: '胚', 2: '陪', 3: '培', 4: '配' }, anchorWord: { hanzi: '陪伴', pinyin: 'péibàn', meaningEn: 'Accompany' } },
  'p_en': { syllable: 'pen', initial: 'p', final: 'en', validTones: [1, 2, 4], pinyinWithTones: { 1: 'pēn', 2: 'pén', 4: 'pèn' }, audioChars: { 1: '喷', 2: '盆', 4: '喷' }, anchorWord: { hanzi: '花盆', pinyin: 'huāpén', meaningEn: 'Flowerpot' } },
  'p_eng': { syllable: 'peng', initial: 'p', final: 'eng', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'pēng', 2: 'péng', 3: 'pěng', 4: 'pèng' }, audioChars: { 1: '烹', 2: '朋', 3: '捧', 4: '碰' }, anchorWord: { hanzi: '朋友', pinyin: 'péngyou', meaningEn: 'Friend' } },
  'p_o': { syllable: 'po', initial: 'p', final: 'o', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'pō', 2: 'pó', 3: 'pǒ', 4: 'pò' }, audioChars: { 1: '坡', 2: '婆', 3: '叵', 4: '破' }, anchorWord: { hanzi: '山坡', pinyin: 'shānpō', meaningEn: 'Hillside' } },
  'p_ou': { syllable: 'pou', initial: 'p', final: 'ou', validTones: [1, 2, 3], pinyinWithTones: { 1: 'pōu', 2: 'póu', 3: 'pǒu' }, audioChars: { 1: '剖', 2: '抔', 3: '掊' }, anchorWord: { hanzi: '解剖', pinyin: 'jiěpōu', meaningEn: 'Dissect' } },
  'p_i': { syllable: 'pi', initial: 'p', final: 'i', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'pī', 2: 'pí', 3: 'pǐ', 4: 'pì' }, audioChars: { 1: '批', 2: '皮', 3: '匹', 4: '屁' }, anchorWord: { hanzi: '皮肤', pinyin: 'pífū', meaningEn: 'Skin' } },
  'p_ian': { syllable: 'pian', initial: 'p', final: 'ian', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'piān', 2: 'pián', 3: 'piǎn', 4: 'piàn' }, audioChars: { 1: '篇', 2: '便', 3: '蹁', 4: '片' }, anchorWord: { hanzi: '照片', pinyin: 'zhàopiàn', meaningEn: 'Photo' } },
  'p_iao': { syllable: 'piao', initial: 'p', final: 'iao', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'piāo', 2: 'piáo', 3: 'piǎo', 4: 'piào' }, audioChars: { 1: '飘', 2: '瓢', 3: '漂', 4: '票' }, anchorWord: { hanzi: '门票', pinyin: 'ménpiào', meaningEn: 'Ticket' } },
  'p_ie': { syllable: 'pie', initial: 'p', final: 'ie', validTones: [1, 3, 4], pinyinWithTones: { 1: 'piē', 3: 'piě', 4: 'piè' }, audioChars: { 1: '瞥', 3: '撇', 4: '氕' }, anchorWord: { hanzi: '撇嘴', pinyin: 'piězuǐ', meaningEn: 'Pout' } },
  'p_in': { syllable: 'pin', initial: 'p', final: 'in', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'pīn', 2: 'pín', 3: 'pǐn', 4: 'pìn' }, audioChars: { 1: '拼', 2: '贫', 3: '品', 4: '聘' }, anchorWord: { hanzi: '拼音', pinyin: 'pīnyīn', meaningEn: 'Pinyin' } },
  'p_ing': { syllable: 'ping', initial: 'p', final: 'ing', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'pīng', 2: 'píng', 3: 'pǐng', 4: 'pìng' }, audioChars: { 1: '乒', 2: '平', 3: '品', 4: '聘' }, anchorWord: { hanzi: '苹果', pinyin: 'píngguǒ', meaningEn: 'Apple' } },
  'p_u': { syllable: 'pu', initial: 'p', final: 'u', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'pū', 2: 'pú', 3: 'pǔ', 4: 'pù' }, audioChars: { 1: '铺', 2: '葡', 3: '普', 4: '瀑' }, anchorWord: { hanzi: '普通话', pinyin: 'pǔtōnghuà', meaningEn: 'Mandarin' } },

  // m-
  'm_a': { syllable: 'ma', initial: 'm', final: 'a', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'mā', 2: 'má', 3: 'mǎ', 4: 'mà' }, audioChars: { 1: '妈', 2: '麻', 3: '马', 4: '骂' }, anchorWord: { hanzi: '妈妈', pinyin: 'māma', meaningEn: 'Mother' } },
  'm_ai': { syllable: 'mai', initial: 'm', final: 'ai', validTones: [2, 3, 4], pinyinWithTones: { 2: 'mái', 3: 'mǎi', 4: 'mài' }, audioChars: { 2: '埋', 3: '买', 4: '卖' }, anchorWord: { hanzi: '买单', pinyin: 'mǎidān', meaningEn: 'Pay bill' } },
  'm_ao': { syllable: 'mao', initial: 'm', final: 'ao', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'māo', 2: 'máo', 3: 'mǎo', 4: 'mào' }, audioChars: { 1: '猫', 2: '毛', 3: '卯', 4: '帽' }, anchorWord: { hanzi: '小猫', pinyin: 'xiǎomāo', meaningEn: 'Cat' } },
  'm_an': { syllable: 'man', initial: 'm', final: 'an', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'mān', 2: 'mán', 3: 'mǎn', 4: 'màn' }, audioChars: { 1: '蛮', 2: '瞒', 3: '满', 4: '慢' }, anchorWord: { hanzi: '慢慢', pinyin: 'mànmàn', meaningEn: 'Slowly' } },
  'm_ang': { syllable: 'mang', initial: 'm', final: 'ang', validTones: [2, 3, 4], pinyinWithTones: { 2: 'máng', 3: 'mǎng', 4: 'màng' }, audioChars: { 2: '忙', 3: '莽', 4: '漭' }, anchorWord: { hanzi: '很忙', pinyin: 'hěn máng', meaningEn: 'Very busy' } },
  'm_e': { syllable: 'me', initial: 'm', final: 'e', validTones: [1], pinyinWithTones: { 1: 'me' }, audioChars: { 1: '么' }, anchorWord: { hanzi: '什么', pinyin: 'shénme', meaningEn: 'What' } },
  'm_ei': { syllable: 'mei', initial: 'm', final: 'ei', validTones: [2, 3, 4], pinyinWithTones: { 2: 'méi', 3: 'měi', 4: 'mèi' }, audioChars: { 2: '没', 3: '美', 4: '妹' }, anchorWord: { hanzi: '没有', pinyin: 'méiyǒu', meaningEn: 'Do not have' } },
  'm_en': { syllable: 'men', initial: 'm', final: 'en', validTones: [2], pinyinWithTones: { 2: 'mén' }, audioChars: { 2: '门' }, anchorWord: { hanzi: '我们', pinyin: 'wǒmen', meaningEn: 'We / Us' } },
  'm_eng': { syllable: 'meng', initial: 'm', final: 'eng', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'mēng', 2: 'méng', 3: 'měng', 4: 'mèng' }, audioChars: { 1: '蒙', 2: '盟', 3: '猛', 4: '梦' }, anchorWord: { hanzi: '做梦', pinyin: 'zuòmèng', meaningEn: 'Dream' } },
  'm_o': { syllable: 'mo', initial: 'm', final: 'o', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'mō', 2: 'mó', 3: 'mǒ', 4: 'mò' }, audioChars: { 1: '摸', 2: '磨', 3: '抹', 4: '墨' }, anchorWord: { hanzi: '周末', pinyin: 'zhōumò', meaningEn: 'Weekend' } },
  'm_ou': { syllable: 'mou', initial: 'm', final: 'ou', validTones: [2, 3, 4], pinyinWithTones: { 2: 'móu', 3: 'mǒu', 4: 'mòu' }, audioChars: { 2: '谋', 3: '某', 4: '缪' }, anchorWord: { hanzi: '某人', pinyin: 'mǒurén', meaningEn: 'Someone' } },
  'm_i': { syllable: 'mi', initial: 'm', final: 'i', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'mī', 2: 'mí', 3: 'mǐ', 4: 'mì' }, audioChars: { 1: '咪', 2: '迷', 3: '米', 4: '密' }, anchorWord: { hanzi: '米饭', pinyin: 'mǐfàn', meaningEn: 'Rice' } },
  'm_ian': { syllable: 'mian', initial: 'm', final: 'ian', validTones: [2, 3, 4], pinyinWithTones: { 2: 'mián', 3: 'miǎn', 4: 'miàn' }, audioChars: { 2: '棉', 3: '免', 4: '面' }, anchorWord: { hanzi: '面条', pinyin: 'miàntiáo', meaningEn: 'Noodles' } },
  'm_iao': { syllable: 'miao', initial: 'm', final: 'iao', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'miāo', 2: 'miáo', 3: 'miǎo', 4: 'miào' }, audioChars: { 1: '喵', 2: '苗', 3: '秒', 4: '妙' }, anchorWord: { hanzi: '秒', pinyin: 'miǎo', meaningEn: 'Second' } },
  'm_ie': { syllable: 'mie', initial: 'm', final: 'ie', validTones: [1, 4], pinyinWithTones: { 1: 'miē', 4: 'miè' }, audioChars: { 1: '咩', 4: '灭' }, anchorWord: { hanzi: '灭火', pinyin: 'mièhuǒ', meaningEn: 'Extinguish' } },
  'm_in': { syllable: 'min', initial: 'm', final: 'in', validTones: [2, 3], pinyinWithTones: { 2: 'mín', 3: 'mǐn' }, audioChars: { 2: '民', 3: '敏' }, anchorWord: { hanzi: '人民', pinyin: 'rénmín', meaningEn: 'People' } },
  'm_ing': { syllable: 'ming', initial: 'm', final: 'ing', validTones: [2, 3, 4], pinyinWithTones: { 2: 'míng', 3: 'mǐng', 4: 'mìng' }, audioChars: { 2: '明', 3: '茗', 4: '命' }, anchorWord: { hanzi: '明天', pinyin: 'míngtiān', meaningEn: 'Tomorrow' } },
  'm_iu': { syllable: 'miu', initial: 'm', final: 'iu', validTones: [4], pinyinWithTones: { 4: 'miù' }, audioChars: { 4: '谬' }, anchorWord: { hanzi: '荒谬', pinyin: 'huāngmiù', meaningEn: 'Absurd' } },
  'm_u': { syllable: 'mu', initial: 'm', final: 'u', validTones: [3, 4], pinyinWithTones: { 3: 'mǔ', 4: 'mù' }, audioChars: { 3: '母', 4: '木' }, anchorWord: { hanzi: '木头', pinyin: 'mùtou', meaningEn: 'Wood' } },

  // f-
  'f_a': { syllable: 'fa', initial: 'f', final: 'a', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'fā', 2: 'fá', 3: 'fǎ', 4: 'fà' }, audioChars: { 1: '发', 2: '罚', 3: '法', 4: '发' }, anchorWord: { hanzi: '方法', pinyin: 'fāngfǎ', meaningEn: 'Method' } },
  'f_an': { syllable: 'fan', initial: 'f', final: 'an', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'fān', 2: 'fán', 3: 'fǎn', 4: 'fàn' }, audioChars: { 1: '番', 2: '烦', 3: '反', 4: '饭' }, anchorWord: { hanzi: '吃饭', pinyin: 'chīfàn', meaningEn: 'Eat food' } },
  'f_ang': { syllable: 'fang', initial: 'f', final: 'ang', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'fāng', 2: 'fáng', 3: 'fǎng', 4: 'fàng' }, audioChars: { 1: '方', 2: '房', 3: '访', 4: '放' }, anchorWord: { hanzi: '房子', pinyin: 'fángzi', meaningEn: 'House' } },
  'f_ei': { syllable: 'fei', initial: 'f', final: 'ei', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'fēi', 2: 'féi', 3: 'fěi', 4: 'fèi' }, audioChars: { 1: '飞', 2: '肥', 3: '匪', 4: '费' }, anchorWord: { hanzi: '飞机', pinyin: 'fēijī', meaningEn: 'Airplane' } },
  'f_en': { syllable: 'fen', initial: 'f', final: 'en', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'fēn', 2: 'fén', 3: 'fěn', 4: 'fèn' }, audioChars: { 1: '分', 2: '坟', 3: '粉', 4: '份' }, anchorWord: { hanzi: '十分钟', pinyin: 'shí fēnzhōng', meaningEn: '10 minutes' } },
  'f_eng': { syllable: 'feng', initial: 'f', final: 'eng', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'fēng', 2: 'féng', 3: 'fěng', 4: 'fèng' }, audioChars: { 1: '风', 2: '冯', 3: '讽', 4: '凤' }, anchorWord: { hanzi: '大风', pinyin: 'dàfēng', meaningEn: 'Big wind' } },
  'f_o': { syllable: 'fo', initial: 'f', final: 'o', validTones: [2], pinyinWithTones: { 2: 'fó' }, audioChars: { 2: '佛' }, anchorWord: { hanzi: '佛', pinyin: 'fó', meaningEn: 'Buddha' } },
  'f_ou': { syllable: 'fou', initial: 'f', final: 'ou', validTones: [3], pinyinWithTones: { 3: 'fǒu' }, audioChars: { 3: '否' }, anchorWord: { hanzi: '是否', pinyin: 'shìfǒu', meaningEn: 'Whether' } },
  'f_u': { syllable: 'fu', initial: 'f', final: 'u', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'fū', 2: 'fú', 3: 'fǔ', 4: 'fù' }, audioChars: { 1: '夫', 2: '服', 3: '府', 4: '父' }, anchorWord: { hanzi: '服务员', pinyin: 'fúwùyuán', meaningEn: 'Waiter' } },

  // d-
  'd_a': { syllable: 'da', initial: 'd', final: 'a', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'dā', 2: 'dá', 3: 'dǎ', 4: 'dà' }, audioChars: { 1: '搭', 2: '达', 3: '打', 4: '大' }, anchorWord: { hanzi: '大学', pinyin: 'dàxué', meaningEn: 'University' } },
  'd_ai': { syllable: 'dai', initial: 'd', final: 'ai', validTones: [1, 3, 4], pinyinWithTones: { 1: 'dāi', 3: 'dǎi', 4: 'dài' }, audioChars: { 1: '呆', 3: '歹', 4: '带' }, anchorWord: { hanzi: '带来', pinyin: 'dàilái', meaningEn: 'Bring' } },
  'd_ao': { syllable: 'dao', initial: 'd', final: 'ao', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'dāo', 2: 'dáo', 3: 'dǎo', 4: 'dào' }, audioChars: { 1: '刀', 2: '答', 3: '倒', 4: '到' }, anchorWord: { hanzi: '知道', pinyin: 'zhīdào', meaningEn: 'To know' } },
  'd_an': { syllable: 'dan', initial: 'd', final: 'an', validTones: [1, 3, 4], pinyinWithTones: { 1: 'dān', 3: 'dǎn', 4: 'dàn' }, audioChars: { 1: '单', 3: '胆', 4: '但' }, anchorWord: { hanzi: '买单', pinyin: 'mǎidān', meaningEn: 'Pay bill' } },
  'd_ang': { syllable: 'dang', initial: 'd', final: 'ang', validTones: [1, 3, 4], pinyinWithTones: { 1: 'dāng', 3: 'dǎng', 4: 'dàng' }, audioChars: { 1: '当', 3: '党', 4: '当' }, anchorWord: { hanzi: '当然', pinyin: 'dāngrán', meaningEn: 'Of course' } },
  'd_e': { syllable: 'de', initial: 'd', final: 'e', validTones: [2], pinyinWithTones: { 2: 'dé' }, audioChars: { 2: '得' }, anchorWord: { hanzi: '我的', pinyin: 'wǒ de', meaningEn: 'My / Mine' } },
  'd_ei': { syllable: 'dei', initial: 'd', final: 'ei', validTones: [3], pinyinWithTones: { 3: 'děi' }, audioChars: { 3: '得' }, anchorWord: { hanzi: '得去', pinyin: 'děi qù', meaningEn: 'Must go' } },
  'd_en': { syllable: 'den', initial: 'd', final: 'en', validTones: [4], pinyinWithTones: { 4: 'dèn' }, audioChars: { 4: '扽' } },
  'd_eng': { syllable: 'deng', initial: 'd', final: 'eng', validTones: [1, 3, 4], pinyinWithTones: { 1: 'dēng', 3: 'děng', 4: 'dèng' }, audioChars: { 1: '灯', 3: '等', 4: '凳' }, anchorWord: { hanzi: '等等', pinyin: 'děngděng', meaningEn: 'Wait a moment' } },
  'd_i': { syllable: 'di', initial: 'd', final: 'i', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'dī', 2: 'dí', 3: 'dǐ', 4: 'dì' }, audioChars: { 1: '低', 2: '敌', 3: '底', 4: '第' }, anchorWord: { hanzi: '第一', pinyin: 'dì yī', meaningEn: 'First' } },
  'd_ia': { syllable: 'dia', initial: 'd', final: 'ia', validTones: [3], pinyinWithTones: { 3: 'diǎ' }, audioChars: { 3: '嗲' } },
  'd_ian': { syllable: 'dian', initial: 'd', final: 'ian', validTones: [1, 3, 4], pinyinWithTones: { 1: 'diān', 3: 'diǎn', 4: 'diàn' }, audioChars: { 1: '颠', 3: '点', 4: '店' }, anchorWord: { hanzi: '商店', pinyin: 'shāngdiàn', meaningEn: 'Store' } },
  'd_iao': { syllable: 'diao', initial: 'd', final: 'iao', validTones: [1, 3, 4], pinyinWithTones: { 1: 'diāo', 3: 'diǎo', 4: 'diào' }, audioChars: { 1: '雕', 3: '鸟', 4: '掉' }, anchorWord: { hanzi: '掉落', pinyin: 'diàoluò', meaningEn: 'Fall' } },
  'd_ie': { syllable: 'die', initial: 'd', final: 'ie', validTones: [1, 2, 4], pinyinWithTones: { 1: 'diē', 2: 'dié', 4: 'diè' }, audioChars: { 1: '爹', 2: '叠', 4: '喋' }, anchorWord: { hanzi: '爹', pinyin: 'diē', meaningEn: 'Dad' } },
  'd_ing': { syllable: 'ding', initial: 'd', final: 'ing', validTones: [1, 3, 4], pinyinWithTones: { 1: 'dīng', 3: 'dǐng', 4: 'dìng' }, audioChars: { 1: '丁', 3: '顶', 4: '定' }, anchorWord: { hanzi: '决定', pinyin: 'juédìng', meaningEn: 'Decide' } },
  'd_iu': { syllable: 'diu', initial: 'd', final: 'iu', validTones: [1], pinyinWithTones: { 1: 'diū' }, audioChars: { 1: '丢' }, anchorWord: { hanzi: '弄丢', pinyin: 'nòngdiū', meaningEn: 'Lose' } },
  'd_ou': { syllable: 'dou', initial: 'd', final: 'ou', validTones: [1, 3, 4], pinyinWithTones: { 1: 'dōu', 3: 'dǒu', 4: 'dòu' }, audioChars: { 1: '都', 3: '抖', 4: '豆' }, anchorWord: { hanzi: '都是', pinyin: 'dōu shì', meaningEn: 'All are' } },
  'd_ong': { syllable: 'dong', initial: 'd', final: 'ong', validTones: [1, 3, 4], pinyinWithTones: { 1: 'dōng', 3: 'dǒng', 4: 'dòng' }, audioChars: { 1: '东', 3: '懂', 4: '动' }, anchorWord: { hanzi: '听懂', pinyin: 'tīngdǒng', meaningEn: 'Understand' } },
  'd_u': { syllable: 'du', initial: 'd', final: 'u', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'dū', 2: 'dú', 3: 'dǔ', 4: 'dù' }, audioChars: { 1: '都', 2: '读', 3: '赌', 4: '度' }, anchorWord: { hanzi: '读书', pinyin: 'dúshū', meaningEn: 'Read book' } },
  'd_uan': { syllable: 'duan', initial: 'd', final: 'uan', validTones: [1, 3, 4], pinyinWithTones: { 1: 'duān', 3: 'duǎn', 4: 'duàn' }, audioChars: { 1: '端', 3: '短', 4: '段' }, anchorWord: { hanzi: '长短', pinyin: 'chángduǎn', meaningEn: 'Length' } },
  'd_ui': { syllable: 'dui', initial: 'd', final: 'ui', validTones: [1, 3, 4], pinyinWithTones: { 1: 'duī', 3: 'duǐ', 4: 'duì' }, audioChars: { 1: '堆', 3: '㨃', 4: '对' }, anchorWord: { hanzi: '对不起', pinyin: 'duìbuqǐ', meaningEn: 'Sorry' } },
  'd_un': { syllable: 'dun', initial: 'd', final: 'un', validTones: [1, 3, 4], pinyinWithTones: { 1: 'dūn', 3: 'dǔn', 4: 'dùn' }, audioChars: { 1: '蹲', 3: '盹', 4: '顿' }, anchorWord: { hanzi: '一顿饭', pinyin: 'yī dùn fàn', meaningEn: 'A meal' } },
  'd_uo': { syllable: 'duo', initial: 'd', final: 'uo', validTones: [1, 3, 4], pinyinWithTones: { 1: 'duō', 3: 'duǒ', 4: 'duò' }, audioChars: { 1: '多', 3: '朵', 4: '舵' }, anchorWord: { hanzi: '多少钱', pinyin: 'duōshao qián', meaningEn: 'How much money' } },

  // t-
  't_a': { syllable: 'ta', initial: 't', final: 'a', validTones: [1, 3, 4], pinyinWithTones: { 1: 'tā', 3: 'tǎ', 4: 'tà' }, audioChars: { 1: '他', 3: '塔', 4: '踏' }, anchorWord: { hanzi: '他们', pinyin: 'tāmen', meaningEn: 'They / Them' } },
  't_ai': { syllable: 'tai', initial: 't', final: 'ai', validTones: [1, 2, 4], pinyinWithTones: { 1: 'tāi', 2: 'tái', 4: 'tài' }, audioChars: { 1: '胎', 2: '台', 4: '太' }, anchorWord: { hanzi: '太好了', pinyin: 'tài hǎo le', meaningEn: 'Great!' } },
  't_ao': { syllable: 'tao', initial: 't', final: 'ao', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'tāo', 2: 'táo', 3: 'tǎo', 4: 'tào' }, audioChars: { 1: '掏', 2: '桃', 3: '讨', 4: '套' }, anchorWord: { hanzi: '外套', pinyin: 'wàitào', meaningEn: 'Coat' } },
  't_an': { syllable: 'tan', initial: 't', final: 'an', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'tān', 2: 'tán', 3: 'tǎn', 4: 'tàn' }, audioChars: { 1: '摊', 2: '谈', 3: '毯', 4: '探' }, anchorWord: { hanzi: '谈话', pinyin: 'tánhuà', meaningEn: 'Talk' } },
  't_ang': { syllable: 'tang', initial: 't', final: 'ang', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'tāng', 2: 'táng', 3: 'tǎng', 4: 'tàng' }, audioChars: { 1: '汤', 2: '糖', 3: '躺', 4: '趟' }, anchorWord: { hanzi: '喝汤', pinyin: 'hē tāng', meaningEn: 'Drink soup' } },
  't_e': { syllable: 'te', initial: 't', final: 'e', validTones: [4], pinyinWithTones: { 4: 'tè' }, audioChars: { 4: '特' }, anchorWord: { hanzi: '特别', pinyin: 'tèbié', meaningEn: 'Special' } },
  't_eng': { syllable: 'teng', initial: 't', final: 'eng', validTones: [2], pinyinWithTones: { 2: 'téng' }, audioChars: { 2: '疼' }, anchorWord: { hanzi: '头疼', pinyin: 'tóuténg', meaningEn: 'Headache' } },
  't_i': { syllable: 'ti', initial: 't', final: 'i', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'tī', 2: 'tí', 3: 'tǐ', 4: 'tì' }, audioChars: { 1: '踢', 2: '提', 3: '体', 4: '替' }, anchorWord: { hanzi: '踢足球', pinyin: 'tī zúqiú', meaningEn: 'Play soccer' } },
  't_ian': { syllable: 'tian', initial: 't', final: 'ian', validTones: [1, 2, 3], pinyinWithTones: { 1: 'tiān', 2: 'tián', 3: 'tiǎn' }, audioChars: { 1: '天', 2: '田', 3: '舔' }, anchorWord: { hanzi: '今天', pinyin: 'jīntiān', meaningEn: 'Today' } },
  't_iao': { syllable: 'tiao', initial: 't', final: 'iao', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'tiāo', 2: 'tiáo', 3: 'tiǎo', 4: 'tiào' }, audioChars: { 1: '挑', 2: '条', 3: '窕', 4: '跳' }, anchorWord: { hanzi: '面条', pinyin: 'miàntiáo', meaningEn: 'Noodles' } },
  't_ie': { syllable: 'tie', initial: 't', final: 'ie', validTones: [1, 3, 4], pinyinWithTones: { 1: 'tiē', 3: 'tiě', 4: 'tiè' }, audioChars: { 1: '贴', 3: '铁', 4: '帖' }, anchorWord: { hanzi: '地铁', pinyin: 'dìtiě', meaningEn: 'Subway' } },
  't_ing': { syllable: 'ting', initial: 't', final: 'ing', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'tīng', 2: 'tíng', 3: 'tǐng', 4: 'tìng' }, audioChars: { 1: '听', 2: '停', 3: '挺', 4: '梃' }, anchorWord: { hanzi: '听音乐', pinyin: 'tīng yīnyuè', meaningEn: 'Listen music' } },
  't_ou': { syllable: 'tou', initial: 't', final: 'ou', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'tōu', 2: 'tóu', 3: 'tǒu', 4: 'tòu' }, audioChars: { 1: '偷', 2: '头', 3: '妵', 4: '透' }, anchorWord: { hanzi: '头发', pinyin: 'tóufa', meaningEn: 'Hair' } },
  't_ong': { syllable: 'tong', initial: 't', final: 'ong', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'tōng', 2: 'tóng', 3: 'tǒng', 4: 'tòng' }, audioChars: { 1: '通', 2: '同', 3: '桶', 4: '痛' }, anchorWord: { hanzi: '同学', pinyin: 'tóngxué', meaningEn: 'Classmate' } },
  't_u': { syllable: 'tu', initial: 't', final: 'u', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'tū', 2: 'tú', 3: 'tǔ', 4: 'tù' }, audioChars: { 1: '突', 2: '图', 3: '土', 4: '兔' }, anchorWord: { hanzi: '地图', pinyin: 'dìtú', meaningEn: 'Map' } },
  't_uan': { syllable: 'tuan', initial: 't', final: 'uan', validTones: [1, 2], pinyinWithTones: { 1: 'tuān', 2: 'tuán' }, audioChars: { 1: '湍', 2: '团' }, anchorWord: { hanzi: '团结', pinyin: 'tuánjié', meaningEn: 'Unite' } },
  't_ui': { syllable: 'tui', initial: 't', final: 'ui', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'tuī', 2: 'tuí', 3: 'tuǐ', 4: 'tuì' }, audioChars: { 1: '推', 2: '颓', 3: '腿', 4: '退' }, anchorWord: { hanzi: '推门', pinyin: 'tuīmén', meaningEn: 'Push door' } },
  't_un': { syllable: 'tun', initial: 't', final: 'un', validTones: [1, 2, 3], pinyinWithTones: { 1: 'tūn', 2: 'tún', 3: 'tǔn' }, audioChars: { 1: '吞', 2: '屯', 3: '氽' }, anchorWord: { hanzi: '吞咽', pinyin: 'tūnyàn', meaningEn: 'Swallow' } },
  't_uo': { syllable: 'tuo', initial: 't', final: 'uo', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'tuō', 2: 'tuó', 3: 'tuǒ', 4: 'tuò' }, audioChars: { 1: '拖', 2: '驼', 3: '妥', 4: '唾' }, anchorWord: { hanzi: '拖鞋', pinyin: 'tuōxié', meaningEn: 'Slippers' } },

  // n-
  'n_a': { syllable: 'na', initial: 'n', final: 'a', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'nā', 2: 'ná', 3: 'nǎ', 4: 'nà' }, audioChars: { 1: '南', 2: '拿', 3: '哪', 4: '那' }, anchorWord: { hanzi: '哪里', pinyin: 'nǎlǐ', meaningEn: 'Where' } },
  'n_ai': { syllable: 'nai', initial: 'n', final: 'ai', validTones: [3, 4], pinyinWithTones: { 3: 'nǎi', 4: 'nài' }, audioChars: { 3: '奶', 4: '耐' }, anchorWord: { hanzi: '牛奶', pinyin: 'niúnǎi', meaningEn: 'Milk' } },
  'n_ao': { syllable: 'nao', initial: 'n', final: 'ao', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'nāo', 2: 'náo', 3: 'nǎo', 4: 'nào' }, audioChars: { 1: '孬', 2: '挠', 3: '脑', 4: '闹' }, anchorWord: { hanzi: '电脑', pinyin: 'diànnǎo', meaningEn: 'Computer' } },
  'n_an': { syllable: 'nan', initial: 'n', final: 'an', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'nān', 2: 'nán', 3: 'nǎn', 4: 'nàn' }, audioChars: { 1: '囡', 2: '南', 3: '赧', 4: '难' }, anchorWord: { hanzi: '南边', pinyin: 'nánbiān', meaningEn: 'South' } },
  'n_ang': { syllable: 'nang', initial: 'n', final: 'ang', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'nāng', 2: 'náng', 3: 'nǎng', 4: 'nàng' }, audioChars: { 1: '囔', 2: '囊', 3: '攮', 4: '馕' } },
  'n_e': { syllable: 'ne', initial: 'n', final: 'e', validTones: [0], pinyinWithTones: { 0: 'ne' }, audioChars: { 0: '呢' }, anchorWord: { hanzi: '你呢', pinyin: 'nǐ ne', meaningEn: 'And you?' } },
  'n_ei': { syllable: 'nei', initial: 'n', final: 'ei', validTones: [3, 4], pinyinWithTones: { 3: 'něi', 4: 'nèi' }, audioChars: { 3: '哪', 4: '内' }, anchorWord: { hanzi: '内容', pinyin: 'nèiróng', meaningEn: 'Content' } },
  'n_en': { syllable: 'nen', initial: 'n', final: 'en', validTones: [4], pinyinWithTones: { 4: 'nèn' }, audioChars: { 4: '嫩' }, anchorWord: { hanzi: '鲜嫩', pinyin: 'xiānnèn', meaningEn: 'Tender' } },
  'n_eng': { syllable: 'neng', initial: 'n', final: 'eng', validTones: [2], pinyinWithTones: { 2: 'néng' }, audioChars: { 2: '能' }, anchorWord: { hanzi: '能去', pinyin: 'néng qù', meaningEn: 'Can go' } },
  'n_i': { syllable: 'ni', initial: 'n', final: 'i', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'nī', 2: 'ní', 3: 'nǐ', 4: 'nì' }, audioChars: { 1: '妮', 2: '泥', 3: '你', 4: '逆' }, anchorWord: { hanzi: '你好', pinyin: 'nǐ hǎo', meaningEn: 'Hello' } },
  'n_ian': { syllable: 'nian', initial: 'n', final: 'ian', validTones: [2, 3, 4], pinyinWithTones: { 2: 'nián', 3: 'niǎn', 4: 'niàn' }, audioChars: { 2: '年', 3: '捻', 4: '念' }, anchorWord: { hanzi: '新年', pinyin: 'xīnnián', meaningEn: 'New Year' } },
  'n_iang': { syllable: 'niang', initial: 'n', final: 'iang', validTones: [2, 4], pinyinWithTones: { 2: 'niáng', 4: 'niàng' }, audioChars: { 2: '娘', 4: '酿' }, anchorWord: { hanzi: '大娘', pinyin: 'dàniáng', meaningEn: 'Aunt' } },
  'n_iao': { syllable: 'niao', initial: 'n', final: 'iao', validTones: [3, 4], pinyinWithTones: { 3: 'niǎo', 4: 'niào' }, audioChars: { 3: '鸟', 4: '尿' }, anchorWord: { hanzi: '小鸟', pinyin: 'xiǎoniǎo', meaningEn: 'Bird' } },
  'n_ie': { syllable: 'nie', initial: 'n', final: 'ie', validTones: [1, 4], pinyinWithTones: { 1: 'niē', 4: 'niè' }, audioChars: { 1: '捏', 4: '聂' }, anchorWord: { hanzi: '捏合', pinyin: 'niēhé', meaningEn: 'Pinch' } },
  'n_in': { syllable: 'nin', initial: 'n', final: 'in', validTones: [2], pinyinWithTones: { 2: 'nín' }, audioChars: { 2: '您' }, anchorWord: { hanzi: '您好', pinyin: 'nín hǎo', meaningEn: 'Hello (polite)' } },
  'n_ing': { syllable: 'ning', initial: 'n', final: 'ing', validTones: [2, 3, 4], pinyinWithTones: { 2: 'níng', 3: 'nǐng', 4: 'nìng' }, audioChars: { 2: '宁', 3: '拧', 4: '泞' }, anchorWord: { hanzi: '安宁', pinyin: 'ānníng', meaningEn: 'Peaceful' } },
  'n_iu': { syllable: 'niu', initial: 'n', final: 'iu', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'niū', 2: 'niú', 3: 'niǔ', 4: 'niù' }, audioChars: { 1: '妞', 2: '牛', 3: '扭', 4: '拗' }, anchorWord: { hanzi: '牛肉', pinyin: 'niúròu', meaningEn: 'Beef' } },
  'n_ong': { syllable: 'nong', initial: 'n', final: 'ong', validTones: [2, 3, 4], pinyinWithTones: { 2: 'nóng', 3: 'nǒng', 4: 'nòng' }, audioChars: { 2: '农', 3: '挵', 4: '弄' }, anchorWord: { hanzi: '农民', pinyin: 'nóngmín', meaningEn: 'Farmer' } },
  'n_u': { syllable: 'nu', initial: 'n', final: 'u', validTones: [2, 3, 4], pinyinWithTones: { 2: 'nú', 3: 'nǔ', 4: 'nù' }, audioChars: { 2: '奴', 3: '努', 4: '怒' }, anchorWord: { hanzi: '努力', pinyin: 'nǔlì', meaningEn: 'Hardworking' } },
  'n_v': { syllable: 'nv', initial: 'n', final: 'ü', validTones: [3, 4], pinyinWithTones: { 3: 'nǚ', 4: 'nǜ' }, audioChars: { 3: '女', 4: '恧' }, anchorWord: { hanzi: '女儿', pinyin: 'nǚ’ér', meaningEn: 'Daughter' } },

  // l-
  'l_a': { syllable: 'la', initial: 'l', final: 'a', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'lā', 2: 'lá', 3: 'lǎ', 4: 'là' }, audioChars: { 1: '拉', 2: '旯', 3: '喇', 4: '辣' }, anchorWord: { hanzi: '辣椒', pinyin: 'làjiāo', meaningEn: 'Chili' } },
  'l_ai': { syllable: 'lai', initial: 'l', final: 'ai', validTones: [2, 4], pinyinWithTones: { 2: 'lái', 4: 'lài' }, audioChars: { 2: '来', 4: '赖' }, anchorWord: { hanzi: '来这里', pinyin: 'lái zhèlǐ', meaningEn: 'Come here' } },
  'l_ao': { syllable: 'lao', initial: 'l', final: 'ao', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'lāo', 2: 'láo', 3: 'lǎo', 4: 'lào' }, audioChars: { 1: '捞', 2: '劳', 3: '老', 4: '烙' }, anchorWord: { hanzi: '老师', pinyin: 'lǎoshī', meaningEn: 'Teacher' } },
  'l_an': { syllable: 'lan', initial: 'l', final: 'an', validTones: [2, 3, 4], pinyinWithTones: { 2: 'lán', 3: 'lǎn', 4: 'làn' }, audioChars: { 2: '蓝', 3: '懒', 4: '烂' }, anchorWord: { hanzi: '蓝色', pinyin: 'lánsè', meaningEn: 'Blue' } },
  'l_ang': { syllable: 'lang', initial: 'l', final: 'ang', validTones: [2, 3, 4], pinyinWithTones: { 2: 'láng', 3: 'lǎng', 4: 'làng' }, audioChars: { 2: '狼', 3: '朗', 4: '浪' }, anchorWord: { hanzi: '开朗', pinyin: 'kāilǎng', meaningEn: 'Cheerful' } },
  'l_e': { syllable: 'le', initial: 'l', final: 'e', validTones: [4, 0], pinyinWithTones: { 4: 'lè', 0: 'le' }, audioChars: { 4: '乐', 0: '了' }, anchorWord: { hanzi: '快乐', pinyin: 'kuàilè', meaningEn: 'Happy' } },
  'l_ei': { syllable: 'lei', initial: 'l', final: 'ei', validTones: [2, 3, 4], pinyinWithTones: { 2: 'léi', 3: 'lěi', 4: 'lèi' }, audioChars: { 2: '雷', 3: '累', 4: '累' }, anchorWord: { hanzi: '很累', pinyin: 'hěn lèi', meaningEn: 'Very tired' } },
  'l_eng': { syllable: 'leng', initial: 'l', final: 'eng', validTones: [2, 3, 4], pinyinWithTones: { 2: 'léng', 3: 'lěng', 4: 'lèng' }, audioChars: { 2: '棱', 3: '冷', 4: '愣' }, anchorWord: { hanzi: '天气冷', pinyin: 'tiānqì lěng', meaningEn: 'Cold weather' } },
  'l_i': { syllable: 'li', initial: 'l', final: 'i', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'lī', 2: 'lí', 3: 'lǐ', 4: 'lì' }, audioChars: { 1: '哩', 2: '离', 3: '里', 4: '力' }, anchorWord: { hanzi: '哪里', pinyin: 'nǎlǐ', meaningEn: 'Where' } },
  'l_v': { syllable: 'lv', initial: 'l', final: 'ü', validTones: [2, 3, 4], pinyinWithTones: { 2: 'lǘ', 3: 'lǚ', 4: 'lǜ' }, audioChars: { 2: '驴', 3: '旅', 4: '绿' }, anchorWord: { hanzi: '绿色', pinyin: 'lǜsè', meaningEn: 'Green' } },

  // g-, k-, h-
  'g_e': { syllable: 'ge', initial: 'g', final: 'e', validTones: [1, 2, 3, 4, 0], pinyinWithTones: { 1: 'gē', 2: 'gé', 3: 'gě', 4: 'gè', 0: 'ge' }, audioChars: { 1: '哥', 2: '格', 3: '葛', 4: '个', 0: '个' }, anchorWord: { hanzi: '哥哥', pinyin: 'gēge', meaningEn: 'Elder brother' } },
  'g_ao': { syllable: 'gao', initial: 'g', final: 'ao', validTones: [1, 3, 4], pinyinWithTones: { 1: 'gāo', 3: 'gǎo', 4: 'gào' }, audioChars: { 1: '高', 3: '搞', 4: '告' }, anchorWord: { hanzi: '高兴', pinyin: 'gāoxìng', meaningEn: 'Happy' } },
  'k_ai': { syllable: 'kai', initial: 'k', final: 'ai', validTones: [1, 3, 4], pinyinWithTones: { 1: 'kāi', 3: 'kǎi', 4: 'kài' }, audioChars: { 1: '开', 3: '铠', 4: '慨' }, anchorWord: { hanzi: '开门', pinyin: 'kāimén', meaningEn: 'Open door' } },
  'k_an': { syllable: 'kan', initial: 'k', final: 'an', validTones: [1, 3, 4], pinyinWithTones: { 1: 'kān', 3: 'kǎn', 4: 'kàn' }, audioChars: { 1: '看', 3: '砍', 4: '看' }, anchorWord: { hanzi: '看电影', pinyin: 'kàn diànyǐng', meaningEn: 'Watch movie' } },
  'h_ao': { syllable: 'hao', initial: 'h', final: 'ao', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'hāo', 2: 'háo', 3: 'hǎo', 4: 'hào' }, audioChars: { 1: '蒿', 2: '豪', 3: '好', 4: '号' }, anchorWord: { hanzi: '你好', pinyin: 'nǐ hǎo', meaningEn: 'Hello' } },
  'h_e': { syllable: 'he', initial: 'h', final: 'e', validTones: [1, 2, 4], pinyinWithTones: { 1: 'hē', 2: 'hé', 4: 'hè' }, audioChars: { 1: '喝', 2: '和', 4: '贺' }, anchorWord: { hanzi: '喝水', pinyin: 'hē shuǐ', meaningEn: 'Drink water' } },

  // j-, q-, x-
  'j_i': { syllable: 'ji', initial: 'j', final: 'i', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'jī', 2: 'jí', 3: 'jǐ', 4: 'jì' }, audioChars: { 1: '鸡', 2: '极', 3: '几', 4: '记' }, anchorWord: { hanzi: '飞机', pinyin: 'fēijī', meaningEn: 'Airplane' } },
  'j_ia': { syllable: 'jia', initial: 'j', final: 'ia', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'jiā', 2: 'jiá', 3: 'jiǎ', 4: 'jià' }, audioChars: { 1: '家', 2: '夹', 3: '假', 4: '价' }, anchorWord: { hanzi: '回家', pinyin: 'huíjiā', meaningEn: 'Go home' } },
  'q_i': { syllable: 'qi', initial: 'q', final: 'i', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'qī', 2: 'qí', 3: 'qǐ', 4: 'qì' }, audioChars: { 1: '七', 2: '骑', 3: '起', 4: '气' }, anchorWord: { hanzi: '对不起', pinyin: 'duìbuqǐ', meaningEn: 'Sorry' } },
  'q_ian': { syllable: 'qian', initial: 'q', final: 'ian', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'qiān', 2: 'qián', 3: 'qiǎn', 4: 'qiàn' }, audioChars: { 1: '千', 2: '钱', 3: '浅', 4: '欠' }, anchorWord: { hanzi: '多少钱', pinyin: 'duōshao qián', meaningEn: 'How much' } },
  'x_i': { syllable: 'xi', initial: 'x', final: 'i', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'xī', 2: 'xí', 3: 'xǐ', 4: 'xì' }, audioChars: { 1: '西', 2: '习', 3: '喜', 4: '细' }, anchorWord: { hanzi: '喜欢', pinyin: 'xǐhuan', meaningEn: 'To like' } },
  'x_ie': { syllable: 'xie', initial: 'x', final: 'ie', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'xiē', 2: 'xié', 3: 'xiě', 4: 'xiè' }, audioChars: { 1: '些', 2: '鞋', 3: '写', 4: '谢' }, anchorWord: { hanzi: '谢谢', pinyin: 'xièxie', meaningEn: 'Thank you' } },

  // zh-, ch-, sh-, r-
  'zh_i': { syllable: 'zhi', initial: 'zh', final: 'i', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'zhī', 2: 'zhí', 3: 'zhǐ', 4: 'zhì' }, audioChars: { 1: '知', 2: '直', 3: '只', 4: '志' }, anchorWord: { hanzi: '知道', pinyin: 'zhīdào', meaningEn: 'Know' } },
  'zh_ong': { syllable: 'zhong', initial: 'zh', final: 'ong', validTones: [1, 3, 4], pinyinWithTones: { 1: 'zhōng', 3: 'zhǒng', 4: 'zhòng' }, audioChars: { 1: '中', 3: '种', 4: '重' }, anchorWord: { hanzi: '中国', pinyin: 'Zhōngguó', meaningEn: 'China' } },
  'ch_i': { syllable: 'chi', initial: 'ch', final: 'i', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'chī', 2: 'chí', 3: 'chǐ', 4: 'chì' }, audioChars: { 1: '吃', 2: '迟', 3: '齿', 4: '翅' }, anchorWord: { hanzi: '吃饭', pinyin: 'chīfàn', meaningEn: 'Eat meal' } },
  'ch_a': { syllable: 'cha', initial: 'ch', final: 'a', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'chā', 2: 'chá', 3: 'chǎ', 4: 'chà' }, audioChars: { 1: '插', 2: '茶', 3: '汊', 4: '差' }, anchorWord: { hanzi: '喝茶', pinyin: 'hē chá', meaningEn: 'Drink tea' } },
  'sh_i': { syllable: 'shi', initial: 'sh', final: 'i', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'shī', 2: 'shí', 3: 'shǐ', 4: 'shì' }, audioChars: { 1: '师', 2: '十', 3: '使', 4: '是' }, anchorWord: { hanzi: '认识', pinyin: 'rènshi', meaningEn: 'To meet' } },
  'sh_ui': { syllable: 'shui', initial: 'sh', final: 'ui', validTones: [3, 4], pinyinWithTones: { 3: 'shuǐ', 4: 'shuì' }, audioChars: { 3: '水', 4: '睡' }, anchorWord: { hanzi: '喝水', pinyin: 'hē shuǐ', meaningEn: 'Drink water' } },
  'r_en': { syllable: 'ren', initial: 'r', final: 'en', validTones: [2, 3, 4], pinyinWithTones: { 2: 'rén', 3: 'rěn', 4: 'rèn' }, audioChars: { 2: '人', 3: '忍', 4: '认' }, anchorWord: { hanzi: '中国人', pinyin: 'Zhōngguórén', meaningEn: 'Chinese person' } },

  // z-, c-, s-
  'z_i': { syllable: 'zi', initial: 'z', final: 'i', validTones: [1, 3, 4], pinyinWithTones: { 1: 'zī', 3: 'zǐ', 4: 'zì' }, audioChars: { 1: '资', 3: '子', 4: '字' }, anchorWord: { hanzi: '汉字', pinyin: 'hànzì', meaningEn: 'Chinese character' } },
  'z_ai': { syllable: 'zai', initial: 'z', final: 'ai', validTones: [3, 4], pinyinWithTones: { 3: 'zǎi', 4: 'zài' }, audioChars: { 3: '崽', 4: '在' }, anchorWord: { hanzi: '再见', pinyin: 'zàijiàn', meaningEn: 'Goodbye' } },
  'c_i': { syllable: 'ci', initial: 'c', final: 'i', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'cī', 2: 'cí', 3: 'cǐ', 4: 'cì' }, audioChars: { 1: '呲', 2: '词', 3: '此', 4: '次' }, anchorWord: { hanzi: '生词', pinyin: 'shēngcí', meaningEn: 'Vocabulary' } },
  's_i': { syllable: 'si', initial: 's', final: 'i', validTones: [1, 3, 4], pinyinWithTones: { 1: 'sī', 3: 'sǐ', 4: 'sì' }, audioChars: { 1: '司', 3: '死', 4: '四' }, anchorWord: { hanzi: '四', pinyin: 'sì', meaningEn: 'Four (4)' } },

  // w-, y-
  'w_u': { syllable: 'wu', initial: 'w', final: 'u', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'wū', 2: 'wú', 3: 'wǔ', 4: 'wù' }, audioChars: { 1: '屋', 2: '无', 3: '五', 4: '物' }, anchorWord: { hanzi: '五', pinyin: 'wǔ', meaningEn: 'Five (5)' } },
  'w_o': { syllable: 'wo', initial: 'w', final: 'o', validTones: [1, 3, 4], pinyinWithTones: { 1: 'wō', 3: 'wǒ', 4: 'wò' }, audioChars: { 1: '窝', 3: '我', 4: '握' }, anchorWord: { hanzi: '我们', pinyin: 'wǒmen', meaningEn: 'We / Us' } },
  'y_i': { syllable: 'yi', initial: 'y', final: 'i', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'yī', 2: 'yí', 3: 'yǐ', 4: 'yì' }, audioChars: { 1: '一', 2: '姨', 3: '以', 4: '意' }, anchorWord: { hanzi: '一', pinyin: 'yī', meaningEn: 'One (1)' } },
  'y_u': { syllable: 'yu', initial: 'y', final: 'ü', validTones: [1, 2, 3, 4], pinyinWithTones: { 1: 'yū', 2: 'yú', 3: 'yǔ', 4: 'yù' }, audioChars: { 1: '迂', 2: '鱼', 3: '雨', 4: '遇' }, anchorWord: { hanzi: '下雨', pinyin: 'xiàyǔ', meaningEn: 'Rain' } },
};
