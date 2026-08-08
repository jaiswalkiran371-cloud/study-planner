from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('setup/', views.study_setup, name='study_setup'),
    path('rate/', views.rate_courses, name='rate_courses'),
    path('plan/generate/', views.generate_plan, name='generate_plan'),
    path('plan/<int:plan_id>/day/', views.plan_day_view, name='plan_day_view'),
    path('plan/<int:plan_id>/week/', views.plan_week_view, name='plan_week_view'),
    path('session/<int:session_id>/status/', views.update_session_status, name='update_session_status'),
    path('plan/<int:plan_id>/progress/', views.progress_view, name='progress_view'),
    path('plan/<int:plan_id>/regenerate/', views.regenerate_plan_view, name='regenerate_plan'),
]