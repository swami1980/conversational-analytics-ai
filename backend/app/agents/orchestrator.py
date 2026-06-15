"""
Strands Agent orchestrator.
Swap AnthropicModel → BedrockModel for AWS production deployment.
"""
import threading
from datetime import date
from queue import Queue, Empty

from strands import Agent
from strands.models.anthropic import AnthropicModel

from app.agents.tools import ALL_TOOLS
from app.config import get_settings

_settings = get_settings()

SYSTEM_PROMPT = f"""You are a recruiting analytics AI assistant for Amazon. You help recruiters,
hiring managers, and HR admins understand hiring data across Amazon orgs.

Today's date: {date.today().isoformat()}

You have access to 7 internal recruiting APIs:
- Requisitions API: Open/closed job requisitions by org/team/level/location
- Candidate Pipeline API: Candidates moving through hiring stages
- Employees API: Current employee roster, headcount, and attrition
- Pending Starts API: Accepted candidates not yet started, onboarding readiness
- Interview Events API: Scheduled/completed interviews, Bar Raiser sessions
- Interview Metrics API: Aggregated funnel metrics (time-to-hire, offer acceptance, conversion rates) by period
- Historical Data API: Quarterly headcount trends and hiring velocity vs plan

Job families: SDE (L4–L7), SDM (L6–L7), TPM (L4–L6), SDET (L4–L6), Data Engineer (L4–L6),
Applied Scientist (L5–L7), Research Scientist (L6–L7), Solutions Architect (L5–L6), DevOps Engineer (L4–L5)

Orgs: AWS, Amazon Advertising, Alexa & Echo, Prime Video, Kindle, Amazon Logistics, Amazon Healthcare, Amazon Fresh

Workflow — follow this every time:
1. Call search_knowledge_base for EVERY question — it searches both API specs and wiki pages.
   - If the question is conceptual ("what is a requisition?", "what does this app do?",
     "what is a Bar Raiser?", "how do I use this?") → the wiki results will answer it
     directly. Return the wiki answer without calling any API.
   - If the question asks for data ("how many open reqs?", "show me the pipeline") →
     use the API spec results to determine which endpoint to call, then proceed to step 2.
2. For single-domain data questions: call call_api with the correct endpoint and parameters.
3. For cross-domain questions (spanning 2+ APIs): call call_apis_parallel with all needed calls.
4. Analyze the returned data and provide a clear, concise, recruiter-friendly answer.
5. If you encounter errors or anomalies, use search_github_issues to check for known issues,
   or create_github_issue to report a new one.

Response style:
- Be direct and data-driven. Recruiters want numbers, not hedging.
- Use bullet points for lists, tables for comparisons.
- Cite which API(s) you used.
- If data is filtered (e.g. to 20 records), note the total and offer to refine the query.
- Role context: hiring managers can only see their own reqs; you will receive role info in the conversation context.
"""


class StreamEvent:
    def __init__(self, event_type: str, payload: dict):
        self.event_type = event_type
        self.payload = payload


def _make_model() -> AnthropicModel:
    return AnthropicModel(
        model_id="claude-sonnet-4-6",
        max_tokens=4096,
        client_args={"api_key": _settings.anthropic_api_key},
    )


def run_agent(
    user_message: str,
    history: list[dict],
    event_queue: Queue,
    user_role: str = "recruiter",
) -> str:
    """
    Run the Strands orchestrator agent. Emits StreamEvent objects onto event_queue
    so the SSE endpoint can forward them to the browser in real time.

    Returns the final text response.
    """
    model = _make_model()

    # Build conversation context including role
    context_prefix = f"[User role: {user_role}]\n\n"
    full_message = context_prefix + user_message

    # Capture tool events via Strands callback
    final_response_holder = []

    class _QueueCallback:
        def __call__(self, **kwargs):
            event_type = kwargs.get("event_type", "")
            data = kwargs.get("data", {})

            if event_type == "tool_use":
                event_queue.put(StreamEvent("tool_call", {
                    "tool_name": data.get("name", ""),
                    "tool_input": data.get("input", {}),
                }))
            elif event_type == "tool_result":
                result_text = data.get("content", "")
                if isinstance(result_text, list):
                    result_text = str(result_text)
                # Truncate very long tool results in the stream (full result still used by agent)
                preview = result_text[:1000] + "..." if len(result_text) > 1000 else result_text
                event_queue.put(StreamEvent("tool_result", {
                    "tool_name": data.get("tool_use_id", ""),
                    "result_preview": preview,
                }))
            elif event_type == "text_delta":
                pass  # Handled via final response

    def _run():
        try:
            agent = Agent(
                model=model,
                tools=ALL_TOOLS,
                system_prompt=SYSTEM_PROMPT,
                callback_handler=_QueueCallback(),
            )
            # Inject history as prior messages
            for turn in history:
                if turn["role"] == "user":
                    agent.messages.append({"role": "user", "content": turn["content"]})
                elif turn["role"] == "assistant":
                    agent.messages.append({"role": "assistant", "content": turn["content"]})

            result = agent(full_message)
            final_response_holder.append(str(result))
        except Exception as e:
            final_response_holder.append(f"Agent error: {e}")
        finally:
            event_queue.put(None)  # Sentinel to signal completion

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=120)

    return final_response_holder[0] if final_response_holder else "No response generated."
