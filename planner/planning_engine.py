from datetime import date
from .models import PlanSetting


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