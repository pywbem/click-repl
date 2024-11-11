from __future__ import with_statement

import sys
import click
import shlex
from prompt_toolkit.history import InMemoryHistory

from ._completer import ClickCompleter
from .exceptions import ClickExit  # type: ignore[attr-defined]
from .exceptions import CommandLineParserError, ExitReplException, InvalidGroupFormat
from .utils import _execute_internal_and_sys_cmds
from .core import ReplContext
from .globals_ import ISATTY, get_current_repl_ctx
from .utils import debug_log  # KS REMOVE


__all__ = ["bootstrap_prompt", "register_repl", "repl"]


def bootstrap_prompt(
    group,
    prompt_kwargs,
    ctx=None,
):
    """
    Bootstrap prompt_toolkit kwargs or use user defined values.

    :param group: click Group
    :param prompt_kwargs: The user specified prompt kwargs.
    """

    defaults = {
        "history": InMemoryHistory(),
        "completer": ClickCompleter(group, ctx=ctx),
        "message": "> ",
    }

    defaults.update(prompt_kwargs)
    return defaults


def repl(
    old_ctx, prompt_kwargs={}, allow_system_commands=True,
    allow_internal_commands=True, allow_general_options=False
    # pylint: disable=dangerous-default-value, too-many-locals
    # pylint: too-many-statements, too-many-branches
):
    """
    Start an interactive shell. All subcommands are available in it.

    :param old_ctx: The current Click context.
    :param prompt_kwargs: Parameters passed to
        :py:func:`prompt_toolkit.PromptSession`.

    If stdin is not a TTY, no prompt will be printed, but only commands read
    from stdin.
    """
    debug_log(f"repl enter {prompt_kwargs=}")  # KS REMOVE
    group_ctx = old_ctx
    # Switching to the parent context that has a Group as its command
    # as a Group acts as a CLI for all of its subcommands
    if old_ctx.parent is not None and not isinstance(old_ctx.command, click.Group):
        group_ctx = old_ctx.parent

    group = group_ctx.command

    # An Optional click.Argument in the CLI Group, that has no value
    # will consume the first word from the REPL input, causing issues in
    # executing the command
    # So, if there's an empty Optional Argument
    for param in group.params:
        if (
            isinstance(param, click.Argument)
            and group_ctx.params[param.name] is None
            and not param.required
        ):
            raise InvalidGroupFormat(
                f"{type(group).__name__} '{group.name}' requires value for "
                f"an optional argument '{param.name}' in REPL mode"
            )

    # Delete the REPL command from those available, as we don't want to allow
    # nesting REPLs (note: pass `None` to `pop` as we don't want to error if
    # REPL command already not present for some reason).
    repl_command_name = old_ctx.command.name
    if isinstance(group_ctx.command, click.CommandCollection):
        available_commands = {
            cmd_name: cmd_obj
            for source in group_ctx.command.sources
            for cmd_name, cmd_obj in source.commands.items()
        }
    else:
        available_commands = group_ctx.command.commands

    debug_log(f"{available_commands=}")  # KS REMOVE

    original_command = available_commands.pop(repl_command_name, None)

    repl_ctx = ReplContext(
        group_ctx,
        bootstrap_prompt(group, prompt_kwargs, group_ctx),
        get_current_repl_ctx(silent=True),
    )

    if ISATTY:
        # If stdin is a TTY, prompt the user for input using PromptSession.
        def get_command() -> str:
            return repl_ctx.session.prompt()  # type: ignore

    else:
        # If stdin is not a TTY, read input from stdin directly.
        def get_command() -> str:
            inp = sys.stdin.readline().strip()
            repl_ctx._history.append(inp)
            return inp

    with repl_ctx:
        while True:
            try:
                command = get_command()
            except KeyboardInterrupt:
                continue
            except EOFError:
                break

            if not command:
                if ISATTY:
                    continue
                else:
                    break

            try:
                args = _execute_internal_and_sys_cmds(
                    command, allow_internal_commands, allow_system_commands
                )
                if args is None:
                    continue

            except CommandLineParserError:
                continue

            except ExitReplException:
                break

            if allow_general_options:
                try:
                    args = shlex.split(command)
                    debug_log(f"repl 144, {command=}, {args=}")
                except ValueError as ve:
                    raise CommandLineParserError("{}".format(ve))

                try:
                    with group.make_context(None, args, parent=group_ctx) as ctx:
                        debug_log(f"group_make_context line 151, {args=}",
                                  pp=ctx.__dict__)
                        group.invoke(ctx)
                        ctx.exit()
                except click.ClickException as ec:
                    ec.show()
                except (ClickExit, SystemExit):
                    pass
                except ExitReplException:
                    break
            else:
                try:
                    # The group command will dispatch based on args.
                    old_protected_args = group_ctx.protected_args
                    try:
                        group_ctx.protected_args = args
                        debug_log(f"l170 {args=} {old_protected_args=} group_ctx=\n", pp=group_ctx.__dict__)
                        group.invoke(group_ctx)
                    finally:
                        group_ctx.protected_args = old_protected_args
                except click.ClickException as ec:
                    ec.show()
                except (ClickExit, SystemExit):
                    pass

                except ExitReplException:
                    break

    if original_command is not None:
        available_commands[repl_command_name] = original_command


def register_repl(group, name="repl"):
    """Register :func:`repl()` as sub-command *name* of *group*."""
    group.command(name=name)(click.pass_context(repl))
