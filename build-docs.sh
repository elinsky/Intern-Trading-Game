#!/bin/bash
# Build documentation for Intern Trading Game

set -e

echo "Building documentation..."

case "$1" in
    public)
        echo "Building public documentation..."
        mkdocs build -f mkdocs-public.yml -d site-public --clean
        echo "Public docs built to site-public/"
        ;;
    private)
        echo "Building private documentation (with API reference)..."
        mkdocs build --clean
        echo "Private docs built to site/"
        ;;
    both)
        echo "Building both public and private documentation..."
        mkdocs build -f mkdocs-public.yml -d site-public --clean
        mkdocs build --clean
        echo "Public docs built to site-public/"
        echo "Private docs built to site/"
        ;;
    serve-public)
        echo "Serving public documentation..."
        mkdocs serve -f mkdocs-public.yml
        ;;
    serve|serve-private)
        echo "Serving private documentation..."
        mkdocs serve
        ;;
    *)
        echo "Usage: $0 {public|private|both|serve-public|serve-private}"
        echo ""
        echo "  public        - Build only public docs (game rules)"
        echo "  private       - Build only private docs (includes API)"
        echo "  both          - Build both versions"
        echo "  serve-public  - Serve public docs locally"
        echo "  serve-private - Serve private docs locally"
        echo "  serve         - Alias for serve-private"
        exit 1
        ;;
esac
