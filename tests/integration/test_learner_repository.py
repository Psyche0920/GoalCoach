"""Integration coverage for durable learner aggregate snapshots."""

from pathlib import Path

import pytest

from goalcoach.domain.models import LearnerState, LearningGoal
from goalcoach.infrastructure.persistence import (
    SqlAlchemyLearnerRepository,
    create_learner_schema,
    create_session_factory,
)


@pytest.mark.asyncio
async def test_repository_round_trips_and_replaces_learner_state(tmp_path: Path) -> None:
    # 每次测试使用独立临时 SQLite 文件，避免测试之间相互污染。
    database_path = tmp_path / "learners.db"
    # 使用真实 SQLAlchemy 会话工厂，覆盖实际事务和序列化行为。
    session_factory = create_session_factory(f"sqlite:///{database_path}")
    # 测试不启动 API，因此在这里显式创建 learner_states 表。
    create_learner_schema(session_factory)
    repository = SqlAlchemyLearnerRepository(session_factory)
    state = LearnerState(goal=LearningGoal(title="Complete HSK 1", target_hsk_level=1))

    # 第一次保存走 INSERT，再读取并验证 JSON 可恢复成完整领域模型。
    await repository.save(state)
    loaded = await repository.get(state.learner_id)

    assert loaded == state

    # 创建新聚合；第二次保存应替换同一主键的快照，而非新增一行。
    replacement = state.model_copy(update={"goal_changed": True}, deep=True)
    await repository.save(replacement)
    reloaded = await repository.get(state.learner_id)

    # 确认 UPDATE 结果可持久读取，且新字段值没有丢失。
    assert reloaded is not None
    assert reloaded.goal_changed is True
