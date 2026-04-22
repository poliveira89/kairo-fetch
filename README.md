# kairo-fetch

A simple CLI tool for fetching emails from Gmail and IMAP providers.

## Installation

### Prerequisites
- Python 3.8+
- Poetry (for dependency management)

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/email-fetch.git
cd email-fetch

# Install dependencies
poetry install

# Install the package in development mode
poetry install --dev
```

## Usage

### Basic Commands

```bash
# Show help
export PYTHONPATH=./src
python -m email_fetch.cli --help

# Fetch emails from IMAP
export PYTHONPATH=./src
python -m email_fetch.cli fetch --provider imap --account my_account --folder inbox --server imap.example.com

# Search emails
python -m email_fetch.cli search --account my_account --query "from:john"

# List accounts
python -m email_fetch.cli list-accounts
```

### Configuration

The tool uses a configuration file located at `~/.email_fetch/config.json`. You can also specify a custom config path.

Example config:
```json
{
  "accounts": {
    "my_gmail": {
      "provider": "gmail",
      "username": "your.email@gmail.com"
    },
    "my_imap": {
      "provider": "imap",
      "username": "your.email@example.com",
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
email_fetch/
├── src/
│   └── email_fetch/
│       ├── cli.py           # CLI interface
│       ├── config.py        # Configuration management
│       ├── models.py        # Data models
│       ├── storage.py       # Storage management
│       └── retrievers/      # Email retrieval implementations
├── pyproject.toml          # Poetry configuration
└── README.md               # This file
```

### Running Tests

```bash
# Run tests (when implemented)
poetry run pytest

# Format code
poetry run black .
poetry run isort .
```

## Features

- [x] Basic CLI structure with Click
- [x] Configuration management
- [x] Storage path management
- [x] Data models with Pydantic
- [ ] IMAP email retrieval
- [ ] Gmail retrieval with Playwright
- [ ] Email indexing
- [ ] Search functionality
- [ ] Attachment handling

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

MIT
