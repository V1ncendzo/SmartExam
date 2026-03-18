from django.urls import path, include
from rest_framework_nested import routers
from .views import (
    ExamViewSet, ExamSubmissionViewSet, SectionSubmissionViewSet, TeacherResponseViewSet
)

router = routers.DefaultRouter()
router.register(r'exams', ExamViewSet, basename='exam')
router.register(r'submissions', ExamSubmissionViewSet, basename='exam-submission')
router.register(r'section-submissions', SectionSubmissionViewSet, basename='section-submission')
router.register(r'responses', TeacherResponseViewSet, basename='teacher-response')


urlpatterns = [
    path('', include(router.urls)),
]
