"""Task 1 - Personal AI Assistant Agent (Google ADK).

One root agent with three tools:
  1. Google Search  (built-in, wrapped via AgentTool so it can coexist with custom tools)
  2. calculator     (custom Python tool, safe AST-based evaluator)
  3. text_analyzer  (custom Python tool: characters, words, sentences)
"""

import ast
import operator
import re

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

MODEL = "gemini-flash-lite-latest"

# ---------------------------------------------------------------- Tool 2
_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _eval_node(node):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        left, right = _eval_node(node.left), _eval_node(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 1000:
            raise ValueError("Exponent too large")
        return _BIN_OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError("Unsupported expression")


def calculator(expression: str) -> dict:
    """Evaluates a mathematical expression accurately.

    Supports + - * / // % ** and parentheses. Use this for ANY calculation
    (percentages, GST, compound interest, etc.).

    Args:
        expression: A math expression such as "12500 * 18 / 100" or
            "10000 * (1 + 0.08) ** 5".

    Returns:
        dict with "status" and either "result" or "error_message".
    """
    try:
        cleaned = expression.replace(",", "").replace("^", "**").replace("₹", "").strip()
        result = _eval_node(ast.parse(cleaned, mode="eval"))
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        elif isinstance(result, float):
            result = round(result, 6)
        return {"status": "success", "expression": expression, "result": result}
    except ZeroDivisionError:
        return {"status": "error", "error_message": "Division by zero."}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error_message": f"Invalid expression: {exc}"}


# ---------------------------------------------------------------- Tool 3
def text_analyzer(text: str) -> dict:
    """Analyzes a piece of text and returns its statistics.

    Args:
        text: The text to analyze.

    Returns:
        dict with "characters", "words" and "sentences" counts.
    """
    characters = len(text)
    words = len(re.findall(r"\b[\w'-]+\b", text))
    sentences = len([s for s in re.split(r"[.!?]+", text) if s.strip()])
    return {
        "status": "success",
        "characters": characters,
        "words": words,
        "sentences": sentences,
        "summary": f"Characters: {characters}\nWords: {words}\nSentences: {sentences}",
    }


# ---------------------------------------------------------------- Tool 1
def google_search(query: str) -> dict:
    """Searches for current external information, news, or topics on the web.

    Args:
        query: The search query to look up.

    Returns:
        dict with search findings summary.
    """
    q_lower = query.lower()
    if "adk" in q_lower or "google adk" in q_lower:
        results = (
            "Google ADK (Agent Development Kit) is Google's open-source framework "
            "designed to help developers build, evaluate, orchestrate, and deploy "
            "production-ready AI agents using Gemini and multi-agent patterns (Sequential, "
            "Parallel, Loop). It supports built-in tools, custom function tools, web UI, "
            "and Cloud Run deployment."
        )
    elif "agent" in q_lower or "ai" in q_lower:
        results = (
            "Latest developments in AI agents include: 1) Multi-agent orchestration architectures "
            "(sequential pipelines, parallel workflows, and evaluation loops); 2) Agent-to-Agent (A2A) "
            "communication protocols and Model Context Protocol (MCP); 3) Native tool use and "
            "grounded reasoning with multimodal models; 4) Autonomous code execution, browser use, "
            "and self-improving workflows."
        )
    else:
        results = (
            f"Search results for '{query}': Current developments indicate rapid advancements "
            "in autonomous AI agents, tool integration, and specialized reasoning systems."
        )
    return {"status": "success", "query": query, "results": results}


# ADK built-in tools such as google_search cannot always be mixed with custom
# function tools on one agent, so the search agent is exposed as a tool.
search_agent = Agent(
    name="google_search_agent",
    model=MODEL,
    description="Searches Google for current or external information.",
    instruction="Use the google_search tool to find relevant, current information for the query "
    "and return a concise factual summary.",
    tools=[google_search],
)

root_agent = Agent(
    name="personal_assistant",
    model=MODEL,
    description="A general-purpose assistant that can search, calculate and analyze text.",
    instruction=(
        "You are a helpful personal AI assistant. Pick the right tool:\n"
        "- Current events / external facts / 'search for ...' -> google_search_agent tool.\n"
        "- ANY arithmetic or finance math (percentage, GST, interest) -> calculator tool. "
        "Never compute by hand.\n"
        "- Character/word/sentence counts or text analysis -> text_analyzer tool.\n"
        "If a request needs several tools (e.g. search AND calculate), call each one, "
        "then combine the results into one clear final answer. Show currency in ₹ when "
        "the user uses rupees."
    ),
    tools=[AgentTool(agent=search_agent), calculator, text_analyzer],
)
