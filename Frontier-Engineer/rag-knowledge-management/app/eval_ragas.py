import asyncio
import json
import os
import pandas as pd
import requests

from dotenv import load_dotenv


from ragas import evaluate
from ragas import SingleTurnSample, EvaluationDataset
from langchain_openai import ChatOpenAI
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from ragas.run_config import RunConfig

from .logger import get_logger

# Load environment variables from .env (e.g., OPENAI_API_KEY) before any
# LLM client is constructed. This file is sometimes run standalone
# (`python -m app.eval_ragas`) without going through app/utils.py, which is
# where load_dotenv() would otherwise have been called implicitly.
load_dotenv()

logger = get_logger(__name__)


# LLM used internally by RAGAS to evaluate generated answers.
# This model acts as the "judge" and does not answer user questions.
oai_llm = ChatOpenAI(model="gpt-4o-mini")

logger.info(
    "ChatOpenAI initialized for RAGAS evaluation: model=gpt-4o-mini"
)


def load_jsonl(path):
    """
    Load evaluation questions and reference answers from a JSONL file.
    Each line in the file represents one test case.
    """

    logger.info("Loading test data from: %s", path)

    # Read each non-empty line and convert it from JSON into a Python dictionary.
    with open(path, "r", encoding="utf-8") as f:
        lines = [
            json.loads(line)
            for line in f
            if line.strip()
        ]

    logger.info("Loaded %d test Q&A pairs", len(lines))

    return lines


def print_eval_res(eval_result):
    """
    Display the evaluation results for every question
    and print the average score for each metric.
    """

    scores = eval_result.scores

    # Build the table header dynamically using metric names.
    eval_str = " | Q | "

    for k in scores[0].keys():
        eval_str += str(k) + " | "

    logger.info("Evaluation results table header: %s", eval_str)

    print(eval_str)

    # Print the score for every evaluated question.
    for i, score in enumerate(scores):

        eval_str = f" | {i + 1} | "

        for k in score.keys():
            eval_str += str(score[k]) + " | "

        print(eval_str)

    # Convert the results into a DataFrame to calculate averages.
    res = eval_result.to_pandas()

    means = res.mean(numeric_only=True).to_dict()

    logger.info("RAGAS averages: %s", means)

    print("\n📈 Averages:")

    for k, v in means.items():
        print(f"- {k}: {v:.3f}")


# Resolve the default test-data path relative to this file's own location,
# not the current working directory, so `eval_ragas.py` can be run from any
# directory (e.g., project root via `python -m app.eval_ragas`, or directly
# via `python eval_ragas.py` from inside `app/`) without a FileNotFoundError.
_DEFAULT_TEST_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "seed", "qna_test.json"
)


async def evaluate_rag_system(test_path=_DEFAULT_TEST_PATH):

    """
    Evaluate the RAG system using the RAGAS framework.

    Workflow:
    1. Load test questions.
    2. Call the RAG API for each question.
    3. Build an EvaluationDataset.
    4. Run RAGAS metrics.
    5. Display the evaluation results.
    """

    logger.info("=" * 60)
    logger.info("RAGAS EVALUATION STARTED")
    logger.info("=" * 60)

    # Load all evaluation questions and expected answers.
    test_data = load_jsonl(test_path)

    results = []

    # Evaluate each question individually.
    for idx, item in enumerate(test_data):

        question = item["question"]
        reference_answer = item["answer"]

        logger.info(
            "[%d/%d] Evaluating: question='%s'",
            idx + 1,
            len(test_data),
            question,
        )

        # Send the question to the running RAG API.
        url = "http://localhost:8000/ask"

        myobj = {"question": question}

        logger.debug("POST %s with question='%s'", url, question)

        # The API returns:
        # - generated answer
        # - retrieved context documents
        res = requests.post(url, json=myobj).json()

        answer = res["answer"]
        contexts = res["contexts"]

        logger.info(
            "Got answer (first 100 chars): %s...",
            answer[:100] if answer else "(empty)",
        )

        logger.info(
            "Retrieved %d context(s)",
            len(contexts),
        )

        # Create one evaluation sample for RAGAS.
        results.append(
            SingleTurnSample(
                user_input=question,
                response=answer,
                retrieved_contexts=contexts,
                reference=reference_answer,
            )
        )

        logger.debug(
            "Sample %d appended to evaluation dataset",
            idx + 1,
        )

    # Combine all samples into a RAGAS evaluation dataset.
    logger.info(
        "Creating EvaluationDataset with %d samples",
        len(results),
    )

    ds = EvaluationDataset(results)

    # Metrics used to measure the quality of the RAG pipeline.
    metrics = [
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    ]

    logger.info(
        "Metrics to evaluate: %s",
        [m.name for m in metrics],
    )

    # Configure parallel execution to speed up evaluation.
    run_config = RunConfig(
        max_workers=16,
        timeout=30,
    )

    logger.info(
        "Running RAGAS evaluation (max_workers=16, timeout=30s)..."
    )

    # Execute all evaluation metrics.
    eval_result = evaluate(
        dataset=ds,
        metrics=metrics,
        llm=oai_llm,
        run_config=run_config,
    )

    logger.info("RAGAS evaluation complete")

    print("RAGAS Evals Results")

    # Display detailed scores and averages.
    print_eval_res(eval_result)

    logger.info("=" * 60)
    logger.info("RAGAS EVALUATION FINISHED")
    logger.info("=" * 60)


if __name__ == "__main__":

    # Entry point when this file is executed directly.
    logger.info("Starting RAGAS evaluation script")

    asyncio.run(evaluate_rag_system())