#!/bin/bash

# Script to run the React frontend
echo "Starting Legal AI Frontend..."
echo "Frontend will be available at: http://localhost:5173"
echo ""

# Navigate to frontend directory and start development server
cd frontend
npm install
npm run dev