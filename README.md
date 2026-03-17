# 🏀 Swarm Predictor

**NCAA 2026 March Madness bracket predictor** powered by Monte Carlo simulation and a 3-pillar prediction engine.

## Features
- **Interactive Bracket** — Full 2026 NCAA tournament with Swarm Predictor picks
- **Game Simulator** — Simulate any matchup with live Torvik metrics
- **Tournament Runner** — Run up to 49,999 simulations to generate champion odds
- **Swarm AI Chat** — Talk to an LLM analyst pre-loaded with tournament context

## Prediction Engine
- **Hard Score (55%)** — Torvik adjOE, adjDE, Barthag, SOS, WAB
- **Soft Score (25%)** — Momentum, coach experience, roster continuity, fan energy
- **Chaos Score (20%)** — Historical upset rates, Cinderella profiles, variance

## 2026 Picks
- 🔵 East: **Duke**
- 🔴 South: **Florida**
- 🟡 West: **Arizona**
- 🟢 Midwest: **Michigan**
- 🏆 Champion: **Duke** 77-74 over Michigan

⚠️ Alabama adjusted: Aden Holloway suspended (felony arrest 3/16/26)

## Deploy
```bash
# Local
pip install flask requests
python app.py

# Vercel
vercel --prod
```

## Stack
- Python Flask (local) / Vercel Serverless (prod)
- Vanilla HTML/CSS/JS — zero build step
- OpenRouter free LLM (DeepSeek R1)
- Torvik live data feed
