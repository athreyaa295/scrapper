from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Event(BaseModel):
    id: str
    title: str
    registration_link: str
    registration_deadline: str
    deadline_date: Optional[datetime] = None
    event_date: Optional[str] = None
    priority: str = "🟢 LOW PRIORITY"
    source: str
    category: Optional[str] = None
    days_left: Optional[int] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
