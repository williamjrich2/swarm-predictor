class Console:
    def print(self, *a, **kw): pass

"""
Soft Score Calculator

The human element pillar. This is what separates us from a spreadsheet.

We're scoring things that can't be perfectly measured but absolutely
affect outcomes. Every March Madness upset has roots in these factors.

Factors:
- Neutral court proximity (is it really "neutral" if the arena is 30 min from campus?)
- Fan base size and engagement (ticket sales, alumni density near venue)
- Coach tournament experience (been here before vs first dance)
- Roster continuity (returning core vs transfer portal rebuild)
- Momentum and emotional energy (hot streak, nothing to lose, adrenaline)
- Fatigue and travel (back-to-back games, cross-country flights)
- Physical matchup advantages (height, wingspan, athleticism mismatches)
- Team chemistry signals (low portal churn = cohesion)
"""

import numpy as np

try:
    from geopy.distance import geodesic
    _GEOPY_AVAILABLE = True
except ImportError:
    _GEOPY_AVAILABLE = False

try:
    from engine.momentum_engine import MomentumEngine
    _MOMENTUM_ENGINE_AVAILABLE = True
except ImportError:
    try:
        from .momentum_engine import MomentumEngine
        _MOMENTUM_ENGINE_AVAILABLE = True
    except ImportError:
        _MOMENTUM_ENGINE_AVAILABLE = False

console = Console()

# Major arena locations for tournament sites (lat, lng)
TOURNAMENT_VENUES = {
    # These get updated each year based on the bracket
    "default": (39.7392, -84.1791),  # Dayton, OH (First Four)
}

# Conference "home base" approximate locations
CONFERENCE_HQS = {
    "ACC": (35.7796, -78.6382),     # Raleigh, NC
    "Big 12": (39.0473, -95.6752),  # Lawrence, KS
    "Big Ten": (40.4237, -86.9212), # W. Lafayette, IN
    "SEC": (33.2098, -87.5692),     # Tuscaloosa, AL
    "Big East": (40.7128, -74.0060), # NYC
    "Pac-12": (37.8716, -122.2727), # Berkeley, CA
    "WCC": (37.7749, -122.4194),    # San Francisco
    "AAC": (29.7174, -95.4018),     # Houston
    "MWC": (39.7392, -104.9903),    # Denver
    "A-10": (38.9072, -77.0369),    # DC
    "MVC": (38.6270, -90.1994),     # St. Louis
    "CAA": (37.2707, -76.7075),     # Williamsburg
    "Ivy": (40.3573, -74.6672),     # Princeton
    "MAAC": (40.7128, -74.0060),    # NYC area
    "SoCon": (35.5951, -82.5515),   # Asheville
    "Horizon": (41.8781, -87.6298), # Chicago
    "WCC": (37.7749, -122.4194),
}


