"""Shared Markdown parsing and path rules for vault maintenance."""

import datetime as dt
from pathlib import Path, PurePosixPath
import re

try:
    import yaml
except ImportError:
    requirements = Path(__file__).resolve().with_name("requirements.txt")
    raise SystemExit(f'Install the optional dependency: python -m pip install -r "{requirements}"')

FRONTMATTER = re.compile(r"\A\ufeff?---[ \t]*\r?\n(.*?)^---[ \t]*(?:\r?\n|\Z)", re.M | re.S)
SUPPORT_PATHS = {"AGENTS.md", "attachments", "templates", "vault-framework", "vault-tools"}


class VaultError(Exception):
    pass


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node):
    loader.flatten_mapping(node)
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str) or key in result:
            raise VaultError("Frontmatter keys must be unique strings")
        result[key] = loader.construct_object(value_node)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def text(data, path):
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise VaultError(f"{path}: expected UTF-8 text") from exc


def metadata(data, path):
    source = text(data, path)
    match = FRONTMATTER.match(source)
    if not match:
        if re.match(r"\A\ufeff?---[ \t]*(?:\r?\n|\Z)", source):
            raise VaultError(f"{path}: unclosed frontmatter")
        return {}, source
    try:
        value = yaml.load(match[1], Loader=UniqueLoader)
    # PyYAML's scalar constructors can raise native Python exceptions for
    # incomplete explicitly typed values, such as "!!timestamp tomorrow".
    except (yaml.YAMLError, VaultError, ValueError, TypeError, LookupError,
            AttributeError, OverflowError, RecursionError) as exc:
        raise VaultError(f"{path}: invalid frontmatter: {exc}") from exc
    if value is None:
        value = {}
    if not isinstance(value, dict):
        raise VaultError(f"{path}: frontmatter must be a mapping")
    return value, source[match.end():]


def excluded(path):
    parts = PurePosixPath(path).parts
    return (parts[0] in SUPPORT_PATHS or "guidelines" in parts
            or any(part.startswith(".") for part in parts))


def canonical(value):
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if isinstance(value, list):
        return [canonical(item) for item in value]
    if isinstance(value, dict):
        return {key: canonical(item) for key, item in value.items()}
    return value
