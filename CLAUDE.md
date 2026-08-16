# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Summary

This is a Python utility that automates building custom Telegram Desktop with support for multiple accounts. It prompts the user for configuration, clones Telegram Desktop source, modifies the `kMaxAccounts` constant, and runs a Docker-based build.

## Critical Issues

**Shell injection vulnerability**: The script concatenates user input directly into `os.system()` calls (lines 22, 26). Refactoring to use `subprocess` with argument lists is a priority. See `@.claude/rules/security.md`.

**No error handling**: `os.system()` calls don't check return codes, so build failures may go unnoticed. When refactoring to subprocess, add return code validation.

**Input validation missing**: User inputs (voipn, API credentials) are unchecked. See `@.claude/rules/security.md` for constraints.

## Development

- **Language**: Python 3 (no external dependencies; calls Docker and git via subprocess)
- **Test approach**: Requires Docker and an Ubuntu 18/20+ environment. CI is not set up.
- **Prompts**: Currently all Italian. Translations should be discussed with team before changing.
- **Build quirks**: See `@.claude/rules/docker.md`.

## Code Style

See `@.claude/rules/style.md` for refactoring priorities and English/Italian naming decisions.

## Related Rules

- `@.claude/rules/security.md` — Shell injection, input validation, subprocess best practices
- `@.claude/rules/docker.md` — Docker build process, CentOS environment, build flags
- `@.claude/rules/style.md` — Code style and refactoring approach
