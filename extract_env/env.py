from __future__ import annotations

import re
from dataclasses import InitVar
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Optional
from typing import Self

from extract_env.utils import Source


@dataclass
class EnvService:
    service: str
    key: str
    parent_env: Optional[Env] = None
    line: Optional[int] = None
    source: Source = "compose"

    def __str__(self) -> str:
        return f"{self.service}"

    def __repr__(self) -> str:
        return (
            f"EnvService(service='{self.service}', key='{self.key}', line={self.line})"
        )

    def __hash__(self) -> int:
        return hash((self.service, self.key))

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, EnvService):
            return NotImplemented
        return (
            self.service == other.service
            and self.key == other.key
            and self.source == other.source
        )

    @property
    def parent_key(self) -> str:
        if self.parent_env:
            return self.parent_env.key
        raise AttributeError("No parent_env attribute found.")


@dataclass
class Env:
    key: str = ""
    value: str = ""
    com: InitVar[str] = ""
    line: Optional[int] = None
    services: list[EnvService] = field(default_factory=list)
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
            if self.is_param_expansion:
                return False
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

    def append_services(self, services: list[EnvService] | EnvService) -> Self:
        if isinstance(services, EnvService):
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
    def in_services(self) -> set[str]:
        return {x.service for x in self.services}

    @property
    def service_keys(self) -> set[str]:
        return {x.key for x in self.services}

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
        service_name: Optional[str] = None,
        source: Optional[Source] = None,
    ) -> Env:
        if not isinstance(string, str):
            raise TypeError(f"Expected string, got {type(string)}")

        string.strip(" \n")
        if string.startswith("# ") or string == "":
            return cls(
                key="",
                value="",
                com=string,
                line=line,
                services=[],
                source=source,
            )
        k, _, v = string.partition("=")
        k = k.strip(" \n")
        if service_name and source == "compose":
            service = EnvService(service=service_name, key=k, line=line, source=source)
        else:
            service = None

        key = value = comment = ""
        if prefix != "":
            prefix = f"{prefix}_"
        if postfix != "":
            postfix = f"_{postfix}"
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
        ret_cls = cls(
            key=key,
            value=value,
            com=comment,
            line=line,
            services=[service] if service else [],
            source=source,
        )
        if service:
            service.parent_env = ret_cls

        return ret_cls

    def to_compose_string(self) -> str:
        return f"${{{self.key}}}"


if __name__ == "__main__":
    from extract_env.main import main

    raise SystemExit(
        main(default_map={"write": False, "display": True, "combine": False})
    )
