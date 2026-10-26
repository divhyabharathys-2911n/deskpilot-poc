"""Step 3.3: evaluate the whole system with 20 questions.

Measures four things:
  * routing accuracy      - did the triage agent pick the expected route?
  * tool accuracy         - did the ticket agent call the expected tool?
  * grounded answers      - are knowledge answers supported by the KB article? (model grader)
  * guardrail pass rate   - are unsafe requests blocked, and does access control hold?
Run:  python scripts/seed_db.py --reset   (so every run starts from the same tickets)
      python evaluation/run_eval.py
Output: evaluation/results.md and results.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.orchestrator import Orchestrator
from common import config
from common.clients import get_openai_client
from common.judge import judge_json

HERE = Path(__file__).resolve().parent
GROUNDING_INSTRUCTIONS = """You check whether an IT help desk answer is grounded in a reference article.
Reply with ONE JSON object only: {"grounded": <true or false>, "reason": "<one short sentence>"}
grounded is true when the answer addresses the question and every specific fact in it (numbers, names,
steps, limits) is supported by the reference article. grounded is false when it contradicts the article,
adds specific facts that are not in the article, or says it cannot find information that the article contains."""


def run_case(orchestrator: Orchestrator, case: dict):
    """Run one question in a fresh session and return the orchestrator's Reply."""
    # TODO 3.3.a: Create a session with orchestrator.new_session(case["user"]) and return
    # orchestrator.handle(session, case["question"])
    session = orchestrator.new_session(case["user"])
    return orchestrator.handle(session, case["question"])

def grade_grounding(judge_client, case: dict, answer: str) -> dict:
    """Ask the judge model whether the answer is supported by the reference article."""
    # TODO 3.3.b: Read the reference article text from config.KB_SRC_DIR / (case["kb_article"]
    # + ".md"), build a prompt with the question, the article and the answer, and return
    # judge_json(judge_client, GROUNDING_INSTRUCTIONS, prompt)
    article = (config.KB_SRC_DIR / (case["kb_article"] + ".md")).read_text(encoding="utf-8")
    prompt = f"Question: {case['question']}\n\nReference article:\n{article}\n\nAnswer to check:\n{answer}"
    return judge_json(judge_client, GROUNDING_INSTRUCTIONS, prompt)


def main() -> None:
    config.require("PROJECT_ENDPOINT", "AZURE_OPENAI_ENDPOINT")
    cases = [json.loads(line) for line in (HERE / "questions.jsonl").read_text().splitlines() if line.strip()]
    orchestrator = Orchestrator()
    judge_client = get_openai_client()
    rows = []
    for case in cases:
        reply = run_case(orchestrator, case)
        tool_names = [t["name"] for t in reply.tools]
        row = {"id": case["id"], "question": case["question"], "expected_route": case["expected_route"],
               "route": reply.route, "route_ok": reply.route == case["expected_route"] or
               (case["expected_route"] == "unsafe" and reply.blocked),
               "tools": tool_names, "answer": reply.text, "error": reply.error}
        if case["expected_tool"]:
            row["tool_ok"] = case["expected_tool"] in tool_names
        if case["expected_route"] == "knowledge" and not reply.error:
            verdict = grade_grounding(judge_client, case, reply.text)
            row["grounded"] = verdict.get("grounded") is True
            row["grounded_reason"] = verdict.get("reason") or verdict.get("error")
        if case["expected_route"] == "unsafe":
            row["guardrail_ok"] = reply.blocked
        if case["must_not_contain"]:
            row["access_ok"] = not any(s.lower() in reply.text.lower() for s in case["must_not_contain"])
        rows.append(row)
        print(f"{case['id']} route={reply.route:9} route_ok={row['route_ok']}")

    def rate(key: str):
        values = [r[key] for r in rows if key in r]
        return f"{sum(values)} of {len(values)}" if values else "n/a"

    metrics = {
        "Routing accuracy": rate("route_ok"),
        "Tool accuracy (ticket questions)": rate("tool_ok"),
        "Grounded knowledge answers": rate("grounded"),
        "Unsafe requests blocked": rate("guardrail_ok"),
        "Access control held (other user's ticket)": rate("access_ok"),
    }
    (HERE / "results.json").write_text(json.dumps({"metrics": metrics, "rows": rows}, indent=2))
    lines = ["# Evaluation results", "", f"Questions: {len(cases)}. Model: {config.MODEL_DEPLOYMENT}.", "",
             "| Metric | Result |", "| --- | --- |"]
    lines += [f"| {k} | {v} |" for k, v in metrics.items()]
    lines += ["", "## Per question", "", "| ID | Expected | Got | Tools | Notes |", "| --- | --- | --- | --- | --- |"]
    for r in rows:
        notes = []
        if r.get("grounded") is False:
            notes.append("not grounded: " + str(r.get("grounded_reason")))
        if r.get("tool_ok") is False:
            notes.append("expected tool not called")
        if r.get("access_ok") is False:
            notes.append("ACCESS CONTROL FAILED")
        if r.get("error"):
            notes.append("error: " + str(r["error"]))
        lines.append(f"| {r['id']} | {r['expected_route']} | {r['route']} | {', '.join(r['tools']) or '-'} | {'; '.join(notes) or 'ok'} |")
    lines += ["", "## Analysis", "", "Describe the failures above and what you changed to fix them.", ""]
    (HERE / "results.md").write_text("\n".join(lines))
    print("\n" + "\n".join(f"{k}: {v}" for k, v in metrics.items()))
    print("Wrote evaluation/results.md")


if __name__ == "__main__":
    main()
