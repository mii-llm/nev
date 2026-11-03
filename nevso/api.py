"""Thin interface over the frozen controller and native model backends.

Install editable from the Nev checkout; models/builds remain in that checkout.
No downloads, global environment changes, or model imports happen on import.
"""
from copy import deepcopy
from dataclasses import dataclass
import importlib.util
import json
from pathlib import Path
import re
from threading import Lock
import time
from typing import Callable

from jsonschema import Draft202012Validator

_ARMS = {"rank": "nev_ranked", "select": "nev_selected", "none": "nesso_only"}
_RESERVED = {"__answer__", "__clarify__", "__unsupported__"}


def _load(path, name):
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing Nevso source: {path}. Install editable from the Nev checkout "
            "or pass repo_root='/path/to/nev'."
        )
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@dataclass(frozen=True)
class Tool:
    """A JSON-schema function and its Python handler, called with keyword args.

    description can be one string or {"en": "...", "it": "..."}.
    Handlers return JSON-serializable results; exceptions propagate to the caller.
    """
    name: str
    description: str | dict[str, str]
    parameters: dict
    handler: Callable

    def __post_init__(self):
        if not isinstance(self.name, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", self.name):
            raise ValueError("Tool names must be nonempty identifiers")
        if self.name in _RESERVED:
            raise ValueError("Tool name is reserved by the controller")
        if not callable(self.handler):
            raise TypeError("Tool handler must be callable")
        descriptions = self.description
        if isinstance(descriptions, str):
            descriptions = {"en": descriptions, "it": descriptions}
        if not isinstance(descriptions, dict) or set(descriptions) != {"en", "it"}:
            raise ValueError("Provide one description or both en and it descriptions")
        if any(not isinstance(v, str) or not v.strip() for v in descriptions.values()):
            raise ValueError("Tool descriptions must be nonempty strings")
        if not isinstance(self.parameters, dict) or self.parameters.get("type") != "object":
            raise ValueError("Tool parameters must be an object JSON schema")
        Draft202012Validator.check_schema(self.parameters)
        # Snapshot caller-owned dictionaries before registration.
        object.__setattr__(self, "description", deepcopy(descriptions))
        object.__setattr__(self, "parameters", deepcopy(self.parameters))

    def schema(self, language):
        return {"type": "function", "function": {
            "name": self.name, "description": self.description[language],
            "parameters": deepcopy(self.parameters),
        }}


class Agent:
    """Load once, run independent requests, then close (or use a with block).

    rank/select rank once per request, matching compare_routing.py. none skips
    Nev ranking, though both models remain loaded. Calls on one instance cannot
    overlap. A supplied backend is borrowed and is not closed by this wrapper.
    """

    def __init__(self, tools, *, engine="gguf", precision="q8", threads=4,
                 strategy="rank", repo_root=None, backend=None):
        if engine not in {"gguf", "cuda"}:
            raise ValueError("engine must be gguf or cuda")
        if precision not in {"q8", "f16"}:
            raise ValueError("precision must be q8 or f16 (GGUF only)")
        if type(threads) is not int or threads < 1:
            raise ValueError("threads must be a positive integer")
        if strategy not in _ARMS:
            raise ValueError("strategy must be rank, select or none")
        registered = list(tools)
        if not registered or any(not isinstance(t, Tool) for t in registered):
            raise ValueError("Provide a nonempty sequence of Tool objects")
        if len({t.name for t in registered}) != len(registered):
            raise ValueError("Tool names must be unique")
        # Snapshot schemas; later edits to a Tool cannot change the active registry.
        self._schemas = {lang: [t.schema(lang) for t in registered] for lang in ("en", "it")}
        self._handlers = {t.name: t.handler for t in registered}
        root = Path(repo_root).resolve() if repo_root else Path(__file__).resolve().parents[1]
        cpu = root / "experiments" / "cpu_gguf"
        self._runtime = _load(cpu / "abstract_agent" / "runtime.py", "_nevso_controller")
        self._owns_backend = backend is None
        if backend is None:
            if engine == "gguf":
                backend = _load(cpu / "cpu_backend.py", "_nevso_cpu_backend").Backend(
                    precision=precision, threads=threads)
            else:
                backend = _load(root / "experiments" / "abstract_agent" / "backend.py",
                                "_nevso_cuda_backend").Backend()
        self._backend = backend
        self._closed = False
        self._lock = Lock()
        self.strategy = strategy
        self.engine = engine
        self.precision = precision if engine == "gguf" else "nesso3_bf16_nev_fp32"

    def _execute(self, call):
        # The existing controller validates schema + grounding before dispatch.
        result = self._handlers[call["name"]](**deepcopy(call["arguments"]))
        # Fail loudly on unsupported outputs instead of feeding invented prose back.
        json.dumps(result, ensure_ascii=False, allow_nan=False)
        return deepcopy(result)

    def run(self, request, *, language="en", strategy=None):
        if not isinstance(request, str) or not request.strip():
            raise ValueError("request must be a nonempty string")
        if language not in {"en", "it"}:
            raise ValueError("language must be en or it")
        mode = self.strategy if strategy is None else strategy
        if mode not in _ARMS:
            raise ValueError("strategy must be rank, select or none")
        if not self._lock.acquire(blocking=False):
            raise RuntimeError("This Agent is busy; run requests sequentially")
        try:
            if self._closed:
                raise RuntimeError("Agent is closed")
            schemas = deepcopy(self._schemas[language])
            self._backend.synchronize()
            started = time.perf_counter()
            ranking = None
            if mode != "none":
                ranking = self._backend.rank(request, language, schemas, [], [], False)
                names = {s["function"]["name"] for s in schemas}
                probabilities = ranking["probabilities"]
                if set(probabilities) != names or ranking["choice"] not in names:
                    raise ValueError("Backend ranking does not match the tool registry")
                schemas.sort(key=lambda s: -probabilities[s["function"]["name"]])
                if mode == "select":
                    schemas = [s for s in schemas if s["function"]["name"] == ranking["choice"]]
            row = self._runtime.GenericAgent(self._backend).run(
                request, language, schemas, self._execute, "nesso_only", 7100)
            row.update(request=request, language=language, strategy=mode, arm=_ARMS[mode],
                       engine=self.engine, precision=self.precision, initial_ranking=ranking,
                       rank_ms=ranking["elapsed_ms"] if ranking else 0.0,
                       total_ms=(time.perf_counter()-started)*1000)
            return row
        finally:
            # Existing backends retain generation metrics; do not grow them forever
            # when the wrapper is used for many independent requests.
            if self._owns_backend and hasattr(self._backend, "generation_metrics"):
                self._backend.generation_metrics.clear()
            self._lock.release()

    def close(self):
        if not self._lock.acquire(blocking=False):
            raise RuntimeError("Cannot close an Agent while a request is running")
        try:
            if not self._closed:
                self._closed = True
                if self._owns_backend:
                    self._backend.close()
        finally:
            self._lock.release()

    def __enter__(self):
        if self._closed:
            raise RuntimeError("Agent is closed")
        return self

    def __exit__(self, *exc):
        self.close()


def format_trace(result):
    """Readable tool selection, validation, calls, observations and answer."""
    lines = [f"User ({result['language']}): {result['request']}",
             f"Strategy: {result['strategy']}"]
    ranking = result.get("initial_ranking")
    if ranking:
        lines.append("Nev initial choice: " + ranking["choice"])
    for event in result["trace"]:
        lines.append(f"\nTurn {event['turn']+1}; tools: " + ", ".join(event["tool_order"]))
        lines.append("Nesso3: " + event["assistant"])
        for item in event["validation"]:
            if item["error"]:
                lines.append("Rejected: " + json.dumps(item, ensure_ascii=False))
        for item in event["observations"]:
            lines.append(("Cached: " if item["cached"] else "Tool result: ")
                         + json.dumps(item, ensure_ascii=False))
    lines.extend([f"\nStatus: {result['status']}", "Errors: " + ", ".join(result["errors"]),
                  f"Elapsed: {result['total_ms']/1000:.2f} s"])
    return "\n".join(lines)
