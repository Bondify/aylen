# Aylen Legal AI Agent - Web Application

A professional Legal AI application with React frontend that provides consistent legal analysis across different countries using Claude 3.5 Sonnet.

## Features

- 🎨 **Professional Web UI**: Clean, modern React interface
- 🤖 **Structured Analysis**: Uses Pydantic AI for consistent, structured responses
- 🌍 **Multi-Country Support**: Analyze laws across multiple countries simultaneously
- 📋 **Consistent Criteria**: Same analysis framework applied to all countries
- 🔄 **Easy Comparison**: Side-by-side country analysis
- ⚡ **Real-time Results**: Fast API responses with loading states

## Architecture

- **Frontend**: React + Vite + Tailwind CSS
- **Backend**: FastAPI + Pydantic AI
- **AI Model**: Claude 3.5 Sonnet via AWS Bedrock
- **Data**: YAML-based survey questions with structured criteria

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) package manager
- AWS credentials configured for Bedrock access
- Access to Claude models in AWS Bedrock (us-east-1 region)

### Installation

1. **Install Python dependencies**:
```bash
uv sync
```

2. **Install Node.js dependencies**:
```bash
cd frontend
npm install
cd ..
```

### Setup

Configure AWS credentials for Bedrock access:

```bash
# Option 1: AWS CLI
aws configure

# Option 2: Environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

Make sure you have access to Claude models in AWS Bedrock (us-east-1 region).

### Running the Application

You need to run both the backend and frontend:

**Terminal 1 - Backend**:
```bash
./run-backend.sh
# Or manually: uv run python backend/api.py
```

**Terminal 2 - Frontend**:
```bash
./run-frontend.sh
# Or manually: cd frontend && npm run dev
```

Then open your browser to:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Usage

1. **Select Survey Question**: Choose from available legal surveys
2. **Select Countries**: Pick one or more countries to analyze
3. **Analyze**: Click the analyze button to get results
4. **Review Results**: See structured analysis for each country with confidence levels

## Survey Questions

The agent loads survey questions from `legal_surveys.yaml`. Current surveys include:

- **Gender Discrimination**: Specialized bodies for employment discrimination complaints
- **Fair Recruitment**: Government awareness-raising measures on fair recruitment
- **Flexible Work**: Government instructional resources for flexible work arrangements

Each survey contains:
- **ID**: Unique identifier
- **Question**: The legal question to analyze
- **Criteria**: Detailed analysis criteria for consistent evaluation

## Supported Countries

- France
- Spain  
- Saudi Arabia
- United States
- Germany
- United Kingdom
- Canada

## API Endpoints

- `GET /surveys` - Get all available surveys
- `GET /countries` - Get all supported countries  
- `POST /analyze` - Analyze a survey across countries

## Development

### Backend Development
```bash
# Run with auto-reload
uv run uvicorn backend.api:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development
```bash
cd frontend
npm run dev
```

### Adding New Surveys
Edit `legal_surveys.yaml` to add new survey questions with their criteria.

### Adding New Countries
Add new countries to the `Country` enum in `legal_agent.py`.