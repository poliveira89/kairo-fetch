# AGENTS.md - kairo-fetch Development Guide

## Purpose

This document provides AI coding agents with the specific conventions, rules, and context needed to work effectively with the kairo-fetch codebase.

## Codebase Structure & Conventions

### Project Layout

```
kairo/
├── cli.py              # Main CLI interface
├── config.py           # Configuration management
├── models.py           # Data models (Pydantic)
├── storage.py          # Storage operations
└── retrievers/         # Provider-specific implementations
    └── gmail.py        # Gmail retrieval

tests/                  # Test suite
```

### Naming Conventions

- **Classes**: PascalCase (`EmailAccount`, `StorageManager`)
- **Functions**: snake_case (`get_email_path`, `load_index`)
- **Variables**: snake_case (`account_config`, `email_data`)
- **Files**: snake_case (`cli.py`, `storage.py`)
- **Directories**: snake_case (`retrievers/`)

### Type System

- **Strict typing**: All functions and methods have type hints
- **Pydantic models**: For data validation and serialization
- **TypedDict**: For configuration structures
- **Optional types**: Use `| None` for nullable fields

### Code Formatting

- 4-space indentation
- 88-character line length limit
- Consistent quote style (double quotes for strings)
- Docstrings for all public functions and classes
- Type hints on separate lines for complex signatures

## Development Rules

### 1. Test-Driven Development (TDD)

**Mandatory**: All new features and bug fixes require tests.

- Write tests first, then implementation
- Tests must cover both success and failure cases
- Focus on edge cases and error conditions
- Maintain high test coverage (100%)

### 2. Code Organization

**Single Responsibility Principle**: Each module has a clear, focused purpose.

- `cli.py`: User interface only
- `config.py`: Configuration management only
- `models.py`: Data structures only
- `storage.py`: File operations only
- `retrievers/`: Provider-specific logic only

### 3. Error Handling

- Use specific exception types
- Provide meaningful error messages
- Handle edge cases gracefully
- Don't swallow exceptions silently

### 4. Configuration Management

- All configuration through `Config` class
- No hardcoded paths or credentials
- Configuration and sensitive data stored in `~/.kairo/config.json`

### 5. Storage Operations

- Use `StorageManager` for all file operations
- Follow established path structure
- Maintain index consistency
- Handle file system errors gracefully
- Default storage in `~/.kairo/storage`

## Object Design Patterns

### Data Models (models.py)

```python
class EmailAccount(BaseModel):
    """Email account configuration."""
    provider: str
    username: str
    password: str | None = None
    # ... other fields
```

- Use Pydantic for validation
- Include docstrings
- Default values for optional fields
- Type hints for all fields

### Service Classes

```python
class StorageManager:
    """Handles email and attachment storage."""
    
    def __init__(self, base_path: str):
        self.base_path: Path = Path(base_path)
        # ... initialization
    
    def get_email_path(self, account_name: str, folder: str, email_id: str) -> Path:
        """Get path for specific email."""
        # ... implementation
```

- Clear, focused methods
- Type hints for parameters and return values
- Docstrings explaining purpose and behavior
- Private methods prefixed with `_`

### CLI Commands

```python
@cli.command()
@click.option("--account", required=True, help="Account name")
def search(ctx: click.Context, account: str) -> None:
    """Search emails in index."""
    # Command implementation
```

- Use Click decorators for options
- Required parameters marked explicitly
- Help text for all options
- Context passed for shared state

## Testing Strategy

### Test Organization

```
tests/
├── test_cli.py           # CLI unit tests
├── test_config.py       # Configuration tests
├── test_storage.py      # Storage operation tests
└── test_gmail_retriever.py # Provider-specific tests
```

### Test Requirements

1. **Unit Tests**: Isolate individual components
2. **Integration Tests**: Test component interactions
3. **Error Tests**: Verify error handling
4. **Edge Cases**: Test boundary conditions

### Test Examples

