# kairo-fetch

A simple CLI tool for fetching emails from Gmail and IMAP providers.

## Installation

### Prerequisites
- Python 3.8+
- Poetry (for dependency management)

### Setup

```bash
# Install dependencies
poetry install

# Install the package in development mode
poetry install --dev
```

## Usage

### Basic Commands

```bash
# Show help
python -m kairo.cli --help

# Initialize kairo configuration
python -m kairo.cli init

# Fetch emails from Gmail
python -m kairo.cli fetch --provider gmail --account my_gmail --folder inbox

# Fetch emails from IMAP (not yet implemented)
python -m kairo.cli fetch --provider imap --account my_imap --folder inbox --server imap.example.com

# Search emails (not yet implemented)
python -m kairo.cli search --account my_account --query "from:john"

# List accounts (not yet implemented)
python -m kairo.cli list-accounts
```

### Configuration

The tool uses a configuration file located at `~/.kairo/config.json`. You can also specify a custom config path.

Example config:
```json
{
  "accounts": {
    "gmail": {
      "provider": "gmail",
      "username": "your.email@gmail.com",
      "client_id": "your-client-id.apps.googleusercontent.com",
      "client_secret": "your-client-secret"
    },
    "imaps": {
      "provider": "imap",
      "username": "your.email@example.com",
      "password": "your-password",
      "server": "imap.example.com",
      "port": 993
    }
  },
  "storage": {
    "path": "/path/to/storage"
  }
}
```

## Development

### Project Structure

```
kairo/
├── cli.py               # CLI interface
├── config.py           # Configuration management
├── models.py           # Data models (Pydantic)
├── storage.py          # Storage operations
└── retrievers/         # Email retrieval implementations
    └── gmail.py        # Gmail-specific retrieval

tests/
├── test_cli.py         # CLI tests
├── test_config.py     # Configuration tests
├── test_storage.py    # Storage tests
└── test_gmail_retriever.py # Gmail retriever tests
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest tests/test_cli.py

# Format code
poetry run black .
poetry run isort .

# Type checking
poetry run pyright

# Linting
poetry run pylint kairo/
```

## Features

### Implemented
- [x] Basic CLI structure with Click
- [x] Configuration management with JSON
- [x] Storage path management
- [x] Data models with Pydantic
- [x] Gmail retrieval with OAuth2 authentication
- [x] Email storage and indexing
- [x] OAuth2 authentication flow

### Planned
- [ ] IMAP email retrieval
- [ ] Advanced search functionality
- [ ] Attachment handling
- [ ] Email filtering and processing
- [ ] Scheduled fetching

## Authentication

### Gmail OAuth2 Setup

1. Create a project in Google Cloud Console
2. Enable Gmail API
3. Create OAuth 2.0 credentials
4. Add the following scopes:
   - `https://www.googleapis.com/auth/gmail.readonly` (read-only)

5. Configure your account in `~/.kairo/config.json`:
```json
{
  "accounts": {
    "gmail": {
      "provider": "gmail",
      "username": "your.email@gmail.com",
      "client_id": "your-client-id",
      "client_secret": "your-client-secret"
    }
  }
}
```

6. Run the fetch command and follow the OAuth2 flow:
```bash
python -m kairo.cli fetch --provider gmail --account my_gmail --folder inbox
```

## Storage

Emails are stored in `~/.kairo/storage/` by default:

```
.kairo/
├── config.json          # Configuration file
└── storage/             # Email storage
    └── gmail/        # Account-specific storage
        ├── emails/      # Email files (.eml format)
        │   └── inbox/   # Folder structure
        │       └── email_id.eml
        ├── attachments/ # Attachment files
        └── index.json   # Search index
```

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Follow the existing code style and conventions
2. Write tests for new features
3. Update documentation as needed
4. Maintain backward compatibility
5. Use descriptive commit messages

### Development Workflow

1. Create a feature branch
2. Implement the feature with tests
3. Run the full test suite
4. Update documentation
5. Submit a pull request

## License

MIT

## Support

For issues, questions, or feature requests, please open an issue on GitHub.
