#!/usr/bin/env python3
"""Read what Cargo takes from a workspace's manifests that its plans omit.

`cargo metadata` and `cargo build --unit-graph` say nothing of a package's
`[lints]` table, nor of which of its targets have no test harness. This
reads each workspace member's manifest, and its workspace's, as Cargo does,
and writes, for each member, by its package ID:

- `lints`: the lint flags Cargo gives rustc, rustdoc and Clippy for the
  package's `[lints]`, ordered as Cargo orders them, then a `--check-cfg`
  for each name `unexpected_cfgs` declares;
- `check_cfg`: the `--check-cfg` flags Cargo gives every compile: `docsrs`
  and `test`, and the package's features;
- `plain`: the targets with `harness = false`, each `{kind, name}`;
- `doctest`: whether the package has a library whose documentation is
  tested.

Usage: manifests.py METADATA OUTPUT, METADATA what `cargo metadata` wrote.
"""

import json
import sys
import tomllib
from pathlib import Path

LEVELS = {"forbid": "--forbid", "deny": "--deny", "warn": "--warn", "allow": "--allow"}

# The crate types whose documentation Cargo tests: a library a test can link.
DOCTESTED = {"lib", "rlib", "proc-macro"}

# The manifest tables of targets that can have no harness, by their kind.
TARGET_TABLES = {"lib": "lib", "bin": "bin", "test": "test", "bench": "bench", "example": "example"}


def manifest(path: Path) -> dict:
    """Read the manifest at `path`."""
    with path.open("rb") as file:
        return tomllib.load(file)


def lints_of(package: dict, root: dict, where: str) -> dict:
    """The lints of the manifest `package`, its workspace's if it says so."""
    lints = package.get("lints", {})
    if lints.get("workspace") is True:
        if len(lints) != 1:
            raise SystemExit(f"{where}: `lints.workspace` takes no other keys beside it")
        return root.get("workspace", {}).get("lints", {})
    return lints


def lint_flags(lints: dict, where: str) -> list[str]:
    """The flags of `lints`, as Cargo's `lints_to_rustflags` orders them.

    Cargo sorts by priority, then by lint name, last first, then by flag.
    """
    found: list[tuple[int, str, str]] = []
    checked: list[str] = []
    for tool, table in lints.items():
        for name, config in table.items():
            if isinstance(config, str):
                level, priority = config, 0
            else:
                level, priority = config.get("level"), config.get("priority", 0)
                if tool == "rust" and name == "unexpected_cfgs":
                    checked.extend(config.get("check-cfg", []))
            if level not in LEVELS:
                raise SystemExit(f"{where}: lint `{tool}.{name}` has no level Cargo knows")
            option = (
                f"{LEVELS[level]}={name}" if tool == "rust" else f"{LEVELS[level]}={tool}::{name}"
            )
            found.append((priority, name, option))
    found.sort(key=lambda each: each[2])
    found.sort(key=lambda each: each[1], reverse=True)
    found.sort(key=lambda each: each[0])
    return [option for _, _, option in found] + [f"--check-cfg={each}" for each in checked]


def plain_targets(package: dict, name: str) -> list[dict]:
    """The targets of the manifest `package` that have no harness."""
    plain: list[dict] = []
    for key, kind in TARGET_TABLES.items():
        tables = package.get(key, {})
        for table in tables if isinstance(tables, list) else [tables]:
            if table.get("harness", True) is False:
                default = name.replace("-", "_") if kind == "lib" else name
                plain.append({"kind": kind, "name": table.get("name", default)})
    return plain


def main() -> None:
    """Write the facts of each workspace member."""
    metadata = json.loads(Path(sys.argv[1]).read_text())
    root = manifest(Path(metadata["workspace_root"]) / "Cargo.toml")
    members = set(metadata["workspace_members"])
    facts = []
    for package in metadata["packages"]:
        if package["id"] not in members:
            continue
        where = package["manifest_path"]
        own = manifest(Path(where))
        features = ", ".join(f'"{each}"' for each in sorted(package["features"]))
        facts.append(
            {
                "id": package["id"],
                "lints": lint_flags(lints_of(own, root, where), where),
                "check_cfg": [
                    "--check-cfg=cfg(docsrs,test)",
                    f"--check-cfg=cfg(feature, values({features}))",
                ],
                "plain": plain_targets(own, package["name"]),
                "doctest": any(
                    target.get("doctest", False) and DOCTESTED & set(target["crate_types"])
                    for target in package["targets"]
                ),
            }
        )
    Path(sys.argv[2]).write_text(json.dumps(facts))


if __name__ == "__main__":
    main()
