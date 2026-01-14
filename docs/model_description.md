# Model Description
## Crime, Wrongful Detention & Forensic Capacity — An Agent-Based Model (Brazil)

### 1. What this model is
This repository implements an **agent-based model (ABM)** with an **explicit social network** to study the dynamics of crime under alternative institutional regimes. Individuals interact through persistent ties (a network), commit crimes probabilistically, and may be arrested, detained pre-trial, convicted, imprisoned, and released. The model represents an urban setting inspired by Brazilian metropolitan contexts, where a key concern is the imbalance between **pre-trial detention and convictions**, and the role of **investigative/forensic capacity** in preventing wrongful detention.

The model is explicitly **mechanism-based**: it encodes plausible social and institutional mechanisms and observes how macro-level patterns (crime persistence, incarceration rates, wrongful detention) emerge from micro-level rules.

### 2. What question it answers
The model evaluates the policy trade-off between:
- **Coercive capacity** (policing intensity: arrest attempts, enforcement pressure),
and
- **Forensic/investigative capacity** (quality of evidence and targeting accuracy: the ability to identify true offenders and correctly convict them).

It asks:

**How do investments in investigative/forensic capacity versus coercive policing affect:**
1) long-run crime levels and persistence (inertia),
2) wrongful detention (detaining non-offenders),
3) conviction-to-detention ratios,
4) the endogenous production of future criminals via criminogenic detention/prison exposure?

A core hypothesis is:

> Increasing coercive capacity without adequate forensic capacity can increase wrongful detention and criminogenic exposure, generating persistent crime even under higher incarceration pressure.

### 3. Agents, states, and attributes
Each node in the network is an individual agent with a discrete state:

- **LAWFUL (L)**: law-abiding
- **AT_RISK (R)**: susceptible/at risk of entering crime
- **CRIMINAL (C)**: criminally active
- **DETAINED (D)**: pre-trial detention (not yet convicted)
- **PRISON (P)**: convicted and serving a sentence

Key agent attributes:
- `base_propensity`: baseline inclination towards crime (heterogeneity)
- `stigma`: increases with detention; raises future propensity
- `criminal_capital`: increases with detention/prison exposure; raises future propensity and crime rate
- `crime_history`: rolling window of recent crime events (evidence proxy)

### 4. Environment: explicit social network
Agents are embedded in a **scale-free network** (Barabási–Albert), capturing hub-like connectivity patterns common in social systems. The network supports:
- peer influence (exposure to criminal neighbors),
- persistence of social ties,
- rewiring under incarceration (ties decay and criminal ties form).

This structure is crucial for modeling social spillovers and “schools of crime” dynamics.

### 5. Time and scheduling
Time is discrete. **One tick = one day**.

A daily tick includes:
1) **Social influence and state transitions** (L → R → C)
2) **Crime generation** (C agents may commit crime events; crime is a count)
3) **Institutional enforcement** (police arrest attempts)
4) **Detention countdown and judicial processing** (D → P or D → R)
5) **Prison countdown** (P → R)
6) **Network rewiring** (upon detention/prison events)
7) **Data collection** (crime, detentions, convictions, shares by state)

### 6. Behavioral rules (core mechanisms)

#### 6.1 Social influence and entry into crime
Agents transition based on:
- baseline propensity,
- the fraction of criminal neighbors,
- stigma and criminal capital.

Intuition:
- exposure to criminals increases risk,
- detention/prison raise stigma/capital, making future crime more likely.

#### 6.2 Crime events (count-based)
Criminal agents commit crimes probabilistically. Each day produces a **count** of crime events, not victim-level interactions. (Victimization modeling can be added later.)

#### 6.3 Policing and arrest targeting (coercion vs forensics)
Each day, police make a number of arrest attempts proportional to **coercive capacity**.
Target selection depends on **forensic capacity**:
- high forensics: arrests more likely target true criminals,
- low forensics: higher chance of detaining non-offenders (wrongful detention).

Arrested agents enter **DETAINED (D)** for a stochastic detention duration.

#### 6.4 Judicial outcome: conviction vs release
At the end of detention, the agent is either:
- **convicted → PRISON (P)**, or
- **released → AT_RISK (R)**.

Conviction probability increases with forensic capacity and with a proxy for evidence strength. In v0.2, evidence is derived from the agent’s **rolling crime history** over the last N days.

#### 6.5 Criminogenic pre-trial detention (key premise)
Pre-trial detention is modeled as intrinsically criminogenic:
- it raises `stigma` at detention entry,
- and upon release (even without conviction), it raises `criminal_capital`.

This encodes mechanisms such as socialization, reputational damage, and reduced legal opportunity.

#### 6.6 Prison and congestion (optional)
Prison increases criminal capital further. Additionally, a congestion mechanism can shorten sentences as prison population grows, potentially weakening incapacitation effects.

#### 6.7 Network rewiring under incarceration (v0.2)
Upon detention or imprisonment, the agent’s ties are modified:
- some ties to lawful neighbors are dropped (social ties decay),
- new ties to criminal agents are formed (criminal exposure increases).

This produces more realistic “school of crime” dynamics.

### 7. Outputs and metrics
The simulation produces time series for:
- daily crime events
- detentions, wrongful detentions, convictions
- population shares in each state (L, R, C, D, P)

Derived metrics for analysis:
- wrongful detention rate
- conviction/detention ratio
- crime persistence under policy regimes

### 8. Experiments and policy scenarios
The model supports counterfactual experiments by varying:
- coercive capacity (arrest intensity),
- forensic capacity (targeting/evidence quality),
- judicial throughput (detention duration),
- prison congestion (sentence shortening),
and rewiring intensity.

A recommended experiment is a grid sweep over (forensics × coercion) to map regimes where “more coercion” reduces crime versus regimes where it amplifies wrongful detention and long-run crime.

### 9. Implementation modules
- `model/network.py`: network generation (scale-free)
- `model/agents.py`: agent definition, states, rolling evidence window
- `model/model.py`: dynamics, policing, judicial outcomes, rewiring, and data collection
- `run_baseline.py`: reads `config.yml`, runs simulation, writes CSV + params YAML into `experiments/`

