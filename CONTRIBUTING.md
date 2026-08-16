# Contributing to TgDesktop Multi-Account Builder

First off, thank you for considering contributing to TgDesktop Multi-Account Builder! It's people like you that make this tool such a great resource.

## Code of Conduct

This project and everyone participating in it is governed by the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the [issue list](https://github.com/LightYagami28/TgDesktop-multi-account/issues) as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

* **Use a clear and descriptive title**
* **Describe the exact steps which reproduce the problem**
* **Provide specific examples to demonstrate the steps**
* **Describe the behavior you observed after following the steps**
* **Explain which behavior you expected to see instead and why**
* **Include screenshots and animated GIFs if possible**
* **Include your environment details** (OS, Python version, Docker version)

### Security Vulnerabilities

**Do not** open public issues for security vulnerabilities. Instead, report directly to:

- **Telegram**: https://t.me/LightYagami28

Include as much detail as possible:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

* **Use a clear and descriptive title**
* **Provide a step-by-step description of the suggested enhancement**
* **Provide specific examples to demonstrate the steps**
* **Describe the current behavior and expected behavior**
* **Explain why this enhancement would be useful**

### Pull Requests

* Fill in [the required template](.github/pull_request_template.md)
* Follow the [Python style guide](#styleguides)
* Include appropriate test cases
* End all files with a newline
* Document new code based on the [Documentation Styleguide](#documentation-styleguide)

## Styleguides

### Python Style Guide

All Python code must adhere to [PEP 8](https://www.python.org/dev/peps/pep-0008/).

* Use 4 spaces for indentation
* Use snake_case for variables and functions
* Use UPPER_CASE for constants
* Maximum line length: 100 characters (except for URLs)
* Write docstrings for all public functions
* Write comments only when WHY is non-obvious

### Commit Messages

* Use the present tense ("Add feature" not "Added feature")
* Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
* Limit the first line to 72 characters or less
* Reference issues and pull requests liberally after the first line
* Consider starting the commit message with an applicable emoji:
  * 🎨 when improving the format/structure of the code
  * 🐛 when fixing a bug
  * 🚀 when improving performance
  * 📝 when writing docs
  * ✅ when adding tests
  * 🔒 when dealing with security
  * 🔧 when changing configuration files

### Documentation Styleguide

* Use Markdown
* Reference functions with backticks: `` `function_name()` ``
* Reference code blocks with triple backticks and language specification
* Use [Markdown headings](https://daringfireball.net/projects/markdown/syntax#header) instead of underlines

## Development Setup

1. **Fork the repository**
   ```bash
   git clone https://github.com/YOUR-USERNAME/TgDesktop-multi-account.git
   cd TgDesktop-multi-account
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run tests**
   ```bash
   python3 -m pytest test_telegram_maker.py -v
   ```

5. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Testing

* Write tests for new features
* Ensure all tests pass: `python3 -m pytest test_telegram_maker.py -v`
* Maintain or improve code coverage
* Test your changes with real Docker builds when possible

## Additional Notes

### Issue and Pull Request Labels

This section lists the labels we use to help organize and categorize issues and pull requests.

* `bug` - Something isn't working
* `enhancement` - New feature or request
* `documentation` - Improvements or additions to documentation
* `security` - Security related issues
* `performance` - Performance improvement
* `good first issue` - Good for newcomers
* `help wanted` - Extra attention is needed

### Attribution

This CONTRIBUTING guide is adapted from the [Atom Contributing Guide](https://github.com/atom/atom/blob/master/CONTRIBUTING.md).

---

**Thank you for contributing! 🎉**
