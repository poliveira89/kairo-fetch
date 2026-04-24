#!/bin/bash

# Install git hooks for the project

echo "Installing git hooks..."

# Create .git/hooks directory if it doesn't exist
mkdir -p .git/hooks

# Create pre-commit hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash

# Kairo pre-commit hook - runs linting

echo "Running pre-commit checks..."

# Check if we're in the project root
if [ ! -f "Makefile" ]; then
    echo "Error: Not in project root directory"
    exit 1
fi

# Run linting
if make lint; then
    echo "✅ All format checks passed!"
    exit 0
else
    echo "❌ Linting failed. Please fix the issues before committing."
    exit 1
fi

# Run check
if make check; then
    echo "✅ All syntax checks passed!"
    exit 0
else
    echo "❌ Syntax failed. Please fix the issues before committing."
    exit 1
fi
EOF

# Make the hook executable
chmod +x .git/hooks/pre-commit

echo "✅ Git hooks installed successfully!"
echo "Pre-commit hook will run 'make lint' before each commit."
