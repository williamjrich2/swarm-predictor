class Console:
    def print(self, *a, **kw): pass

"""
Momentum Engine

Scores team momentum entering a tournament game.

This is what Jake described: Auburn 2019. A team on a hot streak
carries emotional energy that raw efficiency metrics miss.

College basketball is a lot less about numbers and often times
more about energy, intensity, passion, and momentum.
That's why they call it the madness.
"""

import numpy as np

console = Console()

MADNESS_PRINCIPLE = """
March Madness outcomes are fundamentally driven by human factors:
- A team on a hot streak plays with a different energy
- Conference tournament champions have nothing to prove and everything to gain
- Underdogs play free; favorites play with the weight of expectation
- Injuries, locker room dynamics, and travel fatigue create invisible advantages
- The math tells us the floor. The human element determines the ceiling.
Historical analysis of 25 years confirms: teams that are "getting hot"
at tournament time outperform their seed at significantly higher rates.
"""


class MomentumEngine:
    """
    Scores team momentum entering a tournament game.

    Inputs:
    - Team data dict (standard swarm-predictor format)
    - Optional recent_games list: [{won: bool, margin: int, opp_quality: float}]
    - Optional conf_tourney_data dict: {wins: int, champ: bool, games_played: int}

    Output:
    - momentum_score: float (0-1)
    - momentum_label: str (e.g. "Red Hot", "Warm", "Neutral", "Cold")
    - momentum_narrative: str (human-readable description)
    - component_scores: dict (breakdown of each factor)
    """

    # Momentum labels by score range
    LABELS = [
        (0.85, "🔥 RED HOT"),
        (0.70, "♨️  Getting Hot"),
        (0.55, "✅  Warm"),
        (0.45, "🌡  Neutral"),
        (0.30, "❄️  Cold"),
        (0.00, "🧊 Ice Cold"),
    ]

    def __init__(self, config: dict = None):
        self.config = config or {}
        # Momentum weight in soft score (increased from 0.15 to 0.20 per Jake)
        self.momentum_weight = self.config.get("momentum_weight", 0.20)

    def calculate_momentum(self, team_data: dict, recent_games: list = None,
                           conf_tourney_data: dict = None) -> dict:
        """
        Full momentum calculation for a team.

        Args:
            team_data: Standard team dict with adj_o, adj_d, barthag, etc.
            recent_games: List of recent game results, most recent first.
                          Each: {won: bool, margin: int, opp_quality: float (0-1)}
            conf_tourney_data: {wins: int, champ: bool, games_played: int}

        Returns:
            {momentum_score, momentum_label, momentum_narrative, component_scores}
        """
        components = {}

        # 1. Win/loss streak momentum (most important)
        streak_result = self._calc_streak_momentum(team_data, recent_games)
        components["streak"] = streak_result

        # 2. Conference tournament energy
        conf_result = self.assess_conf_tourney_energy(team_data, conf_tourney_data)
        components["conf_tourney"] = conf_result

        # 3. Recent scoring trajectory (are they improving?)
        trajectory = self._calc_scoring_trajectory(team_data, recent_games)
        components["trajectory"] = trajectory

        # 4. Season-long WAB momentum (how much have they won vs expectations)
        wab_momentum = self._calc_wab_momentum(team_data)
        components["wab"] = wab_momentum

        # 5. Fatigue factor
        fatigue = self._calc_fatigue(team_data, conf_tourney_data)
        components["fatigue"] = fatigue

        # 6. "Nothing to lose" factor for underdogs
        underdog_energy = self._calc_underdog_energy(team_data)
        components["underdog_energy"] = underdog_energy

        # Composite score (weighted)
        weights = {
            "streak": 0.30,
            "conf_tourney": 0.20,
            "trajectory": 0.15,
            "wab": 0.15,
            "fatigue": 0.10,      # negative factor
            "underdog_energy": 0.10,
        }

        raw_score = (
            weights["streak"] * components["streak"]["score"] +
            weights["conf_tourney"] * components["conf_tourney"]["energy_level"] +
            weights["trajectory"] * components["trajectory"]["score"] +
            weights["wab"] * components["wab"]["score"] +
            weights["fatigue"] * (1 - components["fatigue"]["fatigue_level"]) +
            weights["underdog_energy"] * components["underdog_energy"]["score"]
        )

        momentum_score = max(0.0, min(1.0, raw_score))
        label = self._get_label(momentum_score)
        narrative = self._build_narrative(team_data, components, momentum_score, label)

        return {
            "momentum_score": round(momentum_score, 4),
            "momentum_label": label,
            "momentum_narrative": narrative,
            "component_scores": {k: v for k, v in components.items()},
        }

    def detect_hot_streak(self, recent_games: list) -> dict:
        """
        Analyze a recent games list to detect hot streak.

        Args:
            recent_games: List of dicts, most recent first.
                Each: {won: bool, margin: int, opp_quality: float}

        Returns:
            {hot: bool, streak_length: int, avg_margin: float, quality_wins: int}
        """
        if not recent_games:
            return {"hot": False, "streak_length": 0, "avg_margin": 0, "quality_wins": 0}

        # Count current streak
        streak = 0
        for game in recent_games:
            if game.get("won", False):
                streak += 1
            else:
                break

        # Quality wins (opponent quality > 0.6)
        quality_wins = sum(
            1 for g in recent_games[:10]
            if g.get("won") and g.get("opp_quality", 0) > 0.6
        )

        # Average margin in last 5 games
        last5 = recent_games[:5]
        margins = [g.get("margin", 0) for g in last5]
        avg_margin = np.mean(margins) if margins else 0

        # Is this a HOT streak?
        hot = (
            streak >= 5 or
            (streak >= 3 and avg_margin > 10) or
            (streak >= 3 and quality_wins >= 2)
        )

        return {
            "hot": hot,
            "streak_length": streak,
            "avg_margin": round(float(avg_margin), 1),
            "quality_wins": quality_wins,
        }

    def assess_conf_tourney_energy(self, team_data: dict,
                                    conf_tourney_data: dict = None) -> dict:
        """
        Assess the energy effect of conference tournament performance.

        Conference tournament champions arrive in March Madness riding
        a 4-5 game win streak with crowd energy, momentum, and proven
        ability to win consecutive games under pressure.

        Returns:
            {conf_champ: bool, games_played: int, fatigue_level: float, energy_level: float}
        """
        if conf_tourney_data:
            wins = conf_tourney_data.get("wins", 0)
            champ = conf_tourney_data.get("champ", False)
            games = conf_tourney_data.get("games_played", 0)
        else:
            # Infer from team data
            wins = int(team_data.get("conf_tourney_wins", 0))
            champ = bool(team_data.get("conf_champ", False))
            games = wins + int(team_data.get("conf_tourney_losses", 0))

        # Energy from winning conf tourney
        if champ and wins >= 4:
            energy = 0.90  # Peak energy: won 4+ in conf tourney
        elif champ and wins >= 3:
            energy = 0.80
        elif champ:
            energy = 0.70
        elif wins >= 3:
            energy = 0.65  # Deep conf run, didn't win it
        elif wins >= 2:
            energy = 0.55
        elif wins >= 1:
            energy = 0.50
        else:
            energy = 0.40  # Auto-bid or lost early

        # Fatigue: too many games can wear a team down
        if games >= 5:
            fatigue = 0.50  # 5 games in a week is brutal
        elif games >= 4:
            fatigue = 0.30
        elif games >= 3:
            fatigue = 0.15
        else:
            fatigue = 0.05

        return {
            "conf_champ": champ,
            "games_played": games,
            "wins": wins,
            "fatigue_level": fatigue,
            "energy_level": round(energy, 3),
        }

    # ------------------------------------------------------------------
    # PRIVATE HELPERS
    # ------------------------------------------------------------------

    def _calc_streak_momentum(self, team_data: dict, recent_games: list) -> dict:
        """Calculate momentum from win/loss streak."""
        # Try to get streak from team data
        streak_str = str(team_data.get("streak", "W0"))
        sign = 1 if streak_str.startswith("W") else -1
        try:
            length = int(re.sub(r'[^0-9]', '', streak_str))
        except Exception:
            import re
            nums = re.findall(r'\d+', streak_str)
            length = int(nums[0]) if nums else 0

        if recent_games:
            hot_data = self.detect_hot_streak(recent_games)
            streak_len = hot_data["streak_length"]
            avg_margin = hot_data["avg_margin"]
        else:
            streak_len = length if sign > 0 else 0
            avg_margin = float(team_data.get("avg_margin", 5))

        # Momentum score from streak
        if sign < 0:
            # Losing streak is very bad
            score = max(0.05, 0.4 - (length * 0.08))
        elif streak_len >= 10:
            score = 0.95
        elif streak_len >= 7:
            score = 0.85
        elif streak_len >= 5:
            score = 0.75
        elif streak_len >= 3:
            score = 0.65
        elif streak_len >= 1:
            score = 0.55
        else:
            score = 0.45

        # Margin bonus: winning decisively feels different than squeaking by
        if avg_margin > 15:
            score = min(1.0, score + 0.10)
        elif avg_margin > 10:
            score = min(1.0, score + 0.05)
        elif avg_margin < 3 and sign > 0:
            score = max(0.1, score - 0.05)  # Winning ugly reduces momentum

        return {
            "score": round(score, 3),
            "streak_length": streak_len,
            "streak_sign": "W" if sign > 0 else "L",
            "avg_margin": round(avg_margin, 1),
        }

    def _calc_scoring_trajectory(self, team_data: dict, recent_games: list) -> dict:
        """Are they scoring MORE than their season average recently? That's a trend."""
        # Without game-by-game data, use WAB as a proxy for performance trajectory
        wab = float(team_data.get("wab", team_data.get("WAB", 0)) or 0)
        adj_o = float(team_data.get("adj_o", 105) or 105)
        adj_d = float(team_data.get("adj_d", 100) or 100)

        # Efficiency margin
        em = adj_o - adj_d

        if recent_games:
            # Calculate recent margin trend
            margins = [g.get("margin", 0) for g in recent_games[:5]]
            recent_avg = np.mean(margins) if margins else 0
            # Is recent better than season average?
            season_avg = float(team_data.get("avg_margin", 5))
            trend = recent_avg - season_avg
            score = 0.5 + min(0.4, max(-0.4, trend / 20))
        else:
            # Use efficiency margin as proxy
            if em > 25:
                score = 0.90
            elif em > 20:
                score = 0.80
            elif em > 15:
                score = 0.70
            elif em > 10:
                score = 0.60
            elif em > 5:
                score = 0.55
            elif em > 0:
                score = 0.50
            else:
                score = 0.40

        return {"score": round(score, 3), "efficiency_margin": round(em, 1)}

    def _calc_wab_momentum(self, team_data: dict) -> dict:
        """Wins Above Bubble is a strong signal of consistent quality."""
        wab = float(team_data.get("wab", team_data.get("WAB", 0)) or 0)

        if wab > 10:
            score = 0.90
        elif wab > 7:
            score = 0.80
        elif wab > 5:
            score = 0.70
        elif wab > 3:
            score = 0.60
        elif wab > 1:
            score = 0.55
        elif wab > 0:
            score = 0.50
        else:
            score = 0.35  # Below-bubble team entering tournament

        return {"score": round(score, 3), "wab": round(wab, 2)}

    def _calc_fatigue(self, team_data: dict, conf_tourney_data: dict = None) -> dict:
        """Fatigue from conference tournament games or heavy schedule."""
        games_recent = int(team_data.get("games_last_14_days", 3))

        if conf_tourney_data:
            games_recent = max(games_recent, conf_tourney_data.get("games_played", 0))

        if games_recent >= 5:
            fatigue = 0.60
        elif games_recent >= 4:
            fatigue = 0.40
        elif games_recent >= 3:
            fatigue = 0.20
        else:
            fatigue = 0.05

        return {
            "fatigue_level": round(fatigue, 3),
            "games_recent": games_recent,
            "rested": fatigue < 0.15,
        }

    def _calc_underdog_energy(self, team_data: dict) -> dict:
        """
        The 'nothing to lose' factor. Underdogs play free.
        Seeds 10-16 from mid-major conferences get a big boost.
        """
        seed = int(team_data.get("seed", 8))
        conf = str(team_data.get("conf", ""))

        from engine.chaos_score import ChaosScoreCalculator
        is_mid_major = conf in ChaosScoreCalculator.CINDERELLA_CONFERENCES

        if seed >= 13:
            base = 0.80  # 13-16 seeds have zero pressure
        elif seed >= 10:
            base = 0.70
        elif seed >= 7:
            base = 0.55
        elif seed >= 4:
            base = 0.45
        else:
            base = 0.35  # Top seeds carry the weight of expectation

        if is_mid_major and seed >= 10:
            base = min(1.0, base + 0.10)

        return {
            "score": round(base, 3),
            "seed": seed,
            "is_underdog": seed >= 7,
            "is_mid_major": is_mid_major,
        }

    def _get_label(self, score: float) -> str:
        """Get momentum label from score."""
        for threshold, label in self.LABELS:
            if score >= threshold:
                return label
        return "🧊 Ice Cold"

    def _build_narrative(self, team_data: dict, components: dict,
                         score: float, label: str) -> str:
        """Build a human-readable momentum narrative."""
        team_name = team_data.get("team", "This team")
        streak = components["streak"]
        conf = components["conf_tourney"]
        fatigue = components["fatigue"]

        lines = [f"{team_name} — Momentum: {label} ({score*100:.0f}/100)"]

        if streak["streak_sign"] == "W" and streak["streak_length"] >= 5:
            lines.append(f"  🔥 On a {streak['streak_length']}-game win streak, "
                        f"winning by {streak['avg_margin']:.0f} pts avg")
        elif streak["streak_sign"] == "L":
            lines.append(f"  ⚠️  Lost last {streak['streak_length']} games — "
                        f"confidence may be shaken")
        else:
            lines.append(f"  📊 {streak['streak_sign']}{streak['streak_length']} streak entering tournament")

        if conf["conf_champ"]:
            lines.append(f"  🏆 Conference champion — rode {conf['wins']} wins in conf tourney")
        elif conf["wins"] >= 2:
            lines.append(f"  ✅ Went {conf['wins']}-1 in conference tournament")

        if fatigue["fatigue_level"] > 0.35:
            lines.append(f"  😤 Potential fatigue: {fatigue['games_recent']} games in last 2 weeks")

        if components["underdog_energy"]["is_underdog"]:
            lines.append(f"  🎯 Underdog energy: playing with house money, nothing to lose")

        wab = components["wab"]["wab"]
        if wab > 5:
            lines.append(f"  📈 {wab:.1f} wins above bubble — consistently beating expectations")

        return "\n".join(lines)


# Import re at module level
import re
