from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from .models import Course, StudentProfile, UserCourseRating
from .forms import StudySetupForm
from datetime import date
from .planning_engine import calculate_time_budget, PlanValidationError, generate_schedule
from .models import Plan, StudySession
from collections import defaultdict
from datetime import timedelta

def home(request):
    return render(request, 'planner/home.html')


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'planner/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'planner/login.html', {'error': 'Invalid username or password'})
    return render(request, 'planner/login.html')


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def dashboard(request):
    plans = Plan.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'planner/dashboard.html', {'plans': plans})

from .planning_engine import calculate_time_budget, PlanValidationError

@login_required
def study_setup(request):
    if request.method == 'POST':
        form = StudySetupForm(request.POST)
        if form.is_valid():
            try:
                budget = calculate_time_budget(
                    form.cleaned_data['exam_date'],
                    form.cleaned_data['daily_hours']
                )
            except PlanValidationError as e:
                form.add_error(None, str(e))
                return render(request, 'planner/study_setup.html', {'form': form})

            request.session['exam_date'] = str(form.cleaned_data['exam_date'])
            request.session['daily_hours'] = str(form.cleaned_data['daily_hours'])
            request.session['time_budget'] = budget
            course_ids = [c.id for c in form.cleaned_data['courses']]
            request.session['selected_course_ids'] = course_ids
            return redirect('rate_courses')
    else:
        form = StudySetupForm()
    return render(request, 'planner/study_setup.html', {'form': form})


@login_required
def rate_courses(request):
    course_ids = request.session.get('selected_course_ids', [])
    courses = Course.objects.filter(id__in=course_ids)

    if request.method == 'POST':
        for course in courses:
            rating = request.POST.get(f'rating_{course.id}')
            UserCourseRating.objects.update_or_create(
                user=request.user, course=course,
                defaults={'rating': rating}
            )
        return redirect('generate_plan')

    return render(request, 'planner/rate_courses.html', {'courses': courses})


@login_required
def generate_plan(request):
    exam_date = date.fromisoformat(request.session['exam_date'])
    daily_hours = float(request.session['daily_hours'])
    course_ids = request.session.get('selected_course_ids', [])
    courses = Course.objects.filter(id__in=course_ids)

    plan = Plan.objects.create(
        user=request.user, start_date=date.today(),
        exam_date=exam_date, daily_hours=daily_hours
    )

    # NOTE: for now this schedules ONE course at a time using the full
    # daily hours each, run sequentially. True multi-course interleaving
    # (Section 13.4 fairness) comes in a later day once you have 2+ courses
    # loaded to actually test it against.
    current_start = date.today()
    for course in courses:
        rating_obj = UserCourseRating.objects.get(user=request.user, course=course)
        schedule = generate_schedule(
            course, student_rating=rating_obj.rating,
            exam_date=exam_date, daily_hours=daily_hours,
            start_date=current_start
        )
        for s in schedule:
            StudySession.objects.create(
                plan=plan, topic=s['topic'], date=s['date'],
                duration=s['duration'], session_type='learning'
            )

    return redirect('plan_day_view', plan_id=plan.id)

@login_required
def plan_day_view(request, plan_id):
    plan = Plan.objects.get(id=plan_id, user=request.user)
    sessions = StudySession.objects.filter(plan=plan).order_by('date')

    grouped = defaultdict(list)
    for s in sessions:
        grouped[s.date].append(s)

    return render(request, 'planner/plan_day_view.html', {
        'plan': plan, 'grouped': dict(sorted(grouped.items()))
    })


@login_required
def plan_week_view(request, plan_id):
    plan = Plan.objects.get(id=plan_id, user=request.user)
    sessions = StudySession.objects.filter(plan=plan).order_by('date')

    grouped = defaultdict(list)
    for s in sessions:
        # Week number relative to plan start (week 1, week 2, ...)
        days_in = (s.date - plan.start_date).days
        week_num = (days_in // 7) + 1
        grouped[week_num].append(s)

    return render(request, 'planner/plan_week_view.html', {
        'plan': plan, 'grouped': dict(sorted(grouped.items()))
    })