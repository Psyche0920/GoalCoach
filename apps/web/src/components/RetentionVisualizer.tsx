import React, { useState, useMemo } from 'react';
import { 
  TrendingUp, 
  Calendar, 
  CheckCircle2, 
  Clock, 
  Sparkles, 
  Activity, 
  Award,
  BookOpen
} from 'lucide-react';
import { 
  ResponsiveContainer, 
  ComposedChart, 
  Area, 
  Line, 
  XAxis, 
  YAxis, 
  Tooltip, 
  CartesianGrid, 
  Legend 
} from 'recharts';
import { LearnerState, CurriculumConcept } from '../types.ts';
import { HSK1_TEACHING_CARDS_EXPANDED } from '../data/cards.ts';
import { KnowledgeTree } from './KnowledgeTree.tsx';

interface RetentionVisualizerProps {
  learnerState: LearnerState | null;
  concepts: CurriculumConcept[];
  overallProgress: number;
  onReviewConcept: (conceptId: string, isPinyin?: boolean) => void;
}

export const RetentionVisualizer: React.FC<RetentionVisualizerProps> = ({
  learnerState,
  concepts,
  overallProgress,
  onReviewConcept,
}) => {
  const goalCompletionPercent = Math.round(overallProgress > 1 ? Math.min(100, overallProgress) : Math.max(0, overallProgress) * 100);
  // Timeframe state: default to 'all' (From Day 1 onwards)
  const [timeframe, setTimeframe] = useState<'all' | '30d' | '7d'>('all');

  // 1. 计算每个知识点绑定的教学卡片数量
  const cardCountByConcept = useMemo(() => {
    const map: Record<string, number> = {};
    for (const card of HSK1_TEACHING_CARDS_EXPANDED) {
      if (card.conceptId) {
        map[card.conceptId] = (map[card.conceptId] || 0) + 1;
      }
    }
    return map;
  }, []);

  // 总卡片数
  const totalCards = HSK1_TEACHING_CARDS_EXPANDED.length;

  // 2. 核心进度统计 (Goal Progress Metrics - Strictly preserved)
  const { completedCards, learnedCount, masteredCount } = useMemo(() => {
    let completed = 0;
    let learned = 0;
    let mastered = 0;

    for (const c of concepts) {
      const mastery = learnerState?.mastery?.[c.conceptId];
      const cardCount = cardCountByConcept[c.conceptId] || 1;

      if (mastery && mastery.evidenceCount > 0) {
        learned++;
        if (mastery.masteryScore >= 0.8) {
          mastered++;
          completed += cardCount;
        } else {
          // 按掌握度比例折算已完成卡片
          completed += Math.max(1, Math.round(cardCount * mastery.masteryScore));
        }
      }
    }

    return {
      completedCards: Math.min(totalCards, completed),
      learnedCount: learned,
      masteredCount: mastered,
    };
  }, [concepts, learnerState, cardCountByConcept, totalCards]);

  // 剩余未完成卡片数
  const remainingCards = Math.max(0, totalCards - completedCards);

  // 过去每日学习强度与预计还需天数
  const targetDailyMinutes = learnerState?.goal?.dailyAvailableMinutes || 15;
  const estimatedDailyCardVelocity = Math.max(2, Math.round(targetDailyMinutes / 3.5));

  // 预测还需天数
  const estimatedDaysRemaining = remainingCards === 0 
    ? 0 
    : Math.max(1, Math.ceil(remainingCards / estimatedDailyCardVelocity));

  // 3. 构建从 Day 1 开始完整的历史学习曲线与趋势数据 (From Day 1 to present)
  const { 
    trendData, 
    totalMinutesSinceDay1, 
    totalCardsSinceDay1, 
    activeDaysCount, 
    day1DateString,
    hasActiveHistory 
  } = useMemo(() => {
    const today = new Date();
    const sessions = learnerState?.sessions || [];

    // Find Day 1 timestamp
    let day1Timestamp = today.getTime() - 13 * 86400000; // Default at least 14 days baseline
    if (sessions.length > 0) {
      const earliestSession = sessions.reduce((min, s) => {
        const t = new Date(s.startedAt).getTime();
        return t < min ? t : min;
      }, new Date(sessions[0].startedAt).getTime());
      day1Timestamp = earliestSession;
    }

    const day1Date = new Date(day1Timestamp);
    // Align to start of day
    const day1Start = new Date(day1Date.getFullYear(), day1Date.getMonth(), day1Date.getDate()).getTime();
    const todayStart = new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime();

    // Calculate total days from Day 1 to today
    const totalDaysFromDay1 = Math.max(7, Math.ceil((todayStart - day1Start) / 86400000) + 1);

    // Filter day count based on chosen timeframe
    let daysToInclude = totalDaysFromDay1;
    if (timeframe === '7d') {
      daysToInclude = 7;
    } else if (timeframe === '30d') {
      daysToInclude = Math.min(30, totalDaysFromDay1);
    }

    const data = [];
    const weekdayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    let cumulativeCardsCounter = 0;
    let sumMinutes = 0;
    let sumCards = 0;
    let activeDays = 0;

    for (let i = daysToInclude - 1; i >= 0; i--) {
      const targetDate = new Date(today);
      targetDate.setDate(today.getDate() - i);
      const dateKey = `${targetDate.getMonth() + 1}/${targetDate.getDate()}`;
      const weekday = weekdayNames[targetDate.getDay()];
      const isToday = i === 0;

      const dayIndexFromDay1 = totalDaysFromDay1 - i;

      // Exact day timestamps
      const curDayStart = new Date(targetDate.getFullYear(), targetDate.getMonth(), targetDate.getDate()).getTime();
      const curDayEnd = curDayStart + 86400000;

      let actualMinutes = 0;
      let actualCards = 0;

      for (const s of sessions) {
        const sTime = new Date(s.startedAt).getTime();
        if (sTime >= curDayStart && sTime < curDayEnd) {
          const duration = (new Date(s.endedAt).getTime() - sTime) / 60000;
          actualMinutes += Math.max(1, Math.round(duration));
          actualCards += (s.conceptsCovered?.length || 1) * 2;
        }
      }

      if (actualMinutes > 0 || actualCards > 0) {
        activeDays++;
      }

      sumMinutes += actualMinutes;
      sumCards += actualCards;
      cumulativeCardsCounter += actualCards;

      data.push({
        date: isToday ? `${dateKey} (Today)` : `${dateKey} ${weekday}`,
        shortDate: dateKey,
        dayNumber: `Day ${dayIndexFromDay1}`,
        minutes: actualMinutes,
        cards: actualCards,
        cumulativeCards: cumulativeCardsCounter,
      });
    }

    return {
      trendData: data,
      totalMinutesSinceDay1: sumMinutes,
      totalCardsSinceDay1: sumCards,
      activeDaysCount: activeDays,
      day1DateString: `${day1Date.getFullYear()}-${day1Date.getMonth() + 1}-${day1Date.getDate()}`,
      hasActiveHistory: sumMinutes > 0 || sumCards > 0,
    };
  }, [learnerState, timeframe]);

  return (
    <div className="space-y-8 select-none pb-12">
      {/* =========================================================================
          1. GOAL PROGRESS OVERVIEW (Strictly Unchanged as Requested)
          ========================================================================= */}
      <section className="bg-white rounded-3xl border-2 border-zinc-900 p-6 sm:p-8 shadow-[0_5px_0_#18181b] space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          {/* Goal progress core metrics */}
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 text-emerald-800 text-xs font-black border border-emerald-200">
              <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
              <span>Goal Progress</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-black text-zinc-950 tracking-tight">
              Goal Completion <span className="text-emerald-600 text-3xl sm:text-4xl">{goalCompletionPercent}%</span>
            </h1>
            <p className="text-sm font-semibold text-zinc-600 max-w-xl leading-relaxed">
              {hasActiveHistory ? (
                <>Based on your learning history ({totalMinutesSinceDay1} min studied, {totalCardsSinceDay1} cards completed), </>
              ) : (
                <>At your daily target of {targetDailyMinutes} min/day (~{estimatedDailyCardVelocity} cards/day), </>
              )}
              {estimatedDaysRemaining > 0 ? (
                <>
                  estimated <span className="text-zinc-950 font-black underline decoration-emerald-500 decoration-2">{estimatedDaysRemaining} days</span> remaining to reach full mastery!
                </>
              ) : (
                <span className="text-emerald-700 font-black">All goals completed! Continue daily review to maintain fluency.</span>
              )}
            </p>
          </div>

          {/* Progress badges */}
          <div className="grid grid-cols-2 gap-3 shrink-0 sm:w-80">
            <div className="bg-zinc-50 border-2 border-zinc-200 rounded-2xl p-3.5 text-center">
              <span className="text-xs font-bold text-zinc-500 block mb-1">Cards Completed</span>
              <span className="text-lg font-black text-emerald-700">
                {completedCards} <span className="text-xs text-zinc-400 font-bold">/ {totalCards}</span>
              </span>
            </div>
            <div className="bg-zinc-50 border-2 border-zinc-200 rounded-2xl p-3.5 text-center">
              <span className="text-xs font-bold text-zinc-500 block mb-1">Concepts Learned</span>
              <span className="text-lg font-black text-zinc-900">
                {learnedCount} <span className="text-xs text-zinc-400 font-bold">/ {concepts.length}</span>
              </span>
            </div>
          </div>
        </div>

        {/* Dynamic progress bar */}
        <div className="space-y-2 pt-2">
          <div className="flex justify-between items-center text-xs font-black">
            <span className="text-zinc-500">
              Goal Completion
            </span>
            <span className="text-emerald-700 font-black text-sm">{goalCompletionPercent}%</span>
          </div>
          <div className="w-full bg-zinc-100 rounded-full h-4 overflow-hidden border-2 border-zinc-200 p-0.5">
            <div
              className="h-full rounded-full transition-all duration-700 ease-out bg-gradient-to-r from-emerald-400 via-emerald-500 to-green-600 shadow-xs"
              style={{ width: `${goalCompletionPercent}%` }}
            />
          </div>
        </div>
      </section>

      {/* =========================================================================
          2. STUDY CURVE & TRENDS (From Day 1 to Present)
          ========================================================================= */}
      <section className="bg-white rounded-3xl border-2 border-zinc-900 p-6 sm:p-8 shadow-[0_5px_0_#18181b] space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-emerald-600" />
              <h2 className="text-lg sm:text-xl font-black text-zinc-950">
                Study Curve & Trends
              </h2>
            </div>
            <p className="text-xs font-bold text-zinc-500">
              Tracking your learning velocity from Day 1 ({day1DateString}) to present
            </p>
          </div>

          {/* Timeframe selector: Day 1 (All) / 30 Days / 7 Days */}
          <div className="flex items-center gap-2 flex-wrap">
            <div className="inline-flex bg-zinc-100 p-1 rounded-2xl border border-zinc-200 text-xs font-black">
              <button
                type="button"
                onClick={() => setTimeframe('all')}
                className={`px-3 py-1.5 rounded-xl transition-all cursor-pointer ${
                  timeframe === 'all'
                    ? 'bg-zinc-950 text-white shadow-xs'
                    : 'text-zinc-600 hover:text-zinc-950'
                }`}
              >
                Since Day 1 (All)
              </button>
              <button
                type="button"
                onClick={() => setTimeframe('30d')}
                className={`px-3 py-1.5 rounded-xl transition-all cursor-pointer ${
                  timeframe === '30d'
                    ? 'bg-zinc-950 text-white shadow-xs'
                    : 'text-zinc-600 hover:text-zinc-950'
                }`}
              >
                Past 30 Days
              </button>
              <button
                type="button"
                onClick={() => setTimeframe('7d')}
                className={`px-3 py-1.5 rounded-xl transition-all cursor-pointer ${
                  timeframe === '7d'
                    ? 'bg-zinc-950 text-white shadow-xs'
                    : 'text-zinc-600 hover:text-zinc-950'
                }`}
              >
                Past 7 Days
              </button>
            </div>
          </div>
        </div>

        {/* Aggregate Milestone Badges */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="bg-emerald-50/60 border border-emerald-200 rounded-2xl p-3.5 flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500 text-white flex items-center justify-center font-black shadow-xs">
              <Clock className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[11px] font-bold text-zinc-500 block">Total Study Time</span>
              <span className="text-base font-black text-emerald-950">{totalMinutesSinceDay1} Minutes</span>
            </div>
          </div>

          <div className="bg-sky-50/60 border border-sky-200 rounded-2xl p-3.5 flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-sky-500 text-white flex items-center justify-center font-black shadow-xs">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[11px] font-bold text-zinc-500 block">Cards Completed</span>
              <span className="text-base font-black text-sky-950">{totalCardsSinceDay1} Cards</span>
            </div>
          </div>

          <div className="bg-amber-50/60 border border-amber-200 rounded-2xl p-3.5 flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500 text-white flex items-center justify-center font-black shadow-xs">
              <Award className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[11px] font-bold text-zinc-500 block">Active Study Days</span>
              <span className="text-base font-black text-amber-950">{activeDaysCount} Days Active</span>
            </div>
          </div>
        </div>

        {!hasActiveHistory && (
          <div className="bg-amber-50/80 border border-amber-200/90 rounded-2xl p-3.5 flex items-start sm:items-center gap-3 text-xs text-amber-900 font-bold">
            <Clock className="w-4 h-4 text-amber-600 shrink-0 mt-0.5 sm:mt-0" />
            <span>
              Your daily sessions will dynamically populate this study curve from Day 1 onward.
            </span>
          </div>
        )}

        {/* Recharts curve & trends chart */}
        <div className="w-full h-72 pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart
              data={trendData}
              margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
            >
              <defs>
                <linearGradient id="colorMinutes" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e4e4e7" />
              <XAxis 
                dataKey="shortDate" 
                tickLine={false} 
                axisLine={{ stroke: '#d4d4d8' }}
                tick={{ fontSize: 11, fill: '#71717a', fontWeight: 'bold' }}
              />
              {/* Left Y Axis: Study Time */}
              <YAxis 
                yAxisId="left"
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 11, fill: '#10b981', fontWeight: 'bold' }}
                domain={[0, 'auto']}
              />
              {/* Right Y Axis: Completed Cards */}
              <YAxis 
                yAxisId="right"
                orientation="right"
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 11, fill: '#0284c7', fontWeight: 'bold' }}
                domain={[0, 'auto']}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#09090b',
                  borderRadius: '16px',
                  border: '1px solid #27272a',
                  color: '#ffffff',
                  fontWeight: 'bold',
                  fontSize: '12px',
                  boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.3)',
                }}
                labelStyle={{ color: '#a1a1aa', marginBottom: '4px' }}
                formatter={(value: any, name: string) => {
                  if (name === 'minutes') return [`${value} min`, 'Study Time'];
                  if (name === 'cards') return [`${value} cards`, 'Daily Cards'];
                  return [value, name];
                }}
              />
              <Legend 
                verticalAlign="top" 
                align="right" 
                iconType="circle"
                wrapperStyle={{ paddingBottom: '12px', fontSize: '11px', fontWeight: 'bold' }}
              />
              {/* 面积图：每日时长 */}
              <Area
                yAxisId="left"
                type="monotone"
                dataKey="minutes"
                name="minutes"
                stroke="#10b981"
                strokeWidth={3}
                fillOpacity={1}
                fill="url(#colorMinutes)"
              />
              {/* 折线图：每日卡片数 */}
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="cards"
                name="cards"
                stroke="#0284c7"
                strokeWidth={3}
                dot={{ r: 4, fill: '#0284c7', strokeWidth: 2, stroke: '#ffffff' }}
                activeDot={{ r: 6, fill: '#0284c7' }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </section>

      {/* =========================================================================
          3. KNOWLEDGE TREE (Concept Mastery as Illustrated Book Tree from attached pic)
          ========================================================================= */}
      <KnowledgeTree
        learnerState={learnerState}
        concepts={concepts}
        onSelectConcept={(conceptId, isPinyin) => onReviewConcept(conceptId, isPinyin)}
      />
    </div>
  );
};
