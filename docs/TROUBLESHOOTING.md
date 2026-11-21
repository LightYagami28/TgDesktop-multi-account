# Troubleshooting

## Docker build fails

Check that Docker is installed and running, that the upstream `tdesktop/` source
is present as described in the [README](../README.md), and that the host has
enough disk space and memory for the build.

## Credentials or logs

The documented workflow requests credentials interactively and masks the
displayed prefix. Do not put credentials in command history, committed files, or
issue reports.

## Tests fail

Run the unit test and syntax-check commands in [Testing](TESTING.md), then
compare the failing step with the current CI workflow and `SPEC.md` status
notes.
