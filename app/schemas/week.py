from pydantic import BaseModel


class WeekData(BaseModel):
    week_number: int
    title: str
    description: str
    lessons_count: int
    total_points: int
    badge_slug: str
    badge_emoji: str

    model_config = {"from_attributes": True}
