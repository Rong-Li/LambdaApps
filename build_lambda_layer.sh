#!/bin/bash

# Generate lock file for reproducible builds
uv lock

# Export to requirements.txt for Lambda
uv export --format requirements-txt --no-hashes > requirements.txt

# Create build directory
mkdir -p python/

# Install to build directory with Lambda-compatible wheels
uv pip install --python-platform x86_64-manylinux2014 \
    --only-binary=:all: \
    --python-version 3.14 --target python/ \
    -r requirements.txt


# Create deployment package
zip -r lambda-uv.zip python/

# Cleanup
rm requirements.txt && rm -r python/

echo "✅ uv locked deployment package created: lambda-uv-locked.zip"
