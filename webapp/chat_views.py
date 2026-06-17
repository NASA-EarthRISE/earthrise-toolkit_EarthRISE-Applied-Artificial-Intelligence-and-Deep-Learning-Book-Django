# webapp/chat_views.py
"""
Chat endpoints for the EarthRISE Book Assistant.

  GET  /api/chat/stream?message=<text>   — SSE streaming response
  POST /api/chat/clear                   — clear session history
"""

import json
import uuid

from django.http import StreamingHttpResponse, JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.encoding import smart_str

from .openai_client import client, CHAT_MODEL
from .rag import build_context_snippets
from .prompts import SYSTEM_PROMPT


# ── SSE helper ────────────────────────────────────────────────────────────────

def _sse(data: dict, event: str = None) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    if event:
        return f"event: {event}\ndata: {payload}\n\n"
    return f"data: {payload}\n\n"


# ── Streaming chat endpoint ───────────────────────────────────────────────────

@csrf_exempt
def api_message_stream(request):
    if request.method != "GET":
        return JsonResponse({"error": "Use GET with query params"}, status=405)

    user_text = smart_str(request.GET.get("message", "")).strip()
    if not user_text:
        return HttpResponseBadRequest("message is required")

    # Ensure the session has a stable ID and history list
    if not request.session.get("session_id"):
        request.session["session_id"] = str(uuid.uuid4())
    session_id = request.session["session_id"]

    try:
        context = build_context_snippets(user_text, top_k=20, session_id=session_id)
    except Exception:
        context = ""

    history = request.session.get("history", [])

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.append({
        "role": "system",
        "content": f"Relevant book content:\n{context}" if context else "No relevant content retrieved.",
    })
    messages.extend(history[-10:])
    messages.append({"role": "user", "content": user_text})

    def stream():
        yield _sse({"status": "starting"})
        collected = []
        try:
            resp = client.chat.completions.create(
                model=CHAT_MODEL,
                messages=messages,
                stream=True,
            )
            for chunk in resp:
                try:
                    delta = chunk.choices[0].delta if chunk.choices and chunk.choices[0].delta else None
                except Exception:
                    delta = None
                if delta and delta.content:
                    collected.append(delta.content)
                    yield _sse({"delta": delta.content})

            full = "".join(collected)
            history.append({"role": "user",      "content": user_text})
            history.append({"role": "assistant",  "content": full})
            request.session["history"] = history
            request.session.modified = True

            yield _sse({"done": True, "full": full}, event="done")

        except Exception as e:
            yield _sse({"error": str(e)}, event="error")

    response = StreamingHttpResponse(stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


# ── Clear chat endpoint ───────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def api_clear_chat(request):
    """Clear server-side history and issue a fresh session ID."""
    request.session["history"] = []
    request.session["session_id"] = str(uuid.uuid4())
    request.session.modified = True
    return JsonResponse({"ok": True})
