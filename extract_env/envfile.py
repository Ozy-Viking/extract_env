from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Any
from typing import DefaultDict
from typing import Optional
from typing import Self

from extract_env.abstract import File
from extract_env.env import Env
from extract_env.utils import Source
from extract_env.utils import print_file_to_terminal


class EnvFile(File):

    def __init__(
        self,
        file_path: Path | str | File = "./.env",
        prefix: str = "",
        postfix: str = "",
        use_current_env: bool = True,
        file_text: str = "",
        *,
        envs: Optional[list[Env]] = None,
    ) -> None:
        if isinstance(file_path, File):
            file_path = file_path.file_path
        self.file_path = Path(file_path)
        self.file_read = False
        self.prefix = prefix
        self.postfix = postfix
        self.use_current_env = use_current_env
        self.env_file_text = file_text

        if not self.file_path.exists():
            self.file_path.touch()
        if envs is None:
            envs = []
        if not isinstance(envs, list):
            raise TypeError(f"Expected list, got {type(envs)}")
        if len(envs) > 0:
            self.envs = OrderedDict({idx: x for idx, x in enumerate(envs)})
            self.update_keys()
        else:
            self.envs = OrderedDict()

        self.read_file()

    @property
    def next_key(self) -> int:
        return len(self.envs)

    def update_keys(
        self, remove_duplicates: bool = True, check_param_expansion: bool = True
    ) -> Self:
        if check_param_expansion:
            self.check_and_remove_parameter_expansion()
        current_dict = [(k, v) for k, v in enumerate(self.envs.values())]

        self.envs = OrderedDict({k: v for k, v in current_dict})
        if remove_duplicates:
            self.remove_duplicates()
        return self

    def keys(self):
        return [x.key for x in self.envs.values() if x.key is not None]

    def __getitem__(self, key: str | int) -> Env:
        if isinstance(key, int):
            return self.envs[key]
        elif isinstance(key, str):
            if key in self.keys():
                for env in self.envs.values():
                    if env.key == key:
                        return env
        else:
            raise NotImplementedError(
                f"Expected str or int for the key, got {type(key)}"
            )
        raise KeyError(f"Key '{key}' not found")

    def __setitem__(self, key: str | int, value: str | Env, update_keys: bool = True):

        if isinstance(key, int):
            if not isinstance(value, Env):
                raise TypeError(
                    f"Expected 'Env' when given a key if type int, got {type(value)}"
                )
            self.envs[key] = value
        elif isinstance(key, str):
            if isinstance(value, Env):
                raise TypeError(
                    f"Expected 'str' when given a key if type str, got '{type(value)}'"
                )
            if key in self.keys():
                for env in self.envs.values():
                    if env.key == key:
                        env = value
            else:
                self.envs[len(self)] = Env(key, value)
        else:
            raise NotImplementedError(
                f"Expected str or int for the key, got {type(key)}"
            )
        if update_keys:
            self.update_keys(check_param_expansion=False)

    def __delitem__(self, key: str | int, update_keys: bool = True):
        if isinstance(key, int):
            del self.envs[key]
        elif isinstance(key, str):
            if key in self.keys():
                for k, v in self.envs.items():
                    if v.key == key:
                        del self.envs[k]
        else:
            raise NotImplementedError(
                f"Expected str or int for the key, got {type(key)}"
            )
        if update_keys:
            self.update_keys(check_param_expansion=False)

    def find_duplicates(self) -> dict[str, int]:
        keys = [k for k in self.keys() if k is not None and k != ""]
        return {x: keys.count(x) for x in keys if keys.count(x) > 1}

    def remove_duplicates(self) -> Self:
        duplicates = self.find_duplicates()
        if not duplicates:
            return self

        duplicates_pos: dict[str, list[int]] = {}
        for kd in duplicates:
            duplicates_pos[kd] = []
            for k in self.envs:
                if self.envs[k].key == kd:
                    duplicates_pos[kd].append(k)

        best_of_the_dups: dict[str, dict[int, Env]] = {}
        for k, l in duplicates_pos.items():
            current = l[0]
            best_of_the_dups[k] = {current: self[current]}
            for idx, pos in enumerate(l):
                if idx == 0:
                    continue
                if self.envs[current] < self.envs[pos]:
                    current = l[idx]
                    best_of_the_dups[k] = {pos: self[pos]}
                elif self.envs[pos].source == "compose":
                    best_of_the_dups[k][pos] = self[pos]

            first = self[current]
            value = first.value
            first_pos = current
            if len(best_of_the_dups[k].values()) > 1:
                for idx, (pos, env) in enumerate(best_of_the_dups[k].items()):
                    if idx == 0:
                        value = env.value
                        first = env
                        first_pos = pos

                    elif value != env.value:
                        raise ValueError(
                            f"Duplicate keys ({k}) with different values: {value} != {env.value}"
                        )
                    elif value == env.value:
                        first.append_services(env.services)

                for ke in [*best_of_the_dups[k].keys()]:
                    if ke == first_pos:
                        continue
                    del best_of_the_dups[k][ke]

            first_position = self.first_pos_for_key(k)
            first_pos_comment = self[first_position].comment
            first.comment = first_pos_comment
            self.__setitem__(first_position, first, update_keys=False)
            del_list = sorted([x for x in l if x != first_position], reverse=True)
            for d in del_list:
                self.__delitem__(d, update_keys=False)
        self.update_keys(remove_duplicates=False)
        return self

    def first_pos_for_key(self, key: str) -> int:
        for k, v in self.envs.items():
            if v.key == key:
                return k
        raise KeyError(f"Key '{key}' not found")

    def check_and_remove_parameter_expansion(self) -> Self:
        pos_list = []
        for k, v in self.envs.items():
            if v.value and "${" in v.value:
                pos_list.append(k)
        for k in pos_list:
            del self[k]
        return self

    def append(
        self,
        env: Env | str | list | OrderedDict,
        source: Optional[Source] = None,
        line: Optional[int] = None,
        update_keys: bool = True,
    ) -> Self:
        if isinstance(env, str):
            env = Env.from_string(
                env, self.prefix, self.postfix, line=line, source=source
            )
            if env.is_param_expansion:
                if self.env_file_read:
                    env_key = env.param_expansion_key
                    self[env_key].append_services(env.services)
                return self

            self.envs.update({len(self): env})
        elif isinstance(env, list):
            for e in env:
                self.append(e, source, update_keys=False)
        elif isinstance(env, OrderedDict):
            for k, v in env.items():
                if isinstance(v, Env):
                    self.append(v, source, update_keys=False)
                else:
                    raise TypeError(f"Expected type 'Env' got {type(v)}")
        elif isinstance(env, Env):
            if env.is_param_expansion:
                if self.env_file_read:
                    env_key = env.param_expansion_key
                    if env_key in self.keys():
                        self[env_key].append_services(env.services)
                    elif env_key not in self.keys():
                        env.value = ""
                        env.comment = "Need to add a value for this parameter."
                        self.envs[len(self)] = env
                return self
            self.envs[len(self)] = env

        if isinstance(env, Env) and env.key and env.key in self.keys():
            for e in self.envs.values():
                if e.key == env.key:
                    e.append_services(env.services)
                    break

        if update_keys:
            self.update_keys()
        return self

    def __iter__(self):
        return iter(self.envs.items())

    def __len__(self):
        return len(self.envs)

    def __repr__(self):
        return f"{self.__class__.__name__}(envs={repr(self.envs)}, prefix='{self.prefix}', postfix='{self.postfix}',  use_current_env={self.use_current_env}, file_path='{self.file_path}')"

    def __str__(self):
        return self.envs.__repr__()

    def read_file(
        self,
    ) -> Self:
        self.env_file_read = True

        if not self.file_path.exists():
            self.file_path.touch()
            self.env_file_text = ""
            return self

        with open(self.file_path, "r") as file:
            self.env_file_text = file.read()
        for idx, line in enumerate(self.env_file_text.splitlines()):
            self.append(line, line=idx, source="dot_env", update_keys=False)
        self.update_keys()
        return self

    @staticmethod
    def flatten_list_with_service(
        input_list: dict[str, list[Any]]
    ) -> list[tuple[str, Any]]:
        return [(x, y) for x in input_list.keys() for y in input_list[x]]

    def move_to_end(self, key: str | int) -> Self:
        if isinstance(key, int):
            self.envs.move_to_end(key)
        elif isinstance(key, str):
            if key in self.keys():
                for k, v in self.envs.items():
                    if v.key == key:
                        self.envs.move_to_end(k)
        else:
            raise NotImplementedError(
                f"Expected str or int for the key, got {type(key)}"
            )
        self.update_keys()
        return self

    def insert(self, key: int, value: Env) -> Self:
        self.append(value)
        start = key
        end = len(self.envs) - 1
        step = 1

        for k in range(start, end, step):
            self.envs.move_to_end(k)
        self.update_keys()
        return self

    def sort(self) -> Self:
        self.envs = OrderedDict(sorted(self.envs.items(), key=lambda x: x[1].key))
        return self

    def __sorted__(self):
        return self.sort()

    @property
    def env_with_no_services(self) -> list[Env]:
        ret_list: list[Env] = []
        for k, v in self.envs.items():
            if v.key and not v.services:
                ret_list.append(v)
        return ret_list

    @property
    def stats(self) -> dict[str, int]:
        return {
            "total": len(self),
            "with_services": len([x for x in self.envs.values() if x.services]),
            "with_no_services": len([x for x in self.envs.values() if not x.services]),
            "new": len([x for x in self.envs.values() if x.source == "compose"]),
        }

    def update_file(self, display: bool = False, write: bool = True) -> Self:
        print(
            f'\nWriting {self.stats["new"]} new environment variable/s of a total {self.stats["total"]} to {self.file_path}\n'
        )

        if display:
            print_file_to_terminal(
                self.file_path,
                [str(x) for x in self.envs.values()],
                display_line_num=True,
            )

        if write:
            with open(self.file_path, "wt") as file:
                for line, env in self.envs.items():
                    file.write(str(env))
        return self

    @property
    def env_services_dict(self) -> dict[str, dict[str, Env]]:
        ret_dict = DefaultDict(dict)
        for env in self.envs.values():
            for service in env.services:
                ret_dict[service][env.key] = env
        return ret_dict

    def find_env_service(self, service_name: str, service_key: str) -> Env:
        """Find the environment variable linked to a particular service name.

        Args:
            service_name (str): The name of the service to the environment variable is in.
            service_key (str): The name of the environment variable key within than service.

        Raises:
            ValueError: More than 1 environment variable found for the service name and service key.
            KeyError: No environment variable found for the service name and service key.

        Returns:
            Env: _description_
        """
        results = []
        for env in self.envs.values():
            if service_name in env.in_services and service_key in env.service_keys:
                results.append(env)
        if len(results) > 1:
            raise ValueError(
                f"Found more than one environment variable for service '{service_name}'"
            )
        elif len(results) == 1:
            return results[0]
        else:
            raise KeyError(
                f"No environment variable found for service '{service_name}' with key '{service_key}'"
            )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EnvFile):
            return NotImplemented
        return self.envs == other.envs and self.file_path == other.file_path


if __name__ == "__main__":
    from extract_env.main import main

    raise SystemExit(
        main(default_map={"write": False, "display": True, "combine": True})
    )
