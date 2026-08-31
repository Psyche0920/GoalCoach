-- GoalCoach HSK1 Learning Content Database (SQLite)
-- Database #1: structured HSK1 learning content for the MVP.
-- PostgreSQL-specific ARRAY/JSONB fields were converted to JSON stored as TEXT.
-- SQLite JSON1 functions can read these JSON strings when needed.

PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS curriculum_concepts (
    concept_id          TEXT PRIMARY KEY,
    hsk_level           INTEGER NOT NULL CHECK (hsk_level = 1),
    sequence_no         INTEGER NOT NULL UNIQUE CHECK (sequence_no BETWEEN 1 AND 20),
    slug                TEXT NOT NULL UNIQUE,
    title_zh            TEXT NOT NULL,
    title_en            TEXT NOT NULL,
    concept_type        TEXT NOT NULL CHECK (concept_type IN ('communication','grammar','vocabulary','mixed')),
    communicative_goal  TEXT NOT NULL,
    grammar_focus       TEXT NOT NULL DEFAULT '[]',
    vocabulary_focus    TEXT NOT NULL DEFAULT '[]',
    difficulty          INTEGER NOT NULL DEFAULT 1 CHECK (difficulty BETWEEN 1 AND 5),
    estimated_minutes   INTEGER NOT NULL DEFAULT 6 CHECK (estimated_minutes > 0),
    source_ref          TEXT NOT NULL DEFAULT 'HSK3.0-2026',
    is_active           INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    metadata            TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS teaching_cards (
    card_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    concept_id          TEXT NOT NULL REFERENCES curriculum_concepts(concept_id) ON DELETE CASCADE,
    card_order          INTEGER NOT NULL,
    card_type           TEXT NOT NULL CHECK (card_type IN ('goal','vocab','grammar','example','tip','mini_dialogue')),
    prompt_zh           TEXT,
    pinyin              TEXT,
    meaning_en          TEXT,
    explanation_en      TEXT,
    example_zh          TEXT,
    example_pinyin      TEXT,
    example_en          TEXT,
    payload             TEXT NOT NULL DEFAULT '{}',
    UNIQUE(concept_id, card_order)
);

CREATE TABLE IF NOT EXISTS exercises (
    exercise_id         TEXT PRIMARY KEY,
    concept_id          TEXT NOT NULL REFERENCES curriculum_concepts(concept_id) ON DELETE CASCADE,
    exercise_order      INTEGER NOT NULL,
    exercise_type       TEXT NOT NULL CHECK (exercise_type IN (
                            'meaning_mcq','zh_to_en_mcq','en_to_zh_mcq',
                            'fill_blank','reorder','translate_to_zh','dialogue_choice'
                          )),
    prompt              TEXT NOT NULL,
    prompt_pinyin       TEXT,
    instruction         TEXT NOT NULL,
    answer              TEXT NOT NULL,
    options             TEXT,
    accepted_answers    TEXT NOT NULL DEFAULT '[]',
    explanation         TEXT NOT NULL,
    target_tokens       TEXT NOT NULL DEFAULT '[]',
    error_tags          TEXT NOT NULL DEFAULT '[]',
    difficulty          INTEGER NOT NULL DEFAULT 1 CHECK (difficulty BETWEEN 1 AND 5),
    points              INTEGER NOT NULL DEFAULT 10 CHECK (points > 0),
    metadata            TEXT NOT NULL DEFAULT '{}',
    UNIQUE(concept_id, exercise_order)
);

CREATE TABLE IF NOT EXISTS concept_prerequisites (
    concept_id          TEXT NOT NULL REFERENCES curriculum_concepts(concept_id) ON DELETE CASCADE,
    prerequisite_id     TEXT NOT NULL REFERENCES curriculum_concepts(concept_id) ON DELETE CASCADE,
    PRIMARY KEY (concept_id, prerequisite_id),
    CHECK (concept_id <> prerequisite_id)
);

CREATE INDEX IF NOT EXISTS idx_concepts_hsk_sequence ON curriculum_concepts(hsk_level, sequence_no);
CREATE INDEX IF NOT EXISTS idx_cards_concept ON teaching_cards(concept_id, card_order);
CREATE INDEX IF NOT EXISTS idx_exercises_concept ON exercises(concept_id, exercise_order);
CREATE INDEX IF NOT EXISTS idx_exercises_type ON exercises(exercise_type);

INSERT INTO curriculum_concepts
(concept_id,hsk_level,sequence_no,slug,title_zh,title_en,concept_type,communicative_goal,grammar_focus,vocabulary_focus,difficulty,estimated_minutes,metadata)
VALUES
('hsk1_c01',1,1,'greetings','问候与告别','Greetings & Goodbye','communication','Greet someone and say goodbye.','[]','["你好", "您好", "谢谢", "再见"]',1,5,'{"skills":["reading","speaking"],"theme":"social"}'),
('hsk1_c02',1,2,'self_intro','自我介绍：我叫… / 我是…','Self-introduction: 我叫… / 我是…','mixed','Say your name and basic identity.','["A叫B", "A是B"]','["我", "你", "叫", "名字", "学生", "老师"]',1,6,'{"skills":["reading","speaking"],"theme":"personal_information"}'),
('hsk1_c03',1,3,'pronouns_shi','人称代词 + 是','Pronouns + 是','grammar','Identify people with simple 是 sentences.','["A是B"]','["我", "你", "他", "她", "我们", "你们", "他们", "是"]',1,6,'{"skills":["reading","writing"],"theme":"people"}'),
('hsk1_c04',1,4,'ma_questions','吗：一般疑问句','Yes/No Questions with 吗','grammar','Turn a statement into a yes/no question using 吗.','["陈述句+吗？"]','["吗", "是", "学生", "老师", "中国人"]',1,7,'{"skills":["reading","speaking"],"theme":"questions"}'),
('hsk1_c05',1,5,'ne_followup','呢：反问与追问','Follow-up Questions with 呢','grammar','Ask “what about ...?” in a short conversation.','["名词/代词+呢？"]','["呢", "我", "你", "他", "她"]',1,6,'{"skills":["dialogue","speaking"],"theme":"questions"}'),
('hsk1_c06',1,6,'shenme','什么：询问事物','Asking What with 什么','grammar','Ask what something is or what someone does.','["什么", "A是什么？"]','["什么", "名字", "书", "吃", "喝"]',1,7,'{"skills":["reading","speaking"],"theme":"questions"}'),
('hsk1_c07',1,7,'shui','谁：询问人物','Asking Who with 谁','grammar','Ask and answer who a person is.','["谁", "谁是…？"]','["谁", "老师", "学生", "朋友"]',1,6,'{"skills":["reading","speaking"],"theme":"people"}'),
('hsk1_c08',1,8,'na_nar','哪 / 哪儿：选择与地点','Which / Where with 哪 / 哪儿','grammar','Ask which one or where someone/something is.','["哪+量词+名词", "哪儿"]','["哪", "哪儿", "学校", "家", "商店"]',2,7,'{"skills":["reading","dialogue"],"theme":"location"}'),
('hsk1_c09',1,9,'zhe_na','这 / 那：指示','This / That with 这 / 那','grammar','Point out nearby and distant people or things.','["这/那+量词+名词"]','["这", "那", "个", "书", "人"]',1,6,'{"skills":["reading","writing"],"theme":"objects"}'),
('hsk1_c10',1,10,'you_meiyou','有 / 没有：存在与拥有','Have / Not Have with 有 / 没有','grammar','Say what someone has or does not have.','["A有B", "A没有B"]','["有", "没有", "书", "朋友", "钱"]',2,7,'{"skills":["reading","speaking"],"theme":"possession"}'),
('hsk1_c11',1,11,'bu_negation','不：否定','Negation with 不','grammar','Negate habitual, present or future statements with 不.','["不+动词/形容词"]','["不", "是", "喜欢", "去", "吃"]',2,7,'{"skills":["reading","writing"],"theme":"negation"}'),
('hsk1_c12',1,12,'de_possession','的：所属关系','Possession with 的','grammar','Express possession and simple noun modification.','["A的B"]','["的", "我", "你", "朋友", "书", "老师"]',2,7,'{"skills":["reading","writing"],"theme":"possession"}'),
('hsk1_c13',1,13,'hen_adjective','很 + 形容词','Adjectival Predicates with 很','grammar','Describe people, things and conditions with adjective predicates.','["主语+很+形容词"]','["很", "好", "大", "小", "漂亮", "高兴", "冷", "热"]',2,7,'{"skills":["reading","speaking"],"theme":"description"}'),
('hsk1_c14',1,14,'ye_dou','也 / 都：也与范围','Also / All with 也 / 都','grammar','Say “also” and “all/both” with correct word order.','["主语+也+谓语", "主语+都+谓语"]','["也", "都", "喜欢", "是"]',2,8,'{"skills":["reading","writing"],"theme":"comparison"}'),
('hsk1_c15',1,15,'numbers_0_10','数字 0–10','Numbers 0–10','vocabulary','Recognize and use basic numbers.','[]','["零", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]',1,6,'{"skills":["reading","listening"],"theme":"numbers"}'),
('hsk1_c16',1,16,'ji_duoshao','几 / 多少：询问数量','Asking Quantity with 几 / 多少','grammar','Ask about small or open quantities.','["几+量词+名词", "多少+名词"]','["几", "多少", "个", "人", "书", "钱"]',2,8,'{"skills":["reading","dialogue"],"theme":"numbers"}'),
('hsk1_c17',1,17,'measure_ge','量词 个','General Measure Word 个','grammar','Use numeral/demonstrative + 个 + noun.','["数词/这/那+个+名词"]','["个", "一个", "这个", "那个", "人", "学生"]',2,7,'{"skills":["reading","writing"],"theme":"classifiers"}'),
('hsk1_c18',1,18,'zai_location','在：地点表达','Location with 在','grammar','Say where a person or thing is.','["主语+在+地点"]','["在", "家", "学校", "医院", "商店", "中国"]',2,8,'{"skills":["reading","speaking"],"theme":"location"}'),
('hsk1_c19',1,19,'basic_time','今天 / 明天 / 昨天 + 点','Basic Time & Day Expressions','mixed','Talk about today/tomorrow/yesterday and simple clock times.','["时间+主语+谓语", "数字+点"]','["今天", "明天", "昨天", "现在", "点", "上午", "下午"]',2,8,'{"skills":["reading","dialogue"],"theme":"time"}'),
('hsk1_c20',1,20,'likes_wants_ability','喜欢 / 想 / 会 / 能','Likes, Wants & Ability','grammar','Express preference, intention and basic ability.','["喜欢+名词/动词", "想+动词", "会+动词", "能+动词"]','["喜欢", "想", "会", "能", "吃", "喝", "学习", "说", "汉语"]',3,10,'{"skills":["reading","speaking","writing"],"theme":"daily_life"}')
ON CONFLICT(concept_id) DO NOTHING;

INSERT INTO teaching_cards
(concept_id,card_order,card_type,prompt_zh,pinyin,meaning_en,explanation_en,example_zh,example_pinyin,example_en,payload)
VALUES
('hsk1_c01',1,'vocab','你好','nǐ hǎo','hello','A standard greeting.','你好！','nǐ hǎo','Hello!','{"ui":"tap_card"}'),
('hsk1_c01',2,'mini_dialogue',NULL,NULL,NULL,'Use a very short greeting pair.','你好！— 你好！',NULL,'Hello! — Hello!','{"ui":"dialogue"}'),
('hsk1_c02',1,'grammar','我叫…','wǒ jiào…','My name is…','Use 叫 before a name when introducing yourself.','我叫安娜。','wǒ jiào Ānnà','My name is Anna.','{"ui":"pattern_card"}'),
('hsk1_c03',1,'grammar','A 是 B','A shì B','A is B','是 links a person/thing to an identity or noun category.','她是老师。','tā shì lǎoshī','She is a teacher.','{"ui":"pattern_card"}'),
('hsk1_c04',1,'grammar','陈述句 + 吗？',NULL,'statement + 吗?','Put 吗 at the end of a statement to form a neutral yes/no question.','你是学生吗？','nǐ shì xuésheng ma','Are you a student?','{"ui":"pattern_card","grading_gate":"target_concept"}'),
('hsk1_c05',1,'grammar','你呢？','nǐ ne','What about you?','呢 can return the same topic/question to another person.','我是学生。你呢？','wǒ shì xuésheng. nǐ ne','I am a student. What about you?','{"ui":"dialogue"}'),
('hsk1_c06',1,'grammar','什么','shénme','what','Place 什么 where the unknown thing would appear.','这是什么？','zhè shì shénme','What is this?','{"ui":"pattern_card"}'),
('hsk1_c07',1,'grammar','谁','shéi','who','Place 谁 where the unknown person would appear.','她是谁？','tā shì shéi','Who is she?','{"ui":"pattern_card"}'),
('hsk1_c08',1,'grammar','哪儿','nǎr','where','Use 哪儿 to ask about location.','你在哪儿？','nǐ zài nǎr','Where are you?','{"ui":"pattern_card"}'),
('hsk1_c09',1,'grammar','这 / 那','zhè / nà','this / that','Use 这 for something near; 那 for something farther away.','这是我的书。','zhè shì wǒ de shū','This is my book.','{"ui":"contrast_card"}'),
('hsk1_c10',1,'grammar','有 / 没有','yǒu / méiyǒu','have / do not have','Use 没有, not 不有, to negate 有.','我有书。我没有钱。','wǒ yǒu shū. wǒ méiyǒu qián','I have books. I do not have money.','{"ui":"contrast_card","common_error":"不有"}'),
('hsk1_c11',1,'grammar','不 + 动词/形容词','bù + verb/adjective','not','不 commonly negates present habits, preferences and future intentions.','我不喝茶。','wǒ bù hē chá','I do not drink tea.','{"ui":"pattern_card"}'),
('hsk1_c12',1,'grammar','A 的 B','A de B','A’s B','的 links a possessor/modifier to a noun.','我的老师','wǒ de lǎoshī','my teacher','{"ui":"pattern_card"}'),
('hsk1_c13',1,'grammar','主语 + 很 + 形容词',NULL,'subject + 很 + adjective','Beginner Chinese commonly uses 很 before an adjective predicate.','天气很好。','tiānqì hěn hǎo','The weather is good.','{"ui":"pattern_card"}'),
('hsk1_c14',1,'grammar','也 / 都','yě / dōu','also / all','Both usually appear before the main predicate.','我们都是学生。','wǒmen dōu shì xuésheng','We are all students.','{"ui":"contrast_card"}'),
('hsk1_c15',1,'vocab','一 二 三 四 五','yī èr sān sì wǔ','1 2 3 4 5','Learn numbers in small chunks.','三个人','sān ge rén','three people','{"ui":"tap_card"}'),
('hsk1_c16',1,'grammar','几 / 多少','jǐ / duōshao','how many / how much','几 often asks a small expected number; 多少 is more open-ended.','你有几个朋友？','nǐ yǒu jǐ ge péngyou','How many friends do you have?','{"ui":"contrast_card"}'),
('hsk1_c17',1,'grammar','数词 + 个 + 名词',NULL,'number + 个 + noun','个 is a common general classifier.','三个学生','sān ge xuésheng','three students','{"ui":"pattern_card"}'),
('hsk1_c18',1,'grammar','主语 + 在 + 地点',NULL,'subject + 在 + place','Use 在 before the location.','我在学校。','wǒ zài xuéxiào','I am at school.','{"ui":"pattern_card"}'),
('hsk1_c19',1,'example','今天 / 明天 / 昨天',NULL,'today / tomorrow / yesterday','Time expressions often appear near the beginning of the sentence.','我明天去学校。','wǒ míngtiān qù xuéxiào','I will go to school tomorrow.','{"ui":"timeline_card"}'),
('hsk1_c20',1,'grammar','喜欢 / 想 / 会 / 能',NULL,'like / want / know how / be able','These verbs express different attitudes or abilities before another verb/noun.','我想学汉语。','wǒ xiǎng xué Hànyǔ','I want to learn Chinese.','{"ui":"contrast_card"}')
ON CONFLICT(concept_id, card_order) DO NOTHING;

INSERT INTO exercises
(exercise_id,concept_id,exercise_order,exercise_type,prompt,instruction,answer,options,accepted_answers,explanation,target_tokens,error_tags,difficulty)
VALUES
('hsk1_c01_e01','hsk1_c01',1,'meaning_mcq','你好','Choose the meaning.','{"value":"Hello"}','["Hello","Thank you","Goodbye","Sorry"]','[]','你好 means “hello”.','["你好"]','["vocab_meaning"]',1),
('hsk1_c01_e02','hsk1_c01',2,'en_to_zh_mcq','Goodbye','Choose the Chinese expression.','{"value":"再见"}','["你好","谢谢","再见","不客气"]','[]','再见 is the standard beginner expression for goodbye.','["再见"]','["vocab_recall"]',1),
('hsk1_c01_e03','hsk1_c01',3,'fill_blank','A: 你好！ B: ____！','Complete the dialogue.','{"value":"你好"}',NULL,'["你好"]','Return the greeting with 你好.','["你好"]','["dialogue"]',1),
('hsk1_c01_e04','hsk1_c01',4,'dialogue_choice','A: 谢谢！ B: ____','Choose the best reply.','{"value":"不客气"}','["不客气","再见","你好","对不起"]','[]','不客气 is a common reply to 谢谢.','["不客气"]','["dialogue"]',1),

('hsk1_c02_e01','hsk1_c02',1,'fill_blank','我____安娜。','Complete: “My name is Anna.”','{"value":"叫"}',NULL,'["叫"]','Use 叫 before your name.','["叫"]','["self_intro"]',1),
('hsk1_c02_e02','hsk1_c02',2,'reorder','["我","学生","是"]','Put the words in the correct order.','{"tokens":["我","是","学生"]}',NULL,'[]','Basic noun-predicate identity: 我是学生。','["我", "是", "学生"]','["word_order"]',1),
('hsk1_c02_e03','hsk1_c02',3,'translate_to_zh','My name is Li Ming.','Translate into Chinese.','{"value":"我叫李明。"}',NULL,'["我叫李明","我叫李明。"]','Use 我叫 + name.','["我", "叫"]','["self_intro"]',2),
('hsk1_c02_e04','hsk1_c02',4,'dialogue_choice','A: 你叫什么名字？ B: ____','Choose the best answer.','{"value":"我叫王明。"}','["我叫王明。","我是很好。","你叫王明。","再见。"]','[]','Answer a name question with 我叫 + name.','["我", "叫"]','["dialogue"]',1),

('hsk1_c03_e01','hsk1_c03',1,'fill_blank','她____老师。','Choose the missing word.','{"value":"是"}',NULL,'["是"]','Use 是 to link 她 and 老师.','["是"]','["copula"]',1),
('hsk1_c03_e02','hsk1_c03',2,'reorder','["他","学生","是"]','Put the words in order.','{"tokens":["他","是","学生"]}',NULL,'[]','The order is subject + 是 + noun.','["他", "是", "学生"]','["word_order"]',1),
('hsk1_c03_e03','hsk1_c03',3,'en_to_zh_mcq','She is a student.','Choose the correct Chinese sentence.','{"value":"她是学生。"}','["她是学生。","她学生是。","是她学生。","她很学生。"]','[]','Use 她 + 是 + 学生.','["她", "是", "学生"]','["copula", "word_order"]',1),
('hsk1_c03_e04','hsk1_c03',4,'translate_to_zh','I am a teacher.','Translate into Chinese.','{"value":"我是老师。"}',NULL,'["我是老师","我是老师。"]','Use 我是老师。','["我", "是", "老师"]','["copula"]',2),

('hsk1_c04_e01','hsk1_c04',1,'fill_blank','你是学生____？','Make it a yes/no question.','{"value":"吗"}',NULL,'["吗"]','Add 吗 at the end of a statement.','["吗"]','["target_ma"]',1),
('hsk1_c04_e02','hsk1_c04',2,'reorder','["吗","你","老师","是"]','Put the words in order.','{"tokens":["你","是","老师","吗"]}',NULL,'[]','吗 goes at the end.','["吗"]','["target_ma", "word_order"]',1),
('hsk1_c04_e03','hsk1_c04',3,'en_to_zh_mcq','Are you a student?','Choose the sentence that specifically uses 吗.','{"value":"你是学生吗？"}','["你是学生吗？","你是不是学生？","你学生吗是？","吗你是学生？"]','[]','The target pattern is statement + 吗.','["吗"]','["target_ma"]',2),
('hsk1_c04_e04','hsk1_c04',4,'translate_to_zh','Is she a teacher? Use 吗.','Translate using the target grammar.','{"value":"她是老师吗？"}',NULL,'["她是老师吗","她是老师吗？"]','For this exercise, correct meaning alone is not enough; the target is 吗.','["吗", "她", "是", "老师"]','["target_ma", "target_concept_gate"]',2),

('hsk1_c05_e01','hsk1_c05',1,'fill_blank','我是学生。你____？','Complete “What about you?”','{"value":"呢"}',NULL,'["呢"]','Use 呢 to return the topic/question.','["呢"]','["target_ne"]',1),
('hsk1_c05_e02','hsk1_c05',2,'dialogue_choice','A: 我很好。你呢？ B: ____','Choose a natural answer.','{"value":"我也很好。"}','["我也很好。","你呢？","什么？","再见吗？"]','[]','Answer the returned topic naturally.','["呢"]','["dialogue"]',1),
('hsk1_c05_e03','hsk1_c05',3,'reorder','["呢","他"]','Make “What about him?”','{"tokens":["他","呢"]}',NULL,'[]','Pronoun + 呢 forms a short follow-up.','["呢"]','["word_order"]',1),
('hsk1_c05_e04','hsk1_c05',4,'translate_to_zh','I am a teacher. What about you?','Translate into Chinese.','{"value":"我是老师。你呢？"}',NULL,'["我是老师，你呢？","我是老师。你呢？","我是老师。你呢"]','Use 你呢？ for the follow-up.','["呢"]','["target_ne"]',2),

('hsk1_c06_e01','hsk1_c06',1,'fill_blank','这____什么？','Complete the question.','{"value":"是"}',NULL,'["是"]','这是什么？ means “What is this?”','["什么"]','["what_question"]',1),
('hsk1_c06_e02','hsk1_c06',2,'reorder','["什么","是","这"]','Put the words in order.','{"tokens":["这","是","什么"]}',NULL,'[]','Keep 什么 in the position of the unknown noun.','["什么"]','["word_order"]',1),
('hsk1_c06_e03','hsk1_c06',3,'meaning_mcq','什么','Choose the meaning.','{"value":"what"}','["what","who","where","which"]','[]','什么 means “what”.','["什么"]','["vocab_meaning"]',1),
('hsk1_c06_e04','hsk1_c06',4,'translate_to_zh','What is this?','Translate into Chinese.','{"value":"这是什么？"}',NULL,'["这是什么","这是什么？"]','Use 这 + 是 + 什么.','["什么"]','["what_question"]',2),

('hsk1_c07_e01','hsk1_c07',1,'meaning_mcq','谁','Choose the meaning.','{"value":"who"}','["who","what","where","how"]','[]','谁 asks about a person.','["谁"]','["vocab_meaning"]',1),
('hsk1_c07_e02','hsk1_c07',2,'reorder','["谁","她","是"]','Put the words in order.','{"tokens":["她","是","谁"]}',NULL,'[]','谁 occupies the unknown person position.','["谁"]','["word_order"]',1),
('hsk1_c07_e03','hsk1_c07',3,'dialogue_choice','A: 他是谁？ B: ____','Choose the best answer.','{"value":"他是我的老师。"}','["他是我的老师。","他在哪儿？","什么老师？","我是学生吗？"]','[]','A 谁 question expects a person identity.','["谁"]','["dialogue"]',1),
('hsk1_c07_e04','hsk1_c07',4,'translate_to_zh','Who is she?','Translate into Chinese.','{"value":"她是谁？"}',NULL,'["她是谁","她是谁？"]','Use 她 + 是 + 谁.','["谁"]','["who_question"]',2),

('hsk1_c08_e01','hsk1_c08',1,'meaning_mcq','哪儿','Choose the meaning.','{"value":"where"}','["where","who","what","when"]','[]','哪儿 means “where”.','["哪儿"]','["vocab_meaning"]',1),
('hsk1_c08_e02','hsk1_c08',2,'reorder','["哪儿","你","在"]','Put the words in order.','{"tokens":["你","在","哪儿"]}',NULL,'[]','The basic location question is 你在哪儿？','["哪儿", "在"]','["word_order", "location"]',1),
('hsk1_c08_e03','hsk1_c08',3,'fill_blank','你在____？','Complete: “Where are you?”','{"value":"哪儿"}',NULL,'["哪儿","哪里"]','哪儿/哪里 can ask location; this module teaches 哪儿.','["哪儿"]','["where_question"]',1),
('hsk1_c08_e04','hsk1_c08',4,'en_to_zh_mcq','Which book?','Choose the best phrase.','{"value":"哪本书？"}','["哪本书？","哪儿书？","谁本书？","什么在书？"]','[]','哪 combines with a classifier before a noun.','["哪"]','["which_question", "classifier"]',2),

('hsk1_c09_e01','hsk1_c09',1,'meaning_mcq','这 / 那','Choose the best meaning pair.','{"value":"this / that"}','["this / that","who / what","here / where","I / you"]','[]','这 = this; 那 = that.','["这", "那"]','["demonstrative"]',1),
('hsk1_c09_e02','hsk1_c09',2,'fill_blank','____是我的书。（near me）','Choose “this”.','{"value":"这"}',NULL,'["这"]','Use 这 for something near the speaker.','["这"]','["demonstrative"]',1),
('hsk1_c09_e03','hsk1_c09',3,'reorder','["个","那","学生"]','Put the phrase in order.','{"tokens":["那","个","学生"]}',NULL,'[]','Demonstrative + classifier + noun.','["那", "个"]','["word_order", "classifier"]',1),
('hsk1_c09_e04','hsk1_c09',4,'translate_to_zh','That is my teacher.','Translate into Chinese.','{"value":"那是我的老师。"}',NULL,'["那是我的老师","那是我的老师。"]','Use 那 for “that”.','["那"]','["demonstrative"]',2),

('hsk1_c10_e01','hsk1_c10',1,'fill_blank','我____一本书。','Complete: “I have a book.”','{"value":"有"}',NULL,'["有"]','Use 有 for possession.','["有"]','["possession"]',1),
('hsk1_c10_e02','hsk1_c10',2,'en_to_zh_mcq','I do not have money.','Choose the correct sentence.','{"value":"我没有钱。"}','["我没有钱。","我不有钱。","我有不钱。","没有我钱。"]','[]','有 is negated with 没有.','["没有"]','["negation_you"]',1),
('hsk1_c10_e03','hsk1_c10',3,'reorder','["朋友","有","我"]','Put the words in order.','{"tokens":["我","有","朋友"]}',NULL,'[]','Subject + 有 + object.','["有"]','["word_order"]',1),
('hsk1_c10_e04','hsk1_c10',4,'translate_to_zh','She does not have a book.','Translate into Chinese.','{"value":"她没有书。"}',NULL,'["她没有书","她没有书。"]','Use 没有, not 不有.','["没有"]','["negation_you"]',2),

('hsk1_c11_e01','hsk1_c11',1,'fill_blank','我____喝茶。','Complete: “I do not drink tea.”','{"value":"不"}',NULL,'["不"]','Use 不 before the verb 喝.','["不"]','["negation_bu"]',1),
('hsk1_c11_e02','hsk1_c11',2,'reorder','["不","我","学生","是"]','Put the words in order.','{"tokens":["我","不","是","学生"]}',NULL,'[]','不 comes before 是.','["不"]','["word_order", "negation_bu"]',1),
('hsk1_c11_e03','hsk1_c11',3,'en_to_zh_mcq','I do not like coffee.','Choose the correct structure.','{"value":"我不喜欢咖啡。"}','["我不喜欢咖啡。","我喜欢不咖啡。","不我喜欢咖啡。","我没有喜欢咖啡。"]','[]','Use 不 before 喜欢 for a general preference.','["不"]','["negation_bu"]',2),
('hsk1_c11_e04','hsk1_c11',4,'translate_to_zh','I will not go tomorrow.','Translate into Chinese.','{"value":"我明天不去。"}',NULL,'["我明天不去","我明天不去。","明天我不去。","明天我不去"]','Use 不 for a future intention.','["不"]','["negation_bu"]',2),

('hsk1_c12_e01','hsk1_c12',1,'fill_blank','我____书','Complete: “my book”.','{"value":"的"}',NULL,'["的"]','A 的 B marks possession/modification.','["的"]','["de_possession"]',1),
('hsk1_c12_e02','hsk1_c12',2,'reorder','["老师","的","我"]','Make “my teacher”.','{"tokens":["我","的","老师"]}',NULL,'[]','Possessor + 的 + noun.','["的"]','["word_order", "de_possession"]',1),
('hsk1_c12_e03','hsk1_c12',3,'en_to_zh_mcq','her friend','Choose the correct phrase.','{"value":"她的朋友"}','["她的朋友","她朋友的","的她朋友","她是朋友"]','[]','Use 她的 + noun.','["的"]','["de_possession"]',1),
('hsk1_c12_e04','hsk1_c12',4,'translate_to_zh','This is my book.','Translate into Chinese.','{"value":"这是我的书。"}',NULL,'["这是我的书","这是我的书。"]','我的 modifies 书.','["的"]','["de_possession"]',2),

('hsk1_c13_e01','hsk1_c13',1,'fill_blank','天气____好。','Complete the natural beginner sentence.','{"value":"很"}',NULL,'["很"]','很 commonly links the subject and adjective predicate.','["很"]','["adjective_predicate"]',1),
('hsk1_c13_e02','hsk1_c13',2,'reorder','["很","她","高兴"]','Put the words in order.','{"tokens":["她","很","高兴"]}',NULL,'[]','Subject + 很 + adjective.','["很"]','["word_order", "adjective_predicate"]',1),
('hsk1_c13_e03','hsk1_c13',3,'en_to_zh_mcq','The school is big.','Choose the beginner pattern.','{"value":"学校很大。"}','["学校很大。","学校是大。","很学校大。","学校大很。"]','[]','Adjective predicates normally do not use 是 here.','["很"]','["shi_overuse", "adjective_predicate"]',2),
('hsk1_c13_e04','hsk1_c13',4,'translate_to_zh','She is very happy.','Translate into Chinese.','{"value":"她很高兴。"}',NULL,'["她很高兴","她很高兴。"]','Use 她很高兴。','["很"]','["adjective_predicate"]',2),

('hsk1_c14_e01','hsk1_c14',1,'fill_blank','我是学生，她____是学生。','Complete: “She is also a student.”','{"value":"也"}',NULL,'["也"]','也 appears before 是.','["也"]','["ye_word_order"]',1),
('hsk1_c14_e02','hsk1_c14',2,'fill_blank','我们____是学生。','Complete: “We are all students.”','{"value":"都"}',NULL,'["都"]','都 marks the group as all/both.','["都"]','["dou_word_order"]',1),
('hsk1_c14_e03','hsk1_c14',3,'reorder','["也","我","喜欢","茶"]','Put the words in order.','{"tokens":["我","也","喜欢","茶"]}',NULL,'[]','也 normally comes after the subject and before the predicate.','["也"]','["word_order"]',2),
('hsk1_c14_e04','hsk1_c14',4,'translate_to_zh','They are all teachers.','Translate into Chinese.','{"value":"他们都是老师。"}',NULL,'["他们都是老师","他们都是老师。"]','Use 他们 + 都 + 是 + 老师.','["都"]','["dou_word_order"]',2),

('hsk1_c15_e01','hsk1_c15',1,'meaning_mcq','八','Choose the number.','{"value":"8"}','["6","7","8","9"]','[]','八 = 8.','["八"]','["number"]',1),
('hsk1_c15_e02','hsk1_c15',2,'en_to_zh_mcq','three','Choose the Chinese number.','{"value":"三"}','["二","三","五","十"]','[]','三 = three.','["三"]','["number"]',1),
('hsk1_c15_e03','hsk1_c15',3,'fill_blank','九 + 一 = ____','Answer in Chinese.','{"value":"十"}',NULL,'["十"]','九加一等于十.','["十"]','["number"]',1),
('hsk1_c15_e04','hsk1_c15',4,'reorder','["个","三","人"]','Make “three people”.','{"tokens":["三","个","人"]}',NULL,'[]','Number + classifier + noun.','["三", "个"]','["number", "classifier"]',2),

('hsk1_c16_e01','hsk1_c16',1,'fill_blank','你有____个朋友？','Ask “how many friends?”','{"value":"几"}',NULL,'["几"]','几 is natural for a small expected count.','["几"]','["quantity_question"]',1),
('hsk1_c16_e02','hsk1_c16',2,'meaning_mcq','多少','Choose the meaning.','{"value":"how many / how much"}','["how many / how much","who","where","this"]','[]','多少 asks quantity/amount.','["多少"]','["quantity_question"]',1),
('hsk1_c16_e03','hsk1_c16',3,'reorder','["钱","多少","这","？"]','Make “How much is this?” using the given tokens.','{"tokens":["这","多少","钱","？"]}',NULL,'[]','A beginner price question can be 这多少钱？','["多少", "钱"]','["word_order", "quantity_question"]',2),
('hsk1_c16_e04','hsk1_c16',4,'dialogue_choice','A: 你有几个学生？ B: ____','Choose the best answer.','{"value":"我有三个学生。"}','["我有三个学生。","我是学生吗？","学生在哪儿？","我很好。"]','[]','A 几 question expects a number response.','["几", "个"]','["dialogue", "quantity_question"]',1),

('hsk1_c17_e01','hsk1_c17',1,'fill_blank','三____学生','Add the classifier.','{"value":"个"}',NULL,'["个"]','Use 个 between the number and 学生.','["个"]','["classifier"]',1),
('hsk1_c17_e02','hsk1_c17',2,'reorder','["人","个","一"]','Make “one person”.','{"tokens":["一","个","人"]}',NULL,'[]','Number + 个 + noun.','["个"]','["word_order", "classifier"]',1),
('hsk1_c17_e03','hsk1_c17',3,'en_to_zh_mcq','this student','Choose the correct phrase.','{"value":"这个学生"}','["这个学生","这学生个","个这学生","学生这个"]','[]','Demonstrative + 个 + noun.','["个", "这"]','["classifier"]',1),
('hsk1_c17_e04','hsk1_c17',4,'translate_to_zh','three students','Translate into Chinese.','{"value":"三个学生"}',NULL,'["三个学生"]','Use 三 + 个 + 学生.','["个"]','["classifier"]',2),

('hsk1_c18_e01','hsk1_c18',1,'fill_blank','我____学校。','Complete: “I am at school.”','{"value":"在"}',NULL,'["在"]','在 introduces the location.','["在"]','["location"]',1),
('hsk1_c18_e02','hsk1_c18',2,'reorder','["家","他","在"]','Put the words in order.','{"tokens":["他","在","家"]}',NULL,'[]','Subject + 在 + place.','["在"]','["word_order", "location"]',1),
('hsk1_c18_e03','hsk1_c18',3,'en_to_zh_mcq','She is at the hospital.','Choose the correct sentence.','{"value":"她在医院。"}','["她在医院。","她医院在。","在她医院。","她是医院。"]','[]','Use 她 + 在 + 医院.','["在"]','["location"]',1),
('hsk1_c18_e04','hsk1_c18',4,'translate_to_zh','I am in China.','Translate into Chinese.','{"value":"我在中国。"}',NULL,'["我在中国","我在中国。"]','Use 在 before 中国.','["在"]','["location"]',2),

('hsk1_c19_e01','hsk1_c19',1,'meaning_mcq','明天','Choose the meaning.','{"value":"tomorrow"}','["today","tomorrow","yesterday","morning"]','[]','明天 = tomorrow.','["明天"]','["time"]',1),
('hsk1_c19_e02','hsk1_c19',2,'reorder','["去","我","明天","学校"]','Put the words in a natural order.','{"tokens":["我","明天","去","学校"]}',NULL,'[]','A common order is subject + time + verb + place/object.','["明天"]','["word_order", "time"]',2),
('hsk1_c19_e03','hsk1_c19',3,'fill_blank','现在三____。','Complete: “It is 3 o’clock now.”','{"value":"点"}',NULL,'["点"]','Use 点 after the hour number.','["点"]','["clock_time"]',1),
('hsk1_c19_e04','hsk1_c19',4,'translate_to_zh','I will go to school tomorrow.','Translate into Chinese.','{"value":"我明天去学校。"}',NULL,'["我明天去学校","我明天去学校。","明天我去学校。","明天我去学校"]','Both common time placements are accepted.','["明天"]','["time"]',2),

('hsk1_c20_e01','hsk1_c20',1,'fill_blank','我____喝茶。（like）','Complete using “like”.','{"value":"喜欢"}',NULL,'["喜欢"]','喜欢 expresses preference.','["喜欢"]','["preference"]',1),
('hsk1_c20_e02','hsk1_c20',2,'fill_blank','我____学汉语。（want）','Complete using “want”.','{"value":"想"}',NULL,'["想"]','想 + verb expresses intention/desire.','["想"]','["intention"]',1),
('hsk1_c20_e03','hsk1_c20',3,'dialogue_choice','A: 你会说汉语吗？ B: ____','Choose the best answer.','{"value":"我会说一点儿。"}','["我会说一点儿。","我是汉语。","我在汉语。","我有说。"]','[]','会 + verb expresses learned ability.','["会"]','["ability", "dialogue"]',2),
('hsk1_c20_e04','hsk1_c20',4,'translate_to_zh','I want to learn Chinese.','Translate into Chinese.','{"value":"我想学汉语。"}',NULL,'["我想学汉语","我想学汉语。","我想学习汉语。","我想学习汉语"]','Use 想 + 学/学习 + 汉语.','["想"]','["intention"]',2)
ON CONFLICT(exercise_id) DO NOTHING;

INSERT INTO concept_prerequisites(concept_id, prerequisite_id) VALUES
('hsk1_c02','hsk1_c01'),('hsk1_c03','hsk1_c02'),('hsk1_c04','hsk1_c03'),
('hsk1_c05','hsk1_c04'),('hsk1_c06','hsk1_c03'),('hsk1_c07','hsk1_c03'),
('hsk1_c08','hsk1_c06'),('hsk1_c09','hsk1_c03'),('hsk1_c10','hsk1_c03'),
('hsk1_c11','hsk1_c03'),('hsk1_c12','hsk1_c09'),('hsk1_c13','hsk1_c11'),
('hsk1_c14','hsk1_c03'),('hsk1_c16','hsk1_c15'),('hsk1_c17','hsk1_c15'),
('hsk1_c18','hsk1_c08'),('hsk1_c19','hsk1_c15'),('hsk1_c20','hsk1_c11')
ON CONFLICT DO NOTHING;

CREATE VIEW IF NOT EXISTS v_concept_catalog AS
SELECT concept_id, hsk_level, sequence_no, slug, title_zh, title_en,
       concept_type, communicative_goal, grammar_focus, vocabulary_focus,
       difficulty, estimated_minutes, metadata
FROM curriculum_concepts
WHERE is_active = 1
ORDER BY sequence_no;

CREATE VIEW IF NOT EXISTS v_exercise_bank AS
SELECT e.exercise_id, e.concept_id, c.sequence_no, c.title_en,
       e.exercise_order, e.exercise_type, e.prompt, e.prompt_pinyin,
       e.instruction, e.answer, e.options, e.accepted_answers,
       e.explanation, e.target_tokens, e.error_tags, e.difficulty, e.points
FROM exercises e
JOIN curriculum_concepts c ON c.concept_id = e.concept_id
WHERE c.is_active = 1;

-- Flat module view: simple and reliable for FastAPI/Python.
CREATE VIEW IF NOT EXISTS v_teaching_modules AS
SELECT c.concept_id, c.sequence_no, c.title_zh, c.title_en,
       c.communicative_goal, c.grammar_focus, c.vocabulary_focus,
       tc.card_id, tc.card_order, tc.card_type, tc.prompt_zh, tc.pinyin,
       tc.meaning_en, tc.explanation_en, tc.example_zh, tc.example_pinyin,
       tc.example_en, tc.payload
FROM curriculum_concepts c
LEFT JOIN teaching_cards tc ON tc.concept_id = c.concept_id
WHERE c.is_active = 1;

COMMIT;

-- Useful SQLite queries:
-- SELECT * FROM v_concept_catalog ORDER BY sequence_no;
-- SELECT * FROM v_exercise_bank WHERE concept_id='hsk1_c04' ORDER BY RANDOM() LIMIT 3;
-- Search JSON error_tags:
-- SELECT * FROM v_exercise_bank
-- WHERE EXISTS (SELECT 1 FROM json_each(error_tags) WHERE value='word_order')
-- ORDER BY RANDOM() LIMIT 5;
