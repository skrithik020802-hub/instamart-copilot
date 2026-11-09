"""mock_llm.py -- deterministic, offline stand-in for an LLM API.
Interface mirrors a hosted chat API: response = chat(messages, tools=None)
response.choices[0].message.content / .tool_calls
Three behaviours are selected by a marker word in system message:
  "CLASSIFY"        -> support-ticket classifier
  "POLICY ASSISTANT"-> RAG policy responder
  "AGENT"           -> refund agent that requests tool calls
"""
import json, math, re
from types import SimpleNamespace as NS

class TransientLLMError(Exception):
    """Simulated temporary failure (timeout / server busy)."""
    pass

_state = {"calls": 0, "ok": 0}

def reset():
    """Restart the counters. Call once before each full run."""
    _state["calls"] = 0
    _state["ok"] = 0

CATS = ["billing", "delivery", "technical", "fraud"]
KW = {
    "fraud": {"unauthorized", "fraud", "hacked", "charged"},
    "billing": {"charged", "invoice", "bill", "refund", "deducted", "money"},
    "technical": {"app", "crash", "login", "otp", "error", "payment"},
    "delivery": {"arrived", "rider", "delivery", "late", "arrived"}
}

def est_tokens(text):
    return math.ceil(len((text or "").split()) * 1.3)

def _words(t):
    return set(re.findall(r"[a-z]+", (t or "").lower()))

def _resp(content=None, tool_calls=None, finish="stop", messages=None):
    prompt = sum(est_tokens(m.get("content") or json.dumps(m.get("tool_calls") or [])) for m in (messages or []))
    comp = est_tokens(content or json.dumps(tool_calls or []))
    msg = NS(role="assistant", content=content, tool_calls=tool_calls)
    return NS(choices=[NS(message=msg, finish_reason=finish)],
              usage=NS(prompt_tokens=prompt, completion_tokens=comp, total_tokens=prompt + comp))

def _classify(messages):
    system, user = messages[0]["content"], messages[-1]["content"]
    _state["calls"] += 1
    if _state["calls"] % 9 == 0:
        raise TransientLLMError("503 server busy")
    _state["ok"] += 1
    order = ["fraud", "technical", "billing", "delivery"]
    w = _words(user)
    cat = next((c for c in order if KW[c] & w), "billing")
    if _state["ok"] % 13 == 0:
        return _resp(f"The customer appears to have a {cat}-related problem.")
    if _state["ok"] % 17 == 0:
        return _resp(json.dumps({"category": "shipping", "reason": "unrecognized category"}))
    return _resp(json.dumps({"category": cat, "reason": f"matched {cat} terms"}))

STOP = {"the", "a", "an", "is", "of", "to", "for", "in", "on", "at", "by", "with", "from", "it", "this", "that", "i", "my", "be", "can", "after", "from", "what", "who", "when", "how"}

def _stems(t):
    return {w[:5] for w in re.findall(r"[a-z]+", (t or "").lower()) if w not in STOP}

def _policy(messages):
    user = messages[-1]["content"]
    m = re.search(r"CONTEXT:\s*(.*?)\s*QUESTION:\s*(.*)", user, re.DOTALL)
    if not m:
        return _resp("I could not find that information in the policy documents.")
    context, question = m.group(1), m.group(2)
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", context) if s.strip()]
    qs = _stems(question)
    best, best_score = None, 0.0
    for s in sents:
        sc = sum(1.0 / (len(s.split()) + 1) for q in qs if q in _stems(s))
        if sc > best_score:
            best, best_score = s, sc
    if best is None or best_score < 0.01:
        return _resp("I could not find that information in the policy documents.", messages=messages)
    return _resp(best, messages=messages)

def _agent(messages, tools):
    user = next(m["content"] for m in messages if m["role"] == "user")
    tool_msgs = [m for m in messages if m["role"] == "tool"]
    call = lambda n, a: _resp(None, [{"id": f"call_{len(tool_msgs)+1}", "type": "function", "function": {"name": n, "arguments": json.dumps(a)}}], finish="tool_calls", messages=messages)
    if "[LOOP]" in user:
        return call("search_policy", {"query": "refund policy late delivery"})
    if not tool_msgs:
        m = re.search(r"ORD-\d{6}", user)
        if m:
            return call("get_order", {"order_id": m.group(0)})
        return call("get_order", {"order_id": "ORD-000000"})

    last = tool_msgs[-1]
    data = json.loads(last["content"])
    if last["name"] == "get_order":
        if "error" in data:
            return _resp("NOT_FOUND: no such order.", messages=messages)
        return call("search_policy", {"query": "refund policy late delivery"})
    if last["name"] == "search_policy":
        order = json.loads(next(m for m in tool_msgs if m["name"] == "get_order")["content"])
        if order.get("status") != "completed":
            return _resp("DENIED: only completed orders can be refunded.", messages=messages)
        return call("calculate_refund", {"order_amount": order["order_amount"], "delivery_minutes": order["delivery_minutes"]})
    if last["name"] == "calculate_refund":
        amt = data.get("refund_inr", 0)
        if amt == 0:
            return _resp("DENIED: delivery was within policy limits.", messages=messages)
        order = json.loads(next(m for m in tool_msgs if m["name"] == "get_order")["content"])
        if amt > 1000:
            return call("escalate_to_human", {"order_id": order["order_id"], "refund_inr": amt})
        return call("issue_refund", {"order_id": order["order_id"], "refund_inr": amt})
    if last["name"] == "issue_refund":
        return _resp(f"REFUND: INR {data['refund_inr']:.2f} issued.", messages=messages)
    if last["name"] == "escalate_to_human":
        return _resp("ESCALATE: refund above INR 1000 requires supervisor review.", messages=messages)
    return _resp("DENIED: unable to process.", messages=messages)

def chat(messages, tools=None):
    head = messages[0]["content"].upper()
    if "CLASSIFY" in head:
        return _classify(messages)
    if "POLICY ASSISTANT" in head:
        return _policy(messages)
    if "AGENT" in head:
        return _agent(messages, tools)
    raise ValueError("first message must name one of CLASSIFY, POLICY ASSISTANT, AGENT")
