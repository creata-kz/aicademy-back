from pydantic import BaseModel


class QuizPairOut(BaseModel):
    id: int
    question: str
    option_a_icon: str
    option_a_label: str
    option_b_icon: str
    option_b_label: str
    sort_order: int

    model_config = {"from_attributes": True}


class QuizResponseIn(BaseModel):
    quiz_pair_id: int
    selected_option: str  # "a" or "b"


class OnboardingResponsesIn(BaseModel):
    responses: list[QuizResponseIn]


class OnboardingResult(BaseModel):
    archetype: str
    archetype_stats: dict
