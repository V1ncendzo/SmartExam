from django.urls import path
from . import views_expert

urlpatterns = [
    path('dashboard/', views_expert.examiner_dashboard, name='examiner_dashboard'),
    path('grade/<uuid:pk>/', views_expert.examiner_grade_response, name='examiner_grade'),
]
