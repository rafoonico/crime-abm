from __future__ import annotations
import os
import random
import numpy as np
import networkx as nx
from mesa import Model
from mesa.datacollection import DataCollector
from mesa.time import RandomActivation

from .agents import PersonAgent, Status
from .network import make_scale_free_network


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


class CrimeABM(Model):
    """
    ABM of crime with explicit social network, policing, pre-trial detention (D) and prison (P).
    v0.2 features:
      - Evidence proxy based on rolling window of crimes (last N days)
      - Network rewiring on detention/prison events (drop lawful ties, add criminal ties)
    """

    def __init__(
        self,
        n_agents: int = 500,
        seed: int = 42,

        # Network
        sf_m: int = 3,

        # Initial states
        initial_criminal_share: float = 0.05,
        initial_at_risk_share: float = 0.20,

        # Behavior
        peer_influence_weight: float = 0.35,
        risk_threshold: float = 0.30,
        crime_base_rate: float = 0.05,

        # Institutions
        coercive_capacity: float = 0.03,
        forensic_capacity: float = 0.70,
        detention_days_mean: int = 30,
        conviction_base_prob: float = 0.60,
        prison_sentence_days_mean: int = 180,

        # Criminogenic effects
        detention_stigma_increment: float = 0.10,
        detention_criminal_capital_increment: float = 0.15,
        prison_criminal_capital_increment: float = 0.20,

        # Congestion
        congestion_strength: float = 0.0,

        # v0.2: evidence + rewiring
        evidence_window_days: int = 30,
        rewiring_enabled: bool = True,
        drop_lawful_edge_prob: float = 0.20,
        add_criminal_edge_prob: float = 0.25,
        max_new_edges_per_event: int = 3,
    ):
        super().__init__()
        self.random = random.Random(seed)
        np.random.seed(seed)

        self.n_agents = int(n_agents)
        self.seed = seed

        # Store params
        self.sf_m = int(sf_m)
        self.peer_influence_weight = peer_influence_weight
        self.risk_threshold = risk_threshold
        self.crime_base_rate = crime_base_rate

        self.coercive_capacity = coercive_capacity
        self.forensic_capacity = forensic_capacity
        self.detention_days_mean = int(detention_days_mean)
        self.conviction_base_prob = conviction_base_prob
        self.prison_sentence_days_mean = int(prison_sentence_days_mean)

        self.detention_stigma_increment = detention_stigma_increment
        self.detention_criminal_capital_increment = detention_criminal_capital_increment
        self.prison_criminal_capital_increment = prison_criminal_capital_increment

        self.congestion_strength = congestion_strength

        self.evidence_window_days = int(evidence_window_days)

        self.rewiring_enabled = bool(rewiring_enabled)
        self.drop_lawful_edge_prob = drop_lawful_edge_prob
        self.add_criminal_edge_prob = add_criminal_edge_prob
        self.max_new_edges_per_event = int(max_new_edges_per_event)

        # Build network
        self.G: nx.Graph = make_scale_free_network(self.n_agents, self.sf_m, seed=seed)

        # Scheduler
        self.schedule = RandomActivation(self)

        # Create agents
        self.agents_by_id: dict[int, PersonAgent] = {}
        for i in range(self.n_agents):
            u = self.random.random()
            if u < initial_criminal_share:
                status = Status.CRIMINAL
            elif u < initial_criminal_share + initial_at_risk_share:
                status = Status.AT_RISK
            else:
                status = Status.LAWFUL

            base_propensity = clamp(self.random.gauss(0.15, 0.05))
            agent = PersonAgent(
                unique_id=i,
                model=self,
                status=status,
                base_propensity=base_propensity,
                evidence_window_days=self.evidence_window_days,
            )
            self.agents_by_id[i] = agent
            self.schedule.add(agent)

        # Daily counters
        self.crime_events_today = 0
        self.wrongful_detentions_today = 0
        self.detentions_today = 0
        self.convictions_today = 0

        # Data collector
        self.datacollector = DataCollector(
            model_reporters={
                "crime_events": lambda m: m.crime_events_today,
                "detentions": lambda m: m.detentions_today,
                "wrongful_detentions": lambda m: m.wrongful_detentions_today,
                "convictions": lambda m: m.convictions_today,
                "share_criminal": lambda m: m.share_in_state(Status.CRIMINAL),
                "share_detained": lambda m: m.share_in_state(Status.DETAINED),
                "share_prison": lambda m: m.share_in_state(Status.PRISON),
            }
        )

    def share_in_state(self, st: Status) -> float:
        return sum(1 for a in self.agents_by_id.values() if a.status == st) / self.n_agents

    # ---------- Daily cycle ----------

    def step(self):
        self.crime_events_today = 0
        self.wrongful_detentions_today = 0
        self.detentions_today = 0
        self.convictions_today = 0

        # Agents act first (offending + timers + transitions)
        self.schedule.step()

        # Then policing (design choice)
        self.police_step()

        self.datacollector.collect(self)

    # ---------- Agent processes ----------

    def register_daily_crime(self, agent: PersonAgent):
        # push today's crimes into rolling window
        agent.crime_history.append(1 if agent.crime_today > 0 else 0)

    def update_risk_state(self, agent: PersonAgent):
        if agent.status not in (Status.LAWFUL, Status.AT_RISK, Status.CRIMINAL):
            return

        peer = agent.share_criminal_neighbors()
        propensity = clamp(
            agent.base_propensity
            + self.peer_influence_weight * peer
            + 0.25 * agent.stigma
            + 0.35 * agent.criminal_capital
        )

        if agent.status == Status.LAWFUL and propensity >= self.risk_threshold:
            agent.status = Status.AT_RISK

        if agent.status == Status.AT_RISK:
            if self.random.random() < propensity:
                agent.status = Status.CRIMINAL

    def attempt_crime(self, agent: PersonAgent):
        peer = agent.share_criminal_neighbors()
        p = clamp(self.crime_base_rate + 0.25 * agent.criminal_capital + 0.10 * peer)
        if self.random.random() < p:
            self.crime_events_today += 1
            agent.crime_today += 1

    # ---------- Policing & institutions ----------

    def police_step(self):
        n_attempts = max(0, int(self.coercive_capacity * self.n_agents))
        if n_attempts == 0:
            return

        criminals = [a for a in self.agents_by_id.values() if a.status == Status.CRIMINAL]
        non_criminals = [a for a in self.agents_by_id.values() if a.status in (Status.LAWFUL, Status.AT_RISK)]

        for _ in range(n_attempts):
            if self.random.random() < self.forensic_capacity and criminals:
                target = self.random.choice(criminals)
                wrongful = False
            else:
                if not non_criminals:
                    continue
                target = self.random.choice(non_criminals)
                wrongful = True

            if target.status in (Status.DETAINED, Status.PRISON):
                continue

            self.detentions_today += 1
            if wrongful:
                self.wrongful_detentions_today += 1

            det_days = max(1, int(np.random.exponential(self.detention_days_mean)))
            target.detain(det_days)

            # immediate criminogenic effect (stigma at entry)
            target.stigma = clamp(target.stigma + self.detention_stigma_increment)

            # v0.2 rewiring on detention event
            if self.rewiring_enabled:
                self.rewire_on_incarceration_event(target)

    def resolve_judicial_outcome(self, agent: PersonAgent):
        """
        At end of detention, either convict or release.
        Evidence proxy: crimes committed in last N days.
        """
        crimes_recent = agent.crimes_last_window()
        # Map crimes_recent -> evidence strength
        # 0 crimes => weak evidence; 1+ crimes => stronger evidence (bounded)
        evidence = 0.35 + 0.65 * clamp(crimes_recent / max(1, self.evidence_window_days * 0.15))
        # conviction probability increases with forensics and evidence
        p_convict = clamp(self.conviction_base_prob * self.forensic_capacity * evidence)

        if self.random.random() < p_convict:
            self.convictions_today += 1

            base = max(1, int(np.random.exponential(self.prison_sentence_days_mean)))
            if self.congestion_strength > 0:
                prison_share = self.share_in_state(Status.PRISON)
                base = max(1, int(base * (1.0 - self.congestion_strength * prison_share)))

            agent.imprison(base)

            # prison increases criminal capital
            agent.criminal_capital = clamp(agent.criminal_capital + self.prison_criminal_capital_increment)

            # rewiring again (prison as stronger mixing)
            if self.rewiring_enabled:
                self.rewire_on_incarceration_event(agent)

        else:
            # release to AT_RISK but with criminogenic increment (your key premise)
            agent.status = Status.AT_RISK
            agent.criminal_capital = clamp(agent.criminal_capital + self.detention_criminal_capital_increment)

    def release_from_prison(self, agent: PersonAgent):
        agent.status = Status.AT_RISK
        # small reintegration penalty + retained criminal capital
        agent.criminal_capital = clamp(agent.criminal_capital + 0.05)

    # ---------- v0.2: Network rewiring ----------

    def rewire_on_incarceration_event(self, agent: PersonAgent):
        """
        Simple rewiring:
          - With some probability, drop edges to LAWFUL neighbors (social ties decay)
          - Add edges to CRIMINAL nodes (new criminal ties / exposure)
        """
        agent_id = agent.unique_id

        # Drop some lawful ties
        neighbors = list(self.G.neighbors(agent_id))
        for nbr_id in neighbors:
            nbr = self.agents_by_id[nbr_id]
            if nbr.status == Status.LAWFUL and self.random.random() < self.drop_lawful_edge_prob:
                if self.G.has_edge(agent_id, nbr_id):
                    self.G.remove_edge(agent_id, nbr_id)

        # Add some criminal ties
        criminals = [a.unique_id for a in self.agents_by_id.values() if a.status == Status.CRIMINAL and a.unique_id != agent_id]
        if not criminals:
            return

        added = 0
        attempts = 0
        while added < self.max_new_edges_per_event and attempts < self.max_new_edges_per_event * 5:
            attempts += 1
            cand = self.random.choice(criminals)
            if cand == agent_id:
                continue
            if not self.G.has_edge(agent_id, cand):
                self.G.add_edge(agent_id, cand)
                added += 1
