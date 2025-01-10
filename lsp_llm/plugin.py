import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, cast

from litellm import completion

from lsp_llm.lsp_types import (
    CodeAction,
    CodeActionParams,
    Command,
    ExecuteCommandParams,
    Position,
    Range,
    WorkspaceEdit,
)

if TYPE_CHECKING:
    from lsp_llm.python_lsp import LSPServer

logger = logging.getLogger(__name__)

COMMAND_COMMON = """
* Do not include explanations
* Do not include tests
* Do include minimal comments
* Do not include markdown
* do not include backticks ("```") or anything else surrounding the result
* do not preface the resulting code with anything
* Do not include the INSTRUCTION or CODE text in your response
"""

SYSTEM_PROMPT_COMPLETE = (
    """
You are a helpful code assistant.
Complete the following code.
It will be inserted directly into a python source file.
"""
    + COMMAND_COMMON
)

SYSTEM_PROMPT_INSTRUCT = (
    """
You are a helpful code assistant.
You will get two messages: instructions then code
The format will be
INSTRUCTIONS
instructions here
CODE
code here

Follow the instructions to modify the code
"""
    + COMMAND_COMMON
)

SYSTEM_PROMPT_APPEND = (
    """
You are a helpful code assistant
You will be given tow messages: instructions then context
The format will be
INSTRUCTIONS
instructions here
CODE
context here

Your response will be added after the context
Follow the instructions to produce the requested code
"""
    + COMMAND_COMMON
)

SYSTEM_PROMPT_EXPLAIN = """
You are a helpful code assistant
Please explain the provided code
* Format each line to begin with "#"
* Keep line lengths under 80 characters
"""


def _calc_new_start(text: str, old_start: Position) -> Position:
    start = old_start.copy()
    newlines = [i for i, c in enumerate(text) if c == "\n"] + [0]
    last_newline = max(newlines)
    num_newlines = len(newlines) - 1
    if num_newlines > 0:
        start["line"] += num_newlines
        start["character"] = len(text) - last_newline - 1
    else:
        start["character"] += len(text)
    return start


def _parse_instructions_code(text: str) -> str:
    result = "INSTRUCTIONS\n"
    text_l = text.lstrip().split("\n")
    for i, line in enumerate(text_l):
        split_i = i
        if line == "" or not line.lstrip().startswith("#"):
            break
    instructions = "\n".join(text_l[:split_i])
    code = "\n".join(text_l[split_i:])
    result += instructions
    result += "\nCODE\n"
    result += code
    return result


@dataclass
class LLMCommand:
    title: str
    instruction: str
    input_parser: Callable[[str], str] = lambda x: x
    replace: bool = True


COMMANDS: dict[str, LLMCommand] = {
    "gay.maddie.complete": LLMCommand(
        "LLM Autocomplete",
        SYSTEM_PROMPT_COMPLETE,
    ),
    "gay.maddie.instructreplace": LLMCommand(
        "LLM Instruct (Replace)",
        SYSTEM_PROMPT_INSTRUCT,
        _parse_instructions_code,
    ),
    "gay.maddie.instructappend": LLMCommand(
        "LLM Instruct (Append)",
        SYSTEM_PROMPT_APPEND,
        _parse_instructions_code,
        False,
    ),
    "gay.maddie.explain": LLMCommand(
        "LLM Explain",
        SYSTEM_PROMPT_EXPLAIN,
        replace=False,
    ),
}


def pylsp_settings() -> dict[str, Any]:
    logger.info("Initializing pylsp_llmls")

    return {
        "plugins": {
            "pylsp_llmls": {
                "model": "ollama/deepseek-coder-v2:16b",
                "options": {},
            }
        }
    }


def execute_command(server: "LSPServer", params: ExecuteCommandParams) -> None:
    logger.info(f"workspace/executeCommand: {params}")
    # cfg = config.plugin_settings("pylsp_llmls")
    # model = cfg.get("model")
    # options = cfg.get("options", {})
    model = "ollama/deepseek-coder-v2:16b"
    options: dict[str, str] = {}
    command = params["command"]
    doc_uri, range_u, text = params["arguments"]
    doc_uri = cast(str, doc_uri)
    range = cast(Range, range_u)
    text = cast(str, text)

    command_info = COMMANDS.get(command)

    if command_info is None:
        return

    response = completion(
        model=model,
        messages=[
            {
                "role": "system",
                "content": command_info.instruction,
            },
            {"role": "user", "content": command_info.input_parser(text)},
        ],
        stream=True,
        **options,
    )

    if command_info.replace:
        edit: WorkspaceEdit = {
            "changes": {doc_uri: [{"range": range, "newText": ""}]}
        }
        logger.info("applying workspace edit: %s %s", command, edit)
        server.apply_edit(edit)
        start: Position = range["start"]
    else:
        start = range["end"]
        edit = {
            "changes": {
                doc_uri: [
                    {
                        "range": {"start": start, "end": start},
                        "newText": "\n\n\n",
                    }
                ]
            }
        }
        logger.info("applying workspace edit: %s %s", command, edit)
        server.apply_edit(edit)
        start["line"] += 2
        start["character"] = 0

    range["end"] = range["start"] = start

    for chunk in response:
        t = chunk.choices[0].delta.content
        if t is None:
            continue
        edit = {"changes": {doc_uri: [{"range": range, "newText": t}]}}
        logger.info("applying workspace edit: %s %s", command, edit)
        server.apply_edit(edit)
        start = _calc_new_start(t, start)
        range["end"] = range["start"] = start


def code_actions(
    server: "LSPServer", params: CodeActionParams
) -> list[CodeAction | Command] | None:
    uri = params["textDocument"]["uri"]
    document = server.get_document(uri)
    if document is None:
        logger.warn(f"doc not found: {uri}")
        return None
    logger.info(f"textDocument/codeAction: {document} {params}")
    range = params["range"]
    start_offset = document.offset_at_position(range["start"])
    end_offset = document.offset_at_position(range["end"])
    text = document.source[start_offset:end_offset]

    # ...
    range_d = cast(dict[str, Any], range)

    return [
        {
            "title": command.title,
            "kind": "source",
            "command": {
                "title": command.title,
                "command": command_name,
                "arguments": [document.uri, range_d, text],
            },
        }
        for command_name, command in COMMANDS.items()
    ]
