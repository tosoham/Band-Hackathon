# BandGate

Band of Agents Hackathon project for a cybersecurity/government RFP promise gate.

Implementation should run through Docker Compose as defined in [PLAN.md](PLAN.md).

## Day 1 Run Commands

```bash
cp .env.example .env
docker compose up --build
```

Backend smoke commands:

```bash
docker compose run backend python run_demo.py
docker compose run backend pytest
```

Default local URLs:

- Frontend: http://localhost:3000
- Backend health: http://localhost:8000/health
- Backend state: http://localhost:8000/state
