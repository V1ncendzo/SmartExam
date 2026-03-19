import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


class User(AbstractUser):
    ROLE_CHOICES = [
        ('ADMIN', 'Board of Education (Admin)'),
        ('EXAMINER', 'Expert (Examiner)'),
        ('TEACHER', 'Candidate (Teacher)'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='TEACHER')
    
    def save(self, *args, **kwargs):
        """Automatically set superusers to the ADMIN role."""
        if self.is_superuser:
            self.role = 'ADMIN'
        super().save(*args, **kwargs)

class Exam(models.Model):
    """Core Exam definition aligning with VSTEP structure."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(help_text="Total exam duration (e.g., 170 mins for VSTEP)")
    total_marks = models.DecimalField(max_digits=5, decimal_places=2, default=10.0, help_text="Total score out of 10")
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Section(models.Model):
    """VSTEP 4 Sections: Listening, Reading, Writing, Speaking."""
    SECTION_CHOICES = [
        ('LISTENING', 'Listening'),
        ('READING', 'Reading'),
        ('WRITING', 'Writing'),
        ('SPEAKING', 'Speaking'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam = models.ForeignKey(Exam, related_name='sections', on_delete=models.CASCADE)
    section_type = models.CharField(max_length=15, choices=SECTION_CHOICES)
    order = models.PositiveIntegerField(help_text="Typical VSTEP: 1:L, 2:R, 3:W, 4:S")
    time_limit_minutes = models.PositiveIntegerField(help_text="E.g., 40 mins for Listening, 60 mins for Reading")
    total_marks = models.DecimalField(max_digits=5, decimal_places=2, default=10.0)

    class Meta:
        ordering = ['order']
        unique_together = ('exam', 'section_type')

    def __str__(self):
        return f"{self.exam.title} - {self.get_section_type_display()}"


class Part(models.Model):
    """
    Groups questions together. 
    Listening: Audio tracks. Reading: Passages. Writing: Tasks. Speaking: Parts.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    section = models.ForeignKey(Section, related_name='parts', on_delete=models.CASCADE)
    title = models.CharField(max_length=255, blank=True)
    directions = models.TextField(blank=True)
    
    # Used for Reading Section
    passage_text = models.TextField(blank=True)
    
    # Used for Listening Section - Offloaded to Nginx/CDN for high frequency playback
    audio_file = models.FileField(upload_to='exams/media/listening/', blank=True, null=True)
    
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.section} - Part {self.order}"

class Question(models.Model):
    """Individual questions linked to a Part."""
    QUESTION_TYPES = [
        ('MCQ', 'Multiple Choice'),
        ('TFNG', 'True / False / Not Given'),
        ('MATCHING', 'Matching'),
        ('TEXT_LONG', 'Writing Text Area'),
        ('AUDIO_REC', 'Speaking Audio Record'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    part = models.ForeignKey(Part, related_name='questions', on_delete=models.CASCADE)
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    prompt = models.TextField()
    order = models.PositiveIntegerField()
    marks = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    
    # Exclusively for Speaking section
    prep_time_seconds = models.PositiveIntegerField(default=0, help_text="Time to prepare before speaking")
    response_time_seconds = models.PositiveIntegerField(default=0, help_text="Time limit for audio recording")

    class Meta:
        ordering = ['order']
        # Optimization: queries heavily filter by part and list them by order
        indexes = [
            models.Index(fields=['part', 'order']),
        ]

class Choice(models.Model):
    """Used for MCQ, TFNG, Matching."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(Question, related_name='choices', on_delete=models.CASCADE)
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)


# --- SUBMISSION LOGIC ---

class ExamSubmission(models.Model):
    """Tracks a student's entire exam session."""
    STATUS_CHOICES = [
        ('IN_PROGRESS', 'In Progress'),
        ('SUBMITTED', 'Submitted'),
        ('GRADING', 'Grading Queue'),
        ('COMPLETED', 'Completed'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IN_PROGRESS')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    consolidated_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ('user', 'exam')
        # Optimization: quickly find active exams or grading queue backlog
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['user', 'status']),
        ]

class SectionSubmission(models.Model):
    """Tracks time and score for an individual section (e.g. Reading)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam_submission = models.ForeignKey(ExamSubmission, related_name='section_submissions', on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    time_spent_seconds = models.PositiveIntegerField(default=0)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    is_completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('exam_submission', 'section')

class TeacherResponse(models.Model):
    """Granular responses for every question/task in VSTEP."""
    STATUS_CHOICES = [
        ('PENDING', 'Just submitted'),
        ('AI_PROCESSING', 'AI Processing'),
        ('READY_FOR_GRADING', 'Ready for Grading'),
        ('COMPLETED', 'Graded'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    section_submission = models.ForeignKey(SectionSubmission, related_name='responses', on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # 1. Listening / Reading Object Answers (MCQ, TFNG)
    selected_choice = models.ForeignKey(Choice, null=True, blank=True, on_delete=models.SET_NULL)
    
    # 2. Writing Subjective Answer
    text_answer = models.TextField(blank=True)
    word_count = models.PositiveIntegerField(default=0)
    
    # 3. Speaking Audio Answer
    audio_file = models.FileField(upload_to='submissions/speaking/', null=True, blank=True)
    
    # Grading metadata (for Writing/Speaking queued logic)
    is_graded = models.BooleanField(default=False, help_text="Becomes True once AI or Human grades it")
    marks_awarded = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    
    # Detailed VSTEP Criteria (Out of 10)
    task_fulfillment_score = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    coherence_score = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    vocabulary_score = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    grammar_score = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    
    general_feedback = models.TextField(blank=True)
    grader_comments = models.TextField(blank=True) # Legacy for backward compatibility
    
    ai_feedback = models.JSONField(null=True, blank=True, help_text="Stores grammar/fluency metrics from AI agent")
    ai_evaluation_data = models.JSONField(null=True, blank=True, help_text="Detailed AI analysis (errors, suggestions, etc)")

    class Meta:
        unique_together = ('section_submission', 'question')
        # Optimization: Used heavily by Celery workers querying for ungraded records
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['is_graded', 'question']),
        ]
