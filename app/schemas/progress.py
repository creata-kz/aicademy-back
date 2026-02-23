from pydantic import BaseModel
from datetime import datetime


class LessonProgressOut(BaseModel):
    lesson_slug: str
    video_completed: bool
    quiz_completed: bool
    quiz_best_score: int
    quiz_attempts: int
    assignment_completed: bool
    assignment_points: int
    lesson_completed: bool
    total_points_earned: int
    completed_at: datetime | None = None


class WeekProgressOut(BaseModel):
    week_number: int
    lessons_total: int
    lessons_completed: int
    completion_percent: int
    completed: bool


class TrackProgressOut(BaseModel):
    track_slug: str
    total_points: int
    weeks: list[WeekProgressOut]
    badges_earned: list[str]
    current_lesson_slug: str | None = None


class QuizSubmission(BaseModel):
    answers: dict[str, str]  # question_id -> selected option text


class QuizResult(BaseModel):
    score: int  # 0-100
    points_earned: int
    correct_count: int
    total_count: int
    passed: bool


class VideoCompleteResponse(BaseModel):
    points_earned: int


class AssignmentCompleteResponse(BaseModel):
    points_earned: int
