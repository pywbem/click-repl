import click
import pytest

import click_repl

from click_repl.utils import debug_log  # TODO remove this
from tests import mock_stdin

# pylint: disable=disallowed-name


def test_simple_repl():
    @click.group()
    def cli():
        pass

    @cli.command()
    @click.option("--baz", is_flag=True)
    def foo(baz):
        print("Foo!")

    @cli.command()
    @click.option("--foo", is_flag=True)
    def bar(foo):
        print("Bar!")

    click_repl.register_repl(cli)

    with pytest.raises(SystemExit):
        cli(args=[], prog_name="test_simple_repl")


@pytest.mark.parametrize("allow_general_ops_value", [False, True])
def test_repl_dispatches_subcommand(capsys, allow_general_ops_value):
    @click.group(invoke_without_command=True)
    @click.pass_context
    def cli(ctx):
        if ctx.invoked_subcommand is None:
            click_repl.repl(ctx, allow_general_options=allow_general_ops_value)

    @cli.command()
    def foo():
        print("Foo!")

    with mock_stdin("foo\n"):
        with pytest.raises(SystemExit):
            cli(args=[], prog_name="test_repl_dispatches_subcommand")

    assert capsys.readouterr().out.replace("\r\n", "\n") == "Foo!\n"

# Test that group command and subcommands are called.  Includes
# setting the allow_general_options parameter on repl call.


@pytest.mark.parametrize("allow_general_ops_value", [None, False, True])
def test_group_command_called(capsys, allow_general_ops_value):
    @click.group(invoke_without_command=True)
    @click.pass_context
    def cli(ctx):
        print("cli()")
        if ctx.invoked_subcommand is None:
            if allow_general_ops_value is None:
                click_repl.repl(ctx)
            else:
                click_repl.repl(ctx,
                                allow_general_options=allow_general_ops_value)

    @cli.command()
    def foo():
        print("Foo!")

    @cli.command()
    def bar():
        print("Bar!")

    with mock_stdin("foo\nbar\n"):
        with pytest.raises(SystemExit):
            cli(args=[], prog_name="test_group_called")

    assert capsys.readouterr().out.replace("\r\n", "\n") == (
        "cli()\ncli()\nFoo!\ncli()\nBar!\n"
    )


@click.group(invoke_without_command=True)
@click.argument("argument", required=False)
@click.pass_context
def cli_arg_required_false(ctx, argument):
    if ctx.invoked_subcommand is None:
        click_repl.repl(ctx)


@cli_arg_required_false.command()
def foo():
    print("Foo")


@pytest.mark.parametrize(
    "args, stdin, expected_err, expected_output",
    [
        ([], "foo\n", click_repl.exceptions.InvalidGroupFormat, ""),
        (["temp_arg"], "", SystemExit, ""),
        (["temp_arg"], "foo\n", SystemExit, "Foo\n"),
    ],
)
def test_group_argument_with_required_false(
    capsys, args, stdin, expected_err, expected_output
):
    with pytest.raises(expected_err):
        with mock_stdin(stdin):
            cli_arg_required_false(args=args, prog_name="cli_arg_required_false")

    assert capsys.readouterr().out.replace("\r\n", "\n") == expected_output


#
# test_group_with_multiple_optional_args without allow_general_options parameter
#

@click.group(invoke_without_command=True)
@click.argument("argument")
@click.option("--option1", default=1, type=click.STRING)
@click.option("--option2")
@click.pass_context
def cmd(ctx, argument, option1, option2):
    print(f"cli({argument}, {option1}, {option2})")
    if ctx.invoked_subcommand is None:
        click_repl.repl(ctx)


@cmd.command("foo")
def foo2():
    print("Foo!")


@pytest.mark.parametrize(
    "args, expected",
    [
        (["hi"], "cli(hi, 1, None)\ncli(hi, 1, None)\nFoo!\n"),
        (
            ["--option1", "opt1", "hi"],
            "cli(hi, opt1, None)\ncli(hi, opt1, None)\nFoo!\n",
        ),
        (["--option2", "opt2", "hi"], "cli(hi, 1, opt2)\ncli(hi, 1, opt2)\nFoo!\n"),
        (
            ["--option1", "opt1", "--option2", "opt2", "hi"],
            "cli(hi, opt1, opt2)\ncli(hi, opt1, opt2)\nFoo!\n",
        ),
    ],
)
def test_group_with_multiple_optional_args(capsys, args, expected):
    with pytest.raises(SystemExit):
        with mock_stdin("foo\n"):
            cmd(args=args, prog_name="test_group_with_multiple_args")
    assert capsys.readouterr().out.replace("\r\n", "\n") == expected

