import sys
from typing import OrderedDict, TextIO
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedSeq, Comment
from ruamel.yaml.tokens import CommentToken
from pathlib import Path
from icecream import ic

yaml = YAML(typ="rt")
yaml.indent(offset=2)


def load_yaml(file: Path):
    with open(file, "r") as f:
        return yaml.load(f)



def dump_yaml(data, stream: TextIO | Path=sys.stdout):
    return yaml.dump(data, stream=stream)


def get_comments(seq) -> dict[int, str]:
    comments = Comment()
    if "_yaml_comment" in dir(seq):
        comments = seq._yaml_comment
    else:
        return {}
    ret = {}

    for key, comment in comments.items.items():
        ret[key] = comment[0].value.strip()
    return ret


if __name__ == "__main__":
    compose = Path("example/compose.yaml")
    data = load_yaml(compose)

    dump_yaml(data)
