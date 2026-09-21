import React, { useState, useEffect, useRef } from 'react';
import { Sidebar } from './components/Sidebar.tsx';
import { TopStatusBar } from './components/TopStatusBar.tsx';
import { BottomNav } from './components/BottomNav.tsx';
import { DailyPlanView } from './components/DailyPlanView.tsx';
import { RoadmapView } from './components/RoadmapView.tsx';
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
  const [appError, setAppError] = useState<string | null>(null);
  const activityStartedAt = useRef<number | null>(null);

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

  const refreshRoadmap = async (): Promise<void> => {
    const response = await fetch(`/api/v1/learners/${learnerId}/roadmap`);
    if (!response.ok) throw new Error(await parseApiError(response, 'The roadmap could not be loaded.'));
    const body = await response.json() as { roadmap?: CurriculumConcept[] };
    setConcepts(Array.isArray(body.roadmap) ? body.roadmap : []);
  };

  const acceptProgress = (summary: ProgressSummary): void => {
    setProgressSummary(summary);
    setOverallProgress(summary.goalCompletion);
    setLearnedProgress(summary.learnedProgress);
    setMasteredProgress(summary.masteredProgress);
  };

  const acceptResponse = async (
    data: LearningLoopResponse,
    refreshRoadmapProjection = false,
  ): Promise<void> => {
    if (data.state) acceptLearnerState(data.state);
    if (data.progressSummary) acceptProgress(data.progressSummary);
    setNextAction(data.nextAction);
    if (refreshRoadmapProjection) await refreshRoadmap();
  };

  const currentActivitySeconds = (): number => {
    if (activityStartedAt.current === null) return 0;
    return Math.min(
      86_400,
      Math.max(0, Math.round((Date.now() - activityStartedAt.current) / 1_000)),
    );
  };

  // Fetch initial learner state and curriculum
  useEffect(() => {
    async function init() {
      try {
        const res = await fetch(`/api/v1/learners/${learnerId}`);
        if (res.ok) {
          const data = await res.json();
          setNextAction(data.nextAction);
          if (data.progressSummary) acceptProgress(data.progressSummary);
          acceptLearnerState(data.state as LearnerState);
        }
        await refreshRoadmap();
      } catch (err) {
        setAppError(err instanceof Error ? err.message : 'GoalCoach could not be initialized.');
      } finally {
        setLoading(false);
      }
    }
    init();
  }, [learnerId]);

  // Replanning is an explicit backend event, never a read-only plan fetch.
  const handleRegeneratePlan = async (): Promise<void> => {
    setAppError(null);
    try {
      const data = await dispatchLearningEvent('REPLAN_REQUESTED', {
        reason: 'Learner requested a refreshed daily plan.',
      });
      await acceptResponse(data, true);
    } catch (error) {
      setAppError(error instanceof Error ? error.message : 'Today’s plan could not be refreshed.');
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
    await acceptResponse(data, true);
  };

  const handleStartAgentSession = async (): Promise<void> => {
    setIsTeachingOpen(true);
    setTeachingLoading(true);
    setTeachingError(null);
    setAgentGradingResult(null);
    setAgentReplanned(false);
    try {
      let data = await dispatchLearningEvent('SESSION_STARTED', {});
      const replanned = data.replanned;
      await acceptResponse(data, replanned);
      // Planning and teaching remain separate backend events. If this turn
      // regenerated the plan, request the teaching turn only after it finishes.
      if (!data.teachingAction && data.nextAction === 'teach') {
        data = await dispatchLearningEvent('SESSION_STARTED', {});
        await acceptResponse(data);
      }
      if (!data.teachingAction) {
        throw new Error(
          data.nextAction === 'complete'
            ? 'Today’s plan is complete.'
            : 'No teaching action was returned.',
        );
      }
      setTeachingAction(data.teachingAction);
      setAgentReplanned(replanned || data.replanned);
      activityStartedAt.current = Date.now();
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
      await acceptResponse(data);
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
        time_spent_seconds: currentActivitySeconds(),
      });
      setAgentGradingResult(data.gradingResult ?? null);
      setAgentReplanned(data.replanned);
      await acceptResponse(data, true);
      activityStartedAt.current = Date.now();
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
      const data = await dispatchLearningEvent('SESSION_ENDED', {
        additional_active_seconds: currentActivitySeconds(),
      });
      await acceptResponse(data, true);
      activityStartedAt.current = null;
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
          {appError && (
            <p role="alert" className="mb-5 rounded-2xl bg-rose-50 p-4 text-sm font-bold text-rose-800">
              {appError}
            </p>
          )}
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
            <RoadmapView
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
