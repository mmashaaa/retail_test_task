"""Optional Langfuse tracing.

If LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY are set, every user turn becomes a
trace and every node / LLM call a nested span (latency, token cost, inputs and
outputs visible in the Langfuse UI). If the keys are absent the decorators are
transparent no-ops, so the agent runs anywhere without Langfuse configured.
"""
import os
import functools

LANGFUSE_ENABLED = bool(
    os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")
)

if LANGFUSE_ENABLED:
    from langfuse.decorators import observe, langfuse_context  # noqa: F401

    def flush():
        langfuse_context.flush()

    def update_observation(**kwargs):
        langfuse_context.update_current_observation(**kwargs)

    def update_trace(**kwargs):
        langfuse_context.update_current_trace(**kwargs)

else:
    def observe(*dargs, **dkwargs):
        # Support both @observe and @observe(as_type="generation").
        if len(dargs) == 1 and callable(dargs[0]) and not dkwargs:
            return dargs[0]

        def deco(fn):
            @functools.wraps(fn)
            def wrapper(*a, **k):
                return fn(*a, **k)
            return wrapper
        return deco

    def flush():
        pass

    def update_observation(**kwargs):
        pass

    def update_trace(**kwargs):
        pass
