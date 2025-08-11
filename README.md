# Aylen Legal AI Agent

A simple Legal AI agent using Pydantic AI that provides consistent legal analysis across different countries.

## Features

- 🤖 **Structured Analysis**: Uses Pydantic AI for consistent, structured responses
- 🌍 **Multi-Country Support**: Analyze laws across France, Spain, Saudi Arabia, and more
- 📋 **Consistent Criteria**: Same analysis framework applied to all countries
- 🔄 **Easy Comparison**: Built-in function to compare laws across multiple countries

## Quick Start

### Prerequisites

- Python 3.9+
- [uv](https://docs.astral.sh/uv/) package manager
- AWS credentials configured for Bedrock access
- Access to Claude models in AWS Bedrock (us-east-1 region)

### Installation

```bash
# Install dependencies using uv
uv sync

# Or install in development mode with dev dependencies
uv sync --group dev
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

# Option 3: AWS credentials file (~/.aws/credentials)
```

Make sure you have access to Claude models in AWS Bedrock (us-east-1 region).

### Usage

```bash
# Run the example
uv run python legal_agent.py
```

This will analyze "Is there any paternity leave?" for France, Spain, and Saudi Arabia.

## Example Output

```
=== France ===
Answer: Yes, France provides paternity leave
Legal Basis: French Labor Code (Code du travail)
Duration/Amount: 28 days (25 days + 3 days birth leave)
Eligibility: Employee status, child birth or adoption
Confidence: High
```

## Development

```bash
# Install with dev dependencies
uv sync --group dev

# Run linting
uv run ruff check .

# Format code
uv run ruff format .
```

## Project Structure

```
aylen/
├── pyproject.toml          # Project configuration and dependencies
├── apy_keys.yaml          # API keys (not in git)
├── legal_agent.py         # Main Legal AI agent
└── README.md             # This file
```