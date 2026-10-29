#!/usr/bin/env python3
"""Give a git repository's crate a manifest it can be built from on its own.

A crate of a git repository's workspace can take values from its
workspace's manifest, `version.workspace = true` and the like, and depend on
the repository's other crates by their paths. Vendored, each crate is a
directory of its own, apart from its workspace and its siblings, so this
writes its manifest for it: each value it takes from its workspace written
in, each path dependency on another crate of the repository a dependency
on that crate in the git source the lock pins them all from, at its exact
version, and its development dependencies, which Cargo never resolves for
a crate outside the workspace it builds, left out.

Usage: normalize.py REPOSITORY CRATE SOURCE OUTPUT, CRATE the crate's
directory from the repository's root, `.` for the root itself, and SOURCE
the git source `Cargo.lock` names it by, `git+URL?rev=REV`. OUTPUT is made a
copy of the crate's directory, its manifest written anew.
"""

import json
import os
import re
import shutil
import stat
import sys
import tomllib
from pathlib import Path

# The dependency tables of a manifest, or of a `[target.CFG]` table.
DEPENDENCIES = ("dependencies", "build-dependencies")
DEVELOPMENT = ("dev-dependencies", "dev_dependencies")

# The package fields that are paths, relative to the manifest that writes
# them.
PATHS = ("readme", "license-file")

# A key TOML takes without quotes.
BARE = re.compile(r"^[A-Za-z0-9_-]+$")


def read(path: Path) -> dict:
    """The manifest at `path`."""
    with path.open("rb") as file:
        return tomllib.load(file)


def workspace_root(repository: Path, crate: Path) -> Path:
    """The directory of the manifest with `[workspace]` at or above `crate`."""
    at = crate
    while True:
        manifest = at / "Cargo.toml"
        if manifest.is_file() and "workspace" in read(manifest):
            return at
        if at == repository:
            return crate
        at = at.parent


def packages(repository: Path) -> dict[Path, str]:
    """The version of each package of `repository`, by its directory."""
    found = {}
    for manifest in repository.rglob("Cargo.toml"):
        if any(part.startswith(".") or part == "target" for part in manifest.parts):
            continue
        package = read(manifest).get("package")
        if package is None or "name" not in package:
            continue
        version = package.get("version", "0.0.0")
        if isinstance(version, dict):
            root = workspace_root(repository, manifest.parent)
            version = read(root / "Cargo.toml")["workspace"]["package"]["version"]
        found[manifest.parent.resolve()] = version
    return found


def inherited(spec: dict, name: str, workspace: dict, root: Path) -> dict:
    """The dependency `spec` on `name` that takes its workspace's, written
    in: the workspace's, its features with the member's, and `optional` as
    the member says."""
    given = workspace.get("dependencies", {}).get(name)
    if given is None:
        raise SystemExit(f"`{name}` takes its workspace's dependency, which it has none of")
    base = {"version": given} if isinstance(given, str) else dict(given)
    if "path" in base:
        base["path"] = str((root / base["path"]).resolve())
    features = [*base.get("features", []), *spec.get("features", [])]
    if features:
        base["features"] = list(dict.fromkeys(features))
    if spec.get("optional"):
        base["optional"] = True
    return base


def git_source(source: str) -> dict:
    """The dependency fields naming the git source `source`, as `Cargo.lock`
    writes it: `git+URL?rev=REV` is `{git = URL, rev = REV}`."""
    url, _, query = source.removeprefix("git+").partition("?")
    fields = {"git": url}
    for pair in query.split("&") if query else []:
        name, _, given = pair.partition("=")
        fields[name] = given
    return fields


def dependencies(
    table: dict, crate: Path, root: Path, workspace: dict, versions: dict[Path, str], source: dict
) -> dict:
    """The dependency table `table` of the crate at `crate`, each that takes
    its workspace's written in, and each on a path one on that crate in the
    git source `source`, at its exact version."""
    written = {}
    for name, spec in table.items():
        if isinstance(spec, dict) and spec.get("workspace") is True:
            spec = inherited(spec, name, workspace, root)
        elif isinstance(spec, dict) and "path" in spec:
            spec = {**spec, "path": str((crate / spec["path"]).resolve())}
        if isinstance(spec, dict) and "path" in spec:
            version = versions.get(Path(spec["path"]))
            if version is None:
                raise SystemExit(f"`{name}` is at `{spec['path']}`, which is no crate of the repository")
            spec = {key: value for key, value in spec.items() if key not in ("path", "version")}
            spec = {**source, "version": f"={version}", **spec}
        written[name] = spec
    return written


