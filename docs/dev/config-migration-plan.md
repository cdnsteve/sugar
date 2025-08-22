# Sugar Configuration Migration Plan: YAML → JSON

## Overview

As Sugar's configuration system grows in complexity with workflows, metrics, discovery modules, and advanced features, we need a more structured and maintainable configuration format. This document outlines the migration from YAML to JSON configuration files.

## Problems with Current YAML Configuration

### 1. **Complexity and Nesting**
- Deep nesting becomes hard to read and maintain
- Complex workflow configurations with multiple conditional branches
- Difficult to validate schema programmatically
- Limited tooling for IDE support and validation

### 2. **Type Safety Issues**
- YAML's flexible typing can lead to runtime errors
- Inconsistent boolean/string representations (`true` vs `"true"`)
- No compile-time validation of configuration structure
- Difficult to provide meaningful error messages for invalid configs

### 3. **Scalability Concerns**
- Current config approaching 100+ lines for basic setup
- Adding metrics, advanced workflows, and discovery modules will 2-3x size
- Templating and environment-specific configs becoming necessary
- Version management and migrations becoming complex

### 4. **Developer Experience**
- Limited IDE support for validation and auto-completion
- No schema validation during development
- Difficult to generate documentation from config structure
- Error messages often unclear about what's wrong

## Proposed JSON Configuration System

### 1. **Structured Schema with JSON Schema Validation**

#### Main Configuration File: `.sugar/config.json`
```json
{
  "$schema": "./schema/sugar-config-schema.json",
  "version": "2.0",
  "sugar": {
    "core": {
      "loopInterval": 300,
      "maxConcurrentWork": 3,
      "dryRun": true
    },
    "claude": {
      "command": "/Users/steve/.claude/local/claude",
      "timeout": 1800,
      "contextFile": ".sugar/context.json",
      "contextPersistence": {
        "enabled": true,
        "strategy": "project",
        "maxAgeHours": 24
      }
    },
    "discovery": {
      "globalExcludes": [
        "node_modules", ".git", "__pycache__", 
        "venv", ".venv", "build", "dist"
      ],
      "modules": {
        "errorLogs": {
          "enabled": true,
          "config": {
            "paths": ["logs/errors/", "logs/feedback/"],
            "patterns": ["*.json", "*.log"],
            "maxAgeHours": 24
          }
        },
        "github": {
          "enabled": false,
          "config": {
            "repo": "",
            "authMethod": "auto",
            "issueLabels": [],
            "checkIntervalMinutes": 30,
            "workflow": {
              "autoCloseIssues": true,
              "gitWorkflow": "direct_commit",
              "branch": {
                "createBranches": true,
                "namePattern": "sugar/issue-{issue_number}",
                "baseBranch": "main"
              },
              "pullRequest": {
                "autoCreate": true,
                "autoMerge": false,
                "titlePattern": "Fix #{issue_number}: {issue_title}",
                "includeWorkSummary": true
              },
              "commit": {
                "includeIssueRef": true,
                "messagePattern": "Fix #{issue_number}: {work_summary}",
                "autoCommit": true
              }
            }
          }
        }
      }
    },
    "storage": {
      "database": ".sugar/sugar.db",
      "backupInterval": 3600
    },
    "metrics": {
      "enabled": false,
      "endpoint": "https://metrics.sugar-ai.com/v1/events",
      "batchSize": 10,
      "batchIntervalMinutes": 15,
      "collect": {
        "installationInfo": true,
        "usageSessions": true,
        "workCompletion": true,
        "performanceMetrics": true,
        "errorReporting": true
      }
    }
  }
}
```

