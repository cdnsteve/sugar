# Sugar Claude Code Plugin - Testing Plan

Comprehensive testing strategy for ensuring Sugar works reliably as a Claude Code plugin.

## Test Categories

### 1. Plugin Structure Tests
**Location**: `tests/plugin/test_structure.py`

```python
"""Test plugin structure and manifest validity"""

def test_plugin_json_exists():
    """Verify plugin.json exists and is valid"""
    assert Path('.claude-plugin/plugin.json').exists()

def test_plugin_manifest_valid():
    """Verify plugin manifest has required fields"""
    with open('.claude-plugin/plugin.json') as f:
        manifest = json.load(f)
    assert 'name' in manifest
    assert 'version' in manifest
    assert manifest['name'] == 'sugar'

def test_commands_directory():
    """Verify commands directory structure"""
    assert Path('.claude-plugin/commands').is_dir()
    commands = list(Path('.claude-plugin/commands').glob('*.md'))
    assert len(commands) >= 5  # At least 5 commands

def test_agents_directory():
    """Verify agents directory structure"""
    assert Path('.claude-plugin/agents').is_dir()
    agents = list(Path('.claude-plugin/agents').glob('*.md'))
    assert len(agents) >= 3  # At least 3 agents

def test_hooks_configuration():
    """Verify hooks configuration exists and is valid"""
    assert Path('.claude-plugin/hooks/hooks.json').exists()
    with open('.claude-plugin/hooks/hooks.json') as f:
        hooks = json.load(f)
    assert 'hooks' in hooks
    assert isinstance(hooks['hooks'], list)
```

### 2. Command Tests
**Location**: `tests/plugin/test_commands.py`

```python
"""Test slash command functionality"""

def test_sugar_task_command_exists():
    """Verify sugar-task command file exists"""
    assert Path('.claude-plugin/commands/sugar-task.md').exists()

def test_sugar_task_frontmatter():
    """Verify command has valid frontmatter"""
    content = Path('.claude-plugin/commands/sugar-task.md').read_text()
    assert 'name: sugar-task' in content
    assert 'description:' in content
    assert 'usage:' in content

def test_all_commands_have_examples():
    """Verify all commands include usage examples"""
    commands = Path('.claude-plugin/commands').glob('*.md')
    for cmd in commands:
        content = cmd.read_text()
        assert 'examples:' in content.lower() or 'example' in content.lower()

def test_command_consistency():
    """Verify command naming consistency"""
    commands = list(Path('.claude-plugin/commands').glob('*.md'))
    expected = ['sugar-task', 'sugar-status', 'sugar-run',
                'sugar-review', 'sugar-analyze']

    found_names = []
    for cmd in commands:
        content = cmd.read_text()
        match = re.search(r'name: ([\w-]+)', content)
        if match:
            found_names.append(match.group(1))

    for expected_name in expected:
        assert expected_name in found_names
```

### 3. Agent Tests
**Location**: `tests/plugin/test_agents.py`

```python
"""Test agent definitions"""

def test_sugar_orchestrator_exists():
    """Verify orchestrator agent exists"""
    assert Path('.claude-plugin/agents/sugar-orchestrator.md').exists()

def test_agent_frontmatter():
    """Verify agents have proper frontmatter"""
    agents = Path('.claude-plugin/agents').glob('*.md')
    for agent in agents:
        content = agent.read_text()
        assert 'name:' in content
        assert 'description:' in content
        assert 'expertise:' in content or 'type:' in content

def test_agent_specializations():
    """Verify required specialized agents exist"""
    required_agents = [
        'sugar-orchestrator',
        'task-planner',
        'quality-guardian'
    ]

    existing_agents = [f.stem for f in
                      Path('.claude-plugin/agents').glob('*.md')]

    for agent in required_agents:
        assert agent in existing_agents
```

### 4. MCP Server Tests
**Location**: `tests/plugin/test_mcp_server.py`

