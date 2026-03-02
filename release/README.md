# Building & Publishing

## Prerequisites

- Rust toolchain
- [cross](https://github.com/cross-rs/cross) for Linux builds (requires Docker)
- `npm` for publishing

## Build binaries

macOS:

```bash
cargo build --manifest-path cli/Cargo.toml --release
cargo build --manifest-path cli/Cargo.toml --release --target x86_64-apple-darwin
```

Linux (requires Docker):

```bash
cross build --manifest-path cli/Cargo.toml --release --target x86_64-unknown-linux-gnu
cross build --manifest-path cli/Cargo.toml --release --target aarch64-unknown-linux-gnu
```

Copy to dist folders:

```bash
cp cli/target/release/spec cli/dist-darwin-arm64/spec
cp cli/target/x86_64-apple-darwin/release/spec cli/dist-darwin-x64/spec
cp cli/target/x86_64-unknown-linux-gnu/release/spec cli/dist-linux-x64/spec
cp cli/target/aarch64-unknown-linux-gnu/release/spec cli/dist-linux-arm64/spec
```

## Publish to npm

```bash
cd release && bun run release
```

This packs all 4 platform binaries and publishes them to npm as `@workersio/spec`.
