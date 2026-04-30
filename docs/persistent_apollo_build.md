# Persistent Apollo Build Cache

Add the following line to `.apollo.bazelrc`:

```text
startup --output_base="/apollo/.cache/output-base"
```

This keeps Bazel's output base in a stable location under `/apollo/.cache`
instead of the default location. On CADRI instances, that makes Apollo build
artifacts persist across shell sessions and container restarts as long as the
`/apollo` workspace volume is preserved.

After updating `.apollo.bazelrc`, run the normal Apollo build command. Bazel
will create `/apollo/.cache/output-base` on first use if it does not already
exist.