```python
def test_config_loading():
    """Test configuration loading from file."""
    # Setup
    config_path = "test_config.json"
    
    # Exercise
    config = Config(config_path)
    
    # Verify
    assert config.data == expected_data
    
    # Cleanup
    os.remove(config_path)
```

## Common Pitfalls to Avoid

1. **Hardcoding values**: Use configuration system
2. **Direct file access**: Use `StorageManager`
3. **Ignoring errors**: Handle exceptions properly
4. **Breaking contracts**: Maintain API compatibility
5. **Inconsistent naming**: Follow established patterns
6. **Untyped code**: Always use type hints
7. **Untested code**: Write tests first

## Development Workflow

### Adding a Feature

1. Write tests first (TDD)
2. Update data models if needed
3. Implement core logic
4. Add CLI interface if user-facing
5. Update configuration handling
6. Run full test suite
7. Verify format, syntax and code - black, isort, basedpyright
8. Verify integration

### Fixing a Bug

1. Write reproduction test
2. Identify root cause
3. Implement fix
4. Verify all tests pass
5. Verify format, syntax and code - black, isort, basedpyright
6. Add regression test

### Refactoring

1. Ensure comprehensive test coverage
2. Make small, incremental changes
3. Verify behavior unchanged
4. Update tests if interfaces change
5. Maintain backward compatibility

## Documentation Guidelines

### Philosophy

**Code should be self-documenting first, comments should explain the "why" not the "what"**

- *MANDATORY:* Don't write one-liner comments inside methods or classes
- Document macro actions and architectural decisions
- Explain why something was implemented a certain way
- Help future developers understand the reasoning behind choices

### What to Document

**Good candidates for documentation:**

1. **Architectural decisions**: Why a particular approach was chosen
2. **Complex algorithms**: High-level explanation of how they work
3. **Workarounds**: Why a workaround was needed and what it addresses
4. **Important constraints**: Limitations or requirements that affect implementation
5. **Future considerations**: Known issues or planned improvements

**Example of good documentation:**

```python
# Use OAuth2 refresh token flow instead of password auth
# This avoids Google's "less secure apps" restrictions
# and provides better security for user credentials
if access_token:
    retriever = GmailRetriever(username=username, access_token=access_token)
```

### What NOT to Document

**Avoid documenting the obvious:**

```python
# Bad - explains what the code obviously does
# Get the account configuration
account_config = config.get_account(account_name)

# Bad - redundant with function name
# Save the configuration to file
config.save()
```

### Documentation Formats

1. **Module-level docstrings**: Explain the module's purpose and main components
2. **Class docstrings**: Describe the class's responsibility and usage
3. **Function docstrings**: Explain purpose, parameters, return values, and side effects
4. **Inline comments**: Only for explaining non-obvious decisions or complex logic

### Docstring Format

Use Google-style docstrings:

```python
def fetch_emails(folder: str, limit: int) -> list[EmailMetadata]:
    """Fetch emails from the specified folder.
    
    Args:
        folder: Name of folder/label to fetch from
        limit: Maximum number of emails to retrieve
        
    Returns:
        List of email metadata objects
        
    Raises:
        AuthenticationError: If authentication fails
        ConnectionError: If unable to connect to email server
        
    Note:
        Uses OAuth2 authentication when available, falls back to password auth.
        Gmail API has rate limits - consider adding retry logic for production use.
    """
    # Implementation...
```

## Code Quality Standards

- **Type Safety**: 100% type hints
- **Test Coverage**: 100% minimum
- **Documentation**: Focus on "why" not "what"
- **Consistency**: Follow existing patterns
- **Simplicity**: Prefer simple solutions
- **Readability**: Clear, expressive code
- **OOP**: Use classes and objects with proper methods to interact with data

## When in Doubt

1. Look at existing code for patterns
2. Follow the established conventions
3. Write tests first
4. Keep changes minimal and focused
5. Maintain code clarity and simplicity
6. Document decisions, not obvious code
