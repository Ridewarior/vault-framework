# Releases

Each release uses the version in [framework/VERSION](../framework/VERSION). Its Git tag adds a leading `v`, as in `v0.1.0`, and points to the commit used for the build. Versions with a suffix, such as `v0.1.0-rc.1`, are prereleases.

The [release workflow](../.github/workflows/release.yml) runs the installer tests on Linux, macOS, and Windows. A successful build produces an unsigned x86-64 executable and an unsigned ARM64 executable for each operating system. The downloads also include a Unix launcher and a `SHA256SUMS` file.

A candidate branch can produce those files for testing. On `main`, the workflow can also create a GitHub release draft after approval. The maintainer publishes the draft when the downloads are ready. Each version has its own [release page](https://github.com/Ridewarior/vault-framework/releases). The launcher downloads the regular release marked as latest.
