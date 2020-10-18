import os
import sys
import click
import socket
import logging
from pathlib import Path


from gwtool.utils import run_as_root, single_instance
from gwtool.env import env
from gwtool import libgw


@click.group('cli')
def cli():
    # if platform is not linux, run_as_root(), single_instance() will fail.
    if sys.platform != 'linux':
        raise Exception('This script can only be run on linux.')

    run_as_root()
    single_instance()

    fqdn = socket.getfqdn()
    if 'gateway' not in fqdn:
        # we're not on a gateway, may be just debugging the script
        env.configure(workspace=Path(os.getcwd()) / 'example/')
        env.logger.setLevel(logging.DEBUG)
        env.logger.info(f'Running: {" ".join(sys.argv)}')
        env.logger.warning('Not on a gateway box.')
        # loading gateway resources, will fail
        libgw.load()
    else:
        # TODO, use env variables or cli args for env config
        env.configure()
        env.logger.setLevel(logging.INFO)
        env.logger.info(f'Running: {" ".join(sys.argv)}')
        # loading gateway resources
        libgw.load()


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
