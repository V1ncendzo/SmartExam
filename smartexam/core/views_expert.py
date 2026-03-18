from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Avg
from .decorators import examiner_required
from .models import TeacherResponse
from .services import aggregate_section_score

@examiner_required
def examiner_dashboard(request):
    """
    Expert Grading Dashboard. Shows a list of all PENDING or GRADING submissions
    for TEXT_LONG and AUDIO_REC.
    """
    pending_responses = TeacherResponse.objects.filter(
        status__in=['PENDING', 'GRADING'],
        question__question_type__in=['TEXT_LONG', 'AUDIO_REC']
    ).select_related('question__part', 'section_submission__exam_submission__user').order_by('status', 'section_submission__start_time')

    context = {
        'responses': pending_responses
    }
    return render(request, 'core/examiner_dashboard.html', context)


@examiner_required
def examiner_grade_response(request, pk):
    """
    Detail view where Expert sees the response and a Grading Form.
    """
    response = get_object_or_404(TeacherResponse, pk=pk)

    if request.method == 'POST':
        task_fulfillment_score = float(request.POST.get('task_fulfillment_score', 0))
        coherence_score = float(request.POST.get('coherence_score', 0))
        vocabulary_score = float(request.POST.get('vocabulary_score', 0))
        grammar_score = float(request.POST.get('grammar_score', 0))
        general_feedback = request.POST.get('general_feedback', '')

        response.task_fulfillment_score = task_fulfillment_score
        response.coherence_score = coherence_score
        response.vocabulary_score = vocabulary_score
        response.grammar_score = grammar_score
        response.general_feedback = general_feedback

        # Calculate average
        avg_score = (task_fulfillment_score + coherence_score + vocabulary_score + grammar_score) / 4.0
        response.marks_awarded = avg_score
        
        response.status = 'COMPLETED'
        response.is_graded = True
        response.save()
        
        # Trigger ripple aggregation
        aggregate_section_score(response.section_submission)
        
        return redirect('examiner_dashboard')

    context = {
        'response': response
    }
    return render(request, 'core/examiner_grade.html', context)
