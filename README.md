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
  `x86_64-unknown-linux-musl`, their source (`rust-src`), and Clippy.
- `vendored(lock)`: every crate `lock` pins, from crates.io by its checksum
  or from a git repository by its commit, laid out as `cargo vendor` does,
  a git crate's manifest written for it to build on its own when it takes
  values from its workspace's or names a sibling crate's path. A git crate
  from a repository the workspace also imports a library from must be at the commit the host pinned that library at
  (`libraries.pinned_libraries`), or the build fails saying which to update:
  the crates and the settings the library gives them are of one commit.
- `workspace(src, vendor)`: a Cargo workspace, planned by Cargo for
  `target`, by default `x86_64-unknown-linux-gnu`, and `profile`, by
  default `release`. `profile = "dev"` builds as `cargo build` does, and
  tests with the `test` profile, as `cargo test` does; any other profile,
  `quick` say, as `--profile` does. Build scripts are told `PROFILE` as
  Cargo tells them: `release` for a profile that inherits from `release`,
  `debug` otherwise. `profile_env` sets `CARGO_PROFILE_` variables for
  Cargo as it plans, `CARGO_PROFILE_DEV_DEBUG = "line-tables-only"` say.
  With `whole = true`, every crate has the features Cargo resolves for the
  whole workspace, as `cargo test --workspace` gives them, not those of
  the member alone. Give `crates` the
  settings of packages that need more than their manifests say: files
  under the workspace that they read (`data`), files placed relative to a
  package's own directory (`beside`), environment variables (`env`), and
  files placed for them and everything that depends on them (`given`), a
  native library a build script links, say. `beside` is for a git crate
  that reads files of its repository outside its own directory, which
  vendoring leaves behind: `{at = "../shared/words.txt"; place = ...}` for
  a crate that `include_str!`s `../../shared/words.txt` from `src/lib.rs`.
  Planning reads the manifests and the paths of the other files, but none
  under a hidden directory or one of `ignore`, paths relative to the
  workspace, by default `["target", "pekit-out"]`. Add a build's other
  outputs, such as `["target", "pekit-out", "docs/dist"]`, so that they
  don't plan the workspace again when they change. pekit lists nothing of
  a nested checkout or worktree, a directory holding a `.git` of its own.
  Planning doesn't read `.gitignore`. `cet`, on by default for an x86-64
  glibc target, `x86_64-*-gnu`, gives its crates control-flow protection:
  see below.
- `bin(ws, package)`, `library(ws, package)`, `static_library(ws,
  package)`, `example(ws, package, name)`: a member's program, its shared
  library, its static archive and one of its examples that is a program,
  with `features` if given.
