from ragas import SingleTurnSample
from ragas.metrics import Faithfulness
from ragas.llms import LangchainLLMWrapper, BaseRagasLLM
from langchain_core.outputs import LLMResult, Generation
from config import get_settings
from langchain_openai import ChatOpenAI
import asyncio
import json

settings = get_settings()

judge_llm = LangchainLLMWrapper(
    ChatOpenAI(model=settings.OPENROUTER_LLM_DEFAULT_MODEL,
               base_url="https://openrouter.ai/api/v1",
               api_key=settings.OPEN_ROUTER_API_KEY)
)
scorer = Faithfulness(llm=judge_llm)


GROUNDED_SAMPLE = {
    "question": "Mock question?",
    "answer": "Mock answer.",
    "sources": ["Mock source 1", "Mock source 2"],
    "context": ["Mock context 1", "Mock context 2"],
    "confidence": "medium"
}

GROUNDED_RAG_TRIPLE = {
    "question": "What is a RAG?",
    "answer": "RAG (Retrieval-Augmented Generation) is an AI technique where a large language model (LLM) searches an external database or document library for relevant information before answering a question.",
    "sources": ["Mock source 1", "Mock source 2"],
    "context": ["RAG (Retrieval-Augmented Generation) is an AI technique where a large language model (LLM) searches an external database or document library for relevant information before answering a question."],
    "confidence": "high"
}


class FakeBaseRagasLLM(BaseRagasLLM):
    
    
    def __init__(self, model):
        self.model = model
        self.counter = 0


    async def agenerate_text(
        self,
        *args,
        **kwargs
    ):
        self.counter += 1
        statement_json = json.dumps({
            "statements": ["claim one.", "claim two."]
        })
        verdicts_json = json.dumps({
            "statements": [
                {"statement": "claim one.", "reason": "supported by context", "verdict": 1},
                {"statement": "claim two.", "reason": "not found in context", "verdict": 0},
            ]
        })
        result_statements = LLMResult(generations=[[Generation(text=statement_json)]])
        result_verdicts = LLMResult(generations=[[Generation(text=verdicts_json)]])
        if self.counter == 1:
            return result_statements
        else:
            return result_verdicts

    def generate_text(
        self,
        *args,
        **kwargs
    ) -> None:
        raise NotImplementedError("Method not used")


async def respond_llm(answer: str, sources: list[str], confidence: str) -> dict:
    """Mocked LLM response"""
    return {
        "answer": answer,
        "sources": sources,
        "confidence": confidence, 
    }

async def check_faithfulness(question: str, answer: str, context: list[str]) -> float:
    """Checks the faithfulness of the LLM call"""
    sample = SingleTurnSample(
        user_input=question,
        response=answer,
        retrieved_contexts=context,
    )
    result = await scorer.single_turn_ascore(sample)
    return result


async def main():

    llm_response_grounded_sample_response = await respond_llm(
        answer=GROUNDED_SAMPLE["answer"], sources=GROUNDED_SAMPLE["sources"], confidence=GROUNDED_SAMPLE["confidence"]
    )
    our_llm_sample_answer = llm_response_grounded_sample_response["answer"]
    faithfulness_grounded_sample = await check_faithfulness(
        question=GROUNDED_SAMPLE["question"],
        answer=our_llm_sample_answer,
        context=GROUNDED_SAMPLE["context"]
    )
    print(faithfulness_grounded_sample)
    
    #####################################################

    llm_response_rag_triple = await respond_llm(
        answer=GROUNDED_RAG_TRIPLE["answer"], 
        sources=GROUNDED_RAG_TRIPLE["sources"],
        confidence=GROUNDED_RAG_TRIPLE["confidence"]
    )
    our_llm_rag_answer = llm_response_rag_triple["answer"]
    faithfulness_rag_triple = await check_faithfulness(
        question=GROUNDED_RAG_TRIPLE["question"],
        answer=our_llm_rag_answer,
        context=GROUNDED_RAG_TRIPLE["context"]
    )
    print(faithfulness_rag_triple)


if __name__ == "__main__":
    asyncio.run(main())