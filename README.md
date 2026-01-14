# Crime, Wrongful Detention & Forensic Capacity — ABM (Brazil)

This repository implements an **Agent-Based Model (ABM)** with an **explicit social network** to study crime dynamics under alternative institutional regimes. The model focuses on the trade-off between:

- **Coercive capacity** (policing intensity: arrests/enforcement pressure)
- **Forensic/investigative capacity** (targeting accuracy and evidence quality)

It is inspired by Brazilian metropolitan contexts where **pre-trial detention can be high relative to convictions**, and limited investigative capacity may increase **wrongful detention** and criminogenic exposure.

## Research question
How do investments in forensic capacity versus coercive policing affect:
- crime persistence (inertia),
- wrongful detention,
- conviction-to-detention ratios,
- and the endogenous production of criminals through detention/prison exposure?

## Repository structure

```bash
crime-abm/
├── config.yml
├── run_baseline.py
├── notebooks/
├── model/
│ ├── agents.py
│ ├── model.py
│ └── network.py
├── experiments/
└── docs/
└── model_description.md
```

## Setup (Conda)
Create and activate a conda environment:

```bash
conda create -n crime_abm python=3.11 -y
conda activate crime_abm
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run a baseline simulation

Edit parameters in config.yml (optional), then run:

```bash
python run_baseline.py
```

Outputs will be saved to experiments/:

- a CSV with daily metrics (timestamp + key params in filename)

- a companion YAML storing the exact parameters used

Example output:

- experiments/20260113-214455__n500__m3__fc0p55__cc0p04__det45__evw30.csv

- experiments/20260113-214455__n500__m3__fc0p55__cc0p04__det45__evw30.yml

## Notes

- Time is discrete (1 tick = 1 day).

- Crime is modeled as a count of daily events (victimization modeling can be added later).

- Pre-trial detention is explicitly criminogenic: it increases future offending propensity via stigma/criminal capital increments.

- v0.2 introduces rolling evidence windows and network rewiring under incarceration.

## Next steps (planned)

- Parameter sweeps (forensics × coercion grid) saving a summary table

- Calibration hooks using Brazilian public indicators (e.g., FBSP-inspired)

- Extensions: victimization, spatial neighborhoods, heterogeneous policing across districts