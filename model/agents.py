from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from collections import deque
from mesa import Agent


class Status(Enum):
    LAWFUL = auto()       # L
    AT_RISK = auto()      # R
    CRIMINAL = auto()     # C
    DETAINED = auto()     # D (pre-trial)
    PRISON = auto()       # P (post-conviction)


@dataclass
class Timers:
    detained_days_left: int = 0
    prison_days_left: int = 0


class PersonAgent(Agent):
    """
    Individual agent living in a social network.
    v0.2: Keeps rolling crime history for evidence proxy (e.g., crimes in last 30 days).
    """

    def __init__(
        self,
        unique_id: int,
        model,
        status: Status,
        base_propensity: float,
        evidence_window_days: int = 30,
    ):
        super().__init__(unique_id, model)
        self.status = status
        self.base_propensity = base_propensity

        # Criminogenic state variables
        self.criminal_capital = 0.0
        self.stigma = 0.0

        # Timers
        self.timers = Timers()

        # v0.2: rolling window of crime events per day (0/1)
        self.evidence_window_days = max(1, int(evidence_window_days))
        self.crime_history = deque([0] * self.evidence_window_days, maxlen=self.evidence_window_days)

        # bookkeeping
        self.crime_today = 0

    def neighbors(self) -> list["PersonAgent"]:
        nbr_ids = list(self.model.G.neighbors(self.unique_id))
        return [self.model.agents_by_id[i] for i in nbr_ids]

    def share_criminal_neighbors(self) -> float:
        nbrs = self.neighbors()
        if not nbrs:
            return 0.0
        criminal = sum(1 for a in nbrs if a.status == Status.CRIMINAL)
        return criminal / len(nbrs)

    def crimes_last_window(self) -> int:
        return sum(self.crime_history)

    def step(self):
        # start-of-day
        self.crime_today = 0

        # If detained/prison: countdown + no offending
        if self.status == Status.DETAINED:
            self.timers.detained_days_left -= 1
            if self.timers.detained_days_left <= 0:
                self.model.resolve_judicial_outcome(self)
            # still push "no crime" for today at day end
            self.model.register_daily_crime(self)
            return

        if self.status == Status.PRISON:
            self.timers.prison_days_left -= 1
            if self.timers.prison_days_left <= 0:
                self.model.release_from_prison(self)
            self.model.register_daily_crime(self)
            return

        # Otherwise: update risk state then possibly commit crime
        self.model.update_risk_state(self)

        if self.status == Status.CRIMINAL:
            self.model.attempt_crime(self)

        # end-of-day: store crime_today into rolling window
        self.model.register_daily_crime(self)

    # Controlled by model:
    def detain(self, days: int):
        self.status = Status.DETAINED
        self.timers.detained_days_left = max(1, int(days))

    def imprison(self, days: int):
        self.status = Status.PRISON
        self.timers.prison_days_left = max(1, int(days))
