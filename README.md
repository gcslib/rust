# gcslib/rust

Rust programs and libraries built from the crates your `Cargo.lock`
pins, offline, with a pinned Rust: one crate at a time, each a step of its
own, or whole by Cargo.

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

In a build file, plan the Cargo workspace once and build what you need of
it:

```text
import "github.com/gcslib/rust"

def build app() {
    let ws = rust.workspace(dir("."), rust.vendored(file("Cargo.lock")))
    = rust.bin(ws, "app")
}

def test app_tests(tests: List<rust.RustTest> = rust.tests(rust.workspace(dir("."), rust.vendored(file("Cargo.lock"))), "app")) {
    let ran = for each in tests { = rust.run_test(each) }
}
```

Each crate, with the features Cargo resolves for the member you build,
each build script and each run of one is a step. A change rebuilds the
crates it reaches and no others, and programs that use the same crates,
with the same features, share them.

## What it provides

- `rust_1_98`: Rust 1.98.1, each part pinned by its SHA-256, with the
  standard libraries for `x86_64-unknown-linux-gnu` and
  `x86_64-unknown-linux-musl`, and Clippy.
- `vendored(lock)`: every crate `lock` pins, from crates.io by its checksum
  or from a git repository by its commit, laid out as `cargo vendor` does,
  a git crate's manifest written for it to build on its own when it takes
  values from its workspace's or names a sibling crate's path. A git crate
  from a repository the workspace also imports a library from must be at the commit the host pinned that library at
  (`libraries.pinned_libraries`), or the build fails saying which to update:
  the crates and the settings the library gives them are of one commit.
- `workspace(src, vendor)`: a Cargo workspace, planned by Cargo for
  `target`, by default `x86_64-unknown-linux-gnu`. Give `crates` the
  settings of packages that need more than their manifests say: files
  under the workspace that they read (`data`), files placed relative to a
  package's own directory (`beside`), environment variables (`env`), and
  files placed for them and everything that depends on them (`given`), a
  native library a build script links, say. `beside` is for a git crate
  that reads files of its repository outside its own directory, which
  vendoring leaves behind: `{at = "../shared/words.txt"; place = ...}` for
  a crate that `include_str!`s `../../shared/words.txt` from `src/lib.rs`.
- `bin(ws, package)`, `library(ws, package)`, `static_library(ws,
  package)`, `example(ws, package, name)`: a member's program, its shared
  library, its static archive and one of its examples that is a program,
  with `features` if given.
- `tests(ws, package)`: a member's test programs, with `features` if
  given, each integration test with the package's programs that
  `CARGO_BIN_EXE_<name>` names; `run_test(test)` runs one, with those
  programs where it was told, and `args` if given.
- `doctests(ws, package)`: a member's documentation tests, run by rustdoc
  as `cargo test --doc` runs them, each crate's a step.
- `clippy(ws, package)`: Clippy's checks of a member, as `cargo clippy
  --all-targets` makes them, each crate a step, with `flags` after its
  lints, `-Dwarnings` say, and the workspace's `clippy.toml` or
  `.clippy.toml` if it has one.
- `docs(ws, package)`: the documentation of a member's library, made by
  rustdoc as `cargo doc --no-deps` makes it, a step, with `flags` after
  its lints, `-Dwarnings` say.
- `cargo_build(src, vendor, bins)`: the binaries `bins` of a Cargo
  workspace, built whole by Cargo in one step, by default static musl
  programs. Give `target = "x86_64-unknown-linux-gnu"` for programs linked
  against glibc; the flags and the C compiler for crates' C follow the
  target.
- `crates(lock)` and `git_crates(lock)`: the crates a lock file pins.
- `default_rustflags(target)`, `default_target_c(target)` and
  `builtin_headers(c)`: the flags and the C toolchain a build for `target`
  takes unless given, and where a C toolchain's own headers are.

A member's crates are compiled with what Cargo takes from its manifest and
its plans leave out: its `[lints]`, its `--check-cfg` flags and which of its
targets have no test harness, which `manifests.py` reads, and link-time
optimization worked out per crate as Cargo works it out.

It needs the [gcc](https://github.com/gcslib/gcc),
[buildenv](https://github.com/gcslib/buildenv) and
[python](https://github.com/gcslib/python) libraries.

The comments at the top of `rust.gcsl` and `crates.gcsl` document each in
full.

## Status

gcslib is new, and its libraries' APIs can still change. Pin the commit you
build with: `pekit lock` does so in `pekit.lock`.

## Licence

MIT. See [LICENSE](LICENSE).
