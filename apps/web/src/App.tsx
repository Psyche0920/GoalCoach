import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar.tsx';
import { TopStatusBar } from './components/TopStatusBar.tsx';
import { BottomNav } from './components/BottomNav.tsx';
import { DailyPlanView } from './components/DailyPlanView.tsx';
import { CurriculumRoadmapView } from './components/CurriculumRoadmapView.tsx';
import { RetentionVisualizer } from './components/RetentionVisualizer.tsx';
import { DuolingoExerciseModal } from './components/DuolingoExerciseModal.tsx';
import { PinyinLessonModal } from './components/PinyinLessonModal.tsx';
import { ModernChatDrawer } from './components/ModernChatDrawer.tsx';
import { LearnerProfileDrawer } from './components/LearnerProfileDrawer.tsx';
import { LearnerState, NextAction, CurriculumConcept, GradingResult, LearningGoal } from './types.ts';
import { HSK1_CONCEPTS } from './data/hsk1Curriculum.ts';

export function App() {
  const [learnerId] = useState('learner_001');
  const [learnerState, setLearnerState] = useState<LearnerState | null>(null);
  const [overallProgress, setOverallProgress] = useState(0.0);
  const [learnedProgress, setLearnedProgress] = useState(0.0);
  const [masteredProgress, setMasteredProgress] = useState(0.0);
  const [nextAction, setNextAction] = useState<NextAction>('teach');
  const [concepts, setConcepts] = useState<CurriculumConcept[]>(HSK1_CONCEPTS);
  const [activeTab, setActiveTab] = useState<'plan' | 'curriculum' | 'retention'>('plan');

  const [selectedStudyConceptId, setSelectedStudyConceptId] = useState<string | null>(null);
  const [selectedPinyinConceptId, setSelectedPinyinConceptId] = useState<string | null>(null);
  const [studyMode, setStudyMode] = useState<'review' | 'new' | 'remedial' | 'daily_quiz'>('new');
  const [todayMistakes, setTodayMistakes] = useState<string[]>([]);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isProfileDrawerOpen, setIsProfileDrawerOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  const acceptLearnerState = (incoming: LearnerState) => {
    setLearnerState((current) => {
      if ((incoming.stateVersion ?? 0) < (current?.stateVersion ?? 0)) return current;
      return incoming;
    });
  };

  // Fetch initial learner state and curriculum
  useEffect(() => {
    async function init() {
      try {
        const res = await fetch(`/api/v1/learners/${learnerId}`);
        if (res.ok) {
          const data = await res.json();
          acceptLearnerState(data.state);
          setNextAction(data.nextAction);
          setOverallProgress(data.overallProgress);
          setLearnedProgress(data.progressSummary?.learnedProgress ?? 0);
          setMasteredProgress(data.progressSummary?.masteredProgress ?? 0);
          const planRes = await fetch(`/api/v1/learners/${learnerId}/today-plan`);
          if (planRes.ok) {
            const plan = await planRes.json();
            setLearnerState((current) => current && (plan.stateVersion ?? 0) >= (current.stateVersion ?? 0)
              ? { ...current, activePlan: plan, stateVersion: plan.stateVersion }
              : current);
          }
        }

        const conceptsRes = await fetch('/api/v1/curriculum/concepts');
        if (conceptsRes.ok) {
          const data = await conceptsRes.json();
          if (Array.isArray(data) && data.length > 0) {
            setConcepts(data);
          }
        }
      } catch (err) {
        console.error('Failed to initialize learner state:', err);
      } finally {
        setLoading(false);
      }
    }
    init();
  }, [learnerId]);

  // Handle plan regeneration
  const handleRegeneratePlan = async () => {
    try {
      const res = await fetch(`/api/v1/learners/${learnerId}/today-plan`);
      if (res.ok) {
        const plan = await res.json();
        setLearnerState((current) => current && (plan.stateVersion ?? 0) >= (current.stateVersion ?? 0)
          ? { ...current, activePlan: plan, stateVersion: plan.stateVersion }
          : current);
      }
    } catch (err) {
      console.error('Failed to regenerate plan:', err);
    }
  };

  // Handle goal update
  const handleUpdateGoal = async (updatedGoal: Partial<LearningGoal>) => {
    try {
      const res = await fetch(`/api/v1/learners/${learnerId}/goal`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedGoal),
      });
      if (res.ok) {
        const data = await res.json();
        acceptLearnerState(data.state);
        setNextAction(data.nextAction);
        // Immediately regenerate plan to adapt to new target domain / interests
        const planRes = await fetch(`/api/v1/learners/${learnerId}/plan`, { method: 'POST' });
        if (planRes.ok) {
          const planData = await planRes.json();
          acceptLearnerState(planData.state);
          setNextAction(planData.nextAction);
        }
      }
    } catch (err) {
      console.error('Failed to update goal:', err);
    }
  };

  // Handle submitting answer to structured rubric grader
  const handleSubmitAnswer = async (exerciseId: string, answer: string): Promise<GradingResult | null> => {
    try {
      const res = await fetch('/api/v1/answers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          learner_id: learnerId,
          exercise_id: exerciseId,
          answer,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        acceptLearnerState(data.state);
        setOverallProgress(data.overallProgress);
        setLearnedProgress(data.progressSummary?.learnedProgress ?? 0);
        setMasteredProgress(data.progressSummary?.masteredProgress ?? 0);
        setNextAction(data.nextAction);
        return data.gradingResult;
      }
    } catch (err) {
      console.error('Failed to submit answer:', err);
    }
    return null;
  };

  // Handle completing concept study with audio demonstration & practice
  const handleCompleteConcept = async (conceptId: string, score: number = 100) => {
    try {
      const res = await fetch(`/api/v1/learners/${learnerId}/complete-concept`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ concept_id: conceptId, score, mode: studyMode }),
      });
      if (res.ok) {
        const data = await res.json();
        acceptLearnerState(data.state);
        setOverallProgress(data.overallProgress);
        setLearnedProgress(data.progressSummary?.learnedProgress ?? 0);
        setMasteredProgress(data.progressSummary?.masteredProgress ?? 0);
        setNextAction(data.nextAction);
      }
    } catch (err) {
      console.error('Failed to complete concept:', err);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-50 flex items-center justify-center p-4 select-none">
        <div className="text-center space-y-4">
          <div className="w-12 h-12 border-4 border-zinc-950 border-t-emerald-500 rounded-full animate-spin mx-auto" />
          <h2 className="text-lg font-black text-zinc-950 tracking-tight">Starting GoalCoach...</h2>
          <p className="text-xs text-zinc-500 font-bold">Loading HSK 1 curriculum & spaced repetition path</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-950 flex select-none">
      {/* Desktop Sidebar (Duolingo Style) */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenChat={() => setIsChatOpen(true)}
        onOpenProfile={() => setIsProfileDrawerOpen(true)}
        learnerState={learnerState}
        overallProgress={overallProgress}
        nextAction={nextAction}
      />

      {/* Main Layout Area */}
      <div className="flex-1 flex flex-col min-w-0 pb-20 lg:pb-0">
        {/* Top Status Bar (Duolingo Streak / Energy / Daily Quota) */}
        <TopStatusBar
          learnerState={learnerState}
          overallProgress={overallProgress}
          nextAction={nextAction}
          onRegeneratePlan={handleRegeneratePlan}
          onOpenChat={() => setIsChatOpen(true)}
          onOpenProfile={() => setIsProfileDrawerOpen(true)}
        />

        {/* Main Content View */}
        <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-8 py-6">
          {activeTab === 'plan' && (
            <DailyPlanView
              plan={learnerState?.activePlan || null}
              goal={learnerState?.goal || null}
              concepts={concepts}
              learnerState={learnerState}
              overallProgress={overallProgress}
              todayMistakes={todayMistakes}
              onStartStudy={(conceptId, mode = 'new') => {
                setStudyMode(mode);
                if (conceptId.startsWith('hsk1_p')) {
                  setSelectedPinyinConceptId(conceptId);
                } else {
                  setSelectedStudyConceptId(conceptId);
                }
              }}
              onUpdateGoal={handleUpdateGoal}
              onRegeneratePlan={handleRegeneratePlan}
              onLearningUpdate={(update) => {
                setOverallProgress(update.progressSummary.goalCompletion);
                setLearnedProgress(update.progressSummary.learnedProgress);
                setMasteredProgress(update.progressSummary.masteredProgress);
                setLearnerState((current) => {
                  if (!current || update.stateVersion < (current.stateVersion ?? 0)) return current;
                  const conceptProgress = { ...(current.conceptProgress ?? {}) };
                  for (const affected of update.affectedConcepts) conceptProgress[affected.conceptId] = affected;
                  return { ...current, activePlan: update.plan, conceptProgress, stateVersion: update.stateVersion };
                });
              }}
            />
          )}

          {activeTab === 'curriculum' && (
            <CurriculumRoadmapView
              concepts={concepts}
              learnerState={learnerState}
              goal={learnerState?.goal || null}
              onStartStudy={(conceptId, isPinyin) => {
                const p = learnerState?.conceptProgress?.[conceptId];
                const isAlreadyLearned = (p?.learnedPercent ?? 0) >= 100;
                setStudyMode(isAlreadyLearned ? 'review' : 'new');
                if (isPinyin || conceptId.startsWith('hsk1_p')) {
                  setSelectedPinyinConceptId(conceptId);
                } else {
                  setSelectedStudyConceptId(conceptId);
                }
              }}
              onUpdateGoal={handleUpdateGoal}
              onOpenProfile={() => setIsProfileDrawerOpen(true)}
            />
          )}

          {activeTab === 'retention' && (
            <RetentionVisualizer
              learnerState={learnerState}
              concepts={concepts}
              overallProgress={overallProgress}
              onReviewConcept={(conceptId) => {
                if (conceptId.startsWith('hsk1_p')) {
                  setStudyMode('review');
                  setSelectedPinyinConceptId(conceptId);
                } else {
                  setStudyMode('review');
                  setSelectedStudyConceptId(conceptId);
                }
              }}
            />
          )}
        </main>
      </div>

      {/* Mobile Bottom Navigation */}
      <BottomNav
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenChat={() => setIsChatOpen(true)}
      />

      {/* Pinyin Interactive Lab Modal with Native Fluent Audio Demonstrations & Practice */}
      {selectedPinyinConceptId && (
        <PinyinLessonModal
          conceptId={selectedPinyinConceptId}
          onClose={() => setSelectedPinyinConceptId(null)}
          onComplete={(score) => {
            handleCompleteConcept(selectedPinyinConceptId, score);
          }}
          learnerState={learnerState}
          concepts={concepts}
          onUpdateLearnerState={setLearnerState}
        />
      )}

      {/* Duolingo Practice Modal */}
      {selectedStudyConceptId && (
        <DuolingoExerciseModal
          conceptId={selectedStudyConceptId}
          targetDomain={learnerState?.goal?.targetDomain || 'general'}
          mode={studyMode}
          onClose={() => setSelectedStudyConceptId(null)}
          onSubmitAnswer={handleSubmitAnswer}
          onCompleteConcept={(conceptId) => {
            handleCompleteConcept(conceptId, 100);
          }}
          onRecordMistake={(exerciseId) => {
            setTodayMistakes((prev) => Array.from(new Set([...prev, exerciseId])));
          }}
        />
      )}

      {/* Modern Panda Coach Chat Drawer */}
      <ModernChatDrawer
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        context={{
          currentGoal: learnerState?.goal?.title,
          activePlanItems: learnerState?.activePlan?.items?.map((i) => i.objective),
          errorCount: learnerState?.errorProfile?.length,
        }}
      />

      {/* Learner Profile Drawer (Triggered by clicking Panda Logo/Name) */}
      <LearnerProfileDrawer
        isOpen={isProfileDrawerOpen}
        onClose={() => setIsProfileDrawerOpen(false)}
        displayName={learnerState?.displayName || 'Ann'}
        goal={learnerState?.goal || null}
        learnedProgress={learnedProgress}
        masteredProgress={masteredProgress}
        onUpdateGoal={handleUpdateGoal}
      />
    </div>
  );
}

export default App;
