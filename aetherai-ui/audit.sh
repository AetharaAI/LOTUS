#!/bin/bash
# Project audit script for Apriel frontend

echo "=== PROJECT STRUCTURE ==="
tree -L 4 -I 'node_modules|.git|.next|dist|build' || find . -maxdepth 4 -type f -name "*.ts" -o -name "*.tsx" -o -name "*.json" | head -50

echo -e "\n=== PACKAGE.JSON ==="
cat package.json

echo -e "\n=== TSCONFIG.JSON ==="
cat tsconfig.json 2>/dev/null || echo "No tsconfig found"

echo -e "\n=== NEXT.CONFIG ==="
cat next.config.js 2>/dev/null || cat next.config.mjs 2>/dev/null || echo "No next config found"

echo -e "\n=== APP DIRECTORY STRUCTURE ==="
ls -la app/ 2>/dev/null || echo "No app directory"

echo -e "\n=== LIB DIRECTORY STRUCTURE ==="
ls -la lib/ 2>/dev/null || echo "No lib directory"

echo -e "\n=== COMPONENTS DIRECTORY ==="
ls -la components/ 2>/dev/null || echo "No components directory"

echo -e "\n=== CURRENT ENV VARS (sanitized) ==="
cat .env.local 2>/dev/null | sed 's/=.*/=***REDACTED***/' || echo "No .env.local"

echo -e "\n=== VERCEL ENV VARS (from vercel.json if exists) ==="
cat vercel.json 2>/dev/null || echo "No vercel.json"