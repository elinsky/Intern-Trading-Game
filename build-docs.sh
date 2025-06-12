#!/bin/bash
# Build documentation for Intern Trading Game

set -e

echo "Building documentation..."

case "$1" in
    build)
        echo "Building documentation..."
        mkdocs build --clean
        echo "Docs built to site/"
        ;;
    serve)
        echo "Serving documentation..."
        mkdocs serve
        ;;
    *)
        echo "Usage: $0 {build|serve}"
        echo ""
        echo "  build - Build documentation"
        echo "  serve - Serve documentation locally"
        exit 1
        ;;
esac
