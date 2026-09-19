# AI Operations Integrator

> Enterprise-ready AI automation for CRM operations, data quality, and daily management reporting.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white)
![Status](https://img.shields.io/badge/Status-In%20Development-orange)

## Overview

The **AI Operations Integrator** is an intelligent automation layer that connects to CRM systems, analyzes operational data, and produces concise, actionable daily briefs. It reduces manual reconciliation across candidate pipelines, job deals, activities, and data-quality exceptions.

The platform is designed to be CRM-agnostic: HubSpot is the initial integration, while provider-specific adapters keep the core workflow ready for Salesforce, Firefish, and other REST-based CRMs.

## Core Capabilities

- **Daily management briefs** — Summarize new records, pipeline movement, blockers, and priorities.
- **Exception detection** — Identify missing owners, incomplete fields, pending approvals, and stalled stages.
- **Agentic processing** — Use specialized workflow steps to fetch, validate, analyze, and format CRM data.
- **CRM abstraction** — Switch data providers without rewriting the business logic.
- **Secure integration** — Keep tokens and model credentials outside source control.
- **API-first delivery** — Expose results for dashboards, email clients, or other internal systems.

## Architecture

```text
CRM Provider (HubSpot)
               ↓
    Provider Adapter
               ↓
 Data Validation & Normalization
               ↓
 Agentic Analysis Workflow
               ↓
 Daily Briefs + Exceptions
               ↓
 FastAPI / Email / Dashboard
```

## Technology Stack

| Area | Technology |
| --- | --- |
| Backend | Python, FastAPI |
| AI workflow | LLMs, LangGraph |
| CRM integration | HubSpot REST API; extensible adapters |
| Configuration | Environment variables and `.env` |
| Output | JSON API responses and management-ready summaries |

## Prerequisites

- Python 3.10 or newer
- CRM API token with read access to Contacts and Deals
- API access to an LLM provider or a compatible local model endpoint
- Git

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/ai-operations-integrator.git
cd ai-operations-integrator
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
```

```bash
# macOS/Linux
source venv/bin/activate

# Windows PowerShell
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root. Never commit this file or real credentials.

```env
HUBSPOT_API_KEY=your_hubspot_private_app_token
LLM_API_KEY=your_llm_provider_key
LLM_MODEL=your-preferred-model
APP_ENV=development
LOG_LEVEL=INFO
```

## Running the Application

Once the API entry point is available, start the development server with:

```bash
uvicorn app.main:app --reload
```

Open the interactive API documentation at `http://127.0.0.1:8000/docs`.

> Update the module path if the application entry point uses a different package structure.

## Example Output

```json
{
   "date": "2025-01-15",
   "summary": "12 new contacts and 4 deals changed stage.",
   "priorities": [
      "Review 3 unassigned deals",
      "Follow up on 2 stalled opportunities"
   ],
   "exceptions": [
      {
         "type": "missing_owner",
         "count": 3,
         "severity": "high"
      }
   ]
}
```

## Project Status & Roadmap

- [x] Define the product scope and CRM-agnostic architecture
- [x] Add environment-based configuration guidelines
- [ ] Implement the HubSpot data-fetching adapter
- [ ] Add normalization and data-quality validation
- [ ] Build the LangGraph summarization workflow
- [ ] Add automated tests and structured logging
- [ ] Expose production-ready FastAPI endpoints
- [ ] Add email, dashboard, and scheduled-report delivery

## Security & Privacy

- Store all secrets in environment variables or a secure secret manager.
- Do not commit `.env` files, API tokens, customer data, or raw CRM exports.
- Request only the minimum CRM permissions required by the application.
- Redact sensitive information from logs and generated reports.
- Review LLM provider retention and privacy settings before sending CRM data.

## Development Guidelines

1. Keep CRM-specific code inside provider adapters.
2. Validate external API responses before passing data to the AI workflow.
3. Use typed schemas for requests, responses, and normalized CRM records.
4. Add tests for integrations, exception rules, and report formatting.
5. Keep generated reports traceable to their source data and timestamp.

## Contributing

Create a feature branch, make focused changes, add or update tests, and open a pull request with a clear description of the change.

## License

Add the project license and copyright information here before public distribution.