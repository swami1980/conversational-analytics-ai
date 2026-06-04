#!/usr/bin/env python3
"""
LLM-as-judge evaluation harness.
Runs 25 representative recruiting questions against the live API,
then uses Claude Sonnet to score each answer on 3 dimensions.

Usage:
    python judge/run_judge.py --base-url http://localhost:8000 --output judge/results.json
"""
import argparse
import json
import time
import sys
import os
from pathlib import Path

import httpx
import anthropic

JUDGE_SYSTEM = """You are an expert evaluator of recruiting analytics AI systems.
Score the answer on three dimensions (1-5 each):

1. Correctness: Does it answer what was asked? Does it cite real-looking data?
2. Recruiter-friendliness: Is the language clear for a recruiter? Good formatting?
3. Groundedness: Does the answer appear grounded in actual API data vs hallucinated?

Respond ONLY with valid JSON:
{"correctness": <1-5>, "recruiter_friendly": <1-5>, "groundedness": <1-5>, "verdict": "pass|fail", "reasoning": "<one sentence>"}
verdict is "pass" if all scores >= 3, "fail" otherwise.
"""

JUDGE_MODEL = "claude-sonnet-4-6"


def get_token(base_url: str) -> str:
    resp = httpx.post(
        f"{base_url}/api/v1/auth/token",
        data={"username": "recruiter1", "password": "password123"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def ask(base_url: str, token: str, question: str, session_id: str) -> str:
    """Send a question and collect the full SSE stream, returning the final_answer content."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {"session_id": session_id, "message": question}
    final_answer = ""
    try:
        with httpx.Client(timeout=120) as client:
            with client.stream("POST", f"{base_url}/api/v1/chat/stream", headers=headers, json=body) as resp:
                resp.raise_for_status()
                buffer = ""
                for chunk in resp.iter_text():
                    buffer += chunk
                    parts = buffer.split("\n\n")
                    buffer = parts.pop()
                    for part in parts:
                        lines = part.strip().split("\n")
                        event_type = "message"
                        data_str = ""
                        for line in lines:
                            if line.startswith("event: "):
                                event_type = line[7:].strip()
                            if line.startswith("data: "):
                                data_str = line[6:].strip()
                        if event_type == "final_answer" and data_str:
                            try:
                                final_answer = json.loads(data_str).get("content", "")
                            except Exception:
                                pass
    except Exception as e:
        return f"ERROR: {e}"
    return final_answer or "No answer received."


def judge(client: anthropic.Anthropic, question: str, answer: str) -> dict:
    resp = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=256,
        system=JUDGE_SYSTEM,
        messages=[{"role": "user", "content": f"Question: {question}\n\nAnswer:\n{answer}"}],
    )
    text = resp.content[0].text.strip()
    try:
        return json.loads(text)
    except Exception:
        return {"correctness": 0, "recruiter_friendly": 0, "groundedness": 0, "verdict": "error", "reasoning": text}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--output", default="judge/results.json")
    parser.add_argument("--questions", default="judge/questions.json")
    parser.add_argument("--fail-threshold", type=float, default=0.80, help="Min pass rate to exit 0")
    args = parser.parse_args()

    questions = json.loads(Path(args.questions).read_text())
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    judge_client = anthropic.Anthropic(api_key=api_key)

    print(f"Authenticating against {args.base_url}...")
    try:
        token = get_token(args.base_url)
    except Exception as e:
        print(f"Auth failed: {e}", file=sys.stderr)
        sys.exit(1)

    results = []
    session_id = "judge-session-001"
    passed = 0

    for i, q in enumerate(questions, 1):
        print(f"[{i:02d}/{len(questions)}] {q['id']}: {q['question'][:60]}...")
        answer = ask(args.base_url, token, q["question"], session_id)
        time.sleep(1)  # rate limit courtesy
        scores = judge(judge_client, q["question"], answer)

        result = {
            "id": q["id"],
            "question": q["question"],
            "category": q["category"],
            "domain": q["domain"],
            "answer_preview": answer[:300],
            **scores,
        }
        results.append(result)

        verdict_sym = "✓" if scores.get("verdict") == "pass" else "✗"
        print(f"  {verdict_sym} C={scores.get('correctness')} RF={scores.get('recruiter_friendly')} G={scores.get('groundedness')} — {scores.get('reasoning','')}")

        if scores.get("verdict") == "pass":
            passed += 1

    pass_rate = passed / len(questions)
    summary = {
        "total": len(questions),
        "passed": passed,
        "failed": len(questions) - passed,
        "pass_rate": round(pass_rate, 3),
        "threshold": args.fail_threshold,
        "ci_pass": pass_rate >= args.fail_threshold,
        "results": results,
    }

    Path(args.output).write_text(json.dumps(summary, indent=2))
    print(f"\n{'='*50}")
    print(f"Pass rate: {passed}/{len(questions)} ({pass_rate:.1%})")
    print(f"CI threshold: {args.fail_threshold:.0%} → {'PASS' if summary['ci_pass'] else 'FAIL'}")
    print(f"Results saved to {args.output}")

    sys.exit(0 if summary["ci_pass"] else 1)


if __name__ == "__main__":
    main()
