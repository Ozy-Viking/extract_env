from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Optional
from typing import Self

from extract_env.abstract import File
from extract_env.compose import ComposeFile
from extract_env.envfile import EnvFile


class EnvList:

    def __init__(
        self,
        all_files: bool = True,
        combine: bool = True,
        compose_file: Optional[tuple[str | Path, ...]] = None,
        compose_folder="./",
        display: bool = False,
        env_file_name=".env",
        env_folder="./",
        postfix: str = "",
        prefix: str = "",
        update_compose: bool = True,
        use_current_env: bool = True,
        write: bool = True,
    ) -> None:
        self.compose_file: list[Path]
        if compose_file is not None:
            self.compose_file = [
                Path(p)
                for p in compose_file
                if isinstance(p, str) or isinstance(p, Path)
            ]
        else:
            self.compose_file = []
        self.all_files = all_files
        self.combine = combine
        self.updated = []

        self.compose_folder = Path(compose_folder)
        self.env_file_name = env_file_name
        self.env_folder = Path(env_folder)
        self.postfix = postfix
        self.prefix = prefix
        self.use_current_env = use_current_env
        self.preview_files = display
        self.write_files = {
            "compose": update_compose,
            ".env": write,
        }
        self.find_compose_files()
        self.find_env_files()
        self.envs: dict[str, dict[str, File]]
        self.init_envs()

        self.combine_files()
        self.update_files()

    def init_envs(self) -> Self:
        self.envs: dict[str, dict[str, File]] = {}
        for compose_name in self.compose_files:
            self.envs[compose_name] = OrderedDict()
        return self

    def find_env_files(self) -> Self:
        self.env_files = {}
        env_file_names = [x.env_file_name for x in self.compose_files.values()]
        print(env_file_names)
        for env_file_name in env_file_names:
            self.env_files[env_file_name] = EnvFile(self.env_folder / env_file_name)
        return self

    def find_compose_files(self) -> Self:
        if self.compose_file:
            self.compose_files = {}
            for file in self.compose_file:
                self.compose_files[file.name] = ComposeFile(
                    file,
                    combine=self.combine,
                    prefix=self.prefix,
                    postfix=self.postfix,
                    env_file_name_base=self.env_file_name,
                )
            return self

        elif self.all_files:
            try:
                self.compose_files = ComposeFile.find_files(
                    compose_folder=self.compose_folder,
                    combine=self.combine,
                    prefix=self.prefix,
                    postfix=self.postfix,
                    env_file_name_base=self.env_file_name,
                )
            except FileNotFoundError as e:
                print(e)
                raise SystemExit(1)
        else:
            raise ValueError(
                f"Compose files not specified nor all_files=True. Values are: {self.all_files=} {self.compose_file=}"
            )
        return self

    def update_env_files(self) -> Self:

        return self

    def combine_files(
        self,
    ) -> Self:
        for compose_name, compose_file in self.compose_files.items():
            self.envs[compose_name] = {
                "compose": compose_file,
                ".env": self.env_files[compose_file.env_file_name],
            }
            self.env_files[compose_file.env_file_name].append(
                env=compose_file.envs, source="compose"
            )
            if orphan_keys := self.keys_not_in_compose(compose_name):

                print(
                    f"\nFound {len(orphan_keys)} environment variable/s with no docker services in '{compose_file.file_path}':"
                )

                for key in orphan_keys:
                    print("- ", key)
                print()

        return self

    def keys_not_in_compose(self, compose_name: str) -> list[str]:
        return [
            key
            for key in self.envs[compose_name][".env"].keys()
            if key not in self.envs[compose_name]["compose"].keys()
        ]

    def update_files(self) -> Self:
        for file in self.envs.values():

            if self.preview_files:
                print("########   " + file["compose"].file_path.name + "   ########")

            file[".env"].update_file(
                write=self.write_files[".env"], display=self.preview_files
            )
            self.updated.append(file[".env"].file_path)
            file["compose"].update_file(
                write=self.write_files["compose"], display=self.preview_files
            )
            self.updated.append(file["compose"].file_path.name)
        print("# Files updated:", *self.updated, sep="\n-  ", end="\n\n")

        return self


if __name__ == "__main__":
    from extract_env.main import main

    raise SystemExit(main(default_map={"write": False, "display": False, "test": True}))
