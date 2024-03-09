from abc import ABC
from abc import abstractmethod
from pathlib import Path
from typing import OrderedDict
from typing import Self

from extract_env.env import Env


class File(ABC):
    def __init__(self) -> None:
        self.envs: OrderedDict
        self.file_read: bool
        self.file_path: Path

    @abstractmethod
    def read_file(self) -> Self: ...
    @abstractmethod
    def update_file(self, write: bool, display: bool) -> Self: ...

    @abstractmethod
    def __getitem__(self, key) -> Env: ...
    @abstractmethod
    def __setitem__(self, key, value): ...
    @abstractmethod
    def __delitem__(self, key): ...
    @abstractmethod
    def __eq__(self, __value: object) -> bool: ...
    @abstractmethod
    def __len__(self) -> int: ...
    @abstractmethod
    def keys(self) -> list[str]: ...
