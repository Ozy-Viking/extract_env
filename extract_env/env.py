from __future__ import annotations

from collections import OrderedDict
from dataclasses import InitVar, dataclass, field
from pathlib import Path
import re
from typing import Any, DefaultDict, Literal, Optional, Self
from webbrowser import get
from icecream import ic

from extract_env.yaml_io import dump_yaml, get_comments, load_yaml

Source = Literal["compose"] | Literal["dot_env"]


@dataclass
class Env:
    key: str = ""
    value: str = ""
    com: InitVar[str] = ""
    line: Optional[int] = None
    services: list[str] = field(default_factory=list)
    source: Optional[Source] = None
    _comment: str = field(default="", init=False, repr=False)

    def __post_init__(self, com: str = ""):
        self.comment = com
        self.line = self.line if self.line or self.line == 0 else None

        self.key = self.key.strip(" \n") if self.key else ""
        if self.key and self.key.startswith("# "):
            self.comment = self.key
            self.key = ""

        self.value = self.value.strip(" \n") if self.value else ""
        if self.value and self.value.startswith("# "):
            self.comment = self.value
            self.value = ""
        if self.value and " #" in self.value:
            self.value, _, self.comment = self.value.partition(" #")

    @property
    def comment(self) -> str:
        return self._comment

    @comment.setter
    def comment(self, value: str) -> None:
        self._comment = value
        self.normalize_comment()

    def normalize_comment(self) -> Self:
        self._comment = self._comment.strip(" \n") if self._comment else ""
        if self._comment and self._comment.startswith("#"):
            self._comment = self._comment.lstrip("# \n")
        return self

    def __hash__(self) -> int:
        return hash((self.key, self.value))

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Env):
            return NotImplemented
        return self.key == other.key and self.value == other.value

    def __gt__(self, other: Any) -> bool:
        if not isinstance(other, Env):
            return NotImplemented
        if self.source == other.source:
            return False
        if self.source == "compose":
            return True
        elif other.source == "compose":
            return False
        return NotImplemented

    def __str__(self) -> str:
        ret_string = ""
        if self.key:
            ret_string += f"{self.key}={self.value}"
        if self.comment:
            space = " # " if self.key else "# "
            ret_string += space + self.comment
        return ret_string + "\n"

    def append_services(self, services: list[str] | str) -> Self:
        if isinstance(services, str):
            self.services = list(set([*self.services, services]))
        elif isinstance(services, list):
            self.services = list(set([*self.services, *services]))
        else:
            raise TypeError(f"Expected list or str, got {type(services)}")
        return self

    @property
    def construct(self) -> tuple[bool, bool, bool]:
        return (self.hasKey, self.hasValue, self.hasComment)

    @property
    def isBlankLine(self) -> bool:
        return self.construct == (False, False, False)

    @property
    def isCommentOnly(self) -> bool:
        return self.construct == (False, False, True)

    @property
    def hasKeyValuePair(self) -> bool:
        return self.hasKey and self.hasValue

    @property
    def hasKey(self) -> bool:
        return self.key is not None or self.key != ""

    @property
    def hasValue(self) -> bool:
        return self.value is not None or self.value != ""

    @property
    def hasComment(self) -> bool:
        return self.comment is not None or self.comment != ""

    @property
    def is_param_expansion(self) -> bool:
        value = self.value.strip("# \n")
        pattern = r"(?P<param>(?:^\$\{.*\}$)|(?:^\{\{.*\}\}$))"
        return bool(re.match(pattern, value))

    @property
    def param_expansion_key(self) -> str:
        value = self.value.strip("# \n")
        pattern = r"(?P<param>(?:^\$\{(?P<key1>.*)\}$)|(?:^\{\{(?P<key2>.*)\}\}$))"
        match = re.match(pattern, value)
        if not match:
            return ""
        else:
            return match.group("key1") or match.group("key2")

    @classmethod
    def from_string(
        cls,
        string: str,
        prefix: str = "",
        postfix: str = "",
        line: Optional[int] = None,
        service: Optional[str] = None,
        source: Optional[Source] = None,
    ) -> Env:
        if not isinstance(string, str):
            raise TypeError(f"Expected string, got {type(string)}")

        key = value = comment = ""
        string.strip(" \n")
        if string.startswith("# ") or string == "":
            return cls(
                key="",
                value="",
                com=string,
                line=line,
                services=[service] if service else [],
                source=source,
            )
        k, _, v = string.partition("=")

        k = k.strip(" \n")
        if k:
            key = f"{prefix}{k}{postfix}"

        v = v.strip(" \n")
        if v:
            value, _, comment = v.partition(" #")
            value = value.strip(" \n")
            comment = comment.strip(" \n")
        if not comment:
            comment = ""
        if not key:
            key = ""
        return cls(
            key=key,
            value=value,
            com=comment,
            line=line,
            services=[service] if service else [],
            source=source,
        )

    def to_compose_string(self) -> str:
        return f"${{{self.key}}}"


