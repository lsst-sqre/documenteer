"""How a configuration file that does not validate ends a Sphinx build.

A ``documenteer.toml`` or ``technote.toml`` that does not validate is a
mistake in a file a documentation author wrote, and Documenteer composes a
message that says what is wrong with it and how to fix it. Getting that
message in front of the author is what this module is for.

Raising is not enough. Sphinx renders the failure instead of the message, and
two facts about how it does that leave no way to ask it not to. Both were
read from Sphinx 9.1.0 and reproduced on 8.2.3:

1. `sphinx._cli.util.errors.handle_exception` prints the "Configuration
   error!" banner, a versions block, the traceback context, the path of a
   saved traceback file, and an invitation to open an issue against
   sphinx-doc/sphinx for *every* `~sphinx.errors.SphinxError`, with
   `~sphinx.errors.ConfigError` among them. It branches on neither the
   exception's type nor its ``__cause__``, so neither a cleaner `ConfigError`
   nor ``raise ... from None`` removes any of it. (Sphinx 7 printed a
   `SphinxError` as two lines and no traceback; the crash frame is a Sphinx 8
   regression, and worth an upstream issue of its own.)

2. `sphinx.config.eval_config_file` catches `SystemExit` raised while
   :file:`conf.py` executes and re-raises it as a `ConfigError` saying the
   configuration file called `sys.exit`, which lands in the same frame as
   everything else. So ``sys.exit(2)`` at import time is not an exit either.

`os._exit` is the one exit Sphinx cannot intercept: it ends the process
without unwinding the stack, so no ``except`` and no ``finally`` between here
and the interpreter runs. Its cost is that nothing is flushed on the way out,
which is why both streams are flushed first, and that it is only ever right
when the process exists to run this one build. Everywhere else, and for every
programmatic caller of `documenteer.conf.DocumenteerConfig.load`, a
`ConfigError` is still raised and still catchable.

Documenteer itself is one of those callers: ``documenteer technote lint`` and
``documenteer technote sync-cff`` read a technote by running its Sphinx build
inside the command's own process, through the very presets ``sphinx-build``
imports. Exiting there would take the command down mid-run and its report
with it, so such a build runs under `raising_config_errors`, which puts the
`ConfigError` back.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import NoReturn

from sphinx.errors import ConfigError

__all__ = [
    "exit_on_config_error",
    "fail_config",
    "raising_config_errors",
]


_RAISE_INSTEAD_OF_EXITING: ContextVar[bool] = ContextVar(
    "documenteer_raise_config_errors", default=False
)
"""Whether a configuration failure raises rather than ending the process.

A context variable rather than a module global so that the choice belongs to
the caller that made it and unwinds with it, and so that a build driven on one
thread cannot change how a build on another reports.
"""

CONFIG_ERROR_EXIT_STATUS = 2
"""The status a build exits with when a configuration file is invalid.

It is the status Sphinx's own command-line failures use, so a Makefile or CI
job that only reads the exit code sees what it saw before.
"""


def fail_config(message: str, *, source: str) -> NoReturn:
    """Report a configuration problem and end the process.

    Parameters
    ----------
    message
        What is wrong with the file and how to fix it, already composed for
        whoever wrote the file.
    source
        The name of the file the problem is in, such as ``documenteer.toml``.

    Notes
    -----
    The message is printed under a one-line header naming the file, so that a
    problem stated in the file's own vocabulary — ``[[project.citations]]
    entry #1, field date`` — still says which file to open. A message that
    already opens by naming the file, as a validation report counting its
    problems does, keeps its own opening rather than being told twice.

    Raises
    ------
    sphinx.errors.ConfigError
        Raised, rather than the process being ended, inside
        `raising_config_errors`.

    See the module docstring for why this ends the process instead of raising.
    """
    text = message.strip()
    if source not in text.partition("\n")[0]:
        text = f"Configuration error in {source}:\n\n{text}"
    if _RAISE_INSTEAD_OF_EXITING.get():
        raise ConfigError(text)
    sys.stderr.write(f"\n{text}\n\n")
    # Nothing is flushed by os._exit, and stdout is where Sphinx has been
    # writing its progress up to now, so both streams are emptied here.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(CONFIG_ERROR_EXIT_STATUS)


@contextmanager
def exit_on_config_error(source: str) -> Iterator[None]:
    """Turn a `~sphinx.errors.ConfigError` raised inside the block into the
    report and exit of `fail_config`.

    Parameters
    ----------
    source
        The name of the configuration file the block reads.

    Notes
    -----
    This belongs only around work a configuration preset does while
    :file:`conf.py` is being imported. It is what makes every configuration
    failure of a build present identically, whether it comes from validating
    the file or from a check the preset makes afterwards.
    """
    try:
        yield
    except ConfigError as e:
        fail_config(str(e), source=source)


@contextmanager
def raising_config_errors() -> Iterator[None]:
    """Make a configuration failure inside the block raise
    `~sphinx.errors.ConfigError` instead of ending the process.

    This is for a Sphinx build Documenteer runs inside a process of its own
    that has other work to do — the in-process read behind ``documenteer
    technote lint`` and ``documenteer technote sync-cff``. Such a build's
    configuration failure is one result among several the command is
    collecting, so it has to come back as an exception the command can catch
    and report in its own voice.
    """
    token = _RAISE_INSTEAD_OF_EXITING.set(True)
    try:
        yield
    finally:
        _RAISE_INSTEAD_OF_EXITING.reset(token)
