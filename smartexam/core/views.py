from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from .models import (
    Exam, ExamSubmission, SectionSubmission, TeacherResponse, Section
)
from .serializers import (
    ExamListSerializer, ExamDetailSerializer,
    ExamSubmissionSerializer, SectionSubmissionSerializer, TeacherResponseSerializer
)
from .services import submit_section


class ExamViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List published exams and retrieve full exam structures.
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Exam.objects.filter(is_published=True).prefetch_related(
            'sections__parts__questions__choices'
        )

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ExamDetailSerializer
        return ExamListSerializer


class ExamSubmissionViewSet(viewsets.ModelViewSet):
    """
    Manage student exam attempts.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ExamSubmissionSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role in ['ADMIN', 'EXAMINER']:
            return ExamSubmission.objects.all()
        return ExamSubmission.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        
    @action(detail=True, methods=['post'])
    def start_section(self, request, pk=None):
        """
        Starts a section timer for an ongoing exam submission.
        """
        exam_submission = self.get_object()
        section_id = request.data.get('section_id')
        
        if not section_id:
            return Response({"error": "section_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            section = exam_submission.exam.sections.get(id=section_id)
        except Section.DoesNotExist:
            return Response({"error": "Section not found for this exam"}, status=status.HTTP_404_NOT_FOUND)
            
        # Get or create the section submission
        section_sub, created = SectionSubmission.objects.get_or_create(
            exam_submission=exam_submission,
            section=section
        )
        
        serializer = SectionSubmissionSerializer(section_sub)
        return Response(serializer.data, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def finish_exam(self, request, pk=None):
        """
        Finalizes an exam submission.
        """
        exam_submission = self.get_object()
        exam_submission.status = 'GRADING'
        exam_submission.end_time = timezone.now()
        exam_submission.save()
        
        # Check if all sections are graded synchronously, if so mark COMPLETED
        from .services import check_and_complete_exam
        check_and_complete_exam(exam_submission)
        
        return Response({"status": "Exam finished safely and queued for grading."})


class SectionSubmissionViewSet(viewsets.ModelViewSet):
    """
    Handle individual section timers and finalize sections (triggering Celery/Scoring).
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SectionSubmissionSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ['ADMIN', 'EXAMINER']:
            return SectionSubmission.objects.all()
        return SectionSubmission.objects.filter(exam_submission__user=user)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        Finalizes a section (e.g. Reading). Triggers the scoring logics defined in services.py.
        """
        section_submission = self.get_object()
        
        if section_submission.is_completed:
            return Response({"error": "Section already completed"}, status=status.HTTP_400_BAD_REQUEST)
            
        time_spent = request.data.get('time_spent_seconds', 0)
        section_submission.time_spent_seconds = time_spent
        section_submission.save()
        
        # Call core domain logic (sync grading + async celery queue)
        submit_section(section_submission)
        
        return Response({"status": "Section submitted and graded/queued completely."})


class TeacherResponseViewSet(viewsets.ModelViewSet):
    """
    Endpoint mapping student responses to questions.
    Because of high frequency polling (autosaves), this uses simple Create/Update.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TeacherResponseSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ['ADMIN', 'EXAMINER']:
            return TeacherResponse.objects.all()
        return TeacherResponse.objects.filter(section_submission__exam_submission__user=user)

    def create(self, request, *args, **kwargs):
        """
        Uses standard create, but if a response for this section/question already exists, 
        it updates it (upsert behavior) for smooth autosaving.
        """
        section_sub_id = request.data.get('section_submission')
        question_id = request.data.get('question')
        
        existing_response = TeacherResponse.objects.filter(
            section_submission_id=section_sub_id, 
            question_id=question_id
        ).first()
        
        if existing_response:
            serializer = self.get_serializer(existing_response, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data)
            
        return super().create(request, *args, **kwargs)

class GetAIFeedbackView(APIView):
    """
    Returns the AI evaluation payload for a specific response.
    Accessible only to EXAMINER role.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if request.user.role != 'EXAMINER' and not request.user.is_superuser:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
            
        response_obj = get_object_or_404(TeacherResponse, pk=pk)
        
        return Response({
            "status": response_obj.status,
            "ai_evaluation_data": response_obj.ai_evaluation_data
        })

