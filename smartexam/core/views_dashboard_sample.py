from django.shortcuts import render
from .decorators import teacher_required, examiner_required
from .models import ExamSubmission

@teacher_required
def teacher_evaluation_dashboard(request):
    """
    Evaluation Dashboard for the Candidate (The Teacher taking the test).
    Teachers can only see their own exam results to ensure fairness and privacy.
    """
    # Security Logic: Filter exclusively by the logged-in user
    submissions = ExamSubmission.objects.filter(user=request.user).order_by('-end_time')
    
    return render(request, 'core/teacher_dashboard.html', {
        'submissions': submissions
    })


@examiner_required
def examiner_grading_dashboard(request):
    """
    Grading Dashboard for the Expert (The Examiner).
    Examiners can see all exams that are currently queued for grading,
    but they should not be able to modify the core 'Question Bank'.
    """
    # Fetch all submissions waiting for subjective grading
    submissions = ExamSubmission.objects.filter(status='GRADING').order_by('end_time')
    
    # In a real app, you would pass only anonymized data here
    # e.g. excluding user name/details from the template context
    
    return render(request, 'core/examiner_dashboard.html', {
        'submissions': submissions
    })
