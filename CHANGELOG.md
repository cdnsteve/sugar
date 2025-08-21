# Changelog

All notable changes to Sugar will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive test suite with pytest
- CI/CD pipeline with GitHub Actions
- Pre-commit hooks for code quality
- Docker support for containerized deployment
- Security scanning with bandit and safety
- Code coverage reporting
- Type checking with mypy
- Automated release workflow

### Changed
- Project renamed from claude-ccal to Sugar
- CLI command changed from `ccal` to `sugar`
- Package directory renamed from `claude_ccal` to `sugar`
- Configuration directory changed from `.ccal` to `.sugar`
- Updated all documentation with new naming

### Security
- Added security scanning to CI pipeline
- Implemented pre-commit hooks for vulnerability detection

## [0.1.0] - 2024-01-01

### Added
- Initial release of Sugar (formerly Claude CCAL)
- AI-powered autonomous development system
- Claude Code CLI integration
- Project-specific task management
- Error log discovery and processing
- Code quality analysis
- Test coverage analysis
- GitHub integration support
- SQLite-based task storage
- Configurable discovery modules
- Dry-run mode for safe testing
- Comprehensive CLI interface
- Project isolation with `.sugar/` directories

### Features
- `sugar init` - Initialize Sugar in any project
- `sugar add` - Add tasks manually
- `sugar list` - List and filter tasks
- `sugar status` - Show system status
- `sugar run` - Start autonomous development
- `sugar view` - View task details
- `sugar update` - Update existing tasks
- `sugar remove` - Remove tasks

### Documentation
- Complete README with installation instructions
- Library usage guide
- Configuration examples
- Troubleshooting guide
- Multi-project setup instructions