from __future__ import annotations

from typing import Any, NotRequired, TypedDict

type LSPAny = LSPObject | LSPArray | str | int | float | bool | None

type LSPObject = dict[str, LSPAny]

type LSPArray = list[LSPAny]


class Empty(TypedDict):
    pass


ShutdownArgs = Empty
ExitArgs = Empty


class Message(TypedDict):
    jsonrpc: NotRequired[str]


class RequestMessage(Message):
    id: str | int
    method: str
    params: NotRequired[LSPArray | LSPObject]


class ResponseMessage(Message):
    id: str | int | None
    result: NotRequired[LSPAny]
    error: NotRequired[ResponseError | None]


class ResponseError(TypedDict):
    code: int
    message: str
    data: NotRequired[LSPAny]


class WorkDoneProgressParam(TypedDict):
    workDoneToken: NotRequired[str | int]


class PartialResultParams(TypedDict):
    partialResultToken: NotRequired[Any]  # TODO: finish


class Diagnostic(TypedDict):
    range: Range
    severity: NotRequired[int]  # TODO: enum
    code: NotRequired[int | str]
    codeDescription: NotRequired[Any]  # TODO: finish
    souce: NotRequired[str]
    message: str
    tags: NotRequired[list[int]]  # TODO: enum
    relatedInformation: NotRequired[list[Any]]  # TODO: finish
    data: NotRequired[LSPAny]


class CodeActionContext(TypedDict):
    diagnostics: list[Diagnostic]
    only: NotRequired[list[str]]  # TODO: enum
    triggerKind: NotRequired[int]  # TODO: enum


class CodeActionParams(WorkDoneProgressParam, PartialResultParams):
    textDocument: TextDocumentIdentifier
    range: Range
    context: CodeActionContext


class TextEdit(TypedDict):
    range: Range
    newText: str


class WorkspaceEdit(TypedDict):
    changes: NotRequired[dict[str, list[TextEdit]]]
    documentChanges: NotRequired[list[Any]]  # TODO: finish
    changeAnnotations: NotRequired[dict[str, Any]]  # TODO: finish


class Command(TypedDict):
    title: str
    command: str
    arguments: NotRequired[list[LSPAny]]


class CodeAction(TypedDict):
    title: str
    kind: NotRequired[str]  # TODO: enum
    diagnostics: NotRequired[list[Diagnostic]]
    isPreferred: NotRequired[bool]
    disabled: NotRequired[Any]  # TODO: finish
    edit: NotRequired[WorkspaceEdit]
    command: NotRequired[Command]
    data: NotRequired[LSPAny]


class ExecuteCommandParams(WorkDoneProgressParam):
    command: str
    arguments: NotRequired[list[LSPAny]]


class ClientInfo(TypedDict):
    name: str
    version: NotRequired[str]


class WorkspaceFolder(TypedDict):
    uri: str
    name: str


class InitializeParams(WorkDoneProgressParam):
    processId: int | None
    clientInfo: NotRequired[ClientInfo]
    locale: NotRequired[str]
    rootPath: NotRequired[str | None]
    rootUri: str | None
    initializationOptions: NotRequired[LSPAny]
    capabilities: LSPObject  # TODO: properly make a class for this?
    trace: NotRequired[str]  # TODO: make an enum
    workspaceFolders: NotRequired[list[WorkspaceFolder] | None]


class ServerInfo(TypedDict):
    name: str
    version: NotRequired[str]


class InitializeResult(TypedDict):
    capabilities: LSPObject  # TODO: do this properly
    serverInfo: NotRequired[ServerInfo]


class TextDocumentItem(TypedDict):
    uri: str
    languageId: str
    version: int
    text: str


class TextDocumentIdentifier(TypedDict):
    uri: str


class VersionedTextDocumentIdentifier(TextDocumentIdentifier):
    version: int


class Position(TypedDict):
    line: int
    character: int


class Range(TypedDict):
    start: Position
    end: Position


class TextDocumentContentChangeEvent(TypedDict):
    range: NotRequired[Range]
    rangeLength: NotRequired[int]
    text: str


class DidChangeTextDocumentParams(TypedDict):
    textDocument: VersionedTextDocumentIdentifier
    contentChanges: list[TextDocumentContentChangeEvent]


class DidOpenTextDocumentParams(TypedDict):
    textDocument: TextDocumentItem


DidCloseTextDocumentParams = DidOpenTextDocumentParams


class ApplyWorkspaceEditParams(TypedDict):
    label: NotRequired[str]
    edit: WorkspaceEdit
