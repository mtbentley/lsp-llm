import sys

from lsp_llm.python_lsp import LSPServer

from .python_lsp import start_io_lang_server


def main() -> None:
    stdin, stdout = sys.stdin.buffer, sys.stdout.buffer
    start_io_lang_server(stdin, stdout, True, LSPServer)
