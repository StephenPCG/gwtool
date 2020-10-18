import os
import sys
import click
import logging
from pathlib import Path


from gwtool.utils import run_as_root, single_instance
from gwtool.env import env


@click.group('cli')
def cli():
    if sys.platform != 'linux':
        # we're probable on macos and debugging the script, don't run as root
        env.configure(workspace=Path(os.getcwd()) / 'example/')
        env.logger.setLevel(logging.DEBUG)
        env.logger.debug('Not on linux platform, running debug mode.')
    else:
        run_as_root()
        single_instance()
        # TODO, use env variables or cli args for env config
        env.configure()


@cli.group('setup', invoke_without_command=True)
@click.pass_context
def cli_setup(ctx):
    if ctx.invoked_subcommand is None:
        click.echo('running: setup all')
    else:
        click.echo(f'running: setup {ctx.invoked_subcommand}')


@cli_setup.command('firewall')
def cli_setup_firewall():
    pass


@cli_setup.command('route')
def cli_setup_route():
    pass


if __name__ == '__main__':
    cli()