#### JSON Schema File: `.sugar/schema/sugar-config-schema.json`
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://sugar-ai.com/schemas/config/v2.0.json",
  "title": "Sugar Configuration Schema",
  "description": "Configuration schema for Sugar AI autonomous development system",
  "type": "object",
  "required": ["version", "sugar"],
  "properties": {
    "version": {
      "type": "string",
      "enum": ["2.0"],
      "description": "Configuration schema version"
    },
    "sugar": {
      "type": "object",
      "required": ["core", "claude", "discovery", "storage"],
      "properties": {
        "core": {
          "type": "object",
          "required": ["loopInterval", "maxConcurrentWork", "dryRun"],
          "properties": {
            "loopInterval": {
              "type": "integer",
              "minimum": 60,
              "maximum": 3600,
              "description": "Seconds between discovery cycles"
            },
            "maxConcurrentWork": {
              "type": "integer",
              "minimum": 1,
              "maximum": 10,
              "description": "Maximum parallel work items"
            },
            "dryRun": {
              "type": "boolean",
              "description": "Enable safe simulation mode"
            }
          }
        },
        "claude": {
          "type": "object",
          "required": ["command", "timeout", "contextFile"],
          "properties": {
            "command": {
              "type": "string",
              "minLength": 1,
              "description": "Path to Claude CLI executable"
            },
            "timeout": {
              "type": "integer",
              "minimum": 60,
              "maximum": 7200,
              "description": "Maximum execution time in seconds"
            }
          }
        }
      }
    }
  }
}
```

### 2. **Configuration Templates and Presets**

#### Preset System: `.sugar/presets/`
```json
// .sugar/presets/github-workflow.json
{
  "name": "GitHub Workflow Integration",
  "description": "Full GitHub integration with PR workflow",
  "config": {
    "sugar": {
      "discovery": {
        "modules": {
          "github": {
            "enabled": true,
            "config": {
              "issueLabels": [],
              "workflow": {
                "gitWorkflow": "pull_request",
                "pullRequest": {
                  "autoCreate": true,
                  "autoMerge": false
                }
              }
            }
          }
        }
      }
    }
  }
}

// .sugar/presets/direct-commit.json
{
  "name": "Direct Commit Workflow",
  "description": "Simple direct commit to main branch",
  "config": {
    "sugar": {
      "discovery": {
        "modules": {
          "github": {
            "enabled": true,
            "config": {
              "workflow": {
                "gitWorkflow": "direct_commit"
              }
            }
          }
        }
      }
    }
  }
}
```

### 3. **Environment-Specific Configurations**

#### Development vs Production
```json
// .sugar/config.json (base)
{
  "extends": ["./environments/base.json"],
  "sugar": {
    "core": {
      "dryRun": true
    }
  }
}

// .sugar/environments/production.json
{
  "sugar": {
    "core": {
      "dryRun": false,
      "maxConcurrentWork": 5
    },
    "metrics": {
      "enabled": true
    }
  }
}
```

## Migration Strategy

### Phase 1: Dual Support (Weeks 1-2)
- **Implement JSON configuration loader alongside YAML**
- **Auto-detect configuration format** (.yaml vs .json)
- **Maintain backward compatibility** with existing YAML configs
- **Add `sugar config migrate` command** to convert YAML → JSON

#### Implementation:
```python
# sugar/config/loader.py
class ConfigLoader:
    def load(self, config_path: str) -> dict:
        if config_path.endswith('.json'):
            return self._load_json(config_path)
        elif config_path.endswith(('.yaml', '.yml')):
            return self._load_yaml(config_path)
        else:
            # Auto-detect
            return self._auto_detect_and_load(config_path)
    
    def _load_json(self, path: str) -> dict:
        with open(path) as f:
            config = json.load(f)
        self._validate_schema(config)
        return config
```

### Phase 2: Enhanced JSON Features (Weeks 3-4)
- **JSON Schema validation** with meaningful error messages
- **Configuration presets and templates**
- **Environment-specific configuration merging**
- **IDE integration** (VS Code extension for Sugar configs)

### Phase 3: Migration Tools (Weeks 5-6)
- **`sugar config validate`** - Validate configuration against schema
- **`sugar config migrate`** - Convert YAML to JSON with validation
- **`sugar config preset apply <preset>`** - Apply configuration presets
- **Configuration documentation generator**

### Phase 4: Deprecation (Weeks 7-8)
- **Mark YAML as deprecated** (warnings in logs)
- **Update all documentation** to use JSON examples
- **Migration guides** for existing users
- **Sunset timeline** for YAML support

## Benefits of JSON Configuration

### 1. **Better Developer Experience**
```bash
# Validate configuration
sugar config validate

