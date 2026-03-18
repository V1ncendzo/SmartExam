import logging
from celery import shared_task
from .models import SectionSubmission, TeacherResponse

logger = logging.getLogger(__name__)

@shared_task
def process_subjective_grading(section_submission_id):
    """
    Asynchronous queue for parsing Writing/Speaking questions.
    In a real app, this might send audio files to a Speech-to-Text API,
    or send text essays to an AI model for grammar/fluency checks.
    """
    try:
        submission = SectionSubmission.objects.get(id=section_submission_id)
    except SectionSubmission.DoesNotExist:
        logger.error(f"Submission {section_submission_id} not found.")
        return

    ungraded_responses = submission.responses.filter(
        is_graded=False,
        question__question_type__in=['TEXT_LONG', 'AUDIO_REC']
    )

    for response in ungraded_responses:
        # --- Mock AI Grading Logic ---
        # 1. 'TEXT_LONG' Evaluation
        if response.question.question_type == 'TEXT_LONG':
            word_count = len(response.text_answer.split())
            response.word_count = word_count
            
            # Simple AI mock check: Provide some marks if word count > 50
            if word_count > 50:
                response.marks_awarded = response.question.marks * 0.8  # 80% score
                response.ai_feedback = {"fluency": 0.8, "grammar": 0.7, "comments": "Good length, some grammar issues."}
            else:
                response.marks_awarded = response.question.marks * 0.3
                response.ai_feedback = {"fluency": 0.3, "grammar": 0.4, "comments": "Too short."}
                
            response.is_graded = True
            response.save()
            logger.info(f"Graded TEXT_LONG question for submission {section_submission_id}")

        # 2. 'AUDIO_REC' Evaluation
        elif response.question.question_type == 'AUDIO_REC':
            if response.audio_file:
                # In production: Check file length via ffmpeg, send to Whisper API, etc.
                response.marks_awarded = response.question.marks * 0.9
                response.ai_feedback = {"pronunciation": 0.9, "clarity": 0.8}
            else:
                response.marks_awarded = 0.0
                response.ai_feedback = {"error": "No audio file provided"}
                
            response.is_graded = True
            response.save()
            logger.info(f"Graded AUDIO_REC question for submission {section_submission_id}")

    # After grading subjective answers, finally aggregate the overall section score
    from .services import aggregate_section_score
    aggregate_section_score(submission)
