from django.db import models
from django.db.models import Sum
from .models import SectionSubmission, TeacherResponse, Question

OBJECTIVE_QUESTION_TYPES = ['MCQ', 'TFNG', 'MATCHING']
SUBJECTIVE_QUESTION_TYPES = ['TEXT_LONG', 'AUDIO_REC']

def score_objective_response(teacher_response: TeacherResponse):
    """
    Scores a single objective question (Reading or Listening).
    Immediate evaluation since the answer is deterministic.
    """
    question = teacher_response.question
    
    if question.question_type not in OBJECTIVE_QUESTION_TYPES:
        return  # Pass if subjective
        
    correct_choice = question.choices.filter(is_correct=True).first()
    
    if correct_choice and teacher_response.selected_choice == correct_choice:
        teacher_response.marks_awarded = question.marks
    else:
        teacher_response.marks_awarded = 0.0
        
    teacher_response.is_graded = True
    teacher_response.save()


def check_and_complete_exam(exam_submission):
    """
    Checks if all responses in the exam are fully graded.
    If so, transitions the ExamSubmission from GRADING to COMPLETED.
    """
    if exam_submission.status in ['COMPLETED', 'IN_PROGRESS']:
        return

    # Check for any ungraded subjective responses
    ungraded_responses_exist = TeacherResponse.objects.filter(
        section_submission__exam_submission=exam_submission,
        is_graded=False
    ).exists()

    if not ungraded_responses_exist:
        total_score = exam_submission.section_submissions.aggregate(
            total=Sum('score')
        )['total'] or 0.0
        
        exam_submission.consolidated_score = total_score
        exam_submission.status = 'COMPLETED'
        exam_submission.save()


def aggregate_section_score(section_submission: SectionSubmission):
    """
    Calculates the total score for a section once all questions are graded.
    """
    # Check if all responses in this section have been graded
    total_responses = section_submission.responses.count()
    graded_responses = section_submission.responses.filter(is_graded=True).count()
    
    if total_responses > 0 and total_responses == graded_responses:
        # Sum all the awarded marks for this section
        total_marks = section_submission.responses.aggregate(
            total=Sum('marks_awarded')
        )['total'] or 0.0
        
        section_submission.score = total_marks
        section_submission.save()
        
        # Check if the overall exam is now fully graded
        check_and_complete_exam(section_submission.exam_submission)
        return True
    
    return False


def submit_section(section_submission: SectionSubmission):
    """
    Triggered when a student completes a section.
    1. Synchronously scores objective questions using Django ORM logic.
    2. Dispatches asynchronous Celery tasks for subjective marking (Writing/Speaking).
    """
    from .tasks import process_subjective_grading  # Late import to prevent circular dependency
    
    # 1. Ensure all questions in this section have a TeacherResponse (even if blank)
    questions = Question.objects.filter(part__section=section_submission.section)
    existing_q_ids = section_submission.responses.values_list('question_id', flat=True)
    missing_qs = questions.exclude(id__in=existing_q_ids)
    
    if missing_qs.exists():
        TeacherResponse.objects.bulk_create([
            TeacherResponse(section_submission=section_submission, question=q)
            for q in missing_qs
        ])
    
    responses = section_submission.responses.all()
    has_subjective_questions = False
    
    for response in responses:
        if response.question.question_type in OBJECTIVE_QUESTION_TYPES:
            # Evaluate objective questions instantly
            score_objective_response(response)
        elif response.question.question_type in SUBJECTIVE_QUESTION_TYPES:
            # Mark for async processing
            has_subjective_questions = True
            
    # Mark section as completed by student
    section_submission.is_completed = True
    section_submission.save()
            
    if has_subjective_questions:
        # Pass to Celery queue if we have Writing or Speaking answers
        process_subjective_grading.delay(section_submission.id)
    else:
        # If section only had objective questions (e.g. Reading),
        # we can finalize the section score immediately.
        aggregate_section_score(section_submission)
        
    return section_submission
