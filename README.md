# GoalCoach

GoalCoach 是一个通过终端运行的 HSK1 闭环学习系统。系统保留三个职责明确的
PydanticAI worker：学习计划、教学策略和答案评分；确定性编排器负责事件路由，
SQLite 负责课程内容与学习者状态持久化。

## 运行

1. 安装依赖：`uv sync`
2. 根据 `.env.example` 配置 `.env`
3. 启动交互终端：

```bash
uv run python -m goalcoach.agents.terminal_harness
```

课程数据位于 `data/database1/goalcoach_hsk1_learning.db`，学习状态默认写入根目录的
`goalcoach.db`。系统不依赖 Web、FastAPI、Streamlit、向量检索或 ChromaDB。