```python
"""Test MCP server implementation"""

import subprocess
import json

def test_mcp_implementation_doc_exists():
    """Verify MCP server documentation exists"""
    assert Path('.claude-plugin/MCP_SERVER_IMPLEMENTATION.md').exists()

@pytest.mark.skipif(not Path('mcp-server/sugar-mcp.js').exists(),
                   reason="MCP server not yet implemented")
def test_mcp_server_executable():
    """Verify MCP server is executable"""
    assert Path('mcp-server/sugar-mcp.js').exists()
    result = subprocess.run(['node', 'mcp-server/sugar-mcp.js', '--version'],
                          capture_output=True, timeout=5)
    assert result.returncode == 0

@pytest.mark.skipif(not Path('mcp-server/sugar-mcp.js').exists(),
                   reason="MCP server not yet implemented")
def test_mcp_server_responds():
    """Test MCP server responds to requests"""
    proc = subprocess.Popen(
        ['node', 'mcp-server/sugar-mcp.js'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE
    )

    request = json.dumps({"method": "getStatus", "params": {}})
    proc.stdin.write(request.encode() + b'\n')
    proc.stdin.flush()

    response = proc.stdout.readline()
    proc.terminate()

    assert response
    data = json.loads(response)
    assert 'success' in data
```

### 5. Hooks Tests
**Location**: `tests/plugin/test_hooks.py`

```python
"""Test hook configuration"""

def test_hooks_json_valid():
    """Verify hooks.json is valid JSON"""
    with open('.claude-plugin/hooks/hooks.json') as f:
        hooks = json.load(f)
    assert 'hooks' in hooks

def test_hooks_have_required_fields():
    """Verify each hook has required fields"""
    with open('.claude-plugin/hooks/hooks.json') as f:
        config = json.load(f)

    for hook in config['hooks']:
        assert 'name' in hook
        assert 'event' in hook
        assert 'action' in hook

def test_hook_events_valid():
    """Verify hook events are valid Claude Code events"""
    valid_events = ['tool-use', 'session-start', 'session-end',
                   'user-prompt-submit', 'file-change']

    with open('.claude-plugin/hooks/hooks.json') as f:
        config = json.load(f)

    for hook in config['hooks']:
        assert hook['event'] in valid_events

def test_hook_throttling():
    """Verify hooks have proper throttling configured"""
    with open('.claude-plugin/hooks/hooks.json') as f:
        config = json.load(f)

    for hook in config['hooks']:
        if 'throttle' in hook:
            assert 'max_per_session' in hook['throttle'] or \
                   'min_interval_seconds' in hook['throttle']
```

### 6. Integration Tests
**Location**: `tests/plugin/test_integration.py`

```python
"""End-to-end integration tests"""

@pytest.fixture
def temp_project(tmp_path):
    """Create temporary project with Sugar initialized"""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Initialize Sugar
    subprocess.run(['sugar', 'init'], cwd=project_dir, check=True)

    yield project_dir

def test_plugin_installation_flow(temp_project):
    """Test complete plugin installation flow"""
    # Copy plugin files
    plugin_src = Path('.claude-plugin')
    plugin_dst = temp_project / '.claude-plugin'
    shutil.copytree(plugin_src, plugin_dst)

    # Verify structure
    assert (plugin_dst / 'plugin.json').exists()
    assert (plugin_dst / 'commands').is_dir()
    assert (plugin_dst / 'agents').is_dir()

def test_task_creation_via_plugin(temp_project):
    """Test creating Sugar task through plugin interface"""
    # Simulate /sugar-task command
    result = subprocess.run(
        ['sugar', 'add', 'Test Task', '--type', 'feature'],
        cwd=temp_project,
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    assert 'Task created' in result.stdout

def test_status_check_via_plugin(temp_project):
    """Test Sugar status through plugin interface"""
    result = subprocess.run(
        ['sugar', 'status'],
        cwd=temp_project,
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    assert 'Total Tasks' in result.stdout or 'tasks' in result.stdout.lower()
```

### 7. Cross-Platform Tests
**Location**: `tests/plugin/test_platforms.py`

```python
"""Platform-specific tests"""

import platform

def test_plugin_works_on_current_platform():
    """Verify plugin structure works on current OS"""
    system = platform.system()
    assert system in ['Darwin', 'Linux', 'Windows']

    # All plugin files should be readable
    for path in Path('.claude-plugin').rglob('*'):
        if path.is_file():
            assert path.exists()
            assert path.stat().st_size > 0

def test_path_separators():
    """Verify no hardcoded path separators"""
    # Check command files don't have hardcoded paths
    commands = Path('.claude-plugin/commands').glob('*.md')
    for cmd in commands:
        content = cmd.read_text()
        # No hardcoded Unix-style paths with home
        assert '~/Dev/' not in content
        assert '/Users/' not in content

def test_line_endings():
    """Verify consistent line endings"""
    for path in Path('.claude-plugin').rglob('*.md'):
        content = path.read_bytes()
        # Should use \n (Unix) line endings consistently
        assert b'\r\n' not in content
```

### 8. Documentation Tests
**Location**: `tests/plugin/test_docs.py`

