from datetime import date
from .models import PlanSetting
from .models import Topic, PYQQuestion, PlanSetting


def calculate_difficulty_score(student_rating):
    """Section 11.4: difficulty = 10 - rating"""
    if not 0 <= student_rating <= 10:
        raise ValueError("Rating must be between 0 and 10.")
    return 10 - student_rating


def calculate_frequency_score(topic):
    """
    Section 12.1: how many distinct papers this topic appeared in,
    scaled to 0-10 relative to total papers available for the course.
    """
    total_papers = PYQQuestion.objects.filter(course=topic.course).values('term').distinct().count()
    papers_with_topic = PYQQuestion.objects.filter(topic=topic).values('term').distinct().count()

    if total_papers == 0:
        return 0
    return round((papers_with_topic / total_papers) * 10, 1)


def calculate_priority_score(topic, student_rating, plan_setting=None):
    """Section 12: weighted combination of importance, difficulty, frequency."""
    settings = plan_setting or PlanSetting.objects.first()
    difficulty = calculate_difficulty_score(student_rating)
    frequency = calculate_frequency_score(topic)

    priority = (
        float(settings.importance_weight) * float(topic.importance)
        + float(settings.difficulty_weight) * difficulty
        + float(settings.frequency_weight) * frequency
    )
    return round(priority, 2)

class PlanValidationError(Exception):
    pass


def calculate_time_budget(exam_date, daily_hours, today=None):
    """
    Returns a dict with study_days, total_hours, revision_hours, learning_hours.
    Mirrors Section 11.3 of the project spec.
    """
    if today is None:
        today = date.today()

    if exam_date <= today:
        raise PlanValidationError("Exam date must be in the future.")

    if daily_hours <= 0:
        raise PlanValidationError("Daily available hours must be greater than zero.")

    study_days = (exam_date - today).days
    total_hours = study_days * float(daily_hours)

    settings = PlanSetting.objects.first()
    revision_percent = float(settings.revision_percent) if settings else 20.0

    revision_hours = total_hours * (revision_percent / 100)
    learning_hours = total_hours - revision_hours

    return {
        'study_days': study_days,
        'total_hours': round(total_hours, 2),
        'revision_hours': round(revision_hours, 2),
        'learning_hours': round(learning_hours, 2),
        'revision_percent': revision_percent,
    }
