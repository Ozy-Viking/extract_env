#!/usr/bin/python3
import click
from icecream import ic

from extract_env import EnvFile

DEFAULTS = {
    "env": "./.env",
    "compose": "./compose.yaml",
    "combine": True,
    "prefix": "",
    "postfix": "",
    "update": True,
    "write": True,
    "display": False,
}


@click.command()
@click.option(
    "-e",
    "--env",
    default=DEFAULTS["env"],
    help=f'.env file to extract and make. Default: {DEFAULTS["env"]}',
    type=click.Path(),
)
@click.option(
    "-c",
    "--compose",
    default=DEFAULTS["compose"],
    help=f'Compose file to extract environment variables, this file must exist.  Default: {DEFAULTS["compose"]}',
    type=click.Path(exists=True),
)
@click.option(
    "-C/-N",
    "--combine/--no-combine",
    default=DEFAULTS["combine"],
    help=f'Combine like named environment variables.  Default: {DEFAULTS["combine"]}',
)
@click.option(
    "-p",
    "--prefix",
    default=DEFAULTS["prefix"],
    help=f'Prefix to add to all environment variable names.  Default: {DEFAULTS["prefix"]}',
)
@click.option(
    "--postfix",
    default=DEFAULTS["postfix"],
    help=f'postfix to add to all environment variable names.  Default: {DEFAULTS["postfix"]}',
)
@click.option(
    "-w/-d",
    "--write/--dry-run",
    default=DEFAULTS["write"],
    help=f'Write the environment variables to file.  Default: {DEFAULTS["write"]}',
)
@click.option(
    "--display/--no-display",
    default=DEFAULTS["display"],
    help=f'Displays the file output in the terminal.  Default: {DEFAULTS["display"]}',
)
@click.option(
    "-u/-n",
    "--update/--no-update",
    default=DEFAULTS["update"],
    help=f"Update the docker compose file with the new environment variable names.  Default: {DEFAULTS["update"]}",
)
@click.help_option("-h", "--help")
def main(**options):
    env_file = (
        EnvFile(
            prefix=options["prefix"],
            postfix=options["postfix"],
            combine=options["combine"],
            compose_path=options["compose"],
            env_path=options["env"],
            update_compose=options["update"],
        )
        .read_current_env_file()
        .read_compose_file()
    )
    env_file.write(write=options["write"], display=options["display"]).update_compose_file(write=options["write"], display=options["display"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
