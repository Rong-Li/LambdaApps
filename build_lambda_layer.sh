#!/bin/bash
set -e

# Build Lambda layers for API and Batch functions
# API layer: lightweight (~15MB) - no pyarrow
# Batch layer: includes pyarrow (~45MB) for Parquet export

PYTHON_VERSION="3.14"
PLATFORM="x86_64-manylinux2014"

# Generate lock file
uv lock

strip_unnecessary_files() {
    local dir=$1
    echo "Stripping unnecessary files from $dir..."
    find "$dir" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$dir" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
    find "$dir" -type d -name "test" -exec rm -rf {} + 2>/dev/null || true
    find "$dir" -type f -name "*.pyc" -delete 2>/dev/null || true
    find "$dir" -type f -name "*.pyo" -delete 2>/dev/null || true
    find "$dir" -type d -name "*.dist-info" -exec sh -c 'rm -f "$1"/RECORD "$1"/INSTALLER "$1"/REQUESTED' _ {} \; 2>/dev/null || true
}

build_layer() {
    local name=$1
    local extras=$2
    
    echo ""
    echo "=========================================="
    echo "Building $name layer..."
    echo "=========================================="
    
    # Export requirements
    if [ -z "$extras" ]; then
        uv export --format requirements-txt --no-hashes --no-dev > requirements-${name}.txt
    else
        uv export --format requirements-txt --no-hashes --no-dev --extra "$extras" > requirements-${name}.txt
    fi
    
    # Create build directory
    rm -rf python/
    mkdir -p python/
    
    # Install dependencies
    uv pip install --python-platform "$PLATFORM" \
        --only-binary=:all: \
        --python-version "$PYTHON_VERSION" \
        --target python/ \
        -r requirements-${name}.txt
    
    # Strip files
    strip_unnecessary_files python/
    
    
    # Create zip
    zip -r -q "lambda-layer-${name}.zip" python/
    
    # Show size
    echo "📦 $name layer: $(du -h lambda-layer-${name}.zip | cut -f1)"
    
    # Cleanup
    rm -f requirements-${name}.txt
    rm -rf python/
}

# Build API layer (no extras - base dependencies only)
build_layer "api" ""

# Build Batch layer (includes pyarrow)
build_layer "batch" "batch"

echo ""
echo "✅ Lambda layers created:"
echo "   - lambda-layer-api.zip   (for lambda-home-api)"
echo "   - lambda-layer-batch.zip (for lambda-home-batch)"
