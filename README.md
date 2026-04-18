# Contoso Support Agent

Multi-agent customer support system with dedicated triage, draft, resolution, and orchestration services.

## Architecture

- Triage Agent: classifies incoming support requests
- Draft Agent: proposes response drafts and resolution paths
- Resolution Agent: finalizes actionable responses
- Orchestrator: coordinates service-to-service workflow and returns unified output

## Repository Structure

```txt
contoso-support-agent/
  orchestrator/main.py
  triage_agent/main.py
  draft_agent/main.py
  resolution_agent/main.py
  shared/
  tests/
  requirements.txt
```

## Prerequisites

- Python 3.10+
- pip 23+

## Setup and Execution

1. Clone and enter repository

```bash
git clone https://github.com/maneeshkumar52/contoso-support-agent.git
cd contoso-support-agent
```

2. Create virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. Run services (four terminals)

```bash
uvicorn triage_agent.main:app --port 8001 --reload
uvicorn draft_agent.main:app --port 8002 --reload
uvicorn resolution_agent.main:app --port 8003 --reload
uvicorn orchestrator.main:app --port 8000 --reload
```

5. Validate

- Orchestrator docs: http://127.0.0.1:8000/docs
- Triage docs: http://127.0.0.1:8001/docs
- Draft docs: http://127.0.0.1:8002/docs
- Resolution docs: http://127.0.0.1:8003/docs

## Testing

```bash
pytest -q
python demo_e2e.py
```

## Troubleshooting

- Inter-service call failures: ensure all four services are running
- Port conflicts: reassign ports and update orchestrator configuration
- Startup import errors: activate virtual environment before launch

## License

See `LICENSE` in this repository.
