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
        return True
    
    return False


def submit_section(section_submission: SectionSubmission):
    """
    Triggered when a student completes a section.
    1. Synchronously scores objective questions using Django ORM logic.
    2. Dispatches asynchronous Celery tasks for subjective marking (Writing/Speaking).
    """
    from .tasks import process_subjective_grading  # Late import to prevent circular dependency
    
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