class SoftScoreCalculator:
    """
    Calculates the Soft Score (0-100) for human/emotional factors.

    This is where March Madness magic lives. The math says one thing,
    but a team playing 2 hours from campus with 80% of the arena
    wearing their colors is a different animal entirely.
    """

    # Momentum bumped to 0.20 per Jake's insight:
    # "College basketball is a lot less about numbers and often times more
    #  about energy, intensity, passion, and momentum."
    WEIGHTS = {
        "neutral_court_proximity": 0.12,
        "fan_base_energy": 0.08,
        "coach_experience": 0.13,
        "roster_continuity": 0.12,
        "momentum": 0.20,          # Increased from 0.15 — The Madness Principle
        "fatigue_travel": 0.10,
        "physical_matchup": 0.25,
    }

    def __init__(self, config: dict = None):
        self.config = config or {}
        # Override weights from config if provided
        if "soft_factors" in self.config:
            for key in self.WEIGHTS:
                cfg_key = f"{key}_weight"
                if cfg_key in self.config["soft_factors"]:
                    self.WEIGHTS[key] = self.config["soft_factors"][cfg_key]

        # Initialize MomentumEngine
        if _MOMENTUM_ENGINE_AVAILABLE:
            self.momentum_engine = MomentumEngine(config)
        else:
            self.momentum_engine = None

    def calculate(self, team_a: dict, team_b: dict, context: dict = None) -> dict:
        """
        Calculate soft scores for both teams.

        Context should include:
        - venue_city, venue_state (where the game is played)
        - round (which tournament round)
        - neutral_site (bool)
        """
        context = context or {}

        score_a = self._score_team(team_a, team_b, context, is_higher_seed=True)
        score_b = self._score_team(team_b, team_a, context, is_higher_seed=False)

        # Normalize relative to each other
        total = score_a["total"] + score_b["total"]
        if total > 0:
            norm_a = (score_a["total"] / total) * 100
            norm_b = (score_b["total"] / total) * 100
        else:
            norm_a = norm_b = 50.0

        return {
            "team_a": {
                "soft_score": round(norm_a, 2),
                "breakdown": score_a,
            },
            "team_b": {
                "soft_score": round(norm_b, 2),
                "breakdown": score_b,
            },
            "edge": "team_a" if norm_a > norm_b else "team_b",
            "edge_margin": round(abs(norm_a - norm_b), 2),
        }

    def _score_team(self, team: dict, opp: dict, ctx: dict, is_higher_seed: bool) -> dict:
        """Calculate soft score components for one team."""

        components = {}

        # ===== 1. NEUTRAL COURT PROXIMITY =====
        # "Neutral" courts aren't really neutral. A 1-seed playing in their
        # home state has a massive advantage even at a "neutral" site.
        components["neutral_court_proximity"] = self._calc_proximity_advantage(team, ctx)

        # ===== 2. FAN BASE ENERGY =====
        # Bigger programs bring more fans. Blue bloods pack arenas even on
        # the road. This creates real energy that affects free throws,
        # momentum swings, and referee psychology.
        components["fan_base_energy"] = self._calc_fan_energy(team, ctx)

        # ===== 3. COACH TOURNAMENT EXPERIENCE =====
        # A coach who's been to 10 Final Fours handles pressure differently
        # than a first-timer. Their team prep, timeout management, and
        # ability to calm players in hostile environments is measurable.
        components["coach_experience"] = self._calc_coach_experience(team)

        # ===== 4. ROSTER CONTINUITY =====
        # Teams that return their core are more cohesive. Transfer portal
        # teams can be talented but fragile under tournament pressure.
        # Chemistry built over years shows up in late-game execution.
        components["roster_continuity"] = self._calc_roster_continuity(team)

        # ===== 5. MOMENTUM / EMOTIONAL ENERGY =====
        # A team on a 12-game win streak plays different than one that
        # limped into the tournament. Conference tournament champions
        # carry emotional energy. "Nothing to lose" underdogs get
        # an adrenaline boost that's real and measurable in performance.
        components["momentum"] = self._calc_momentum(team, is_higher_seed)

        # ===== 6. FATIGUE & TRAVEL =====
        # Playing Thursday then Saturday is different from having 5 days rest.
        # Teams that played in their conference tournament championship
        # game may be running on fumes. Travel distance matters.
        components["fatigue_travel"] = self._calc_fatigue(team, ctx)

        # ===== 7. PHYSICAL MATCHUP =====
        # A team with 4 players over 6'8" against a team whose tallest
        # guy is 6'5" has a tangible advantage. Height, weight, wingspan
        # at each position creates matchup problems that stats don't
        # fully capture.
        components["physical_matchup"] = self._calc_physical_matchup(team, opp)

        # Weighted total
        total = sum(
            components.get(k, 0.5) * w
            for k, w in self.WEIGHTS.items()
        )
        components["total"] = total

        return components

    def _calc_proximity_advantage(self, team: dict, ctx: dict) -> float:
        """
        Score 0-1 based on how close the team is to the game venue.
        Closer = higher score (de facto home court).
        """
        # Without precise location data, use conference HQ as proxy
        conf = str(team.get("conf", team.get("conference", ""))).strip()
        venue_state = ctx.get("venue_state", "")

        # Simple heuristic: if the team's conference region matches the venue state
        # they get a proximity bonus
        team_state = str(team.get("state", team.get("venue_state", ""))).strip()

        if venue_state and team_state:
            if team_state.lower() == venue_state.lower():
                return 0.85  # Playing in home state
            # Check nearby states (simplified)
            return 0.50  # Default neutral

        # Use conference as proxy
        if conf in CONFERENCE_HQS:
            return 0.55  # Slight advantage for recognizable programs
        return 0.50

    def _calc_fan_energy(self, team: dict, ctx: dict) -> float:
        """
        Estimate fan base energy/support.
        Blue bloods and large state schools have massive followings.
        """
        # Use attendance data if available
        attendance = team.get("attendance", team.get("avg_attendance", 0))
        if attendance:
            try:
                att = float(attendance)
                # Normalize: 2000 (small) to 20000 (blue blood)
                return min(1.0, max(0.1, (att - 2000) / 18000))
            except (ValueError, TypeError):
                pass

        # Fall back to seed as proxy (higher seeds = bigger programs usually)
        seed = team.get("seed", team.get("tournament_seed", 8))
        try:
            seed = int(float(seed))
            # 1-seeds have huge followings, 16-seeds have passionate but small ones
            if seed <= 4:
                return 0.75
            elif seed <= 8:
                return 0.55
            elif seed <= 12:
                return 0.40
            else:
                return 0.35  # Small but scrappy fanbases
        except (ValueError, TypeError):
            return 0.50

    def _calc_coach_experience(self, team: dict) -> float:
        """
        Score based on coach's tournament/pressure experience.
        This would ideally pull from a coaching database.
        For now, use heuristics from available data.
        """
        # If we have coaching data
        tourney_apps = team.get("coach_tourney_appearances", team.get("ncaa_apps", 0))
        if tourney_apps:
            try:
                apps = int(float(tourney_apps))
                return min(1.0, apps / 15)  # 15+ appearances = max score
            except (ValueError, TypeError):
                pass

        # Heuristic: higher seeds tend to have more experienced coaches
        seed = team.get("seed", 8)
        try:
            seed = int(float(seed))
            if seed <= 3:
                return 0.75  # Likely experienced
            elif seed <= 8:
                return 0.55
            else:
                return 0.40  # Possible first-timers
        except (ValueError, TypeError):
            return 0.50

    def _calc_roster_continuity(self, team: dict) -> float:
        """
        Score based on how much of the roster returns from last year.
        High continuity = better chemistry under pressure.
        Transfer-heavy rosters can be volatile in March.
        """
        continuity = team.get("roster_continuity", team.get("returning_minutes_pct", None))
        if continuity:
            try:
                c = float(continuity)
                if c > 1:
                    c = c / 100  # Convert from percentage
                return c
            except (ValueError, TypeError):
                pass

        # Default to moderate
        return 0.55

    def _calc_momentum(self, team: dict, is_higher_seed: bool) -> float:
        """
        Score based on recent winning momentum and emotional state.
        Uses MomentumEngine when available for richer calculation.

        Key insight (The Madness Principle): underdogs get an adrenaline
        boost in the tournament. They play free, with nothing to lose.
        Favorites carry the weight of expectation. This is REAL and
        affects performance. College basketball is a lot less about
        numbers and often times more about energy, intensity, passion,
        and momentum. That's why they call it the madness.
        """
        if self.momentum_engine:
            result = self.momentum_engine.calculate_momentum(team)
            return result["momentum_score"]

        # Fallback if MomentumEngine not available
        streak = team.get("streak", team.get("win_streak", 0))
        streak_score = 0.5
        if streak:
            try:
                s = int(float(str(streak).replace("W", "").replace("L", "-")))
                if s > 0:
                    streak_score = min(1.0, 0.5 + (s * 0.05))
                else:
                    streak_score = max(0.1, 0.5 + (s * 0.05))
            except (ValueError, TypeError):
                pass

        underdog_bonus = 0
        if not is_higher_seed:
            seed = team.get("seed", 8)
            try:
                seed = int(float(seed))
                if seed >= 10:
                    underdog_bonus = 0.10
                elif seed >= 7:
                    underdog_bonus = 0.05
            except (ValueError, TypeError):
                pass

        conf_champ = team.get("conf_tourney_champ", team.get("auto_bid", False))
        champ_bonus = 0.08 if conf_champ else 0

        return min(1.0, streak_score + underdog_bonus + champ_bonus)

    def _calc_fatigue(self, team: dict, ctx: dict) -> float:
        """
        Score based on rest and travel factors.
        More rest = higher score. More travel = lower score.
        """
        # Days of rest
        days_rest = team.get("days_rest", team.get("days_since_last_game", 3))
        try:
            rest = int(float(days_rest))
            rest_score = min(1.0, rest / 5)  # 5+ days = fully rested
        except (ValueError, TypeError):
            rest_score = 0.6  # Assume moderate rest

        # Games in last 7 days (conference tourney fatigue)
        recent_games = team.get("games_last_7_days", 1)
        try:
            games = int(float(recent_games))
            if games >= 4:
                rest_score *= 0.7  # Heavy fatigue penalty
            elif games >= 3:
                rest_score *= 0.85
        except (ValueError, TypeError):
            pass

        return rest_score

    def _calc_physical_matchup(self, team: dict, opponent: dict) -> float:
        """
        Score based on physical advantages.

        Compares average height, weight, and athleticism.
        A team with size dominance inside has a real edge that doesn't
        always show up in efficiency metrics.
        """
        # Average height comparison
        team_height = team.get("avg_height_inches", team.get("avg_height", None))
        opp_height = opponent.get("avg_height_inches", opponent.get("avg_height", None))

        height_score = 0.5
        if team_height and opp_height:
            try:
                diff = float(team_height) - float(opp_height)
                # Each inch of average height advantage is significant
                height_score = 0.5 + (diff * 0.05)
                height_score = max(0.2, min(0.8, height_score))
            except (ValueError, TypeError):
                pass

        # Rebounding differential as proxy for physical dominance
        team_reb = team.get("orb_rate", team.get("orb_o", 0))
        opp_reb = opponent.get("orb_rate", opponent.get("orb_o", 0))

        reb_score = 0.5
        if team_reb and opp_reb:
            try:
                diff = float(team_reb) - float(opp_reb)
                reb_score = 0.5 + (diff * 2)
                reb_score = max(0.2, min(0.8, reb_score))
            except (ValueError, TypeError):
                pass

        # Block rate as athleticism proxy
        block_rate = team.get("blk_rate", team.get("block_pct", None))
        block_score = 0.5
        if block_rate:
            try:
                br = float(block_rate)
                block_score = min(0.8, br / 15)  # 15% block rate is elite
            except (ValueError, TypeError):
                pass

        return (height_score * 0.4) + (reb_score * 0.35) + (block_score * 0.25)