# The following is same as test above but with the cli definition withinin the
# test function to be more readable.


@pytest.mark.parametrize(
    "args, expected",
    [
        (["hi"], "cli(hi, 1, None)\ncli(hi, 1, None)\nFoo!\n"),
        (
            ["--option1", "opt1", "hi"],
            "cli(hi, opt1, None)\ncli(hi, opt1, None)\nFoo!\n",
        ),
        (["--option2", "opt2", "hi"], "cli(hi, 1, opt2)\ncli(hi, 1, opt2)\nFoo!\n"),
        (
            ["--option1", "opt1", "--option2", "opt2", "hi"],
            "cli(hi, opt1, opt2)\ncli(hi, opt1, opt2)\nFoo!\n",
        ),
    ],
)
def test_group_with_multiple_optional_args2(capsys, args, expected):

    @click.group(invoke_without_command=True)
    @click.argument("argument")
    @click.option("--option1", default=1, type=click.STRING)
    @click.option("--option2")
    @click.pass_context
    def cmd_mult_args2(ctx, argument, option1, option2):
        print(f"cli({argument}, {option1}, {option2})")
        if ctx.invoked_subcommand is None:
            click_repl.repl(ctx)

    @cmd_mult_args2.command("foo")
    def foo():
        print("Foo!")

    with pytest.raises(SystemExit):
        with mock_stdin("foo\n"):
            cmd_mult_args2(args=args, prog_name="test_group_with_multiple_args2")
    assert capsys.readouterr().out.replace("\r\n", "\n") == expected


#
# test_group_with_optional_args_and_gen_ops_param includes allow_general_options
# parameter allow_general_options
# Test use of the allow_general_options parameter on repl(...)
#

@pytest.mark.parametrize(
    "args, cmd, expected",
    [
        (["hi"], '--option1 foo\n', "cli(hi, 1, None, False)\ncli(hi, 1, None)\nFoo!\n"),
        (["hi"], '--option1 foo\n', "cli(hi, 1, None, False)\ncli(hi, 1, None)\nFoo!\n"),

        # (
        #    # ["--option1", "opt1", "hi"],
        #    # "cli(hi, opt1, None)\ncli(hi, opt1, None)\nFoo!\n",
        # ),
        # (["--option2", "opt2", "hi"], "cli(hi, 1, opt2)\ncli(hi, 1, opt2)\nFoo!\n"),
        # (
        #    # ["--option1", "opt1", "--option2", "opt2", "hi"],
        #    # "cli(hi, opt1, opt2)\ncli(hi, opt1, opt2)\nFoo!\n",
        # ),
    ],
)
def test_group_with_optional_args_and_gen_ops_param(capsys, args, cmd, expected):

    class CtxObj():
        def __init__(self, option1):
            self.option1 = option1

    @click.group(invoke_without_command=True)
    @click.argument("argument")
    @click.option("--option1", default=1, type=click.STRING)
    @click.option("--option2", type=click.BOOL, default=False)
    @click.pass_context
    def cmd_allow_genops(ctx, argument, option1, option2):
        print(f"cli({argument}, {option1}, {option2})")
        if ctx.invoked_subcommand is None:
            ctx.obj = CtxObj(option1)
            click_repl.repl(ctx, allow_general_options=True)
        # Set on subsequent subcommands

    @cmd_allow_genops.command("foo")
    @click.option("--cmdoption1", type=click.STRING)
    @click.pass_obj
    def foo(context, options):
        assert isinstance(context, CtxObj), "context not instance of CtxObj"
        cmd_option1 = context["option1"]
        print(f"--{cmd_option1} Foo!")

    with pytest.raises(SystemExit):
        with mock_stdin(cmd):
            cmd_allow_genops(
                args=args,
                prog_name="test_group_with_optional_args_and_gen_ops_param")
    debug_log(f"Return from cmd3 {expected=}")
    results = capsys.readouterr().out.replace("\r\n", "\n")
    if results == expected:
        assert results == expected
    else:
        with capsys.disabled():
            print(f"ERROR {results=}")
        assert results == expected
