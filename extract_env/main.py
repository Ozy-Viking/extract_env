#!/usr/bin/python3
from calendar import c
import click
from icecream import ic

from extract_env import EnvFile
from extract_env.envlist import EnvList

DEFAULTS = {
    "env_folder": "./example",
    "compose_folder": "./example",
    "combine": True,
    "prefix": "",
    "postfix": "",
    "update": True,
    "write": True,
    "display": False,
    "use_current_env": True,
    "env_file_name": ".env",
    "compose_file": None,
    "all_files": True,
}


@click.command()
@click.option(
    "-e",
    "--env_folder",
    default=DEFAULTS["env_folder"],
    help=f'Folder where the .env file/s to/are located. Default: {DEFAULTS["env_folder"]}',
    type=click.Path(),
)
@click.option(
    "--env-file-name",
    default=DEFAULTS["env_file_name"],
    help=f'Folder where the .env file/s to/are located. Default: {DEFAULTS["env_file_name"]}',
    type=click.Path(),
)
@click.option(
    "--use-current-env/--no-use-current-env",
    default=DEFAULTS["use_current_env"],
    help=f'Use the current env files. Default: {DEFAULTS["use_current_env"]}',
)
@click.option(
    "-c",
    "--compose-folder",
    default=DEFAULTS["compose_folder"],
    help=f'Folder where the compose file/s are located.  Default: {DEFAULTS["compose_folder"]}',
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
)
@click.option(
    "-C/-N",
    "--combine/--no-combine",
    default=DEFAULTS["combine"],
    help=f'Combine like named environment variables across services.  Default: {DEFAULTS["combine"]}',
)
@click.option(
    "-p",
    "--prefix",
    default=DEFAULTS["prefix"],
    help=f'Prefix to add to all environment variable names.  Default: "{DEFAULTS["prefix"]}"',
)
@click.option(
    "--postfix",
    default=DEFAULTS["postfix"],
    help=f'postfix to add to all environment variable names.  Default: "{DEFAULTS["postfix"]}"',
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
    "--update-compose/--no-update-compose",
    default=DEFAULTS["update"],
    help=f'Update the docker compose file with the new environment variable names.  Default: {DEFAULTS["update"]}',
)
@click.option(
    "-A/-O",
    "--all-files/--one-file",
    default=DEFAULTS["all_files"],
    help=f'Update the docker compose file with the new environment variable names.  Default: {DEFAULTS["all_files"]}',
)
@click.option(
    "-f",
    "--compose_file",
    default=DEFAULTS["compose_file"],
    help=f'Update this docker compose file with the new environment variable names, only used with "--one-file".  Default: {DEFAULTS["compose_file"]}',
)
@click.help_option("-h", "--help")
def main(
    all_files,
    combine,
    compose_file,
    compose_folder,
    display,
    env_file_name,
    env_folder,
    postfix,
    prefix,
    update_compose,
    use_current_env,
    write,
):
    # try:
    envs = EnvList(
        all_files=all_files,
        combine=combine,
        compose_file=compose_file,
        compose_folder=compose_folder,
        display=display,
        env_file_name=env_file_name,
        env_folder=env_folder,
        postfix=postfix,
        prefix=prefix,
        update_compose=update_compose,
        use_current_env=use_current_env,
        write=write,
    )

    return 0
    # except Exception as e:
    #     ic(e)
    #     return 1


if __name__ == "__main__":
    raise SystemExit(main(default_map={"write": False, "display": True}))
