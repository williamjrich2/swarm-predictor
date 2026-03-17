"""
Chaos Score Calculator

The unpredictability pillar. March Madness exists because of chaos.

This module quantifies the LIKELIHOOD of chaos occurring and penalizes
or rewards teams based on their vulnerability to or capacity for chaos.

"The tournament doesn't care about your adjusted efficiency."

Key concepts:
- Seed upset probability (12 over 5 happens 35% of the time historically)
- Cinderella factor (mid-majors with nothing to lose play fearless)
- Variance in performance (consistent teams vs boom-or-bust teams)
- Clutch performance under pressure
- The "any given Sunday" randomness inherent in single-elimination
- Referee impact (foul-dependent teams are more vulnerable to chaos)
- Injury uncertainty
"""

import json
import os
import numpy as np
from pathlib import Path
from rich.console import Console

console = Console()

MADNESS_PRINCIPLE = """
March Madness outcomes are fundamentally driven by human factors:
- A team on a hot streak plays with a different energy
- Conference tournament champions have nothing to prove and everything to gain
- Underdogs play free; favorites play with the weight of expectation
- The math tells us the floor. The human element determines the ceiling.
"""


class ChaosScoreCalculator:
    """
    Calculates the Chaos Score (0-100).

    For favorites: Higher chaos score = MORE VULNERABLE to upset
    For underdogs: Higher chaos score = MORE LIKELY to pull the upset

    This is inverted based on context. The engine uses it to adjust
    the final prediction away from what pure math would suggest.
    """

    # Historical first-round upset rates by seed matchup
    # Format: (higher_seed, lower_seed): upset_probability
    HISTORICAL_UPSETS = {
        (1, 16): 0.02,   # 1 loss in ~150 games (UMBC miracle)
        (2, 15): 0.06,   # Happens every few years
        (3, 14): 0.13,   # Not uncommon
        (4, 13): 0.20,   # Fairly regular
        (5, 12): 0.35,   # INFAMOUS. The 5-12 upset is a March staple.
        (6, 11): 0.37,   # 11 seeds often have momentum from play-in
        (7, 10): 0.40,   # Basically a coin flip
        (8, 9): 0.49,    # Near perfect toss-up
    }

    # Round-by-round chaos decay
    # Earlier rounds are more chaotic. By the Final Four, talent wins.
    ROUND_CHAOS_MULTIPLIER = {
        "First Four": 1.1,
        "Round of 64": 1.0,
        "Round of 32": 0.85,
        "Sweet 16": 0.70,
        "Elite 8": 0.55,
        "Final Four": 0.40,
        "Championship": 0.30,
    }

    # Conference "Cinderella potential" (mid-majors that historically upset)
    CINDERELLA_CONFERENCES = {
        "WCC", "MVC", "A-10", "CAA", "SoCon", "Horizon", "MAAC",
        "WAC", "Sun Belt", "Big South", "OVC", "AEC", "Patriot",
        "NEC", "MEAC", "SWAC", "Southland", "Big Sky", "Summit",
    }

    def __init__(self, config: dict = None):
        self.config = config or {}
        self._load_historical_priors()

    def _load_historical_priors(self):
        """
        Load upset rates from historical data file.
        Falls back to hardcoded HISTORICAL_UPSETS if file doesn't exist.
        """
        # Search for the priors file relative to this module
        search_paths = [
            Path("./output/historical/historical_priors.json"),
            Path(__file__).parent.parent / "output/historical/historical_priors.json",
            Path(os.environ.get("SWARM_PRIORS_PATH", "")) if os.environ.get("SWARM_PRIORS_PATH") else None,
        ]

        for path in search_paths:
            if path and path.exists():
                try:
                    data = json.loads(path.read_text())
                    raw = data.get("upset_rates", {})
                    # Convert "5_vs_12": 0.362 → (5, 12): 0.362
                    loaded = {}
                    for key, val in raw.items():
                        parts = key.split("_vs_")
                        if len(parts) == 2:
                            try:
                                loaded[(int(parts[0]), int(parts[1]))] = float(val)
                            except ValueError:
                                pass
                    if loaded:
                        self.HISTORICAL_UPSETS = {**self.HISTORICAL_UPSETS, **loaded}
                        console.print(f"  [dim]Loaded {len(loaded)} historical upset rates from {path}[/dim]")
                        return
                except Exception as e:
                    console.print(f"  [yellow]Could not load historical priors from {path}: {e}[/yellow]")

        # No file found — use hardcoded defaults (already set as class var)

    def calculate(self, team_a: dict, team_b: dict, context: dict = None) -> dict:
        """
        Calculate chaos scores for a matchup.

        For the favorite: chaos score represents vulnerability
        For the underdog: chaos score represents upset potential

        The prediction engine uses this to create realistic upset probabilities.
        """
        context = context or {}
        round_name = context.get("round", "Round of 64")

        # Determine who's favored
        seed_a = self._get_seed(team_a)
        seed_b = self._get_seed(team_b)

        if seed_a <= seed_b:
            favorite, underdog = team_a, team_b
            fav_seed, dog_seed = seed_a, seed_b
            fav_label, dog_label = "team_a", "team_b"
        else:
            favorite, underdog = team_b, team_a
            fav_seed, dog_seed = seed_b, seed_a
            fav_label, dog_label = "team_b", "team_a"

        # Base upset probability from historical data
        matchup_key = (min(fav_seed, dog_seed), max(fav_seed, dog_seed))
        base_upset_prob = self.HISTORICAL_UPSETS.get(matchup_key, 0.20)

        # Round adjustment
        round_mult = self.ROUND_CHAOS_MULTIPLIER.get(round_name, 0.80)

        # Calculate chaos components
        fav_vulnerability = self._calc_vulnerability(favorite, context)
        dog_upset_potential = self._calc_upset_potential(underdog, context)

        # Cinderella factor
        cinderella = self._calc_cinderella_factor(underdog)

        # Performance variance (boom-or-bust teams are more chaotic)
        fav_variance = self._calc_variance(favorite)
        dog_variance = self._calc_variance(underdog)

        # Clutch factor (free throw %, late-game execution)
        fav_clutch = self._calc_clutch(favorite)
        dog_clutch = self._calc_clutch(underdog)

        # Foul dependency (teams that foul a lot or rely on FTs are ref-dependent)
        ref_factor = self._calc_ref_dependency(favorite, underdog)

        # ===== COMPOSITE UPSET PROBABILITY =====
        # Start with historical base, then adjust
        adjusted_upset_prob = base_upset_prob

        # Underdog bonuses
        adjusted_upset_prob += cinderella * 0.05       # Cinderella adds up to 5%
        adjusted_upset_prob += dog_upset_potential * 0.08  # Upset potential adds up to 8%
        adjusted_upset_prob += dog_variance * 0.03     # High-variance dogs are dangerous

        # Favorite penalties
        adjusted_upset_prob += fav_vulnerability * 0.06  # Vulnerable favorites
        adjusted_upset_prob -= fav_clutch * 0.04         # Clutch favorites survive

        # Round decay
        adjusted_upset_prob *= round_mult

        # Clamp
        adjusted_upset_prob = max(0.01, min(0.65, adjusted_upset_prob))

        # Convert to 0-100 scores
        # For the UNDERDOG: chaos score = upset probability normalized
        dog_chaos = adjusted_upset_prob * 100

        # For the FAVORITE: chaos score = inverse (how safe they are)
        fav_chaos = (1 - adjusted_upset_prob) * 100

        return {
            fav_label: {
                "chaos_score": round(fav_chaos, 2),
                "is_favorite": True,
                "seed": fav_seed,
                "vulnerability": round(fav_vulnerability, 3),
                "clutch": round(fav_clutch, 3),
                "variance": round(fav_variance, 3),
            },
            dog_label: {
                "chaos_score": round(dog_chaos, 2),
                "is_favorite": False,
                "seed": dog_seed,
                "upset_potential": round(dog_upset_potential, 3),
                "cinderella_factor": round(cinderella, 3),
                "variance": round(dog_variance, 3),
            },
            "upset_probability": round(adjusted_upset_prob, 4),
            "base_historical_upset_rate": base_upset_prob,
            "round_chaos_multiplier": round_mult,
            "ref_dependency_factor": round(ref_factor, 3),
            "seed_matchup": f"{fav_seed} vs {dog_seed}",
        }

    def _get_seed(self, team: dict) -> int:
        """Get tournament seed, default to 8 (middle)."""
        seed = team.get("seed", team.get("tournament_seed", team.get("ncaa_seed", 8)))
        try:
            s = int(float(seed))
            return max(1, min(16, s))
        except (ValueError, TypeError):
            return 8

    def _calc_vulnerability(self, team: dict, ctx: dict) -> float:
        """
        How vulnerable is the favorite to an upset? (0-1)

        Vulnerable teams: inconsistent, foul-prone, free-throw dependent,
        play slow (gives underdog fewer possessions to fall behind),
        lack tournament experience.
        """
        factors = []

        # Tempo: slower teams give underdogs a better chance
        # (fewer possessions = smaller sample = more variance)
        tempo = team.get("adj_t", team.get("tempo", team.get("pace", None)))
        if tempo:
            try:
                t = float(tempo)
                # Slower tempo (< 65) = more vulnerable
                tempo_vuln = max(0, 1 - ((t - 60) / 15))
                factors.append(tempo_vuln)
            except (ValueError, TypeError):
                pass

        # Three-point dependency: 3pt shooting is high-variance
        three_rate = team.get("three_rate", team.get("3pa_rate", team.get("fg3_rate", None)))
        if three_rate:
            try:
                tr = float(three_rate)
                if tr > 0.40:  # Very 3pt dependent
                    factors.append(0.7)
                elif tr > 0.35:
                    factors.append(0.5)
                else:
                    factors.append(0.3)
            except (ValueError, TypeError):
                pass

        # Free throw shooting: bad FT teams choke in crunch time
        ft_pct = team.get("ft_pct", team.get("ftp", team.get("free_throw_pct", None)))
        if ft_pct:
            try:
                ft = float(ft_pct)
                if ft < 1:
                    ft *= 100
                if ft < 68:
                    factors.append(0.8)  # Very vulnerable
                elif ft < 72:
                    factors.append(0.5)
                else:
                    factors.append(0.2)
            except (ValueError, TypeError):
                pass

        return np.mean(factors) if factors else 0.4

    def _calc_upset_potential(self, team: dict, ctx: dict) -> float:
        """
        How dangerous is this underdog? (0-1)

        Dangerous underdogs: great defense, low turnover rate,
        experienced roster, good 3pt shooting (can get hot),
        play fast (create chaos).
        """
        factors = []

        # Defensive efficiency (great defense travels)
        adj_d = team.get("adj_d", team.get("adjde", None))
        if adj_d:
            try:
                d = float(adj_d)
                # Lower adj_d = better defense. Sub-100 is good.
                if d < 95:
                    factors.append(0.9)  # Elite defense
                elif d < 100:
                    factors.append(0.7)
                elif d < 105:
                    factors.append(0.5)
                else:
                    factors.append(0.3)
            except (ValueError, TypeError):
                pass

        # Low turnover rate (take care of the ball under pressure)
        to_rate = team.get("tov_o", team.get("to_rate", None))
        if to_rate:
            try:
                to = float(to_rate)
                if to < 15:
                    factors.append(0.8)  # Very careful with the ball
                elif to < 18:
                    factors.append(0.5)
                else:
                    factors.append(0.3)
            except (ValueError, TypeError):
                pass

        # 3pt shooting (can get scorching hot in one game)
        three_pct = team.get("fg3_pct", team.get("3pt_pct", None))
        if three_pct:
            try:
                tp = float(three_pct)
                if tp < 1:
                    tp *= 100
                if tp > 37:
                    factors.append(0.8)  # Dangerous from deep
                elif tp > 34:
                    factors.append(0.5)
                else:
                    factors.append(0.3)
            except (ValueError, TypeError):
                pass

        return np.mean(factors) if factors else 0.4

    def _calc_cinderella_factor(self, team: dict) -> float:
        """
        Cinderella potential for mid-major underdogs. (0-1)

        Mid-majors that win their conference tournament play with
        house-money energy. They've already exceeded expectations.
        Combined with the crowd rooting for the underdog, this
        creates real performance boosts.
        """
        conf = str(team.get("conf", team.get("conference", ""))).strip()

        is_mid_major = conf in self.CINDERELLA_CONFERENCES
        seed = self._get_seed(team)

        if is_mid_major and seed >= 10:
            return 0.85  # Peak Cinderella potential
        elif is_mid_major and seed >= 7:
            return 0.60
        elif is_mid_major:
            return 0.40
        elif seed >= 12:
            return 0.50  # Even power conf 12+ seeds get underdog energy
        else:
            return 0.15

    def _calc_variance(self, team: dict) -> float:
        """
        How inconsistent/volatile is this team? (0-1)

        High variance = unpredictable. Good for underdogs (they
        might have their best game), bad for favorites (they might
        have their worst).
        """
        # Use win margin variance if available
        margin_var = team.get("margin_variance", team.get("scoring_variance", None))
        if margin_var:
            try:
                v = float(margin_var)
                return min(1.0, v / 20)  # 20+ point variance is very volatile
            except (ValueError, TypeError):
                pass

        # Heuristic: teams with lots of close games are more volatile
        close_games = team.get("close_games", team.get("games_within_5", None))
        if close_games:
            try:
                cg = float(close_games)
                total = float(team.get("total_games", 30))
                return min(1.0, cg / total)
            except (ValueError, TypeError):
                pass

        return 0.45  # Moderate variance default

    def _calc_clutch(self, team: dict) -> float:
        """
        Clutch performance ability. (0-1)

        Teams that win close games, shoot FTs well, and have
        experienced guards tend to perform better in pressure moments.
        """
        factors = []

        # Free throw percentage (most clutch-relevant stat)
        ft_pct = team.get("ft_pct", team.get("ftp", None))
        if ft_pct:
            try:
                ft = float(ft_pct)
                if ft < 1:
                    ft *= 100
                factors.append(min(1.0, (ft - 60) / 20))  # 80% = max clutch
            except (ValueError, TypeError):
                pass

        # Win percentage in close games
        close_wins = team.get("close_game_win_pct", None)
        if close_wins:
            try:
                factors.append(float(close_wins))
            except (ValueError, TypeError):
                pass

        # Experience (seniors/juniors are more clutch)
        exp = team.get("avg_experience", team.get("roster_experience", None))
        if exp:
            try:
                factors.append(min(1.0, float(exp) / 3))  # 3+ years avg = clutch
            except (ValueError, TypeError):
                pass

        return np.mean(factors) if factors else 0.5

    def _calc_ref_dependency(self, team_a: dict, team_b: dict) -> float:
        """
        How much might referee tendencies affect this game? (0-1)

        Games between a foul-heavy team and a disciplined team
        are more referee-dependent. This adds uncertainty.
        """
        foul_a = team_a.get("fouls_per_game", team_a.get("pf", None))
        foul_b = team_b.get("fouls_per_game", team_b.get("pf", None))

        if foul_a and foul_b:
            try:
                diff = abs(float(foul_a) - float(foul_b))
                return min(1.0, diff / 10)  # Big foul differential = ref dependent
            except (ValueError, TypeError):
                pass

        return 0.3  # Moderate by default