```python
"""Test documentation completeness"""

def test_plugin_readme_exists():
    """Verify plugin README exists"""
    assert Path('.claude-plugin/README.md').exists()

def test_readme_has_installation():
    """Verify README includes installation instructions"""
    content = Path('.claude-plugin/README.md').read_text()
    assert 'install' in content.lower()
    assert 'pip install sugarai' in content

def test_readme_has_examples():
    """Verify README includes usage examples"""
    content = Path('.claude-plugin/README.md').read_text()
    assert '```' in content  # Code blocks
    assert '/sugar-' in content  # Slash commands

def test_all_commands_documented():
    """Verify all commands are documented in README"""
    readme = Path('.claude-plugin/README.md').read_text()
    commands = Path('.claude-plugin/commands').glob('*.md')

    for cmd in commands:
        cmd_name = cmd.stem
        assert cmd_name in readme or f'/{cmd_name}' in readme
```

## Test Execution

### Run All Plugin Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all plugin tests
pytest tests/plugin/ -v

# Run with coverage
pytest tests/plugin/ --cov=.claude-plugin --cov-report=html

# Run specific category
pytest tests/plugin/test_structure.py -v
```

### CI/CD Integration

```yaml
# .github/workflows/plugin-tests.yml
name: Plugin Tests

on: [push, pull_request]

jobs:
  test-plugin:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: [3.11, 3.12]

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-cov

      - name: Test plugin structure
        run: pytest tests/plugin/ -v

      - name: Validate plugin files
        run: python -m json.tool .claude-plugin/plugin.json
```

## Manual Testing Checklist

### Pre-Release Testing

- [ ] Install plugin in test Claude Code environment
- [ ] Test all slash commands work correctly
- [ ] Verify agents are properly invoked
- [ ] Test hooks trigger appropriately
- [ ] Verify MCP server integration (when implemented)
- [ ] Test on macOS
- [ ] Test on Linux
- [ ] Test on Windows
- [ ] Verify documentation is accurate
- [ ] Test with fresh Sugar installation
- [ ] Test with existing Sugar projects

### User Acceptance Testing

- [ ] New user can install and use plugin
- [ ] Slash commands are intuitive
- [ ] Error messages are helpful
- [ ] Performance is acceptable
- [ ] No crashes or hangs
- [ ] Documentation answers common questions

## Performance Testing

### Response Time Targets
- `/sugar-task` creation: < 2 seconds
- `/sugar-status` display: < 1 second
- `/sugar-list` display: < 2 seconds
- Agent invocation: < 500ms overhead

### Load Testing
```python
def test_multiple_rapid_commands():
    """Test handling multiple commands in quick succession"""
    for i in range(10):
        result = subprocess.run(
            ['sugar', 'add', f'Task {i}', '--type', 'feature'],
            capture_output=True,
            timeout=5
        )
        assert result.returncode == 0
```

## Security Testing

### Security Checklist
- [ ] No hardcoded credentials
- [ ] Proper input validation
- [ ] No command injection vulnerabilities
- [ ] File path validation
- [ ] Secure subprocess handling
- [ ] No sensitive data in logs

### Security Tests
```python
def test_no_command_injection():
    """Verify plugin protects against command injection"""
    malicious_input = "test; rm -rf /"
    result = subprocess.run(
        ['sugar', 'add', malicious_input],
        capture_output=True
    )
    # Should handle safely, not execute rm command
    assert result.returncode in [0, 1]  # Success or validation error

def test_no_secrets_in_files():
    """Verify no secrets committed to plugin files"""
    for path in Path('.claude-plugin').rglob('*'):
        if path.is_file():
            content = path.read_text()
            # Check for common secret patterns
            assert 'sk_live_' not in content  # API keys
            assert 'ghp_' not in content      # GitHub tokens
            assert 'password' not in content.lower() or 'PASSWORD' in content
```

## Test Maintenance

### Adding New Tests
1. Create test file in appropriate category
2. Follow naming convention: `test_*.py`
3. Use descriptive test names
4. Include docstrings
5. Add to CI/CD pipeline

### Updating Tests
- Keep tests in sync with plugin changes
- Update expected values when plugin evolves
- Maintain backwards compatibility tests
- Document breaking changes

## Success Criteria

Plugin is ready for marketplace when:
- ✅ All tests pass on all platforms
- ✅ >80% code coverage
- ✅ No critical security issues
- ✅ Performance meets targets
- ✅ Documentation complete and accurate
- ✅ Manual testing checklist completed
- ✅ User acceptance testing positive
