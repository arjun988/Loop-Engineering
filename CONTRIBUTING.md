# Contributing to Loop Engineering MCP Server

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## How to Contribute

### 1. Report Issues

Found a bug? Have a feature request?

- Check [existing issues](https://github.com/yourusername/loop-engineering/issues) first
- If not found, [create a new issue](https://github.com/yourusername/loop-engineering/issues/new)
- Provide clear description, steps to reproduce, expected vs actual behavior

### 2. Submit Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes
4. Test thoroughly (both Python and TypeScript if relevant)
5. Commit with clear messages: `git commit -m "feat: add new skill template"`
6. Push: `git push origin feature/your-feature-name`
7. Open a pull request

### 3. Add Skill Templates

New skill templates are highly valuable! To add one:

1. Create file in `shared/skills/your-skill-name.md`
2. Follow the template format (see existing skills)
3. Include:
   - Clear task description
   - Classification rules (if applicable)
   - Never do / Always do sections
   - Examples of good/bad outputs
   - Success criteria
4. Test with actual loop usage
5. Submit PR with description of use case

### 4. Improve Documentation

- Fix typos, improve clarity
- Add examples
- Update outdated information
- Translate to other languages

## Development Setup

### Python

```bash
cd python
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -e ".[dev]"
pytest
```

### TypeScript

```bash
cd typescript
npm install
npm run build
npm run dev  # for watch mode
```

## Code Style

### Python
- Follow PEP 8
- Use Black for formatting: `black .`
- Type hints where possible
- Docstrings for public functions

### TypeScript
- Follow standard TypeScript conventions
- Use Prettier for formatting
- Explicit types preferred
- JSDoc comments for public APIs

## Commit Messages

Follow conventional commits:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Test additions or changes
- `chore`: Build process or auxiliary tool changes

Examples:
```
feat: add github integration skill template
fix: handle missing state file gracefully
docs: update installation instructions for Windows
```

## Testing

### Python
```bash
pytest
pytest --cov  # with coverage
```

### TypeScript
```bash
npm test
```

### Manual Testing

1. Install package locally:
   ```bash
   # Python
   pip install -e ./python
   
   # TypeScript
   cd typescript && npm link
   ```

2. Configure in your AI agent (Cursor/Kiro/Claude)

3. Test each tool:
   - Create a loop
   - Start/stop loop
   - Add skills
   - View state
   - Check metrics

## Pull Request Guidelines

**Good PR:**
- Focused on single feature/fix
- Includes tests
- Updates documentation
- Clear description of changes
- Screenshots/examples if UI-related

**PR Checklist:**
- [ ] Code follows project style
- [ ] Tests pass (Python & TypeScript if both affected)
- [ ] Documentation updated
- [ ] Commit messages follow convention
- [ ] No merge conflicts

## Areas We Need Help With

### High Priority
- [ ] Additional skill templates (especially for non-JS/TS languages)
- [ ] Better error messages and handling
- [ ] Windows compatibility testing
- [ ] CI/CD pipeline setup

### Medium Priority
- [ ] Metrics visualization/dashboard
- [ ] Integration with issue trackers (Linear, Jira)
- [ ] Slack/Discord notifications
- [ ] VS Code extension

### Nice to Have
- [ ] Web UI for configuration
- [ ] Loop scheduling UI
- [ ] State history visualization
- [ ] Multi-language documentation

## Questions?

- Open a [GitHub Discussion](https://github.com/yourusername/loop-engineering/discussions)
- Tag maintainers in issues
- Check existing issues/PRs for similar questions

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Loop Engineering! 🙏
