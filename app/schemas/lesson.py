from pydantic import BaseModel
from typing import Any


class LessonSummary(BaseModel):
    slug: str
    week_number: int
    lesson_number: int
    title: str
    duration_min: int
    points_for_completion: int
    video_lecturer: str | None = None
    video_lecturer_photo: str | None = None

    model_config = {"from_attributes": True}


class QuizOptionPublic(BaseModel):
    text: str
    is_correct: bool


class QuizQuestionPublic(BaseModel):
    id: str
    text: str
    question_type: str
    options: list[QuizOptionPublic]
    points: int


class QuizPublic(BaseModel):
    pass_score_percent: int
    points_max: int
    max_attempts: int
    questions: list[QuizQuestionPublic]


class LessonSummaryData(BaseModel):
    title: str
    points: list[str]


class AssignmentPublic(BaseModel):
    title: str
    description: str
    assignment_type: str
    submission_type: str
    points_max: int
    steps: list[dict]


class LessonData(BaseModel):
    slug: str
    week_number: int
    lesson_number: int
    title: str
    description: str
    content_type: str
    duration_min: int
    thumbnail_url: str | None = None
    video_url: str | None = None
    video_lecturer: str
    video_lecturer_title: str | None = None
    video_lecturer_photo: str | None = None
    video_lines: list[str]
    points_for_completion: int
    summary: LessonSummaryData | None = None
    quiz: QuizPublic
    assignment: AssignmentPublic

    model_config = {"from_attributes": True}


def strip_quiz_answers(lesson_row: Any) -> dict:
    """Build LessonData dict from DB row, stripping is_correct from quiz options."""
    data = {
        "slug": lesson_row.slug,
        "week_number": lesson_row.week_number,
        "lesson_number": lesson_row.lesson_number,
        "title": lesson_row.title,
        "description": lesson_row.description,
        "content_type": lesson_row.content_type.value if hasattr(lesson_row.content_type, 'value') else lesson_row.content_type,
        "duration_min": lesson_row.duration_min,
        "thumbnail_url": lesson_row.thumbnail_url,
        "video_url": lesson_row.video_url,
        "video_lecturer": lesson_row.video_lecturer,
        "video_lecturer_title": lesson_row.video_lecturer_title,
        "video_lecturer_photo": lesson_row.video_lecturer_photo,
        "video_lines": lesson_row.video_lines or [],
        "points_for_completion": lesson_row.points_for_completion,
        "summary": lesson_row.summary,
        "assignment": lesson_row.assignment or {},
    }

    quiz_raw = lesson_row.quiz or {}
    questions_public = []
    for q in quiz_raw.get("questions", []):
        options_public = [
            {"text": opt["text"], "is_correct": opt.get("is_correct", False)}
            for opt in q.get("options", [])
        ]
        questions_public.append({
            "id": q["id"],
            "text": q["text"],
            "question_type": q["question_type"],
            "options": options_public,
            "points": q["points"],
        })

    data["quiz"] = {
        "pass_score_percent": quiz_raw.get("pass_score_percent", 60),
        "points_max": quiz_raw.get("points_max", 0),
        "max_attempts": quiz_raw.get("max_attempts", 3),
        "questions": questions_public,
    }

    return data
