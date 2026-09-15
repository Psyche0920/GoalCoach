"""多请求自适应教学会话的应用服务。"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from uuid import UUID

from goalcoach.agents.interfaces import Grader, LearnerRepository
from goalcoach.agents.teaching_agent import next_teaching_action
from goalcoach.agents.tools.retrieval_tools import AgentDeps
from goalcoach.application.teaching_loop import (
    evaluate_session_status,
    update_mastery_from_grade,
)
from goalcoach.domain.models import (
    AnswerSubmission,
    ConceptProgress,
    LearnerState,
    LearningEvent,
    TeachingAction,
    TeachingSession,
    TeachingTurn,
    utc_now,
)
from goalcoach.infrastructure.persistence.repositories import ContentRepository
from goalcoach.infrastructure.retrieval.chroma_service import ChromaService


class TeachingSessionNotFoundError(LookupError):
    """当请求的教学会话不存在时抛出。"""


class InvalidTeachingStateError(RuntimeError):
    """当回答与会话当前等待的动作不匹配时抛出。"""


class TeachingSessionRepository(Protocol):
    """定义教学会话读取与保存边界。"""
    async def get(self, session_id: UUID | str) -> TeachingSession | None: ...
    async def save(self, session: TeachingSession) -> None: ...


@runtime_checkable
class TeachingTransitionRepository(Protocol):
    """定义一次完整教学尝试的原子持久化边界。"""

    async def save_transition(
        self,
        learner: LearnerState,
        event: LearningEvent,
        session: TeachingSession,
    ) -> None: ...


class InMemoryTeachingSessionRepository:
    """适用于单进程 API 的线程安全会话存储。"""

    def __init__(self) -> None:
        # 使用字符串作为键，兼容 UUID 和字符串形式的会话标识。
        self._sessions: dict[str, TeachingSession] = {}
        # 使用异步锁，避免并发请求同时覆盖同一个会话。
        self._lock = asyncio.Lock()

    async def get(self, session_id: UUID | str) -> TeachingSession | None:
        # 读取时加锁，确保拿到一致的快照。
        async with self._lock:
            session = self._sessions.get(str(session_id))
            # 返回深拷贝，防止调用方绕过 save 直接修改仓储内容。
            return session.model_copy(deep=True) if session else None

    async def save(self, session: TeachingSession) -> None:
        # 保存时加锁，保证同一进程内的写入互斥。
        async with self._lock:
            # 深拷贝保存，隔离外部对象的后续变更。
            self._sessions[str(session.id)] = session.model_copy(deep=True)


@dataclass(frozen=True, slots=True)
class TeachingStepResult:
    """一次教学步骤对 API/CLI 暴露的完整结果。"""
    session: TeachingSession
    action: TeachingAction | None
    progress: ConceptProgress | None


TeachingDecision = Callable[
    [AgentDeps, TeachingSession], Awaitable[tuple[TeachingAction, str]]
]


class TeachingSessionService:
    """编排教学决策、评分、掌握度更新和持久化。"""

    def __init__(
        self,
        learner_repository: LearnerRepository,
        session_repository: TeachingSessionRepository,
        content_repository: ContentRepository,
        chroma_service: ChromaService,
        grader: Grader,
        teaching_decision: TeachingDecision = next_teaching_action,
    ) -> None:
        # 保存 learner 仓储，用于读取和保存学习者聚合。
        self._learners = learner_repository
        # 保存 session 仓储，用于保存 pending action 和历史 turn。
        self._sessions = session_repository
        # 保存内容仓储，供检索工具读取课程知识点。
        self._content = content_repository
        # 保存向量检索服务，供 Teaching Agent 获取语境。
        self._chroma = chroma_service
        # 保存可替换的评分器，便于测试和更换模型。
        self._grader = grader
        # 保存可替换的教学决策函数，便于测试和策略演进。
        self._teaching_decision = teaching_decision

    async def start_session(self, learner_id: UUID | str, concept_id: str) -> TeachingStepResult:
        # 先读取学习者，确保教学上下文包含已有掌握度和错误记录。
        learner = await self._learners.get(learner_id)
        if learner is None:
            # 首次学习时创建一个最小合法的学习者聚合。
            learner = LearnerState(learner_id=learner_id)
            await self._learners.save(learner)
        # 创建新的教学会话，并绑定学习者与目标知识点。
        session = TeachingSession(learner_id=learner_id, concept_id=concept_id)
        # 请求 Teaching Agent 选择第一步教学动作。
        action = await self._advance(learner, session)
        # 保存初始动作，尤其是 ask 动作对应的 pending exercise。
        await self._sessions.save(session)
        # 返回动作和当前掌握度给调用方。
        return self._result(learner, session, action)

    async def submit_answer(self, session_id: UUID | str, answer: str) -> TeachingStepResult:
        # 去除首尾空白，并拒绝空答案，保护领域模型边界。
        clean_answer = answer.strip()
        if not clean_answer:
            raise ValueError("Answer cannot be empty.")
        # 读取会话，确认请求的会话仍然存在。
        session = await self._sessions.get(session_id)
        if session is None:
            raise TeachingSessionNotFoundError(str(session_id))
        # 读取会话所属学习者，恢复完整的教学上下文。
        learner = await self._learners.get(session.learner_id)
        if learner is None:
            raise TeachingSessionNotFoundError(f"Learner {session.learner_id}")
        # 只有 pending ask 动作才允许提交答案。
        action = session.pending_action
        if action is None or not action.expected_response or action.exercise is None:
            raise InvalidTeachingStateError("Session has no exercise awaiting an answer.")

        # 将用户文本封装为经过校验的领域提交对象。
        submission = AnswerSubmission(
            learner_id=learner.learner_id,
            exercise_id=action.exercise.id,
            answer=clean_answer,
        )
        # 调用被动评分器，不让评分器决定教学策略。
        outcome = await self._grader.grade(action.exercise, submission)
        # 把本次回答和评分追加到会话历史。
        session.turns.append(TeachingTurn(
            action=action,
            learner_response=clean_answer,
            grading_result=outcome.result,
        ))
        # 清除已消费的 pending action，防止重复提交同一道题。
        session.pending_action = None
        # 构造 Agent 依赖并更新掌握度。
        deps = self._deps(learner)
        event = update_mastery_from_grade(
            deps,
            session,
            str(action.exercise.id),
            outcome.result,
        )
        # 根据评分历史决定会话是否完成或达到尝试上限。
        session.status = evaluate_session_status(session)
        # 如果会话仍在进行，立即生成下一步动作。
        next_action = await self._advance(learner, session) if session.status == "active" else None
        # 更新时间，供持久化和并发诊断使用。
        session.updated_at = utc_now()
        if isinstance(self._sessions, TeachingTransitionRepository):
            # 数据库仓储将 learner、event、session 放入同一个事务。
            await self._sessions.save_transition(learner, event, session)
        else:
            # 内存或简单测试仓储使用顺序保存。
            await self._learners.save(learner)
            await self._sessions.save(session)
        # 返回评分后的掌握度和下一动作。
        return self._result(learner, session, next_action)

    async def next_action(self, session_id: UUID | str) -> TeachingStepResult:
        """在 explain、hint 或 remediation 后推进到下一个动作。"""
        session = await self._sessions.get(session_id)
        if session is None:
            raise TeachingSessionNotFoundError(str(session_id))
        if session.status != "active":
            raise InvalidTeachingStateError("Teaching session has already ended.")
        # 非交互动作没有答案，因此必须确认当前没有 pending exercise。
        if session.pending_action is not None:
            raise InvalidTeachingStateError("The pending exercise requires an answer.")
        # 恢复学习者上下文，供下一次 Agent 决策使用。
        learner = await self._learners.get(session.learner_id)
        if learner is None:
            raise TeachingSessionNotFoundError(f"Learner {session.learner_id}")
        # 请求下一教学动作并保存会话。
        action = await self._advance(learner, session)
        await self._sessions.save(session)
        return self._result(learner, session, action)

    async def _advance(self, learner: LearnerState, session: TeachingSession) -> TeachingAction:
        # 让 Teaching Agent 根据知识点、历史和掌握度选择动作。
        action, _ = await self._teaching_decision(self._deps(learner), session)
        if action.expected_response:
            # ask 动作必须包含练习，保存为 pending 供下一次回答使用。
            if action.exercise is None:
                raise InvalidTeachingStateError("Response action has no exercise.")
            session.pending_action = action
        else:
            # explain/hint/remediate 已完成展示，直接记录到历史。
            session.turns.append(TeachingTurn(action=action))
        session.updated_at = utc_now()
        return action

    def _deps(self, learner: LearnerState) -> AgentDeps:
        # 集中创建 Agent 依赖，避免不同入口构造不一致。
        return AgentDeps(learner, self._content, self._chroma)

    @staticmethod
    def _result(
        learner: LearnerState,
        session: TeachingSession,
        action: TeachingAction | None,
    ) -> TeachingStepResult:
        # 只返回当前知识点的进度，避免暴露无关聚合数据。
        return TeachingStepResult(
            session=session,
            action=action,
            progress=learner.concept_progress.get(session.concept_id),
        )
