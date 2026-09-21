import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar.tsx';
import { TopStatusBar } from './components/TopStatusBar.tsx';
import { BottomNav } from './components/BottomNav.tsx';
import { DailyPlanView } from './components/DailyPlanView.tsx';
import { CurriculumRoadmapView } from './components/CurriculumRoadmapView.tsx';
import { RetentionVisualizer } from './components/RetentionVisualizer.tsx';
import { LearnerProfileDrawer } from './components/LearnerProfileDrawer.tsx';
import { TeachingAgentModal } from './components/TeachingAgentModal.tsx';
import { LearnerState, NextAction, CurriculumConcept, GradingResult, LearningGoal, LearningLoopResponse, TeachingAction, ProgressSummary } from './types.ts';

export function App() {
  const [learnerId] = useState('learner_001');
  const [learnerState, setLearnerState] = useState<LearnerState | null>(null);
  const [overallProgress, setOverallProgress] = useState(0.0);
  const [learnedProgress, setLearnedProgress] = useState(0.0);
  const [masteredProgress, setMasteredProgress] = useState(0.0);
  const [progressSummary, setProgressSummary] = useState<ProgressSummary | null>(null);
  const [nextAction, setNextAction] = useState<NextAction>('teach');
  const [concepts, setConcepts] = useState<CurriculumConcept[]>([]);
  const [activeTab, setActiveTab] = useState<'plan' | 'curriculum' | 'retention'>('plan');

  const [isProfileDrawerOpen, setIsProfileDrawerOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [isTeachingOpen, setIsTeachingOpen] = useState(false);
  const [teachingLoading, setTeachingLoading] = useState(false);
  const [teachingAction, setTeachingAction] = useState<TeachingAction | null>(null);
  const [teachingError, setTeachingError] = useState<string | null>(null);
  const [agentGradingResult, setAgentGradingResult] = useState<GradingResult | null>(null);
  const [agentReplanned, setAgentReplanned] = useState(false);

  const acceptLearnerState = (incoming: LearnerState) => {
    setLearnerState((current) => {
      if ((incoming.stateVersion ?? 0) < (current?.stateVersion ?? 0)) return current;
      return incoming;
    });
  };

  const goalForDisplay: LearningGoal | null = (() => {
    if (!learnerState?.goal) return null;
    return learnerState.goal;
  })();

  const parseApiError = async (response: Response, fallback: string): Promise<string> => {
    try {
      const body = await response.json() as { detail?: string | Array<{ msg?: string }> };
      if (typeof body.detail === 'string') return body.detail;
      if (Array.isArray(body.detail)) return body.detail.map((item) => item.msg).filter(Boolean).join(' ') || fallback;
    } catch {
      // The fallback below is safe for empty and non-JSON responses.
    }
    return fallback;
  };

  const dispatchLearningEvent = async (
    eventType: LearningLoopResponse['eventType'],
    payload: Record<string, unknown>,
  ): Promise<LearningLoopResponse> => {
    const response = await fetch('/api/v1/events', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ event_type: eventType, learner_id: learnerId, payload }),
    });
    if (!response.ok) throw new Error(await parseApiError(response, 'GoalCoach could not complete this request.'));
    return response.json() as Promise<LearningLoopResponse>;
  };

  // Fetch initial learner state and curriculum
  useEffect(() => {
    async function init() {
      try {
        const res = await fetch(`/api/v1/learners/${learnerId}`);
        if (res.ok) {
          const data = await res.json();
          setNextAction(data.nextAction);
          setProgressSummary(data.progressSummary ?? null);
          setOverallProgress(data.progressSummary?.goalCompletion ?? 0);
          setLearnedProgress(data.progressSummary?.learnedProgress ?? 0);
          setMasteredProgress(data.progressSummary?.masteredProgress ?? 0);
          let initialState = data.state as LearnerState;
          const planRes = await fetch(`/api/v1/learners/${learnerId}/today-plan`);
          if (planRes.ok) {
            const plan = await planRes.json();
            initialState = { ...initialState, activePlan: plan };
          }
          acceptLearnerState(initialState);
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
        setLearnerState((current) => current ? { ...current, activePlan: plan } : current);
      }
    } catch (err) {
      console.error('Failed to regenerate plan:', err);
    }
  };

  // Handle goal update
  const handleUpdateGoal = async (updatedGoal: Partial<LearningGoal>) => {
    const title = updatedGoal.title?.trim() || goalForDisplay?.title?.trim();
    const dailyMinutes = updatedGoal.dailyAvailableMinutes ?? goalForDisplay?.dailyAvailableMinutes;
    if (!title) throw new Error('Please describe your learning goal.');
    if (!Number.isInteger(dailyMinutes) || dailyMinutes! < 5 || dailyMinutes! > 120) {
      throw new Error('Daily study time must be a whole number between 5 and 120 minutes.');
    }

    const data = await dispatchLearningEvent('GOAL_CREATED', {
      title,
      target_hsk_level: 1,
      daily_available_minutes: dailyMinutes,
    });
    if (!data.state) throw new Error('The updated learner state was missing from the server response.');
    acceptLearnerState(data.state);
    setNextAction('teach');
  };

  const handleStartAgentSession = async (): Promise<void> => {
    setIsTeachingOpen(true);
    setTeachingLoading(true);
    setTeachingError(null);
    setAgentGradingResult(null);
    setAgentReplanned(false);
    try {
      const data = await dispatchLearningEvent('SESSION_STARTED', {});
      if (!data.teachingAction) throw new Error('No teaching action was returned.');
      setTeachingAction(data.teachingAction);
      if (data.progressSummary) {
        setProgressSummary(data.progressSummary);
        setOverallProgress(data.progressSummary.goalCompletion);
        setLearnedProgress(data.progressSummary.learnedProgress);
        setMasteredProgress(data.progressSummary.masteredProgress);
      }
      if (data.state) acceptLearnerState(data.state);
      setNextAction(data.nextAction);
    } catch (error) {
      setTeachingError(error instanceof Error ? error.message : 'The lesson could not be started.');
    } finally {
      setTeachingLoading(false);
    }
  };

  const handleTeachingHelp = async (query: string): Promise<void> => {
    if (!teachingAction) return;
    setTeachingLoading(true);
    setTeachingError(null);
    setAgentGradingResult(null);
    setAgentReplanned(false);
    try {
      const data = await dispatchLearningEvent('HELP_REQUESTED', {
        concept_id: teachingAction.conceptId,
        current_exercise_id: teachingAction.exercisePayload?.exercise_id,
        learner_query: query,
      });
      if (!data.teachingAction) throw new Error('No alternative explanation was returned.');
      setTeachingAction(data.teachingAction);
      if (data.progressSummary) {
        setProgressSummary(data.progressSummary);
        setOverallProgress(data.progressSummary.goalCompletion);
        setLearnedProgress(data.progressSummary.learnedProgress);
        setMasteredProgress(data.progressSummary.masteredProgress);
      }
      if (data.state) acceptLearnerState(data.state);
      setNextAction(data.nextAction);
    } catch (error) {
      setTeachingError(error instanceof Error ? error.message : 'Coach help is temporarily unavailable.');
    } finally {
      setTeachingLoading(false);
    }
  };

  const handleAgentAnswer = async (answer: string): Promise<void> => {
    const exerciseId = teachingAction?.exercisePayload?.exercise_id;
    const conceptId = teachingAction?.exercisePayload?.concept_id || teachingAction?.conceptId;
    if (!exerciseId || !conceptId) {
      setTeachingError('This lesson does not contain a gradable curriculum exercise.');
      return;
    }
    setTeachingLoading(true);
    setTeachingError(null);
    try {
      const data = await dispatchLearningEvent('ANSWER_SUBMITTED', {
        exercise_id: exerciseId,
        concept_id: conceptId,
        answer,
        time_spent_seconds: 30,
      });
      setAgentGradingResult(data.gradingResult ?? null);
      setAgentReplanned(data.replanned);
      if (data.progressSummary) {
        setProgressSummary(data.progressSummary);
        setOverallProgress(data.progressSummary.goalCompletion);
        setLearnedProgress(data.progressSummary.learnedProgress);
        setMasteredProgress(data.progressSummary.masteredProgress);
      }
      if (data.state) acceptLearnerState(data.state);
      setNextAction(data.nextAction);
    } catch (error) {
      setTeachingError(error instanceof Error ? error.message : 'Your answer could not be checked.');
    } finally {
      setTeachingLoading(false);
    }
  };

  const handleCloseAgentSession = async (): Promise<void> => {
    if (!learnerState?.activeSession) {
      setIsTeachingOpen(false);
      return;
    }
    setTeachingLoading(true);
    setTeachingError(null);
    try {
      const data = await dispatchLearningEvent('SESSION_ENDED', {});
      if (data.state) acceptLearnerState(data.state);
      if (data.progressSummary) {
        setProgressSummary(data.progressSummary);
        setOverallProgress(data.progressSummary.goalCompletion);
        setLearnedProgress(data.progressSummary.learnedProgress);
        setMasteredProgress(data.progressSummary.masteredProgress);
      }
      setNextAction(data.nextAction);
      setIsTeachingOpen(false);
    } catch (error) {
      setTeachingError(error instanceof Error ? error.message : 'The study session could not be closed.');
    } finally {
      setTeachingLoading(false);
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
          onOpenProfile={() => setIsProfileDrawerOpen(true)}
        />

        {/* Main Content View */}
        <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-8 py-6">
          {activeTab === 'plan' && (
            <DailyPlanView
              plan={learnerState?.activePlan || null}
              goal={goalForDisplay}
              concepts={concepts}
              learnerState={learnerState}
              overallProgress={overallProgress}
              onStartStudy={() => {
                void handleStartAgentSession();
              }}
              onUpdateGoal={handleUpdateGoal}
              onRegeneratePlan={handleRegeneratePlan}
            />
          )}

          {activeTab === 'curriculum' && (
            <CurriculumRoadmapView
              concepts={concepts}
              learnerState={learnerState}
              onStartStudy={() => {
                void handleStartAgentSession();
              }}
            />
          )}

          {activeTab === 'retention' && (
            <RetentionVisualizer
              learnerState={learnerState}
              concepts={concepts}
              overallProgress={overallProgress}
              progressSummary={progressSummary}
              onReviewConcept={() => {
                void handleStartAgentSession();
              }}
            />
          )}
        </main>
      </div>

      {/* Mobile Bottom Navigation */}
      <BottomNav
        activeTab={activeTab}
        setActiveTab={setActiveTab}
      />

      {/* Learner Profile Drawer (Triggered by clicking Panda Logo/Name) */}
      <LearnerProfileDrawer
        isOpen={isProfileDrawerOpen}
        onClose={() => setIsProfileDrawerOpen(false)}
        displayName={learnerState?.displayName || 'Ann'}
        goal={goalForDisplay}
        learnedProgress={learnedProgress}
        masteredProgress={masteredProgress}
        onUpdateGoal={handleUpdateGoal}
      />

      <TeachingAgentModal
        isOpen={isTeachingOpen}
        action={teachingAction}
        loading={teachingLoading}
        error={teachingError}
        gradingResult={agentGradingResult}
        replanned={agentReplanned}
        onClose={handleCloseAgentSession}
        onContinue={handleStartAgentSession}
        onRequestHelp={handleTeachingHelp}
        onSubmitAnswer={handleAgentAnswer}
      />
    </div>
  );
}

export default App;
