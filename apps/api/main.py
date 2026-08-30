from fastapi import FastAPI, HTTPException, status

from goalcoach.domain.models import AnswerSubmission, GradingResult, LearnerState

app = FastAPI(title="GoalCoach API", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/learners/{learner_id}", response_model=LearnerState)
async def get_learner(learner_id: str) -> LearnerState:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"TODO(interface): connect LearnerRepository for {learner_id}",
    )


@app.post("/api/v1/answers", response_model=GradingResult)
async def submit_answer(submission: AnswerSubmission) -> GradingResult:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"TODO(interface): connect learning loop for {submission.exercise_id}",
    )
