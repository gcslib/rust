# gcslib/rust

Rust programs built by Cargo, offline, from the crates your
`Cargo.lock` pins, with a pinned Rust.

A GCSL library for pekit, Peios's build tool. Import it as
`github.com/gcslib/rust`.

## Usage

In `workspace.gcsl`, register its toolchains:

```text
import Toolchain::* from "github.com/gcslib/gcc"
import Toolchain::* from "github.com/gcslib/rust"
import Toolchain from toolchain

pekitconf = {toolchains = [Toolchain::C gcc_x86_64, Toolchain::Rust rust_1_98]}
```

In a build file:

```text
import "github.com/gcslib/rust"

def build app() {
    = rust.cargo_build(dir("src"), rust.vendored(file("src/Cargo.lock")), bins = ["app"])
}
```

`src` is a Cargo workspace whose binaries include `app`.

## What it provides

- `rust_1_98`: Rust 1.98.1, each part pinned by its SHA-256, with the
  standard libraries for `x86_64-unknown-linux-gnu` and
  `x86_64-unknown-linux-musl`.
- `vendored(lock)`: every crate `lock` pins, from crates.io by its checksum
  or from a git repository by its commit, laid out as `cargo vendor` does.
- `cargo_build(src, vendor, bins)`: the binaries `bins` of a Cargo
  workspace, by default static musl programs.
- `crates(lock)` and `git_crates(lock)`: the crates a lock file pins.

It needs the [gcc](https://github.com/gcslib/gcc) and
[buildenv](https://github.com/gcslib/buildenv) libraries.

The comment at the top of `rust.gcsl` documents each in full.

## Status

gcslib is new, and its libraries' APIs can still change. Pin the commit you
build with: `pekit lock` does so in `pekit.lock`.

## Licence

MIT. See [LICENSE](LICENSE).
