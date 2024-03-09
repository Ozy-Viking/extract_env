from pathlib import Path
from typing import Literal

Source = Literal["compose"] | Literal["dot_env"]


def print_file_to_terminal(
    path: Path | str, document_lines: list[str], display_line_num: bool = True
) -> None:

    print(f"\n# {Path(path).absolute()}\n")
    digits = len(str(len(document_lines)))
    for idx, line in enumerate(document_lines):
        line = line.rstrip("\n")
        line_info = f"{idx+1:<{digits}} | " if display_line_num else ""
        print(line_info, line)
    end_line_info = f"{len(document_lines)+1:<{digits}} |" if display_line_num else ""
    print(f"{end_line_info}", "\n")
