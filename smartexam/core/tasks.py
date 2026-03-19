import logging
import json
import os
import requests
from celery import shared_task
from django.conf import settings
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
            response.status = 'AI_PROCESSING'
            response.save()
            
            grade_vstep_writing_with_ai.delay(response.id)
            logger.info(f"Queued TEXT_LONG question {response.id} for AI grading")

        # 2. 'AUDIO_REC' Evaluation
        elif response.question.question_type == 'AUDIO_REC':
            if response.audio_file:
                # In production: Check file length via ffmpeg, send to Whisper API, etc.
                response.ai_evaluation_data = {"pronunciation": 0.9, "clarity": 0.8}
            else:
                response.ai_evaluation_data = {"error": "No audio file provided"}
                
            response.status = 'READY_FOR_GRADING'
            response.save()
            logger.info(f"AI processed AUDIO_REC question for submission {section_submission_id}")

    # Subjective answers are NOT fully graded yet. They wait for an Expert in the Dashboard!
    # Therefore, we do NOT call aggregate_section_score here anymore.

@shared_task
def grade_vstep_writing_with_ai(teacher_response_id):
    try:
        response = TeacherResponse.objects.get(id=teacher_response_id)
    except TeacherResponse.DoesNotExist:
        return

    text_answer = response.text_answer
    if not text_answer or len(text_answer.split()) < 10:
        response.ai_evaluation_data = {
            "error": "Answer too short or missing.",
            "general_summary": "The candidate did not provide enough text to evaluate properly.",
            "task_fulfillment": 0, "coherence": 0, "vocabulary": 0, "grammar": 0,
            "grammar_vocab_errors": []
        }
        response.status = 'READY_FOR_GRADING'
        response.save()
        return

    api_key = os.environ.get("GEMINI_API_KEY", "")
    system_prompt = """You are an expert VSTEP examiner. Grade the following Writing Task 2 essay.
Provide your evaluation STRICTLY as a JSON object matching this schema (no markdown, just raw JSON):
{
  "task_fulfillment": <float 0-10>,
  "coherence": <float 0-10>,
  "vocabulary": <float 0-10>,
  "grammar": <float 0-10>,
  "general_summary": "<overall feedback string>",
  "grammar_vocab_errors": [{"error": "<wrong usage>", "suggestion": "<correction>"}]
}"""

    try:
        if not api_key:
            # Fallback mock when no key is configured
            import time
            time.sleep(2)
            ai_data = {
                "task_fulfillment": 7.5,
                "coherence": 8.0,
                "vocabulary": 7.0,
                "grammar": 6.5,
                "general_summary": "The essay is well-structured but has repetitive vocabulary.",
                "grammar_vocab_errors": [
                    {"error": "informations", "suggestion": "information"},
                    {"error": "is depending", "suggestion": "depends"}
                ]
            }
        else:
            # Call Gemini REST API
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            payload = {
                "system_instruction": {
                    "parts": [{"text": system_prompt}]
                },
                "contents": [
                    {"role": "user", "parts": [{"text": text_answer}]}
                ],
                "generationConfig": {
                    "response_mime_type": "application/json"
                }
            }
            res = requests.post(url, json=payload, timeout=60)
            response_json = res.json()

            if not res.ok or "candidates" not in response_json:
                error_detail = response_json.get("error", {}).get("message", str(response_json))
                logger.error(f"Gemini API error for {teacher_response_id}: {error_detail}")
                raise ValueError(f"Gemini API error: {error_detail}")

            raw_text = response_json["candidates"][0]["content"]["parts"][0]["text"]
            ai_data = json.loads(raw_text)

        response.ai_evaluation_data = ai_data
        response.status = 'READY_FOR_GRADING'
        response.save()
        logger.info(f"AI grading completed for response {teacher_response_id}")
    except Exception as e:
        logger.error(f"AI grading failed for {teacher_response_id}: {e}")
        response.ai_evaluation_data = {"error": f"AI service failed: {str(e)}"}
        response.status = 'READY_FOR_GRADING'
        response.save()

