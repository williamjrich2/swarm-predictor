"""
Hard Score Calculator

The pure math pillar. This scores teams based entirely on
advanced analytics and statistical performance.

Metrics used:
- Adjusted Offensive Efficiency (points per 100 possessions, adjusted for opponent)
- Adjusted Defensive Efficiency (points allowed per 100 possessions, adjusted)
- Barthag (T-Rank's power rating, probability of beating average D1 team)
- Four Factors (eFG%, TO%, ORB%, FTR) for offense and defense
- Strength of Schedule
- Recent form (last 10 games weighted heavier)
- Head-to-head if available
- Historical seed performance in tournament
"""

import numpy as np
class Console:
    def print(self, *a, **kw): pass

console = Console()


class HardScoreCalculator:
    """
    Calculates the Hard Score (0-100) for a team matchup.

    Higher = stronger team by the numbers.
    This is the "what the math says" pillar.
    """

    # Historical tournament win rates by seed (1985-present averages)
    SEED_WIN_RATES = {
        1: 0.85, 2: 0.72, 3: 0.65, 4: 0.58, 5: 0.52,
        6: 0.48, 7: 0.42, 8: 0.38, 9: 0.37, 10: 0.35,
        11: 0.33, 12: 0.30, 13: 0.18, 14: 0.12, 15: 0.07, 16: 0.02,
    }

    # Weight distribution within the hard score
    WEIGHTS = {
        "efficiency_margin": 0.30,    # Single strongest predictor
        "barthag": 0.20,              # T-Rank power rating
        "four_factors_offense": 0.12, # How well they create shots
        "four_factors_defense": 0.12, # How well they prevent shots
        "sos": 0.10,                  # Quality of opponents faced
        "recent_form": 0.08,          # Performance trend
        "seed_history": 0.08,         # Historical seed success
    }

    def __init__(self, config: dict = None):
        self.config = config or {}

    def calculate(self, team_a: dict, team_b: dict, context: dict = None) -> dict:
        """
        Calculate hard scores for both teams in a matchup.

        Args:
            team_a: dict of team A's unified data
            team_b: dict of team B's unified data
            context: optional dict with round, venue, etc.

        Returns:
            dict with scores and breakdown for both teams
        """
        context = context or {}

        score_a = self._score_team(team_a, team_b)
        score_b = self._score_team(team_b, team_a)

        # Normalize so they're relative to each other
        total = score_a["total"] + score_b["total"]
        if total > 0:
            norm_a = (score_a["total"] / total) * 100
            norm_b = (score_b["total"] / total) * 100
        else:
            norm_a = norm_b = 50.0

        return {
            "team_a": {
                "hard_score": round(norm_a, 2),
                "breakdown": score_a,
            },
            "team_b": {
                "hard_score": round(norm_b, 2),
                "breakdown": score_b,
            },
            "edge": "team_a" if norm_a > norm_b else "team_b",
            "edge_margin": round(abs(norm_a - norm_b), 2),
        }

    def _score_team(self, team: dict, opponent: dict) -> dict:
        """Calculate raw hard score components for one team."""

        components = {}

        # 1. Efficiency Margin
        adj_o = self._safe_float(team, ["adj_o", "adjoe", "adj_offense", "offensive_efficiency"])
        adj_d = self._safe_float(team, ["adj_d", "adjde", "adj_defense", "defensive_efficiency"])
        opp_adj_o = self._safe_float(opponent, ["adj_o", "adjoe"])
        opp_adj_d = self._safe_float(opponent, ["adj_d", "adjde"])

        if adj_o and adj_d:
            eff_margin = adj_o - adj_d
            # Normalize: typical range is -15 to +35
            components["efficiency_margin"] = self._normalize(eff_margin, -15, 35)

            # Matchup-specific: our offense vs their defense, our defense vs their offense
            if opp_adj_d:
                offensive_matchup = adj_o - opp_adj_d  # Positive = we score well vs them
                components["offensive_matchup"] = offensive_matchup
            if opp_adj_o:
                defensive_matchup = opp_adj_o - adj_d  # Negative = we defend well vs them
                components["defensive_matchup"] = defensive_matchup
        else:
            components["efficiency_margin"] = 0.5  # Default to average

        # 2. Barthag (T-Rank power rating)
        barthag = self._safe_float(team, ["barthag", "barthag_rk", "power_rating"])
        if barthag:
            # Barthag is 0-1 probability
            if barthag > 1:
                barthag = barthag / 100  # Might be a percentage
            components["barthag"] = barthag
        else:
            components["barthag"] = 0.5

        # 3. Four Factors - Offense
        efg = self._safe_float(team, ["efg_o", "efg_pct", "off_efg", "efg"])
        to_rate = self._safe_float(team, ["tov_o", "to_rate", "off_to", "turnover_pct"])
        orb_rate = self._safe_float(team, ["orb_o", "orb_rate", "off_reb_rate", "orb_pct"])
        ftr = self._safe_float(team, ["ftr_o", "ft_rate", "off_ftr", "free_throw_rate"])

        off_factors = []
        if efg:
            off_factors.append(self._normalize(efg, 0.42, 0.58))
        if to_rate:
            # Lower turnover rate is better, so invert
            off_factors.append(1 - self._normalize(to_rate, 0.12, 0.25))
        if orb_rate:
            off_factors.append(self._normalize(orb_rate, 0.20, 0.38))
        if ftr:
            off_factors.append(self._normalize(ftr, 0.20, 0.42))

        components["four_factors_offense"] = np.mean(off_factors) if off_factors else 0.5

        # 4. Four Factors - Defense (lower is better for opponent metrics)
        d_efg = self._safe_float(team, ["efg_d", "def_efg", "opp_efg"])
        d_to = self._safe_float(team, ["tov_d", "def_to", "opp_to_rate"])
        d_orb = self._safe_float(team, ["orb_d", "def_reb", "opp_orb"])
        d_ftr = self._safe_float(team, ["ftr_d", "def_ftr", "opp_ftr"])

        def_factors = []
        if d_efg:
            def_factors.append(1 - self._normalize(d_efg, 0.42, 0.58))  # Lower = better defense
        if d_to:
            def_factors.append(self._normalize(d_to, 0.12, 0.25))  # Higher = we force more TOs
        if d_orb:
            def_factors.append(1 - self._normalize(d_orb, 0.20, 0.38))  # Lower = we limit their ORBs
        if d_ftr:
            def_factors.append(1 - self._normalize(d_ftr, 0.20, 0.42))  # Lower = we keep them off the line

        components["four_factors_defense"] = np.mean(def_factors) if def_factors else 0.5

        # 5. Strength of Schedule
        sos = self._safe_float(team, ["sos", "strength_of_schedule", "sos_rank"])
        if sos:
            if sos > 1:  # It's a rank (lower = harder schedule)
                components["sos"] = 1 - self._normalize(sos, 1, 363)
            else:
                components["sos"] = self._normalize(sos, -10, 15)
        else:
            components["sos"] = 0.5

        # 6. Recent Form (win % of last 10 if available)
        win_pct = self._safe_float(team, ["win_pct", "wpct"])
        if win_pct:
            components["recent_form"] = win_pct
        else:
            components["recent_form"] = 0.5

        # 7. Historical Seed Performance
        seed = self._safe_float(team, ["seed", "tournament_seed", "ncaa_seed"])
        if seed and 1 <= seed <= 16:
            components["seed_history"] = self.SEED_WIN_RATES.get(int(seed), 0.25)
        else:
            components["seed_history"] = 0.25

        # Calculate weighted total
        total = 0
        for key, weight in self.WEIGHTS.items():
            val = components.get(key, 0.5)
            total += val * weight

        components["total"] = total

        return components

    def _safe_float(self, data: dict, keys: list) -> float:
        """Try multiple possible column names and return the first valid float."""
        for key in keys:
            val = data.get(key)
            if val is not None:
                try:
                    f = float(val)
                    if not np.isnan(f):
                        return f
                except (ValueError, TypeError):
                    continue
        return None

    def _normalize(self, value: float, min_val: float, max_val: float) -> float:
        """Normalize a value to 0-1 range."""
        if max_val == min_val:
            return 0.5
        normalized = (value - min_val) / (max_val - min_val)
        return max(0.0, min(1.0, normalized))
