"""GoalCoach 的确定性掌握度状态归约器和进度汇总引擎。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from goalcoach.domain.models import ConceptProgress, LearnerState, LearningEvent, ProgressSummary


def reduce_concept_progress(
    current: ConceptProgress,
    event: LearningEvent,
    completes_atomic_unit: bool = False,
    is_spaced_review: bool = False,
) -> ConceptProgress:
    """按照 40/40/20 和掌握门槛规则确定性地更新知识点进度。

    Rules:
    1. The 40/40/20 First-Learning Rule:
       learnedPercent = 100 * (0.40 * card + 0.40 * practice + 0.20 * output)
    2. Monotonicity: learnedPercent never decreases.
    3. Mastery Qualification Rule:
       A concept qualifies for Mastered = 100% iff:
       - successful_spaced_retrievals >= 4
       - evidence_days >= 3
       - average_review_quality >= 0.80
       (Immediate retries or multiple attempts on the same calendar day count as only 1 retrieval).
    """
    # 优先使用事件发生时间，缺失时才使用当前 UTC 时间。
    evidence_at = event.started_at or datetime.now(UTC)
    # 用日期而不是时间戳计算“不同学习日”。
    event_day = evidence_at.date()
    # 读取上一次证据日期，用于避免同日重复增加 evidence_days。
    last_day = current.last_reviewed_at.date() if current.last_reviewed_at else None
    # 首次事件或跨日事件才算新的证据日。
    is_distinct_day = (last_day is None) or (last_day != event_day)

    # 第一阶段：根据卡片、练习和输出计算 40/40/20 学习证据。
    evidence = current.learning_evidence.model_copy()
    if completes_atomic_unit:
        # 完成原子单元时，三类证据一次性全部完成。
        evidence.card_completion = 1.0
        evidence.practice_completion = 1.0
        evidence.output_completion = 1.0
    elif not is_spaced_review and event.event_type != "review":
        # 间隔复习事件不重复增加首次学习证据。
        if event.event_type in ("card", "audio"):
            # 看卡片或听音频只完成卡片部分。
            evidence.card_completion = 1.0
        elif event.event_type == "attempt":
            # 练习尝试根据评分通过与否记录 1.0 或 0.5。
            passed = True
            if event.grading_result:
                passed = event.grading_result.get("passed_gates", True)
            evidence.practice_completion = max(evidence.practice_completion, 1.0 if passed else 0.5)
        elif event.event_type == "output":
            # 自由输出根据评分通过与否记录 1.0 或 0.5。
            passed = True
            if event.grading_result:
                passed = event.grading_result.get("passed_gates", True)
            evidence.output_completion = max(evidence.output_completion, 1.0 if passed else 0.5)

    # 将三个证据按 40/40/20 加权，并限制最大值为 100%。
    raw_learned = min(
        100.0,
        100.0
        * (
            0.40 * evidence.card_completion
            + 0.40 * evidence.practice_completion
            + 0.20 * evidence.output_completion
        ),
    )
    # 单调性：学习进度只能保持或增加，不能因新事件倒退。
    learned_percent = max(current.learned_percent, raw_learned)
    evidence_days = current.evidence_days + 1 if is_distinct_day else current.evidence_days

    # 第二阶段：计算本次事件质量并处理间隔复习统计。
    quality = float(event.engagement_score)
    if event.grading_result:
        # 如果存在评分结果，用三个评分维度的平均值作为质量。
        scores = event.grading_result.get("scores")
        if isinstance(scores, dict) and scores:
            quality = float(
                scores.get("grammatical_correctness", 1.0)
                + scores.get("semantic_precision", 1.0)
                + scores.get("pragmatic_appropriateness", 1.0)
            ) / 3.0

    successful_retrievals = current.successful_spaced_retrievals
    avg_review_quality = current.average_review_quality
    review_count = current.review_quality_count

    is_review_event = is_spaced_review or event.event_type == "review"
    if is_review_event:
        # 只有 review 或显式 spaced review 才更新复习指标。
        is_due = (current.next_review_at is not None and current.next_review_at <= evidence_at)
        # 仅在跨日或已到复习日期时计入成功检索次数。
        if (is_distinct_day or is_due) and quality >= 0.75:
            successful_retrievals += 1

        avg_review_quality = ((avg_review_quality * review_count) + quality) / (review_count + 1)
        review_count += 1

    # 第三阶段：应用掌握门槛，避免一次答对就错误标记 mastered。
    qualifies_mastery = (
        successful_retrievals >= 4
        and evidence_days >= 3
        and avg_review_quality >= 0.80
    )
    is_mastered = current.is_mastered or qualifies_mastery

    # 根据成功复习次数计算下一次复习间隔，至少为一天。
    interval = max(1.0, float(successful_retrievals * 2.0))
    next_review = evidence_at + timedelta(days=interval)

    # 根据学习百分比和掌握标志确定展示状态。
    if is_mastered:
        status = "mastered"
    elif learned_percent >= 100.0:
        status = "almost_mastered"
    elif learned_percent > 0.0:
        status = "learning"
    else:
        status = "not_started"

    # mastered 使用满分；普通学习按事件类型增加有限分值。
    if is_mastered:
        mastery_score = 1.0
    elif is_review_event:
        mastery_score = min(1.0, current.mastery_score + 0.25)
    else:
        mastery_score = min(0.35, (learned_percent / 100.0) * 0.35)

    # 返回不可变意义上的新快照，不直接修改输入对象。
    return current.model_copy(
        update={
            "learned_percent": learned_percent,
            "learning_evidence": evidence,
            "evidence_days": evidence_days,
            "successful_spaced_retrievals": successful_retrievals,
            "review_quality_count": review_count,
            "average_review_quality": avg_review_quality,
            "is_mastered": is_mastered,
            "status": status,
            "mastery_score": mastery_score,
            "last_reviewed_at": evidence_at,
            "next_review_at": next_review,
        }
    )


def compute_progress_summary(
    state: LearnerState,
    all_concepts: list[Any] | None = None,
) -> ProgressSummary:
    """根据学习者所有知识点进度计算聚合指标。"""
    # 只读取已有知识点进度，不在汇总函数中改变状态。
    tracked = state.concept_progress
    # 没有显式课程列表时，用已跟踪数量作为分母，至少保持为 1。
    total_curriculum_count = len(all_concepts) if all_concepts else max(len(tracked), 1)

    if not tracked:
        # 没有任何记录时返回全零摘要。
        return ProgressSummary(
            state_version=state.state_version,
            course_coverage=0.0,
            learned_progress=0.0,
            mastered_progress=0.0,
            goal_completion=0.0,
            goal_scope_learned_percent=0.0,
            goal_scope_mastered_percent=0.0,
            communication_outcome_percent=0.0,
            daily_effective_minutes=0.0,
        )

    # 第一部分：计算课程覆盖率、学习进度和掌握进度。
    concepts_started = sum(1 for p in tracked.values() if p.learned_percent > 0)
    course_coverage = min(100.0, round(100.0 * (concepts_started / total_curriculum_count), 1))

    total_learned = sum(p.learned_percent for p in tracked.values())
    learned_progress = min(100.0, round(total_learned / max(len(tracked), 1), 1))

    concepts_mastered = sum(1 for p in tracked.values() if p.is_mastered)
    mastered_progress = min(100.0, round(100.0 * (concepts_mastered / max(len(tracked), 1)), 1))

    # 第二部分：计算目标范围内的掌握分数。
    goal_scope_learned_percent = learned_progress
    total_mastery = sum(p.mastery_score for p in tracked.values())
    goal_scope_mastered_percent = min(100.0, round(100.0 * (total_mastery / max(len(tracked), 1)), 1))

    # 第三部分：根据已通过 blueprint 的数量计算沟通结果。
    passed_blueprints = len(state.passed_blueprint_ids)
    communication_outcome_percent = min(100.0, round(100.0 * (passed_blueprints / 5.0), 1))

    # 综合目标进度权重：学习 45%、掌握 35%、沟通 20%。
    goal_completion = round(
        0.45 * goal_scope_learned_percent
        + 0.35 * goal_scope_mastered_percent
        + 0.20 * communication_outcome_percent
    )

    return ProgressSummary(
        state_version=state.state_version,
        course_coverage=course_coverage,
        learned_progress=learned_progress,
        mastered_progress=mastered_progress,
        goal_completion=float(goal_completion),
        goal_scope_learned_percent=goal_scope_learned_percent,
        goal_scope_mastered_percent=goal_scope_mastered_percent,
        communication_outcome_percent=communication_outcome_percent,
        daily_effective_minutes=0.0,
    )
