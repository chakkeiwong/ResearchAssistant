from __future__ import annotations

from dataclasses import asdict, dataclass
import os
import subprocess
import time
from typing import Mapping, Sequence


DEFAULT_PARSER_TIMEOUT_SECONDS = 180
PARSER_TIMEOUT_ENV = "RA_PARSER_TIMEOUT_SECONDS"


@dataclass(frozen=True)
class ParserExecutionPolicy:
    timeout_seconds: int = DEFAULT_PARSER_TIMEOUT_SECONDS

    @classmethod
    def from_environment(cls) -> "ParserExecutionPolicy":
        raw = os.environ.get(PARSER_TIMEOUT_ENV)
        if raw is None:
            return cls()
        try:
            timeout_seconds = int(raw)
        except ValueError:
            return cls()
        return cls(timeout_seconds=timeout_seconds) if timeout_seconds > 0 else cls()


@dataclass(frozen=True)
class ParserCommandResult:
    command: list[str]
    returncode: int | None
    stdout: str
    stderr: str
    timeout_seconds: int
    duration_seconds: float
    timed_out: bool = False
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.returncode == 0 and not self.timed_out and self.error is None

    def diagnostics(self) -> dict[str, object]:
        payload = asdict(self)
        payload["stdout"] = self.stdout[-4000:]
        payload["stderr"] = self.stderr[-4000:]
        return payload


def run_parser_command(
    command: Sequence[str],
    *,
    policy: ParserExecutionPolicy | None = None,
    env: Mapping[str, str] | None = None,
) -> ParserCommandResult:
    execution_policy = policy or ParserExecutionPolicy.from_environment()
    command_list = [str(value) for value in command]
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command_list,
            capture_output=True,
            text=True,
            timeout=execution_policy.timeout_seconds,
            env=dict(env) if env is not None else None,
        )
        return ParserCommandResult(
            command=command_list,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            timeout_seconds=execution_policy.timeout_seconds,
            duration_seconds=round(time.monotonic() - started, 6),
        )
    except subprocess.TimeoutExpired as exc:
        return ParserCommandResult(
            command=command_list,
            returncode=None,
            stdout=_timeout_text(exc.stdout),
            stderr=_timeout_text(exc.stderr),
            timeout_seconds=execution_policy.timeout_seconds,
            duration_seconds=round(time.monotonic() - started, 6),
            timed_out=True,
            error=f"command timed out after {execution_policy.timeout_seconds} seconds",
        )
    except OSError as exc:
        return ParserCommandResult(
            command=command_list,
            returncode=None,
            stdout="",
            stderr="",
            timeout_seconds=execution_policy.timeout_seconds,
            duration_seconds=round(time.monotonic() - started, 6),
            error=str(exc),
        )


def _timeout_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value
