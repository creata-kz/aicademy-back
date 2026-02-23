from fastapi import APIRouter, Depends
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.quiz_pair import QuizPair, QuizResponse
from app.schemas.onboarding import QuizPairOut, OnboardingResponsesIn, OnboardingResult

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get("/quiz-pairs", response_model=list[QuizPairOut])
async def get_quiz_pairs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(QuizPair).order_by(QuizPair.sort_order))
    pairs = result.scalars().all()
    return [QuizPairOut.model_validate(p) for p in pairs]


@router.post("/responses", response_model=OnboardingResult)
async def submit_responses(
    body: OnboardingResponsesIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Delete old responses
    await db.execute(delete(QuizResponse).where(QuizResponse.user_id == user.id))

    # Save new responses
    for r in body.responses:
        db.add(
            QuizResponse(
                user_id=user.id,
                quiz_pair_id=r.quiz_pair_id,
                selected_option=r.selected_option,
            )
        )

    # Calculate archetype from responses
    archetype, stats = _calculate_archetype(body.responses)
    user.archetype = archetype
    user.archetype_stats = stats

    await db.commit()
    await db.refresh(user)

    return OnboardingResult(archetype=archetype, archetype_stats=stats)


@router.post("/complete")
async def complete_onboarding(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user.onboarding_complete = True
    await db.commit()
    return {"message": "Onboarding completed"}


def _calculate_archetype(responses: list) -> tuple[str, dict]:
    """Simple archetype calculation based on quiz responses."""
    # Map responses to trait scores
    narrative = 50
    visuals = 50
    system = 50

    for r in responses:
        if r.selected_option == "a":
            narrative += 7
            visuals += 3
        else:
            visuals += 7
            system += 5

    # Normalize to roughly 0-100 range
    narrative = min(100, narrative)
    visuals = min(100, visuals)
    system = min(100, system)

    # Determine archetype
    if narrative >= visuals and narrative >= system:
        archetype = "Visual Narrator"
    elif visuals >= narrative and visuals >= system:
        archetype = "Creative Director"
    else:
        archetype = "System Thinker"

    return archetype, {"narrative": narrative, "visuals": visuals, "system": system}
