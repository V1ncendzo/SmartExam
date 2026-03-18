import random
from django.core.management.base import BaseCommand
from smartexam.core.models import Exam, Section, Part, Question, Choice

class Command(BaseCommand):
    help = 'Seeds the database with a full mock VSTEP Exam'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting VSTEP database seed...'))

        for i in range(1, 4):
            # Create Exam
            exam_title = f"VSTEP Mock Exam {i:02d}"
            exam = Exam.objects.create(
                title=exam_title,
                description="A comprehensive mock exam containing Listening, Reading, Writing, and Speaking sections designed to simulate the real VSTEP test environment.",
                duration_minutes=170,  # 40 + 60 + 60 + 10 = 170
                total_marks=10.0,
                is_published=True
            )
            self.stdout.write(f"Created Exam: {exam.title}")

            # --- 1. LISTENING SECTION ---
            listening = Section.objects.create(
                exam=exam, section_type='LISTENING', order=1, time_limit_minutes=40, total_marks=10.0
            )
            
            # Part 1: Short Announcements (MCQ)
            l_part1 = Part.objects.create(
                section=listening, title="Part 1: Short Announcements",
                directions="Listen to the short announcements and answer the questions.",
                order=1
            )
            q1 = Question.objects.create(
                part=l_part1, question_type='MCQ', prompt="Where is the announcement taking place?",
                order=1, marks=0.28
            )
            Choice.objects.create(question=q1, text="At a train station", is_correct=True)
            Choice.objects.create(question=q1, text="At an airport", is_correct=False)
            Choice.objects.create(question=q1, text="In a supermarket", is_correct=False)
            Choice.objects.create(question=q1, text="At a hospital", is_correct=False)

            # Part 2: Conversations (MCQ)
            l_part2 = Part.objects.create(
                section=listening, title="Part 2: Conversations",
                directions="Listen to the conversation and answer the questions.",
                order=2
            )
            q2 = Question.objects.create(
                part=l_part2, question_type='MCQ', prompt="What are the speakers discussing?",
                order=1, marks=0.28
            )
            Choice.objects.create(question=q2, text="A new project deadline", is_correct=False)
            Choice.objects.create(question=q2, text="Weekend plans", is_correct=False)
            Choice.objects.create(question=q2, text="A software bug", is_correct=True)
            Choice.objects.create(question=q2, text="Dinner reservations", is_correct=False)


            # --- 2. READING SECTION ---
            reading = Section.objects.create(
                exam=exam, section_type='READING', order=2, time_limit_minutes=60, total_marks=10.0
            )
            
            # Part 1: Long Passage
            passage_text = """
            Climate change is one of the most pressing issues of our time. Global temperatures are rising,
            ice caps are melting, and extreme weather events are becoming more frequent. Scientists agree
            that human activities, particularly the burning of fossil fuels, are the primary driver of this
            rapid change. Mitigating its effects will require global cooperation and significant shifts
            towards renewable energy sources.
            """
            r_part1 = Part.objects.create(
                section=reading, title="Part 1: Climate Change",
                directions="Read the passage and answer the questions.",
                passage_text=passage_text.strip(),
                order=1
            )
            
            # MCQ Question
            rq1 = Question.objects.create(
                part=r_part1, question_type='MCQ', prompt="According to the passage, what is the primary cause of climate change?",
                order=1, marks=0.25
            )
            Choice.objects.create(question=rq1, text="Natural climate cycles", is_correct=False)
            Choice.objects.create(question=rq1, text="Human activities", is_correct=True)
            Choice.objects.create(question=rq1, text="Deforestation", is_correct=False)
            Choice.objects.create(question=rq1, text="Volcanic eruptions", is_correct=False)
            
            # TFNG Question
            rq2 = Question.objects.create(
                part=r_part1, question_type='TFNG', prompt="Renewable energy is currently the dominant energy source worldwide.",
                order=2, marks=0.25
            )
            Choice.objects.create(question=rq2, text="True", is_correct=False)
            Choice.objects.create(question=rq2, text="False", is_correct=False)
            Choice.objects.create(question=rq2, text="Not Given", is_correct=True)


            # --- 3. WRITING SECTION ---
            writing = Section.objects.create(
                exam=exam, section_type='WRITING', order=3, time_limit_minutes=60, total_marks=10.0
            )
            
            # Task 1: Letter Writing
            w_part1 = Part.objects.create(
                section=writing, title="Task 1: Email",
                directions="You should spend about 20 minutes on this task.",
                order=1
            )
            Question.objects.create(
                part=w_part1, question_type='TEXT_LONG',
                prompt="You recently visited a restaurant and had a terrible experience. Write an email to the restaurant manager complaining about the service.",
                order=1, marks=3.0
            )

            # Task 2: Essay Writing
            w_part2 = Part.objects.create(
                section=writing, title="Task 2: Essay",
                directions="You should spend about 40 minutes on this task.",
                order=2
            )
            Question.objects.create(
                part=w_part2, question_type='TEXT_LONG',
                prompt="Some people think that university education should be free for everyone. To what extent do you agree or disagree? Write an essay of at least 250 words.",
                order=1, marks=7.0
            )


            # --- 4. SPEAKING SECTION ---
            speaking = Section.objects.create(
                exam=exam, section_type='SPEAKING', order=4, time_limit_minutes=12, total_marks=10.0
            )
            
            # Part 1: Social Interaction
            s_part1 = Part.objects.create(
                section=speaking, title="Part 1: General Introduction",
                directions="Answer the following questions about yourself.",
                order=1
            )
            Question.objects.create(
                part=s_part1, question_type='AUDIO_REC',
                prompt="Let's talk about your hometown. What do you like most about it?",
                order=1, marks=3.0, prep_time_seconds=0, response_time_seconds=60
            )
            
            # Part 2: Solution Discussion
            s_part2 = Part.objects.create(
                section=speaking, title="Part 2: Discussing a Solution",
                directions="You have 1 minute to prepare and 2 minutes to speak.",
                order=2
            )
            Question.objects.create(
                part=s_part2, question_type='AUDIO_REC',
                prompt="You and your friends are planning a weekend trip. The options are: going to the mountains, visiting a beach, or exploring a new city. Which option would you choose and why?",
                order=1, marks=3.0, prep_time_seconds=60, response_time_seconds=120
            )

            # Part 3: Topic Development
            s_part3 = Part.objects.create(
                section=speaking, title="Part 3: Topic Development",
                directions="You have 1 minute to prepare and 3 minutes to speak.",
                order=3
            )
            Question.objects.create(
                part=s_part3, question_type='AUDIO_REC',
                prompt="Topic: The impact of technology on modern education. Discuss its advantages and disadvantages.",
                order=1, marks=4.0, prep_time_seconds=60, response_time_seconds=180
            )

            self.stdout.write(self.style.SUCCESS(f'Successfully seeded VSTEP mock exam with ID: {exam.id}'))
