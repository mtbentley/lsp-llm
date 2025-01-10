import io

from lsp_llm.lsp_types import Position, TextDocumentContentChangeEvent


class Document:
    def __init__(
        self, uri: str, source: str, version: int, lang_id: str
    ) -> None:
        self.uri = uri
        self.source = source
        self.version = version
        self.lang_id = lang_id

    def __str__(self) -> str:
        return self.uri

    @property
    def lines(self) -> list[str]:
        return self.source.splitlines(True)

    def update(
        self, change: TextDocumentContentChangeEvent, version: int
    ) -> None:
        text = change["text"]
        change_range = change["range"]
        self.version = version

        if not change_range:
            self.source = text

        start_line = change_range["start"]["line"]
        start_col = change_range["start"]["character"]
        end_line = change_range["end"]["line"]
        end_col = change_range["end"]["character"]

        if start_line == len(self.lines):
            self.source += text
            return

        new = io.StringIO()

        for i, line in enumerate(self.lines):
            if i < start_line:
                new.write(line)
                continue
            if i > end_line:
                new.write(line)
                continue
            if i == start_line:
                new.write(line[:start_col])
                new.write(text)
            if i == end_line:
                new.write(line[end_col:])

        self.source = new.getvalue()

    def offset_at_position(self, position: Position) -> int:
        return position["character"] + len(
            "".join(self.lines[: position["line"]])
        )
