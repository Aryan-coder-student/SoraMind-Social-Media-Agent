"""Load prompts used for optional Company Knowledge change summaries."""

from pathlib import Path

import yaml


PROMPT_PATH = Path(__file__).with_name("prompt.yml")

with PROMPT_PATH.open(encoding="utf-8") as prompt_file:
    prompt_configuration = yaml.safe_load(prompt_file)

CHANGE_SUMMARY_PROMPT_VERSION: str = prompt_configuration["version"]
CHANGE_SUMMARY_SYSTEM_PROMPT: str = prompt_configuration["system_prompt"]
