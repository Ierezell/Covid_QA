from typing import TypedDict

import torch
from config import LANGUAGES
from .config import MODEL_NAMES
from datatypes import Answer, Chunk
from transformers import AutoModelForQuestionAnswering as AutoModelQA
from transformers import AutoTokenizer
from transformers.pipelines import pipeline


class Res(TypedDict):
    answer: str
    score: float
    start: int
    end: int


class Answerer:
    """
    Simlpe class which provide the ability to get
    the span answering the best the question given a context paragraph

    It is instanciated in :func:`~indexer.indexer.create_models`
    which is called by :func:`~indexer.indexer.process`

    It is used in :func:`~qa.refinder.answer_question`
    """

    def __init__(self, lang: LANGUAGES = 'multi', prefer_gpu: bool = False
                 ) -> None:

        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAMES[lang])
        model = AutoModelQA.from_pretrained(MODEL_NAMES[lang])

        DEVICE = 0 if (torch.cuda.is_available() and prefer_gpu) else -1

        self.nlp = pipeline(
            "question-answering",
            model=model,
            tokenizer=tokenizer,
            framework='pt',
            device=DEVICE
        )

        print(f"Answerer will compute on {'cpu' if DEVICE < 0 else 'gpu'}")

    def answer(self, question: str, chunk: Chunk) -> Answer:
        """Give the best sentence in the context answering the question
            Used in :func:`~qa.refinder.answer_question`
        Args:
            question (str)
            context (str): A paragraph ~1000 characters

        Returns:
            Answer
        """
        with torch.no_grad():
            res: Res = self.nlp(question=question, context=chunk['content'])
            answer: Answer = {
                'score': res['score'],
                'content': chunk['content'],
                'answer': res['answer'],
                'title': chunk['title'],
                'date': chunk['first_seen_date'],
                'start': res['start'],
                'end': res['end'],
                'elected': 'qa',
                'link': [li['path'] for li in chunk['links']]
            }
            # TODO Move the logic of finding the full sentence here
        return answer

        # OR to to it by hand and have more control

        # inputs = self.tokenizer(question, context, add_special_tokens=True,
        #                         return_tensors="pt")
        # input_ids = inputs["input_ids"].tolist()[0]

        # text_tokens = self.tokenizer.convert_ids_to_tokens(input_ids)
        # answer_start_scores, answer_end_scores = self.model(**inputs)

        # answer_start = torch.argmax(answer_start_scores)
        # answer_end = torch.argmax(answer_end_scores) + 1

        # answer = self.tokenizer.convert_tokens_to_string(
        #     self.tokenizer.convert_ids_to_tokens(
        #         input_ids[answer_start:answer_end]
        #     )
        # )

        # score = torch.max(answer_end_scores)+torch.max(answer_end_scores) / 2
        # return {'score': score.item(),
        #         'start': answer_start,
        #         'end': answer_end,
        #         'answer': answer}
