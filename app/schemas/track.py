from pydantic import BaseModel


class TrackListItem(BaseModel):
    slug: str
    title: str
    icon: str
    color: str
    bg: str
    weeks: str
    is_active: bool

    model_config = {"from_attributes": True}


class TrackData(BaseModel):
    slug: str
    title: str
    description: str
    icon: str
    color: str
    bg: str
    weeks_count: int
    lessons_count: int
    total_points: int
    is_active: bool

    model_config = {"from_attributes": True}
