from fastapi import status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db.redis import add_test_result_to_redis
from quiz.schemas import ResultTestSchema, ResultData
from utils.rating_calculation import get_rating


class QuestionCrud:
    async def create_with_answer(self, db: AsyncSession, data):
        from quiz.models.models import AnswerModel

        await self.create(db)

        for answer in data:
            new_answer = AnswerModel(answer=answer.answer, id_question=self.id, is_correct=answer.is_correct)

            await new_answer.create(db)

        await db.refresh(self)

    async def update_with_answers(self, db, data):
        from quiz.models.models import AnswerModel

        await self.update(db, {'question': data.question})

        for answer in self.answers:
            await answer.delete(db)

        for answer in data.answers:
            new_answer = AnswerModel(answer=answer.answer, id_question=self.id, is_correct=answer.is_correct)

            await new_answer.create(db)

        await db.refresh(self)


class QuizCrud:
    async def create_with_questions(self, db: AsyncSession, data):
        from quiz.models.models import QuestionModel

        await self.create(db)

        for question in data.questions:
            new_question = QuestionModel(question=question.question, id_quiz=self.id)

            await new_question.create_with_answer(db, question.answers)

    async def add_question(self, db: AsyncSession, data):
        from quiz.models.models import QuestionModel

        new_question = QuestionModel(question=data.question, id_quiz=self.id)

        await new_question.create_with_answer(db, data.answers)

        await db.refresh(self)

    def get_question_by_id(self, id: int):
        return next((question for question in self.questions if question.id == id), None)

    def get_correct_answer_for_question(self, number: int) -> list:
        question = self.questions[number]

        return [i for i, answer in enumerate(question.answers) if answer.is_correct]

    def add_text_to_answers(self, answers: list) -> list:
        return [
            [f"{item}. {self.questions[i].answers[j].answer}" for j, item in enumerate(answer)]
            for i, answer in enumerate(answers)
        ]

    def validate_answers(self, answers: list):
        # Checking for correlation between the number of answers to questions and the questions themselves
        if len(answers) != len(self.questions):
            detail = 'The number of answers must be equal to the number of questions'
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

        for i, answer in enumerate(answers):
            # Checking the number of answers to a question
            if len(answer) > len(self.questions[i].answers) or len(answer) == 0:
                detail = f'Error entering answers for a question {i}'
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

            # Checking for recurring issues
            if len(answer) != len(set(answer)):
                detail = f'Question {i} repeats the answers'
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

            # Checking if the answer is correct
            for j, item in enumerate(answer):
                if item >= len(self.questions[i].answers) or item < 0:
                    detail = f'Error entering answers for a question {i} answer {j}'
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    async def pass_test(self, db: AsyncSession, test_user, answers: list) -> ResultTestSchema:
        from quiz.models.models import ResultTestModel

        self.validate_answers(answers)

        checking_answers = [set(answer) == set(self.get_correct_answer_for_question(i)) for i, answer in enumerate(answers)]

        result_test = ResultTestModel(
            id_user=test_user.id,
            id_quiz=self.id,
            id_company=self.company.id,
            count_correct_answers=checking_answers.count(True),
            count_questions=len(self.questions)
        )

        await result_test.create_with_questions(db, self, self.add_text_to_answers(answers), checking_answers)

        await AverageScoreCompanyCrud.set_company_rating(db, test_user, self.company.id)
        await AverageScoreGlobalCrud.set_global_rating(db, test_user)

        return result_test


class AverageScoreCompanyCrud:
    @staticmethod
    async def set_company_rating(db: AsyncSession, user, company_id: int):
        from quiz.models.models import AverageScoreCompanyModel, ResultTestModel

        results = await ResultTestModel.get_by_fields(db, return_single=False, id_user=user.id, id_company=company_id)

        rating = get_rating(results)

        average_score_company = await AverageScoreCompanyModel.get_by_fields(db, id_user=user.id, id_company=company_id)

        if average_score_company:
            await average_score_company.update(db, {'rating': rating})
        else:
            average_company = AverageScoreCompanyModel(id_user=user.id, id_company=company_id, rating=rating)
            await average_company.create(db)


class AverageScoreGlobalCrud:
    @staticmethod
    async def set_global_rating(db: AsyncSession, user):
        from quiz.models.models import AverageScoreGlobalModel, ResultTestModel

        results = await ResultTestModel.get_by_fields(db, return_single=False, id_user=user.id)

        rating = get_rating(results)

        average_score_global = await AverageScoreGlobalModel.get_by_fields(db, id_user=user.id)

        if average_score_global:
            await average_score_global.update(db, {'rating': rating})
        else:
            average_company = AverageScoreGlobalModel(id_user=user.id, rating=rating)
            await average_company.create(db)


class ResultTestCrud:
    async def create_with_questions(self, db: AsyncSession, quiz, user_answers: list, checking_answers: list):
        from quiz.models.models import ResultQuestionModel

        await self.create(db)

        for i, question in enumerate(quiz.questions):
            new_question = ResultQuestionModel(
                id_result=self.id,
                question=question.question,
                answer_is_correct=checking_answers[i]
            )

            await new_question.create_with_answers(db, user_answers[i])

        await db.refresh(self)

        await add_test_result_to_redis(
            self.id,
            self.create_test_date()
        )

    def create_test_date(self) -> dict:
        questions = []
        for question in self.questions:
            questions.append({
                'question': question.question,
                'user_answer': [answer.answer for answer in question.user_answers],
                'is_correct': question.answer_is_correct
            })

        return {
            'user_id': self.id_user,
            'company_id': self.id_company,
            'quiz_id': self.id_quiz,
            'created_at': self.created_at.isoformat(),
            'questions': questions
        }


class ResultQuestionCrud:
    async def create_with_answers(self, db: AsyncSession, answers: list):
        from quiz.models.models import UserAnswerModel

        await self.create(db)

        for answer in answers:
            new_answer = UserAnswerModel(id_result_question=self.id, answer=answer)

            await new_answer.create(db)

        await db.refresh(self)