- `tests(ws, package)`: a member's test programs, with `features` if
  given, each integration test with the package's programs that
  `CARGO_BIN_EXE_<name>` names, and the package's examples, which `cargo
  test` builds too; `benches(ws, package)`: its benchmarks, as `cargo test
  --benches` builds them; `run_test(test)` runs one from its package's
  directory, as Cargo does, with the package there, those programs where it
  was told, and `args` if given. The test program is at `/work/deps/<name>`
  and the examples at `/work/examples/<name>`, so that a test that looks
  for an example at `../../examples` from its own path, as in Cargo's
  target directory, finds it.
- `doctests(ws, package)`: a member's documentation tests, run by rustdoc
  as `cargo test --doc` runs them, each crate's a step.
- `clippy(ws, package)`: Clippy's checks of a member, as `cargo clippy
  --all-targets` makes them, each crate a step, with `flags` after its
  lints, `-Dwarnings` say, and the workspace's `clippy.toml` or
  `.clippy.toml` if it has one. Clippy's `cargo` lints read `cargo
  metadata`, which a crate's step cannot, so these checks allow them.
- `cargo_lints(ws)`: Clippy's `cargo` lints of the whole workspace, one
  step that plans as Cargo does with the network off, with `flags` if given,
  `-Wclippy::cargo -Dwarnings` say.
- `docs(ws, package)`: the documentation of a member's library, made by
  rustdoc as `cargo doc --no-deps` makes it, a step, with `flags` after
  its lints, `-Dwarnings` say.
- `cargo_build(src, vendor, bins)`: the binaries `bins` of a Cargo
  workspace, built whole by Cargo in one step, by default static musl
  programs. Give `target = "x86_64-unknown-linux-gnu"` for programs linked
  against glibc; the flags and the C compiler for crates' C follow the
  target. It gives no control-flow protection.
- `cet_std(rust, target)`: the standard libraries of `target`, built from
  the toolchain `rust`'s source for control-flow protection, as a sysroot.
- `crates(lock)` and `git_crates(lock)`: the crates a lock file pins.
- `default_rustflags(target)`, `default_target_c(target)`,
  `builtin_headers(c)` and `cxx_of(cc)`: the flags and the C toolchain a
  build for `target` takes unless given, where a C toolchain's own headers
  are, and the C++ compiler beside a C compiler.

A member's crates are compiled with what Cargo takes from its manifest and
its plans leave out: its `[lints]`, its `--check-cfg` flags and which of its
targets have no test harness, which `manifests.py` reads, and link-time
optimization worked out per crate as Cargo works it out. Its profile's
`strip` applies as Cargo applies it, and so do its `rustflags`, which
Cargo's `profile-rustflags` feature allows.

A build script that compiles C or C++ through the `cc` crate finds the C
compiler in `CC_<target>`, the C++ compiler beside it in `CXX_<target>`
(`x86_64-linux-g++` beside `x86_64-linux-gcc`), and the archiver in
`AR_<target>`. No pkg-config is pinned, so a build script's probe for a
system library fails the same way on every machine. A crate that falls
back without one, or loads its library at run time, builds. Give one that
needs a library both the library and what it needs to find it, through
`given` and `env`.

It needs the [gcc](https://github.com/gcslib/gcc),
[buildenv](https://github.com/gcslib/buildenv) and
[python](https://github.com/gcslib/python) libraries.

The comments at the top of `rust.gcsl` and `crates.gcsl` document each in
full.

## Control-flow protection

`workspace` gives the crates it compiles for an x86-64 glibc target,
`x86_64-*-gnu`, Intel's control-flow protection (CET): indirect-branch
tracking (IBT) and shadow stacks (SHSTK). A linker marks a program with
them only if every object it
links is marked, and upstream's prebuilt standard libraries aren't. So the
library builds the target's standard libraries again from the toolchain's
`rust-src`, each crate a step, cached and shared by every workspace that
uses the same toolchain and target:

- with the features upstream's have, `backtrace` and `panic-unwind`, but
  the C intrinsics of `compiler_builtins`, whose source `rust-src` lacks;
- with the `dist` profile upstream builds them with, so that a crate
  compiled with link-time optimisation finds their bitcode;
- with `-Zcf-protection=full` and `-Zforce-unstable-if-unmarked`, against
  an empty sysroot, so that nothing of upstream's reaches them;
- with their sources named `/rustc/COMMIT/library`, as upstream's are.

`cet_std(rust, target)` gives them as a sysroot. Every crate compiled for
the target is then compiled against that sysroot with
`-Zcf-protection=full`, and the C a build script compiles through the `cc`
crate with `-fcf-protection=full`, in `CFLAGS_<target>` and
`CXXFLAGS_<target>`. A package's `env` can set those itself.

The flags are unstable, and Rust 1.98.1 is stable. rustc alone is told
`RUSTC_BOOTSTRAP=1`, in the step that compiles a crate. Build scripts are
told neither it nor the flags, so a build script's probe of the compiler,
autocfg's say, finds the stable compiler it would find without CET. Build
scripts and procedural macros run on the build's own machine and are
compiled as before. `RUSTC_BOOTSTRAP` is unsupported upstream, so a flag's
behaviour can change between Rust versions: check a program's
`readelf -n` after a toolchain update.

A program is marked only if the C library's own objects it links are too:
its start files, `Scrt1.o`, `crti.o` and `crtn.o`, and
`libc_nonshared.a`. The gcc library's Bootlin glibc isn't built with CET,
so a program linked with `gcc_x86_64` is not marked, though every object
Rust compiled for it is.

It is on by default for an x86-64 glibc target. Give `workspace`
`cet = false` for upstream's standard libraries and no flags. It can't be
on for any other target: CET is x86-64's, and musl's assembly isn't
marked, so a static musl program could never be. `cargo_build`, which builds with Cargo whole, gives no
control-flow protection.

The first build for a target compiles the standard libraries: 42 steps,
about two and a half minutes on a 12-core machine, once per toolchain and
target, after which the store has them.

## Building with a distribution's flags

A distribution that builds another repository's definitions, as a
package workspace imports a project's library and builds `build app()`
from it, gives every crate that repository compiles its own rustc
arguments by setting the context `extra_rustflags`. They come after the
project's `rustflags` and its profile's, as `RUSTFLAGS` would, so they
can override the profile:

```text
import "github.com/gcslib/rust"
import build app from "github.com/example/app"

let flags = ["-Clink-arg=-Wl,--build-id=sha1", "-Cdebuginfo=2", "-Cstrip=none"]

def build main() {
    = build app() with { extra_rustflags = flags }
}
```

Here every program and library `app` builds has a build ID and keeps its
debug information, which a release profile with none would strip, for a
debug package to be split from it. The project needs no change for this.

They apply to crates compiled for the target, as `RUSTFLAGS` does with
`--target`: not to build scripts or procedural macros, which run on the
build's own machine. `workspace` and `cargo_build` read the context, so
every build through this library takes it, including a library's
definitions that pass `rustflags` of their own. A `with` reaches what it
calls and nothing else. Where nothing sets it, the context is empty and
every crate is compiled with the same arguments as without it.

## Status

gcslib is new, and its libraries' APIs can still change. Pin the commit you
build with: `pekit lock` does so in `pekit.lock`.

## Licence

MIT. See [LICENSE](LICENSE).
