from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from .models import Course, StudentProfile, UserCourseRating
from .forms import StudySetupForm


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
    return render(request, 'planner/dashboard.html')

@login_required
def study_setup(request):
    if request.method == 'POST':
        form = StudySetupForm(request.POST)
        if form.is_valid():
            request.session['exam_date'] = str(form.cleaned_data['exam_date'])
            request.session['daily_hours'] = str(form.cleaned_data['daily_hours'])
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
        return redirect('dashboard')

    return render(request, 'planner/rate_courses.html', {'courses': courses})