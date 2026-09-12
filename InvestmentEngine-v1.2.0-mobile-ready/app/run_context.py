from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from typing import Callable, Iterator, TypeVar

_ROOT_JOB_NAME: ContextVar[str] = ContextVar("rosa_root_job_name", default="")
_ROOT_RUN_KIND: ContextVar[str] = ContextVar("rosa_root_run_kind", default="legacy")

F = TypeVar("F", bound=Callable)


@contextmanager
def job_run_context(root_job_name: str, run_kind: str) -> Iterator[None]:
    """Annotate one top-level scheduler/CLI execution without changing job behavior."""
    job_token = _ROOT_JOB_NAME.set(root_job_name)
    kind_token = _ROOT_RUN_KIND.set(run_kind)
    try:
        yield
    finally:
        _ROOT_JOB_NAME.reset(job_token)
        _ROOT_RUN_KIND.reset(kind_token)


def current_job_context() -> tuple[str, str]:
    return _ROOT_JOB_NAME.get(), _ROOT_RUN_KIND.get()


def contextual_job(func: F, root_job_name: str, run_kind: str = "scheduled") -> F:
    """Wrap a scheduler callable so nested repository writes retain root provenance."""

    @wraps(func)
    def wrapped(*args, **kwargs):
        with job_run_context(root_job_name, run_kind):
            return func(*args, **kwargs)

    return wrapped  # type: ignore[return-value]
