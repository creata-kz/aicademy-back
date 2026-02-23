from pydantic import BaseModel


class BadgeOut(BaseModel):
    slug: str
    title: str
    emoji: str
    category: str
    trigger_type: str
    trigger_value: dict
    points_reward: int

    model_config = {"from_attributes": True}
