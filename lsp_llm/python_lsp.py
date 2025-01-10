import errno
import logging
import os
import threading
from concurrent.futures import Future
from typing import Any, BinaryIO, Unpack

from pylsp_jsonrpc.dispatchers import MethodDispatcher  # type: ignore[import-untyped]
from pylsp_jsonrpc.endpoint import Endpoint  # type: ignore[import-untyped]
from pylsp_jsonrpc.streams import (  # type: ignore[import-untyped]
    JsonRpcStreamReader,
    JsonRpcStreamWriter,
)

from lsp_llm.document import Document
from lsp_llm.lsp_types import (
    ApplyWorkspaceEditParams,
    CodeAction,
    CodeActionParams,
    Command,
    DidChangeTextDocumentParams,
    DidCloseTextDocumentParams,
    DidOpenTextDocumentParams,
    Empty,
    ExecuteCommandParams,
    ExitArgs,
    InitializeParams,
    InitializeResult,
    LSPAny,
    RequestMessage,
    ResponseMessage,
    ServerInfo,
    ShutdownArgs,
    WorkspaceEdit,
)
from lsp_llm.plugin import code_actions, execute_command

log = logging.getLogger(__name__)

MAX_WORKERS = 64


class LSPServer(MethodDispatcher):
    def __init__(
        self,
        rx: BinaryIO,
        tx: BinaryIO,
        check_parent_process: bool,
    ) -> None:
        self._jsonrpc_stream_reader = JsonRpcStreamReader(rx)
        self._jsonrpc_stream_writer = JsonRpcStreamWriter(tx)
        self._endpoint = Endpoint(
            self, self._jsonrpc_stream_writer.write, max_workers=MAX_WORKERS
        )
        self._initialized = False
        self._shutdown = False
        self._check_parent_process = check_parent_process
        self.watching_thread: threading.Thread | None = None

    def start(self) -> None:
        self._jsonrpc_stream_reader.listen(self._endpoint.consume)

    def __getitem__(self, item: str) -> Any:
        if self._shutdown and item != "exit":
            log.debug(f"Ignoring non-exit method during shutdown: {item}")
            item = "invalid_request_after_shutdown"
        return super().__getitem__(item)

    def get_document(self, uri: str) -> Document | None:
        return self._documents.get(uri)

    def m_shutdown(self, **kwargs: Unpack[ShutdownArgs]) -> None:
        self._shutdown = True

    def m_invalid_request_after_shutdown(
        self, **kwargs: Unpack[RequestMessage]
    ) -> ResponseMessage:
        return {
            "error": {
                "code": -32600,  # invalid request TODO define elsewhere
                "message": "Request after shutdown not valid",
            },
        }

    def m_exit(self, **kwargs: Unpack[ExitArgs]) -> None:
        self._endpoint.shutdown()
        self._jsonrpc_stream_reader.close()
        self._jsonrpc_stream_writer.close()

    def capabilities(self) -> dict[str, Any]:  # TODO: replace with proper type
        server_caps = {
            "executeCommandProvider": {"commands": []},
            "textDocumentSync": {
                "change": 2,  # incremental TODO: define elsewhere
                "openClose": True,
            },
            "positionEncoding": "utf-8",
            "codeActionProvider": True,
        }

        return server_caps

    def _set_parent_check(self, pid: int) -> None:
        def watch_parent_process(pid: int) -> None:
            alive = True
            if pid < 0:
                alive = False
            try:
                os.kill(pid, 0)
            except OSError as e:
                alive = e.errno == errno.EPERM
            if not alive:
                self.m_exit()
            else:
                threading.Timer(10, watch_parent_process, args=[pid]).start()

        self.watching_thread = threading.Thread(
            target=watch_parent_process, args=(pid,)
        )
        self.watching_thread.daemon = True
        self.watching_thread.start()

    def m_initialize(
        self, **kwargs: Unpack[InitializeParams]
    ) -> InitializeResult:
        self._documents: dict[str, Document] = {}
        if (
            self._check_parent_process
            and kwargs["processId"]
            and self.watching_thread is None
        ):
            self._set_parent_check(kwargs["processId"])

        return InitializeResult(
            capabilities=self.capabilities(),
            serverInfo=ServerInfo(name="llmlsp"),
        )

    def m_initialized(self, **kwargs: Empty) -> None:
        pass

    def m_text_document__did_open(
        self, **kwargs: Unpack[DidOpenTextDocumentParams]
    ) -> None:
        doc = kwargs["textDocument"]
        uri = doc["uri"]
        source = doc["text"]
        version = doc["version"]
        lang_id = doc["languageId"]
        self._documents[uri] = Document(uri, source, version, lang_id)

    def m_text_document__did_close(
        self, **kwargs: Unpack[DidCloseTextDocumentParams]
    ) -> None:
        uri = kwargs["textDocument"]["uri"]
        if uri is None:
            return
        del self._documents[uri]

    def m_text_document__did_change(
        self, **kwargs: Unpack[DidChangeTextDocumentParams]
    ) -> None:
        uri = kwargs["textDocument"]["uri"]
        doc = self.get_document(uri)
        if doc is None:
            log.warn(f"Tried to modify document that's not open: {uri}")
            return
        changes = kwargs["contentChanges"]
        for change in changes:
            doc.update(change, kwargs["textDocument"]["version"])

    def m_text_document__code_action(
        self, **kwargs: Unpack[CodeActionParams]
    ) -> list[Command | CodeAction] | None:
        return code_actions(self, kwargs)

    def m_workspace__execute_command(
        self, **kwargs: Unpack[ExecuteCommandParams]
    ) -> LSPAny:
        return execute_command(self, kwargs)

    def apply_edit(self, edit: WorkspaceEdit) -> Future:
        wse: ApplyWorkspaceEditParams = {"edit": edit}
        f = self._endpoint.request("workspace/applyEdit", wse)

        return f


def start_io_lang_server(
    rfile: BinaryIO,
    wfile: BinaryIO,
    check_parent_process: bool,
    handler_class: type[LSPServer],
) -> None:
    log.info(f"Starting {handler_class.__name__} IO lang server")
    server = handler_class(rfile, wfile, check_parent_process)
    server.start()
