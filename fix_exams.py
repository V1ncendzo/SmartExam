from smartexam.core.models import ExamSubmission
from smartexam.core.services import check_and_complete_exam

stuck_exams = ExamSubmission.objects.filter(status='GRADING')
print(f"Found {stuck_exams.count()} exams in GRADING status.")

for submission in stuck_exams:
    check_and_complete_exam(submission)
    submission.refresh_from_db()
    print(f"Exam {submission.id} is now: {submission.status} with score: {submission.consolidated_score}")
