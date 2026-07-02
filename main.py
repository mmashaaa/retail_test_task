"""CLI chat interface for the retail data-analysis agent.

Usage:
    python main.py --user manager_a

Type a question to get an analysis. Other things you can say:
    "save that report"              -> save the last report
    "list my reports"               -> show your saved reports
    "delete all reports about Nike" -> destructive, asks for confirmation
    "exit"                          -> quit
"""
import argparse
import uuid

from rich.console import Console
from rich.markdown import Markdown
from langgraph.types import Command

from src.graph import DataAgent
from src.observability import observe, update_trace, flush, LANGFUSE_ENABLED

console = Console()


def _pending_interrupt(agent, thread):
    """Return the interrupt payload if the graph is paused awaiting input."""
    snapshot = agent.graph.get_state(thread)
    for task in snapshot.tasks:
        if task.interrupts:
            return task.interrupts[0].value
    return None


@observe(name="chat_turn", capture_input=False, capture_output=False)
def handle_turn(agent, thread, user_id, user_input, last_report):
    """Run one user turn through the graph, resolving any confirmation gate.
    Returns (response_text, new_last_report)."""
    state = {"user_id": user_id, "user_input": user_input,
             "last_report": last_report}
    with console.status("[dim]thinking…[/dim]"):
        result = agent.graph.invoke(state, config=thread)

    # Destructive-delete confirmation gate (LangGraph interrupt).
    while (payload := _pending_interrupt(agent, thread)) is not None:
        console.print(f"\n[bold yellow]⚠ {payload['prompt']}[/bold yellow]")
        answer = console.input("[bold green]confirm ›[/bold green] ").strip()
        with console.status("[dim]working…[/dim]"):
            result = agent.graph.invoke(Command(resume=answer), config=thread)

    response = result.get("response", "(no response)")
    new_last = result.get("report") or last_report
    update_trace(user_id=user_id,
                 session_id=thread["configurable"]["thread_id"],
                 input=user_input, output=response)
    return response, new_last


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", default="manager_a",
                        help="user id (scopes saved reports & preferences)")
    args = parser.parse_args()

    console.print("[bold cyan]Retail Data Assistant[/bold cyan] "
                  f"(user: {args.user}). Type 'exit' to quit.")
    if LANGFUSE_ENABLED:
        console.print("[dim]Langfuse tracing: ON[/dim]")
    console.print()

    agent = DataAgent()
    # One LangGraph thread per session so the confirmation interrupt can resume.
    thread = {"configurable": {"thread_id": f"{args.user}-{uuid.uuid4().hex[:8]}"}}
    last_report = None

    while True:
        try:
            user_input = console.input("[bold green]you ›[/bold green] ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            break

        response, last_report = handle_turn(
            agent, thread, args.user, user_input, last_report)
        console.print()
        console.print(Markdown(response))
        console.print()

    flush()
    console.print("\n[dim]Goodbye.[/dim]")


if __name__ == "__main__":
    run()
