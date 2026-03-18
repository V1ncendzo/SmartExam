from rest_framework import serializers
from .models import (
    Exam, Section, Part, Question, Choice,
    ExamSubmission, SectionSubmission, TeacherResponse
)


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'text']  # Do not expose 'is_correct' to students!


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'question_type', 'prompt', 'order', 'marks', 'prep_time_seconds', 'response_time_seconds', 'choices']


class PartSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Part
        fields = ['id', 'title', 'directions', 'passage_text', 'audio_file', 'order', 'questions']


class SectionSerializer(serializers.ModelSerializer):
    parts = PartSerializer(many=True, read_only=True)

    class Meta:
        model = Section
        fields = ['id', 'section_type', 'order', 'time_limit_minutes', 'total_marks', 'parts']


class ExamListSerializer(serializers.ModelSerializer):
    """Lighter serializer for listing exams without full tree."""
    class Meta:
        model = Exam
        fields = ['id', 'title', 'description', 'duration_minutes', 'total_marks', 'created_at']


class ExamDetailSerializer(serializers.ModelSerializer):
    """Full nested tree for when an exam is started."""
    sections = SectionSerializer(many=True, read_only=True)

    class Meta:
        model = Exam
        fields = ['id', 'title', 'description', 'duration_minutes', 'total_marks', 'sections']


# --- SUBMISSION SERIALIZERS ---

class TeacherResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeacherResponse
        fields = ['id', 'question', 'selected_choice', 'text_answer', 'audio_file', 'is_graded']
        read_only_fields = ['is_graded', 'marks_awarded', 'grader_comments', 'ai_feedback']

    def validate(self, data):
        """
        Ensure the response data matches the question type.
        """
        question = data.get('question')
        if not question:
            return data
            
        if question.question_type in ['MCQ', 'TFNG', 'MATCHING'] and not data.get('selected_choice'):
            raise serializers.ValidationError("An objective question must have a selected_choice.")
            
        if question.question_type == 'TEXT_LONG' and not data.get('text_answer'):
            raise serializers.ValidationError("A writing task must have a text_answer.")
            
        if question.question_type == 'AUDIO_REC' and not data.get('audio_file'):
            raise serializers.ValidationError("A speaking task must have an attached audio_file.")
            
        return data


class SectionSubmissionSerializer(serializers.ModelSerializer):
    responses = TeacherResponseSerializer(many=True, read_only=True)

    class Meta:
        model = SectionSubmission
        fields = ['id', 'section', 'start_time', 'time_spent_seconds', 'is_completed', 'responses']
        read_only_fields = ['start_time', 'time_spent_seconds', 'is_completed', 'score']


class ExamSubmissionSerializer(serializers.ModelSerializer):
    section_submissions = SectionSubmissionSerializer(many=True, read_only=True)

    class Meta:
        model = ExamSubmission
        fields = ['id', 'user', 'exam', 'status', 'start_time', 'end_time', 'consolidated_score', 'section_submissions']
        read_only_fields = ['user', 'status', 'start_time', 'end_time', 'consolidated_score']
