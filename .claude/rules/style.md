# style.md

## Refactoring Approach

The script currently has security vulnerabilities and no error handling. Refactoring should prioritize safety over feature completeness.

**Priority order**:
1. Replace `os.system()` with `subprocess.run()` (security)
2. Add input validation (security)
3. Add error handling and return code checks (reliability)
4. Improve user feedback (UX)
5. Translate to English or make i18n friendly (maintainability)

## Language & Naming

**Current state**: All user prompts and internal comments are in Italian.

**Decision**: Keep Italian prompts as-is during refactoring unless explicitly asked to translate. This maintains the original author's intent and avoids breaking user workflows. Function and variable names should use English regardless (e.g., `validate_api_id()` not `valida_api_id()`).

**Future i18n**: If multi-language support is desired, extract prompts into a dictionary:
```python
messages = {
    "install_prompt": "installare requisiti? [Y/n]: ",
    "download_prompt": "scaricare telegram Desktop source? [Y/n]: ",
    # ...
}
```

## Code Organization

The current script is a single linear flow with no functions. When refactoring, consider:
- **Keep it flat**: Don't over-engineer with classes or utilities.
- **Extract validators**: Create small functions for `validate_voip_count()`, `validate_api_id()`, etc.
- **Extract subprocess calls**: Group Docker commands into clear helper functions (e.g., `build_docker_image()`, `run_build()`).

## Variable Naming

Use clear names over brevity:
- `c` → `download_choice` (line 9)
- `fin`, `fout` → `infile`, `outfile` (lines 15-16)
- `apiid`, `apihash` → keep these (they're clear in context)

## Error Messages

When replacing `os.system()` with subprocess, provide context in error messages:
```python
try:
    subprocess.run([...], check=True)
except subprocess.CalledProcessError as e:
    print(f"Docker build failed (exit code {e.returncode}). Check Docker installation.")
    exit(1)
```

## Testing

No automated tests currently exist. When refactoring:
- Unit test validators independently (no Docker needed)
- Manual test: run script with invalid inputs, verify rejection
- Manual test: run full build with real Docker, verify output and exit codes

## Linting

No linter config exists. When running Claude's edits, follow PEP 8 (4-space indents, snake_case functions, blank lines between sections).