# Apply preset
sugar config preset apply github-workflow

# Migrate from YAML
sugar config migrate --from config.yaml --to config.json

# Check configuration differences
sugar config diff environments/dev.json environments/prod.json
```

### 2. **IDE Integration**
- **VS Code extension** for Sugar configurations
- **Auto-completion** based on JSON schema
- **Real-time validation** and error highlighting
- **Hover documentation** for configuration options

### 3. **Advanced Configuration Management**
```bash
# Environment-specific configs
sugar run --config environments/production.json

# Merge configurations
sugar config merge base.json overrides.json --output final.json

# Generate documentation
sugar config docs --output config-reference.md
```

### 4. **Type Safety and Validation**
```python
# Runtime validation with detailed errors
try:
    config = ConfigLoader().load('.sugar/config.json')
except ConfigValidationError as e:
    print(f"Configuration error at {e.path}: {e.message}")
    print(f"Expected: {e.expected_type}")
    print(f"Got: {e.actual_value}")
```

## Migration Commands

### New CLI Commands
```bash
# Validate current configuration
sugar config validate

# Migrate YAML to JSON
sugar config migrate

# Apply configuration preset
sugar config preset list
sugar config preset apply <name>

# Environment management
sugar config env list
sugar config env switch <environment>

# Schema operations
sugar config schema validate
sugar config schema docs
```

## Backward Compatibility

### 1. **Graceful Migration**
- YAML configs continue to work during transition period
- Automatic detection of configuration format
- Warning messages encouraging migration to JSON
- Migration tool preserves all existing settings

### 2. **Configuration Conversion**
```python
def migrate_yaml_to_json(yaml_path: str, json_path: str):
    """Convert YAML configuration to JSON with schema validation"""
    
    # Load YAML
    yaml_config = yaml.safe_load(open(yaml_path))
    
    # Transform to new JSON structure
    json_config = YamlToJsonTransformer().transform(yaml_config)
    
    # Validate against schema
    validate_config_schema(json_config)
    
    # Write JSON
    with open(json_path, 'w') as f:
        json.dump(json_config, f, indent=2)
```

## Implementation Timeline

### Week 1-2: Foundation
- [ ] Design JSON schema structure
- [ ] Implement JSON configuration loader
- [ ] Create schema validation system
- [ ] Add dual YAML/JSON support

### Week 3-4: Enhanced Features
- [ ] Configuration presets system
- [ ] Environment-specific configuration
- [ ] CLI commands for config management
- [ ] Error handling and validation messages

### Week 5-6: Migration Tools
- [ ] YAML to JSON migration command
- [ ] Configuration validation tools
- [ ] Documentation generation
- [ ] IDE integration (VS Code extension)

### Week 7-8: Adoption
- [ ] Update all documentation
- [ ] Migration guides for users
- [ ] Deprecation warnings for YAML
- [ ] Performance optimization

## Risk Mitigation

### 1. **User Impact**
- **Gradual migration** - no forced immediate changes
- **Clear migration path** with automated tools
- **Comprehensive documentation** and examples
- **Community feedback** during beta period

### 2. **Technical Risks**
- **Schema evolution** - versioned schemas with migration paths
- **Performance** - JSON parsing is faster than YAML
- **Complexity** - better tooling offsets increased structure
- **Testing** - comprehensive test suite for all configuration scenarios

## Success Metrics

### Technical Metrics
- **Configuration validation errors** reduced by 80%
- **Schema validation** catches 95%+ of configuration issues
- **Load time** improved by 30% (JSON vs YAML parsing)
- **Memory usage** reduced by 20% (more efficient parsing)

### User Experience Metrics
- **Setup time** for new users reduced by 50%
- **Configuration errors** in support requests reduced by 70%
- **IDE adoption** by 60%+ of active users
- **Migration completion** by 80%+ of existing users within 6 months

---

*This migration will position Sugar for long-term scalability while significantly improving the developer experience through better tooling, validation, and IDE support.*