from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Exam, Section, Part, Question, Choice,
    ExamSubmission, SectionSubmission, TeacherResponse, User
)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active', 'groups')
    
    # Add role to the fieldsets when editing a user
    fieldsets = UserAdmin.fieldsets + (
        ('SmartExam Roles', {'fields': ('role',)}),
    )
    
    # Add role to the form when creating a user
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('SmartExam Roles', {
            'classes': ('wide',),
            'fields': ('role',),
        }),
    )

# --- INLINE CONFIGURATIONS FOR EASY EXAM CREATION ---

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4

class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1

class PartInline(admin.StackedInline):
    model = Part
    extra = 1

class SectionInline(admin.TabularInline):
    model = Section
    extra = 1


# --- EXAM BUILDER ADMINS ---

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'duration_minutes', 'total_marks', 'is_published', 'created_at')
    list_filter = ('is_published', 'created_at')
    search_fields = ('title', 'description')
    inlines = [SectionInline]

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('get_exam_title', 'get_section_type_display', 'order', 'time_limit_minutes', 'total_marks')
    list_filter = ('section_type', 'exam')
    search_fields = ('exam__title',)
    inlines = [PartInline]

    def get_exam_title(self, obj):
        return obj.exam.title
    get_exam_title.short_description = 'Exam'

@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    list_display = ('get_section_detail', 'title', 'order')
    list_filter = ('section__section_type',)
    search_fields = ('title', 'directions', 'passage_text')
    inlines = [QuestionInline]

    def get_section_detail(self, obj):
        return str(obj.section)
    get_section_detail.short_description = 'Section'

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('part', 'question_type', 'order', 'marks')
    list_filter = ('question_type',)
    search_fields = ('prompt',)
    inlines = [ChoiceInline]


# --- SUBMISSION AND GRADING ADMINS ---

@admin.register(ExamSubmission)
class ExamSubmissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'exam', 'status', 'consolidated_score', 'start_time', 'end_time')
    list_filter = ('status', 'exam')
    search_fields = ('user__username', 'user__email', 'exam__title')
    readonly_fields = ('start_time', 'end_time', 'id')

@admin.register(SectionSubmission)
class SectionSubmissionAdmin(admin.ModelAdmin):
    list_display = ('exam_submission', 'section', 'time_spent_seconds', 'score', 'is_completed')
    list_filter = ('is_completed', 'section__section_type')
    search_fields = ('exam_submission__user__username',)

@admin.register(TeacherResponse)
class TeacherResponseAdmin(admin.ModelAdmin):
    list_display = ('get_user', 'question', 'is_graded', 'marks_awarded')
    list_filter = ('is_graded', 'question__question_type')
    search_fields = ('section_submission__exam_submission__user__username', 'text_answer')
    readonly_fields = ('text_answer', 'audio_file', 'selected_choice')
    
    # Grading fields
    fieldsets = (
        ('Student Answer', {
            'fields': ('section_submission', 'question', 'selected_choice', 'text_answer', 'audio_file', 'word_count')
        }),
        ('Grading Section', {
            'fields': ('is_graded', 'marks_awarded', 'grader_comments', 'ai_feedback')
        }),
    )

    def get_user(self, obj):
        return obj.section_submission.exam_submission.user.username
    get_user.short_description = 'Student'
