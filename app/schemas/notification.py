from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class NotificationOut(BaseModel):
    id: UUID
    user_id: UUID
    text: str
    icon: str | None = None
    color: str | None = None
    read: bool
    created_at: datetime

    model_config = {"from_attributes": True}
