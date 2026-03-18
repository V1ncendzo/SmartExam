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
            
            # Simple AI mock check: Provide some AI suggestions instead of grading
            if word_count > 50:
                response.ai_evaluation_data = {"fluency": 0.8, "grammar": 0.7, "comments": "Good length, some grammar issues."}
            elif word_count > 0:
                response.ai_evaluation_data = {"fluency": 0.3, "grammar": 0.4, "comments": "Too short."}
            else:
                response.ai_evaluation_data = {"error": "No answer provided"}
                
            response.status = 'GRADING'
            response.save()
            logger.info(f"AI processed TEXT_LONG question for submission {section_submission_id}")

        # 2. 'AUDIO_REC' Evaluation
        elif response.question.question_type == 'AUDIO_REC':
            if response.audio_file:
                # In production: Check file length via ffmpeg, send to Whisper API, etc.
                response.ai_evaluation_data = {"pronunciation": 0.9, "clarity": 0.8}
            else:
                response.ai_evaluation_data = {"error": "No audio file provided"}
                
            response.status = 'GRADING'
            response.save()
            logger.info(f"AI processed AUDIO_REC question for submission {section_submission_id}")

    # Subjective answers are NOT fully graded yet. They wait for an Expert in the Dashboard!
    # Therefore, we do NOT call aggregate_section_score here anymore.
