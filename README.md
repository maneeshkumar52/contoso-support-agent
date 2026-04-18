# Contoso Support Agent

Professional-grade multi-service support platform with dedicated triage, draft, resolution, and orchestration services.

## 1. Executive Overview

This repository provides:
- Specialized microservices for support lifecycle stages
- Central orchestrator for service composition
- Clear service boundaries for scale and resilience

## 2. Architecture

```txt
Client
  |
  v
Orchestrator Service (8000)
  |
  +--> Triage Service (8001)
  +--> Draft Service (8002)
  +--> Resolution Service (8003)
```

## 3. Repository Structure

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

## 4. Prerequisites

- Python 3.10+
- pip 23+
- Git

## 5. Local Setup

```bash
git clone https://github.com/maneeshkumar52/contoso-support-agent.git
cd contoso-support-agent
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 6. Run Services (four terminals)

```bash
uvicorn triage_agent.main:app --host 0.0.0.0 --port 8001 --reload
uvicorn draft_agent.main:app --host 0.0.0.0 --port 8002 --reload
uvicorn resolution_agent.main:app --host 0.0.0.0 --port 8003 --reload
uvicorn orchestrator.main:app --host 0.0.0.0 --port 8000 --reload
```

## 7. Validation

- Orchestrator docs: http://127.0.0.1:8000/docs
- Triage docs: http://127.0.0.1:8001/docs
- Draft docs: http://127.0.0.1:8002/docs
- Resolution docs: http://127.0.0.1:8003/docs

```bash
python3 -m compileall -q .
pytest -q
python demo_e2e.py
```

## 8. Troubleshooting

- Inter-service failures: ensure all four services are running
- Port conflicts: adjust port mappings consistently
- Import errors: activate virtual environment before launch

## 9. License

See LICENSE in this repository.
