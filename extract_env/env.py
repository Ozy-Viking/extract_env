from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass
from itertools import count
from typing import Any, Optional, Self
from icecream import ic


@dataclass
class Env:
    key: str | None = None
    value: str | None = None
    comment: str | None = None
    line: Optional[int] = None
    services: list[str] = dataclass.field(default_factory=list)

    def __post_init__(self):
        self.key = self.key.strip(" \n") if self.key else None
        self.value = self.value.strip(" \n") if self.value else None
        self.comment = self.comment.strip(" \n") if self.comment else None
        self.line = self.line if self.line else None

        if self.value and " #" in self.value:
            self.value, _, self.comment = self.value.partition(" #")
        if self.value and self.value.startswith("# "):
            self.comment = self.value
            self.value = None
        if self.comment and not self.comment.startswith("#"):
            self.comment = "# " + self.comment
        if self.comment == "":
            self.comment = None

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Env):
            return NotImplemented
        return self.key == other.key and self.value == other.value

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

    @classmethod
    def from_string(
        cls,
        string: str,
        prefix: Optional[str] = None,
        postfix: Optional[str] = None,
        line: Optional[int] = None,
        service: Optional[str] = None,
    ) -> Env:
        if not isinstance(string, str):
            raise TypeError(f"Expected string, got {type(string)}")
        key = value = comment = None
        string.strip(" \n")
        if string.startswith("# ") or string == "":
            return cls(
                key=None,
                value=None,
                comment=string,
                line=line,
                services=[service] if service else [],
            )
        k, v = string.split("=")

        k = k.strip(" \n")
        if k:
            key = f"{prefix}{k}{postfix}"

        v = v.strip(" \n")
        if v:
            value, _, comment = v.partition(" #")
            value = value.strip(" \n")
            comment = comment.strip(" \n")
        if not comment:
            comment = None
        if not key:
            key = None
        return cls(
            key=key,
            value=value,
            comment=comment,
            line=line,
            services=[service] if service else [],
        )


class EnvFile:
    def __init__(
        self, envs: Optional[list[Env]] = None, prefix: str = "", postfix: str = ""
    ) -> None:
        self.prefix = prefix
        self.postfix = postfix
        if envs is None:
            envs = []
        if not isinstance(envs, list):
            raise TypeError(f"Expected list, got {type(envs)}")
        if len(envs) > 0:
            self.envs: OrderedDict[int, Env] = OrderedDict(
                {idx: x for idx, x in enumerate(envs)}
            )
        else:
            self.envs = OrderedDict()

        ic(self.find_duplicates())

    def keys(self):
        return [x.key for x in self.envs.values() if x.key is not None]

    def __getitem__(self, key: str) -> Env | None:
        if key in self.keys():
            for env in self.envs.values():
                if env.key == key:
                    return env
        return None

    def __setitem__(self, key: str, value: str):
        if key in self.keys():
            for env in self.envs.values():
                ic(env)
                if env.key == key:
                    env = value
        else:
            self.envs[len(self.envs)] = Env(key, value)
        ic(self.envs)

    def find_duplicates(self) -> set[str]:
        keys = self.keys()
        return {x for x in keys if keys.count(x) > 1}

    def append(self, env: Env | str | list) -> Self:
        if isinstance(env, str):
            env = Env.from_string(env, self.prefix, self.postfix)
            self.envs[len(self)] = env
        elif isinstance(env, list):
            for e in env:
                self.append(e)
        elif isinstance(env, Env):
            self.envs[len(self)] = env

        if isinstance(env, Env) and env.key and env.key in self.keys():
            for e in self.envs.values():
                if e.key == env.key:
                    e.services = list(set(*e.services, *env.services))
                    break
        dups = self.find_duplicates()
        count = 0
        del_keys = []
        for k in self.envs.keys():
            if self.envs[k].key in dups:
                count += 1
                if count > 1:
                    del_keys.append(k)
        for k in del_keys:
            del self.envs[k]
        return self

    def __iter__(self):
        return iter(self.envs.values())

    def __len__(self):
        return len(self.envs)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.envs})"

    def __str__(self):
        return f"{self.envs}"