def normalized(repository: Path, crate: Path, source: dict) -> dict:
    """The manifest of the crate at `crate`, of the git source `source`,
    normalized."""
    manifest = read(crate / "Cargo.toml")
    root = workspace_root(repository, crate)
    workspace = read(root / "Cargo.toml").get("workspace", {})
    versions = packages(repository)
    package = manifest.get("package", {})
    for key, value in list(package.items()):
        if isinstance(value, dict) and value.get("workspace") is True:
            value = workspace.get("package", {}).get(key)
            if value is None:
                raise SystemExit(f"`package.{key}` takes its workspace's, which it has none of")
            if key in PATHS:
                value = os.path.relpath(root / value, crate)
            package[key] = value
    for table in DEPENDENCIES:
        if table in manifest:
            manifest[table] = dependencies(manifest[table], crate, root, workspace, versions, source)
    for table in DEVELOPMENT:
        manifest.pop(table, None)
    for target in manifest.get("target", {}).values():
        for table in DEPENDENCIES:
            if table in target:
                target[table] = dependencies(target[table], crate, root, workspace, versions, source)
        for table in DEVELOPMENT:
            target.pop(table, None)
    lints = manifest.get("lints")
    if isinstance(lints, dict) and lints.get("workspace") is True:
        manifest["lints"] = workspace.get("lints", {})
    # What only a workspace's root says, which a crate given on its own has
    # no workspace for.
    for key in ("workspace", "patch", "replace", "profile"):
        manifest.pop(key, None)
    return manifest


def key(text: str) -> str:
    """`text` as a TOML key."""
    return text if BARE.match(text) else json.dumps(text)


def value(item: object) -> str:
    """`item` as an inline TOML value."""
    if isinstance(item, bool):
        return "true" if item else "false"
    if isinstance(item, (int, float)):
        return json.dumps(item)
    if isinstance(item, str):
        return json.dumps(item)
    if isinstance(item, list):
        return "[" + ", ".join(value(each) for each in item) + "]"
    if isinstance(item, dict):
        return "{" + ", ".join(f"{key(k)} = {value(v)}" for k, v in item.items()) + "}"
    raise SystemExit(f"a manifest value of an unknown kind: {item!r}")


def section(path: list[str], table: dict, lines: list[str]) -> None:
    """The table `table` at `path` as a TOML section, its tables as sections
    below it, as manifests write them, `[package.metadata.x]` say, but a
    dependency table's, each dependency inline."""
    inline = bool(path) and path[-1] in DEPENDENCIES
    lines.append("\n[" + ".".join(key(part) for part in path) + "]")
    lines.extend(
        f"{key(k)} = {value(v)}" for k, v in table.items() if inline or not isinstance(v, dict)
    )
    for name, below in table.items():
        if not inline and isinstance(below, dict):
            section([*path, name], below, lines)


def toml(manifest: dict) -> str:
    """`manifest` as TOML: its plain values first, arrays of tables among
    them, then each table as a section."""
    lines = [f"{key(k)} = {value(v)}" for k, v in manifest.items() if not isinstance(v, dict)]
    for name, table in manifest.items():
        if isinstance(table, dict):
            section([name], table, lines)
    return "\n".join(lines).lstrip("\n") + "\n"


def main() -> None:
    repository = Path(sys.argv[1]).resolve()
    crate = (repository / sys.argv[2]).resolve()
    source = git_source(sys.argv[3])
    output = Path(sys.argv[4])
    shutil.copytree(crate, output, symlinks=True)
    # The copy keeps the store's modes, so its directory is read-only:
    # writable just long enough to replace the manifest.
    mode = output.stat().st_mode
    output.chmod(mode | stat.S_IWUSR)
    manifest = output / "Cargo.toml"
    manifest.unlink()
    manifest.write_text(toml(normalized(repository, crate, source)))
    manifest.chmod(0o444)
    output.chmod(mode)


if __name__ == "__main__":
    main()
