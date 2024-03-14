import io
from pathlib import Path
from typing import TextIO

from ruamel.yaml import YAML
from ruamel.yaml.comments import Comment

yaml = YAML(typ="rt")
yaml.indent(offset=2)

output = io.StringIO()


def load_yaml(file: Path):
    with open(file, "r") as f:
        return yaml.load(f)


def dump_yaml(data, stream: TextIO | Path) -> None:
    """
    Dump YAML data to a stream.

    Args:
        data: The YAML data to be dumped.
        stream: The stream to write the YAML data to. It can be a file-like object or a file path.
    """
    yaml.dump(data, stream=stream)


def dump_yaml_to_string_lines(data) -> list[str]:
    """
    Dumps YAML data to a list of strings for representing a page.

    Args:
        data: The YAML data to be dumped.

    Returns:
        A list of strings representing the YAML data.
    """
    yaml.dump(data, stream=output)
    output.seek(0)
    return output.readlines()


def get_comments(seq) -> dict[int, str]:
    """Gets the comment from a Yaml sequence.

    Args:
        seq (_type_): A yaml sequence object with comments.

    Returns:
        dict[int, str]: Comments from the yaml sequence with line number as key.
    """

    comments = Comment()
    if "_yaml_comment" in dir(seq):
        comments = seq.ca
    else:
        return {}
    ret = {}

    for key, comment in comments.items.items():
        if not comment:
            continue
        ret[key] = comment[0].value.strip()
    return ret


if __name__ == "__main__":
    from extract_env.main import main

    raise SystemExit(main(default_map={"write": False, "display": False}))
