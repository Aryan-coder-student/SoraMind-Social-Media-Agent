"""Prompts used for optional Company Knowledge change summaries."""

CHANGE_SUMMARY_PROMPT_VERSION = "section-change-summary-v1"

CHANGE_SUMMARY_SYSTEM_PROMPT = """You summarize factual website content changes.
Use only the supplied facts. Do not infer causes, intentions, or business impact.
Return exactly one JSON object with this schema:
{
  "summary": "non-empty factual summary",
  "category": "short category such as pricing or careers, or null",
  "key_points": ["factual point"]
}
Do not include Markdown or additional keys.
"""
