#!/usr/bin/python3
from typing import Any
import click
import yaml
from icecream import ic
from collections import OrderedDict

from .env import Env, EnvFile

DEFAULTS = {
    "env": "example/.env",
    "compose": "example/compose.yaml",
    "combine": True,
    "prefix": "",
    "postfix": "",
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
@click.help_option("-h", "--help")
def main(**options):
    env_file, initial_dov_env_text = read_current_env_file(options["env"])
    ic(initial_dov_env_text)
    read_compose_file(
        options["compose"],
        options["combine"],
        options["prefix"],
        options["postfix"],
        env_file,
    )

    return 0


def read_compose_file(
    compose_file: str,
    combine: bool = True,
    prefix: str = "",
    postfix: str = "",
    env_file: EnvFile = EnvFile(),
):
    with open(compose_file, "r") as file:
        data = yaml.safe_load(file)
    service_dict: dict[str, dict] = data["services"]
    service_keys: list[str] = data["services"].keys()
    env_dict_list: dict[str, list[str]] = {
        x: service_dict[x]["environment"]
        for x in service_keys
        if "environment" in service_dict[x].keys()
    }
    if combine:
        compose_env = combine_env(env_dict_list, prefix, postfix, env_file=env_file)
    else:
        compose_env = split_env(env_dict_list, prefix, postfix, env_file=env_file)
    return compose_env


def flatten_list_with_service(
    input_list: dict[str, list[Any]]
) -> list[tuple[str, Any]]:

    return [(x, y) for x in input_list.keys() for y in input_list[x]]


def combine_env(
    env_input: dict[str, list[str]],
    prefix: str,
    postfix: str,
    env_file: EnvFile = EnvFile(),
) -> EnvFile:
    """For combining environment variables into a single dictionary with combined keys.

    Args:
        env_input (dict[str, list[str]]): Environment variables to combine from a docker compose file.
        prefix (str): Prefix for the environment variable keys.
        postfix (str): Postfix for the environment variable keys.

    Raises:
        ValueError: This is raised when duplicate keys are found with different values in the compose file.

    Returns:
        dict[str, str]: Combined environment variables.
    """
    env_list = flatten_list_with_service({x: env_input[x] for x in env_input.keys()})
    env_list = [Env.from_string(x[1], prefix, postfix, service=x[0]) for x in env_list]


    return env_file.append(env_list)


def split_env(env_input: dict[str, list[str]], prefix: str, postfix: str,env_file: EnvFile = EnvFile(),) -> list[Env]:
    """Creates a dictionary of environment variables with the service name as a prefix.

    Args:
        env_input (dict[str, list[str]]): Environment variables to combine from a docker compose file.
        prefix (str): Prefix for the environment variable keys.
        postfix (str): Postfix for the environment variable keys.

    Returns:
        dict[str, str]: Combined environment variables.
    """
    services = env_input.keys()
    env_dict = {}

    for service in services:
        service_label = service.upper().replace("-", "_")
        if prefix:
            prefix_service = f"{prefix}_{service_label}_"
        else:
            prefix_service = f"{service_label}_"

        postfix_service = f"_{postfix}" if postfix else ""

        env_list = env_input[service]
        env_dict |= {
            f"{prefix_service}{s.split('=')[0]}{postfix_service}": s.split("=")[1]
            for s in env_list
        }

    return []  # TODO: Return the env_dict


def read_current_env_file(
    env_path: str,
) -> tuple[EnvFile, str]:
    ordered_env: OrderedDict[str, str] = OrderedDict()
    lines = []
    file_text: str
    with open(env_path, "r") as file:
        file_text = file.read()
        for idx, line in enumerate(file.readlines()):
            if not line.startswith("#") and line.strip() != "":
                k, v = line.split("=")
                ordered_env[k] = v.strip()
                v = v.strip(" \n")
                inline_comment = v.partition(" #")[2]
                lines.append(Env(k, v.split(" #")[0], inline_comment, idx + 1))
            else:
                lines.append(Env(None, None, line, idx + 1))

    return EnvFile(lines), file_text


if __name__ == "__main__":
    raise SystemExit(main())
