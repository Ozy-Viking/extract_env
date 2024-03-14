from __future__ import annotations

import re
from pathlib import Path
from typing import DefaultDict
from typing import Optional
from typing import OrderedDict
from typing import Self

from extract_env.abstract import File
from extract_env.env import Env
from extract_env.env import EnvService
from extract_env.utils import print_file_to_terminal
from extract_env.yaml_io import dump_yaml
from extract_env.yaml_io import dump_yaml_to_string_lines
from extract_env.yaml_io import get_comments
from extract_env.yaml_io import load_yaml


class ComposeFile(File):
    def __init__(
        self,
        file_path: Path | str | File,
        combine: bool = True,
        prefix: str = "",
        postfix: str = "",
        compose_name: Optional[str] = None,
        env_file_name_base: str = ".env",
    ):
        if isinstance(file_path, File):
            file_path = file_path.file_path
        self.file_path = Path(file_path)
        self.combine = combine
        self.prefix = prefix
        self.postfix = postfix
        self.compose_name = compose_name
        if self.compose_name is None:
            self.compose_name = self.get_re_compose_name()
        self.env_file_name_base = env_file_name_base
        self.env_services: set[EnvService] = set()
        self.service_envs = DefaultDict(OrderedDict)
        self.envs = OrderedDict()

        if not self.file_path.exists():
            raise FileNotFoundError(f"Compose file not found: {self.file_path}")
        self.read_file()

    def read_file(self):
        self.compose_yaml = data = load_yaml(self.file_path)
        self.compose_file_read = True

        service_dict: dict[str, dict] = data["services"]

        env_dict_list: dict[str, list[str]] = {
            x: service_dict[x]["environment"]
            for x in self.services
            if "environment" in service_dict[x].keys()
        }

        self.comments = {
            k: get_comments(data["services"][k]["environment"])
            for k in self.services
            if "environment" in data["services"][k].keys()
        }

        for service, env_list in env_dict_list.items():
            for line, env_raw in enumerate(env_list):
                env = Env.from_string(
                    env_raw,
                    line=line,
                    source="compose",
                    service_name=service,
                    prefix=self.prefix,
                    postfix=self.postfix,
                )
                self.env_services.add(env.services[0])
                if line in self.comments[service]:
                    env.comment = self.comments[service][line]
                self.service_envs[service][env.key] = env
        self.update_envs_from_service_env()
        return self

    def __str__(self) -> str:
        return f"{self.file_path}"

    def __repr__(self) -> str:
        return f"ComposeFile('{self.file_path}',compose_name={repr(self.compose_name)}, combine={self.combine}, prefix='{self.prefix}', postfix='{self.postfix}')"

    @property
    def env_file_name(self) -> str:
        if not self.compose_name:
            return f"{self.env_file_name_base}"
        return f"{self.env_file_name_base}.{self.compose_name}"

    def update_envs_from_service_env(self) -> Self:
        for sidx, (service, envs) in enumerate(self.service_envs.items()):
            if self.combine:
                if sidx == 0:
                    for env in envs.values():
                        self.envs[env.key] = env
                    continue
                for env in envs.values():
                    if env.key in self.envs:
                        self.envs[env.key].services.extend(env.services)
                        env.services = self.envs[env.key].services
                    else:
                        self.envs[env.key] = env

                continue
            else:
                for env in envs.values():
                    key = self.split_key(service, env)
                    env.key = key
                    self.envs[key] = env
        return self

    def split_key(self, service: str, env: Env) -> str:
        key = env.key

        if self.prefix != "":
            if self.prefix in key:
                key = key.removeprefix(self.prefix + "_")
            return f"{self.prefix.strip('_')}_{service.upper().replace('-', '_')}_{key.strip('_')}"

        return f"{service.upper().replace('-', '_')}_{env.key}"

    def keys(self) -> list[str]:
        return [*self.envs.keys()]

    def service_keys(self, service: str) -> list[str]:
        return [*self.service_envs[service].keys()]

    @property
    def services(self) -> list[str]:
        """
        List of services in the compose file.
        """
        return [*self.compose_yaml["services"].keys()]

    def update_yaml(self) -> Self:
        for env_service in self.env_services:
            env = env_service.parent_env
            if env is None:
                raise ValueError("EnvService has no parent Env")
            self.compose_yaml["services"][env_service.service]["environment"][
                env_service.line
            ] = (env_service.key + "=" + env.to_compose_string())
        return self

    def update_file(self, display: bool = False, write: bool = True) -> Self:
        self.update_yaml()
        if display:
            self.preview()

        if write:
            dump_yaml(self.compose_yaml, self.file_path)

        return self

    def preview(self) -> Self:
        compose_lines = dump_yaml_to_string_lines(self.compose_yaml)
        print_file_to_terminal(self.file_path, compose_lines, display_line_num=True)
        return self

    def __getitem__(self, key: str) -> Env:

        return self.envs[key]

    def __setitem__(self, key, value): ...
    def __delitem__(self, key: str):
        services = self.envs[key].services
        for service in services:
            del self.service_envs[service.service][service.key]

        del self.envs[key]

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, ComposeFile):
            return NotImplemented
        return self.file_path == __value.file_path

    def __len__(self) -> int:
        return len(self.envs)

    @staticmethod
    def regex_pattern() -> re.Pattern[str]:
        return re.compile(
            r"(?P<compose_path>(?:docker-)?compose(?:\.(?P<compose_name>.*))?\.ya?ml)"
        )

    def get_re_compose_name(self) -> str | None:
        if match := self.regex_pattern().match(self.file_path.name):
            return match.group("compose_name")

    def get_re_compose_path(self) -> str | None:
        if match := self.regex_pattern().match(self.file_path.name):
            return match.group("compose_path")

    @classmethod
    def find_files(
        cls,
        compose_folder,
        combine: bool = True,
        prefix: str = "",
        postfix: str = "",
        env_file_name_base: str = ".env",
    ) -> dict[str, ComposeFile]:
        dict_compose_files = {}
        compose_regex = cls.regex_pattern()
        folder = Path(compose_folder)
        for file in folder.iterdir():
            match = compose_regex.match(file.name)
            if match:
                compose_name = match.groupdict().get("compose_name")
                dict_compose_files[file.name] = cls(
                    file,
                    combine=combine,
                    prefix=prefix,
                    postfix=postfix,
                    compose_name=compose_name,
                    env_file_name_base=env_file_name_base,
                )
        if len(dict_compose_files) == 0:
            raise FileNotFoundError(f"No compose files found in: {folder.absolute()}")
        return dict_compose_files


if __name__ == "__main__":
    from extract_env.main import main

    raise SystemExit(main(default_map={"write": False, "display": True}))
