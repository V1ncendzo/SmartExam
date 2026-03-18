from smartexam.core.models import ExamSubmission, TeacherResponse
from smartexam.core.admin import TeacherResponseAdmin
from django.contrib.admin.sites import site

submission = ExamSubmission.objects.filter(status='GRADING').first()
if submission:
    print(f'Found submission {submission.id} in GRADING status.')
    responses = TeacherResponse.objects.filter(section_submission__exam_submission=submission, is_graded=False)
    print(f'Found {responses.count()} ungraded responses.')
    admin_instance = TeacherResponseAdmin(TeacherResponse, site)
    for r in responses:
        r.is_graded = True
        r.marks_awarded = 1.0
        r.save()
        admin_instance.save_model(None, r, None, None)
    
    submission.refresh_from_db()
    print(f'Exam Status is now: {submission.status}')
else:
    print('No grading submissions found.')
