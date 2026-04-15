<p align="center">
  <img src="front/src/assets/lobx_logo.png" alt="LOBX Logo" width="200"/>
</p>

<h1 align="center">LOBX</h1>

<p align="center">
  <strong>Limit Order Book Exchange</strong><br/>
  A research platform for conducting financial market experiments.
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" alt="Python"/></a>
  <a href="https://vuejs.org/"><img src="https://img.shields.io/badge/vue-3-42b883?logo=vuedotjs&logoColor=white" alt="Vue 3"/></a>
  <a href="https://www.docker.com/"><img src="https://img.shields.io/badge/docker-compose-2496ED?logo=docker&logoColor=white" alt="Docker"/></a>
  <a href="https://github.com/lobx-platform/lobx/blob/main/LICENSE"><img src="https://img.shields.io/github/license/lobx-platform/lobx?color=2b9348" alt="License"/></a>
  <a href="https://github.com/lobx-platform/lobx/issues"><img src="https://img.shields.io/github/issues/lobx-platform/lobx" alt="Issues"/></a>
</p>

---

LOBX (Limit Order Book Exchange) is a research platform for conducting financial market experiments. Built for experimental economics research at Royal Holloway, University of London, funded by the Leverhulme Trust (PRG-2021-359).

## Key Features

- **Continuous Double Auction** -- Price-time priority matching engine with a full limit order book
- **Multi-Participant Sessions** -- Cohort-based treatment groups with automatic role assignment
- **AI Trader Integration** -- LLM-powered agents, informed traders, noise traders, and spoofers
- **Real-Time Interface** -- Live order book, price charts, and instant execution feedback
- **Lab Session Management** -- Token-based authentication for controlled lab environments
- **Batch Experiment Mode** -- Headless automated runs for large-scale data collection
- **Docker Deployment** -- Single-command setup via Docker Compose

## Architecture

| Layer | Technology |
|-------|------------|
| Backend | FastAPI (Python 3.11+) |
| Frontend | Vue 3 + Vite |
| Communication | WebSocket (real-time), REST API |
| Infrastructure | Docker Compose |

## Quick Start

### One-Line Installation

```bash
bash <(curl -sSL https://raw.githubusercontent.com/lobx-platform/lobx/main/run.sh)
```

### Development Setup

```bash
sh run.sh dev
```

This starts both the backend (port 8000) and frontend (port 3000) via Docker Compose.

## Alternative Installation without Docker

Clone the repositiory
Ensure you are in the directory where the repo has been placed
Open a terminal. Run the front end executing the following:
```
cd front
npm install
npm audit fix
npm run dev
```
Open a terminal. Run the back end end executing the following:
```
cd back
uv sync
uv run uvicorn api.endpoints:app --reload
```

## Documentation

For detailed documentation, feature explanations, and API references, visit the [Wiki](https://github.com/lobx-platform/lobx/wiki).

## License

MIT License -- see [LICENSE](LICENSE) for details.

---