class EnvFile:
    envs: OrderedDict[int, Env]
    prefix: str
    postfix: str
    combine: bool
    use_current_env: bool
    compose_path: Path
    env_path: Path
    update_compose: bool
    env_file_read: bool = False
    compose_file_read: bool = False

    def __init__(
        self,
        envs: Optional[list[Env]] = None,
        prefix: str = "",
        postfix: str = "",
        combine: bool = True,
        use_current_env: bool = True,
        compose_path: Path = Path("./compose.yaml"),
        compose_file_text: str = "",
        env_path: Path = Path("./.env"),
        env_file_text: str = "",
        update_compose: bool = True,
    ) -> None:

        self.prefix = prefix
        self.postfix = postfix
        self.combine = combine
        self.use_current_env = use_current_env
        self.compose_path = Path(compose_path)
        self.env_path = Path(env_path)
        self.compose_file_text = compose_file_text
        self.env_file_text = env_file_text
        self.update_compose = update_compose

        if not self.env_path.exists():
            self.env_path.touch()
        if envs is None:
            envs = []
        if not isinstance(envs, list):
            raise TypeError(f"Expected list, got {type(envs)}")
        if len(envs) > 0:
            self.envs = OrderedDict({idx: x for idx, x in enumerate(envs)})
            self.update_keys()
        else:
            self.envs = OrderedDict()

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
                            f"Duplicate keys ({k}) with different values in compose file ('{self.compose_path}'): {value} != {env.value}"
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
        env: Env | str | list,
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
        elif isinstance(env, Env):
            if env.is_param_expansion:
                if self.env_file_read:
                    env_key = env.param_expansion_key
                    self[env_key].append_services(env.services)
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
        return f"{self.__class__.__name__}(envs={repr(self.envs)}, prefix='{self.prefix}', postfix='{self.postfix}', combine={self.combine}, use_current_env={self.use_current_env}, compose_path='{self.compose_path}', env_path='{self.env_path}')"

    def __str__(self):
        return self.envs.__repr__()

    def read_current_env_file(
        self,
    ) -> Self:
        self.env_file_read = True

        if not self.env_path.exists():
            self.env_path.touch()
            self.env_file_text = ""
            return self

        with open(self.env_path, "r") as file:
            self.env_file_text = file.read()
        for idx, line in enumerate(self.env_file_text.splitlines()):
            self.append(line, line=idx, source="dot_env", update_keys=False)
        self.update_keys()
        return self

    def read_compose_file(
        self,
    ):
        with open(self.compose_path, "r") as file:
            self.compose_file_text = file.read()
        data = load_yaml(self.compose_path)
        self.compose_file_read = True
        service_dict: dict[str, dict] = data["services"]
        service_keys: list[str] = data["services"].keys()

        env_dict_list: dict[str, list[str]] = {
            x: service_dict[x]["environment"]
            for x in service_keys
            if "environment" in service_dict[x].keys()
        }
        
        comment_dict: dict[str, Any] = {k: get_comments(data["services"][k]["environment"]) for k in service_keys if "environment" in data["services"][k].keys()}
        ic(comment_dict)
        if self.combine:
            self.combine_env(env_dict_list)
        else:
            self.split_env(env_dict_list)
        return self

    @staticmethod
    def flatten_list_with_service(
        input_list: dict[str, list[Any]]
    ) -> list[tuple[str, Any]]:
        return [(x, y) for x in input_list.keys() for y in input_list[x]]

    def combine_env(
        self,
        env_input: dict[str, list[str]],
    ) -> EnvFile:
        """For combining environment variables into a single dictionary with combined keys.

        Args:
            env_input (dict[str, list[str]]): Environment variables to combine from a docker compose file.

        Raises:
            ValueError: This is raised when duplicate keys are found with different values in the compose file.

        Returns:
            dict[str, str]: Combined environment variables.
        """
        env_list = self.flatten_list_with_service(
            {x: env_input[x] for x in env_input.keys()}
        )
        env_list = [
            Env.from_string(
                x[1], self.prefix, self.postfix, service=x[0], source="compose"
            )
            for x in env_list
        ]
        # TODO: Raise value error if duplicate keys are found with different values from the compose file.
        return self.append(env_list)

    def split_env(
        self,
        env_input: dict[str, list[str]],
    ) -> EnvFile:
        """Creates a dictionary of environment variables with the service name as a prefix.

        Args:
            env_input (dict[str, list[str]]): Environment variables to combine from a docker compose file.
            prefix (str): Prefix for the environment variable keys.
            postfix (str): Postfix for the environment variable keys.

        Returns:
            dict[str, str]: Combined environment variables.
        """
        services = env_input.keys()
        env_list = {}

        for service in services:
            service_label = service.upper().replace("-", "_")
            if self.prefix:
                prefix_service = f"{self.prefix}_{service_label}_"
            else:
                prefix_service = f"{service_label}_"

            postfix_service = f"_{self.postfix}" if self.postfix else ""

            env_list = env_input[service]
            for env in env_list:
                self.append(
                    Env.from_string(
                        env,
                        prefix_service,
                        postfix_service,
                        service=service,
                        source="compose",
                    ),
                    source="compose",
                )

        return self  # TODO: Implement the EnvFile

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

    def write(self, display: bool = False, write: bool = True) -> Self:
        print(f"\nWriting {self.stats["new"]} environment variable/s of a total {self.stats["total"]} to {self.env_path}\n")

        if self.env_with_no_services:
            print(
                f"\nFound {len(self.env_with_no_services)} environment variable/s with no docker services in '{self.env_path}':"
            )

            for env in self.env_with_no_services:
                print("- ", env.key)
            print()

        if display:
            print(f"\n# {self.env_path}\n")
            digits = len(str(len(self)))
            for line, env in self.envs.items():
                print(f"{line+1:<{digits}}", "|", str(env), end="")
            print(f"{line+2:<{digits}}", "|")

        if write:
            with open(self.env_path, "wt") as file:
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

    def update_compose_file(self, display: bool = False, write: bool = True) -> Self:
        compose_yaml = load_yaml(self.compose_path)
        env_services_dict = self.env_services_dict

        for service in env_services_dict:
            if "environment" not in compose_yaml["services"][service]:
                continue
            env_vars = [
                (idx, k.partition("=")[0])
                for idx, k in enumerate(
                    compose_yaml["services"][service]["environment"]
                )
            ]
            for idx, env in env_vars:
                compose_yaml["services"][service]["environment"][idx] = (
                    env + "=" + env_services_dict[service][env].to_compose_string()
                )
                
        
        
        if display:
            print(f"\n# {self.compose_path}\n")
            dump_yaml(compose_yaml)
            # digits = len(str(len(lines)))
            # for idx, line in enumerate(lines):
            #     print( f"{idx+1:<{digits}}", "|", line)
            # print( f"{idx+2:<{digits}}", "|")
        if write:
            dump_yaml(
                    compose_yaml,
                    self.compose_path
                )
            
        return self



if __name__ == "__main__":
    e = EnvFile()
