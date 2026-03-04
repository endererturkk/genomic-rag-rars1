import subprocess
import json
import re

from llm.prompt_templates import build_extraction_prompt


class OllamaClient:
    def __init__(self, model_name="llama3:8b-instruct-q4_K_M"):
        self.model_name = model_name

    def generate(self, prompt: str) -> str:
        process = subprocess.Popen(
            ["ollama", "run", self.model_name],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        stdout, stderr = process.communicate(prompt)

        if process.returncode != 0:
            raise RuntimeError(f"Ollama error: {stderr}")

        return stdout.strip()


class LLMExtractor:
    def __init__(self, model_name="llama3:8b-instruct-q4_K_M"):
        self.client = OllamaClient(model_name)

    def _extract_json_block(self, text: str):
        """
        Safely extract the first valid JSON object from text.
        """
        # Remove markdown code fences
        text = re.sub(r"```.*?```", lambda m: m.group(0).replace("```json", "").replace("```", ""), text, flags=re.DOTALL)

        # Find first '{'
        start = text.find("{")
        if start == -1:
            return None

        # Walk character by character to find matching closing brace
        brace_count = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                brace_count += 1
            elif text[i] == "}":
                brace_count -= 1
                if brace_count == 0:
                    return text[start:i+1]

        return None

    def extract(self, query: str, context: str):
        prompt = build_extraction_prompt(context, query)

        raw_output = self.client.generate(prompt)

        json_block = self._extract_json_block(raw_output)

        if not json_block:
            return {
                "error": "No JSON detected",
                "raw_output": raw_output
            }

        try:
            parsed = json.loads(json_block)

            # Normalize PMIDs to string
            for section in ["variants", "diseases", "phenotypes"]:
                if section in parsed:
                    for item in parsed[section]:
                        if "pmid" in item:
                            item["pmid"] = str(item["pmid"])

            return parsed

        except json.JSONDecodeError:
            return {
                "error": "Invalid JSON structure",
                "raw_output": raw_output
            }