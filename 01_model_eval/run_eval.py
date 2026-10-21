"""Step 1.2: compare model deployments on help desk questions.

For each deployment in MODEL_DEPLOYMENTS this script asks the 15 questions in
questions.jsonl, measures latency and tokens, and has a judge model score each answer.
Run:  python 01_model_eval/run_eval.py
Output: 01_model_eval/results.md and results.json
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import config
from common.clients import get_openai_client
from common.judge import judge_json

HERE = Path(__file__).resolve().parent
SYSTEM_PROMPT = (
    "You are an IT help desk assistant for a company. Give short, practical answers. "
    "If you do not know a company-specific fact, say so instead of guessing."
)
JUDGE_INSTRUCTIONS = """You grade an IT help desk answer. Reply with ONE JSON object only:
{"score": <integer 1-5>, "hallucinated": <true or false>, "reason": "<one short sentence>"}
Score 5 = fully meets the rubric, accurate and practical. Score 1 = wrong, unsafe or unhelpful.
Set hallucinated to true if the answer states a specific company fact (an address, number of days,
size or time) as if it were certain when the rubric says it must not."""


def ask_model(client, deployment: str, question: str) -> dict:
    """Ask one question and measure how long it took and how many tokens it used."""
    # TODO 1.2.a: Record start = time.perf_counter(), call
    # client.responses.create(model=deployment, instructions=SYSTEM_PROMPT, input=question),
    # then return a dict with "answer" (response.output_text), "latency_s" (seconds, 2
    # decimals), "input_tokens" and "output_tokens" (from response.usage)
    raise NotImplementedError("TODO 1.2.a")


def grade(client, item: dict, answer: str) -> dict:
    """Score one answer against the rubric with the judge model."""
    # TODO 1.2.b: Build a prompt string with the question, the rubric and the answer, then
    # return judge_json(client, JUDGE_INSTRUCTIONS, prompt)
    raise NotImplementedError("TODO 1.2.b")


def summarise(rows: list[dict], prices: dict) -> dict:
    n = len(rows)
    scores = [r["score"] for r in rows if isinstance(r.get("score"), (int, float))]
    company = [r for r in rows if r["type"] == "company_specific"]
    summary = {
        "avg_score": round(sum(scores) / len(scores), 2) if scores else None,
        "hallucinations": sum(1 for r in company if r.get("hallucinated") is True),
        "company_questions": len(company),
        "avg_latency_s": round(sum(r["latency_s"] for r in rows) / n, 2),
        "avg_output_tokens": round(sum(r["output_tokens"] for r in rows) / n),
    }
    rate = prices.get(rows[0]["deployment"], {})
    if rate.get("input_per_1m") or rate.get("output_per_1m"):
        cost = sum(
            r["input_tokens"] * rate["input_per_1m"] + r["output_tokens"] * rate["output_per_1m"] for r in rows
        ) / 1_000_000
        summary["cost_per_100_questions"] = round(cost / n * 100, 4)
    return summary


def main() -> None:
    config.require("AZURE_OPENAI_ENDPOINT")
    client = get_openai_client()
    questions = [json.loads(line) for line in (HERE / "questions.jsonl").read_text().splitlines() if line.strip()]
    prices = json.loads((HERE / "prices.json").read_text())
    all_rows, summaries = [], {}
    for deployment in config.MODEL_DEPLOYMENTS:
        print(f"\n== {deployment} ==")
        rows = []
        for item in questions:
            result = ask_model(client, deployment, item["question"])
            verdict = grade(client, item, result["answer"])
            row = {"deployment": deployment, "id": item["id"], "type": item["type"], **result,
                   "score": verdict.get("score"), "hallucinated": verdict.get("hallucinated"),
                   "reason": verdict.get("reason") or verdict.get("error")}
            rows.append(row)
            print(f"{item['id']} score={row['score']} latency={row['latency_s']}s")
        summaries[deployment] = summarise(rows, prices)
        all_rows += rows
    (HERE / "results.json").write_text(json.dumps({"summary": summaries, "rows": all_rows}, indent=2))
    lines = ["# Model comparison results", "",
             f"Judge model: {config.MODEL_DEPLOYMENT}. Questions: {len(questions)} "
             "(10 general, 5 company-specific).", "",
             "| Deployment | Avg score (1-5) | Hallucinated company facts | Avg latency (s) | Avg output tokens | Cost per 100 questions |",
             "| --- | --- | --- | --- | --- | --- |"]
    for name, s in summaries.items():
        lines.append(
            f"| {name} | {s['avg_score']} | {s['hallucinations']} of {s['company_questions']} | "
            f"{s['avg_latency_s']} | {s['avg_output_tokens']} | {s.get('cost_per_100_questions', 'not set')} |"
        )
    lines += ["", "## Decision", "", "Write your choice and your reasons here (quality, latency, cost, safety).", ""]
    (HERE / "results.md").write_text("\n".join(lines))
    print("\nWrote 01_model_eval/results.md")


if __name__ == "__main__":
    main()
