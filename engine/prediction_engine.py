"""
Prediction Engine

THE BRAIN. This is the central nervous system that takes the three
scoring pillars (Hard, Soft, Chaos) and synthesizes them into a
single composite prediction for any matchup.

The output is:
- Win probability for each team
- Predicted score margin
- Confidence level
- Detailed breakdown of WHY
- Narrative summary for MiroFish seed docs
"""

import numpy as np
from rich.console import Console
from .hard_score import HardScoreCalculator
from .soft_score import SoftScoreCalculator
from .chaos_score import ChaosScoreCalculator

console = Console()


class PredictionEngine:
    """
    The composite prediction brain.

    Takes unified team data + matchup context and produces
    a prediction with win probabilities, score projections,
    and a narrative explanation.

    Formula:
        raw_prediction = (hard_weight * hard_score) + (soft_weight * soft_score)
        chaos_adjusted = raw_prediction adjusted by chaos/upset probability
        final = chaos_adjusted with confidence interval
    """

    def __init__(self, config: dict = None):
        self.config = config or {}

        # Pillar weights (configurable)
        pred_cfg = self.config.get("prediction", {})
        self.hard_weight = pred_cfg.get("hard_score_weight", 0.55)
        self.soft_weight = pred_cfg.get("soft_score_weight", 0.25)
        self.chaos_weight = pred_cfg.get("chaos_score_weight", 0.20)

        # Initialize calculators
        self.hard_calc = HardScoreCalculator(config)
        self.soft_calc = SoftScoreCalculator(config)
        self.chaos_calc = ChaosScoreCalculator(config)

    def predict_matchup(self, team_a: dict, team_b: dict, context: dict = None) -> dict:
        """
        Generate a full prediction for a single matchup.

        Args:
            team_a: unified data dict for team A (higher seed by convention)
            team_b: unified data dict for team B
            context: dict with round, venue_city, venue_state, neutral_site, etc.

        Returns:
            Comprehensive prediction dict with scores, probabilities, narrative
        """
        context = context or {}
        round_name = context.get("round", "Round of 64")

        team_a_name = self._get_team_name(team_a)
        team_b_name = self._get_team_name(team_b)

        console.print(f"\n[bold cyan]{'='*60}[/bold cyan]")
        console.print(f"[bold cyan]  PREDICTING: {team_a_name} vs {team_b_name}[/bold cyan]")
        console.print(f"[bold cyan]  Round: {round_name}[/bold cyan]")
        console.print(f"[bold cyan]{'='*60}[/bold cyan]")

        # ===== CALCULATE ALL THREE PILLARS =====

        console.print("\n[yellow]Calculating Hard Score (analytics)...[/yellow]")
        hard_result = self.hard_calc.calculate(team_a, team_b, context)

        console.print("[yellow]Calculating Soft Score (human factors)...[/yellow]")
        soft_result = self.soft_calc.calculate(team_a, team_b, context)

        console.print("[yellow]Calculating Chaos Score (unpredictability)...[/yellow]")
        chaos_result = self.chaos_calc.calculate(team_a, team_b, context)

        # ===== COMPOSITE SCORE =====

        # Hard and Soft scores are 0-100 where higher = better for that team
        hard_a = hard_result["team_a"]["hard_score"]
        hard_b = hard_result["team_b"]["hard_score"]
        soft_a = soft_result["team_a"]["soft_score"]
        soft_b = soft_result["team_b"]["soft_score"]

        # Raw composite (before chaos adjustment)
        raw_a = (self.hard_weight * hard_a) + (self.soft_weight * soft_a)
        raw_b = (self.hard_weight * hard_b) + (self.soft_weight * soft_b)

        # Normalize raw scores to win probability
        raw_total = raw_a + raw_b
        if raw_total > 0:
            raw_win_prob_a = raw_a / raw_total
            raw_win_prob_b = raw_b / raw_total
        else:
            raw_win_prob_a = raw_win_prob_b = 0.50

        # ===== CHAOS ADJUSTMENT =====
        # The chaos score tells us how much to distrust the raw prediction
        upset_prob = chaos_result.get("upset_probability", 0.20)

        # Determine favorite
        if raw_win_prob_a >= raw_win_prob_b:
            # Team A is favored by the math
            # Chaos pulls the prediction toward 50/50
            chaos_pull = upset_prob * self.chaos_weight
            final_win_prob_a = raw_win_prob_a - (chaos_pull * (raw_win_prob_a - 0.50))
            final_win_prob_b = 1 - final_win_prob_a
        else:
            chaos_pull = upset_prob * self.chaos_weight
            final_win_prob_b = raw_win_prob_b - (chaos_pull * (raw_win_prob_b - 0.50))
            final_win_prob_a = 1 - final_win_prob_b

        # Clamp probabilities
        final_win_prob_a = max(0.02, min(0.98, final_win_prob_a))
        final_win_prob_b = 1 - final_win_prob_a

        # ===== PREDICTED SCORE =====
        predicted_margin = self._estimate_margin(
            final_win_prob_a, team_a, team_b
        )

        avg_total = self._estimate_total_score(team_a, team_b)
        if final_win_prob_a > final_win_prob_b:
            score_a = round((avg_total / 2) + (abs(predicted_margin) / 2))
            score_b = round((avg_total / 2) - (abs(predicted_margin) / 2))
        else:
            score_b = round((avg_total / 2) + (abs(predicted_margin) / 2))
            score_a = round((avg_total / 2) - (abs(predicted_margin) / 2))

        # ===== CONFIDENCE =====
        # How confident are we? Based on pillar agreement and margin
        confidence = self._calculate_confidence(
            hard_result, soft_result, chaos_result,
            final_win_prob_a, final_win_prob_b
        )

        # ===== PICK =====
        if final_win_prob_a > final_win_prob_b:
            pick = team_a_name
            pick_key = "team_a"
            pick_prob = final_win_prob_a
        else:
            pick = team_b_name
            pick_key = "team_b"
            pick_prob = final_win_prob_b

        # ===== NARRATIVE =====
        narrative = self._generate_narrative(
            team_a_name, team_b_name,
            hard_result, soft_result, chaos_result,
            final_win_prob_a, final_win_prob_b,
            predicted_margin, confidence, context
        )

        # ===== OUTPUT =====
        result = {
            "matchup": f"{team_a_name} vs {team_b_name}",
            "round": round_name,
            "pick": pick,
            "pick_key": pick_key,
            "win_probability": {
                "team_a": round(final_win_prob_a, 4),
                "team_b": round(final_win_prob_b, 4),
            },
            "predicted_score": {
                "team_a": score_a,
                "team_b": score_b,
            },
            "predicted_margin": round(predicted_margin, 1),
            "confidence": round(confidence, 2),
            "pillar_scores": {
                "hard": {"team_a": hard_a, "team_b": hard_b},
                "soft": {"team_a": soft_a, "team_b": soft_b},
                "chaos": {
                    "upset_probability": upset_prob,
                    "team_a": chaos_result.get("team_a", {}),
                    "team_b": chaos_result.get("team_b", {}),
                },
            },
            "raw_win_probability": {
                "team_a": round(raw_win_prob_a, 4),
                "team_b": round(raw_win_prob_b, 4),
            },
            "narrative": narrative,
            "detailed_breakdown": {
                "hard": hard_result,
                "soft": soft_result,
                "chaos": chaos_result,
            },
        }

        # Print summary
        self._print_summary(result, team_a_name, team_b_name)

        return result

    def _get_team_name(self, team: dict) -> str:
        """Extract team name from data dict."""
        for key in ["team", "Team", "team_name", "school", "School", "name"]:
            if key in team and team[key]:
                return str(team[key])
        return "Unknown"

    def _estimate_margin(self, win_prob: float, team_a: dict, team_b: dict) -> float:
        """
        Convert win probability to a predicted point margin.

        Uses the log5 method combined with efficiency data.
        A 60% win prob roughly equals a 3-4 point margin in CBB.
        """
        # Log-odds conversion
        if win_prob <= 0.01 or win_prob >= 0.99:
            return (win_prob - 0.5) * 40

        log_odds = np.log(win_prob / (1 - win_prob))
        # In college basketball, ~0.12 log-odds per point of margin
        margin = log_odds / 0.12

        # Adjust for tempo (faster games have bigger margins)
        tempo_a = team_a.get("adj_t", team_a.get("tempo", 68))
        tempo_b = team_b.get("adj_t", team_b.get("tempo", 68))
        try:
            avg_tempo = (float(tempo_a) + float(tempo_b)) / 2
            tempo_factor = avg_tempo / 68  # 68 is D1 average
            margin *= tempo_factor
        except (ValueError, TypeError):
            pass

        return round(margin, 1)

    def _estimate_total_score(self, team_a: dict, team_b: dict) -> float:
        """Estimate combined total score for the game."""
        adj_o_a = team_a.get("adj_o", 105)
        adj_o_b = team_b.get("adj_o", 105)
        adj_d_a = team_a.get("adj_d", 100)
        adj_d_b = team_b.get("adj_d", 100)

        try:
            # Expected points = (team_offense + opp_defense) / 2, pace adjusted
            expected_a = (float(adj_o_a) + float(adj_d_b)) / 2
            expected_b = (float(adj_o_b) + float(adj_d_a)) / 2

            # Scale from per-100 possessions to actual game (~70 possessions)
            total = (expected_a + expected_b) * 0.70
            return max(100, min(180, total))  # Reasonable range
        except (ValueError, TypeError):
            return 140  # D1 average

    def _calculate_confidence(self, hard, soft, chaos, prob_a, prob_b) -> float:
        """
        How confident are we in this prediction? (0-1)

        High confidence when:
        - All three pillars agree
        - Large margin between teams
        - Low chaos/upset probability

        Low confidence when:
        - Pillars disagree
        - Close matchup
        - High chaos environment
        """
        factors = []

        # 1. Pillar agreement
        hard_edge = hard["edge"]
        soft_edge = soft["edge"]
        if hard_edge == soft_edge:
            factors.append(0.8)  # Pillars agree
        else:
            factors.append(0.3)  # Pillars disagree (uncertain)

        # 2. Margin size
        margin = abs(prob_a - prob_b)
        factors.append(min(1.0, margin * 2))  # 50% gap = max confidence

        # 3. Chaos factor (inverted: more chaos = less confidence)
        upset_prob = chaos.get("upset_probability", 0.20)
        factors.append(1 - upset_prob)

        # 4. Hard score margin (bigger analytics gap = more confidence)
        hard_margin = hard.get("edge_margin", 0)
        factors.append(min(1.0, hard_margin / 30))

        return np.mean(factors)

    def _generate_narrative(self, name_a, name_b, hard, soft, chaos,
                           prob_a, prob_b, margin, confidence, ctx):
        """
        Generate a human-readable narrative explaining the prediction.
        This narrative also serves as seed material for MiroFish.
        """
        round_name = ctx.get("round", "Tournament Game")
        pick = name_a if prob_a > prob_b else name_b
        loser = name_b if prob_a > prob_b else name_a
        prob = max(prob_a, prob_b)
        upset_prob = chaos.get("upset_probability", 0.20)

        lines = []
        lines.append(f"MATCHUP ANALYSIS: {name_a} vs {name_b} ({round_name})")
        lines.append(f"{'='*60}")
        lines.append("")

        # The pick
        lines.append(f"PREDICTION: {pick} wins ({prob*100:.1f}% probability)")
        lines.append(f"Predicted margin: {abs(margin):.1f} points")
        lines.append(f"Confidence: {confidence*100:.0f}%")
        lines.append("")

        # Hard score explanation
        hard_edge = hard["edge"].replace("team_a", name_a).replace("team_b", name_b)
        hard_margin = hard["edge_margin"]
        lines.append(f"ANALYTICS (Hard Score): {hard_edge} has the statistical edge (+{hard_margin:.1f})")
        lines.append(f"  {name_a}: {hard['team_a']['hard_score']:.1f}/100")
        lines.append(f"  {name_b}: {hard['team_b']['hard_score']:.1f}/100")
        lines.append("")

        # Soft score explanation
        soft_edge = soft["edge"].replace("team_a", name_a).replace("team_b", name_b)
        soft_margin = soft["edge_margin"]
        lines.append(f"HUMAN FACTORS (Soft Score): {soft_edge} has the intangible edge (+{soft_margin:.1f})")
        lines.append(f"  {name_a}: {soft['team_a']['soft_score']:.1f}/100")
        lines.append(f"  {name_b}: {soft['team_b']['soft_score']:.1f}/100")
        lines.append("")

        # Chaos analysis
        lines.append(f"CHAOS FACTOR: {upset_prob*100:.1f}% upset probability")
        seed_matchup = chaos.get("seed_matchup", "? vs ?")
        lines.append(f"  Seed matchup: {seed_matchup}")
        lines.append(f"  Historical base upset rate: {chaos.get('base_historical_upset_rate', 0)*100:.1f}%")
        lines.append("")

        # Key factors
        lines.append("KEY FACTORS TO WATCH:")

        # Identify the biggest advantage for each team
        hard_a = hard["team_a"]["hard_score"]
        hard_b = hard["team_b"]["hard_score"]
        if abs(hard_a - hard_b) > 10:
            better = name_a if hard_a > hard_b else name_b
            lines.append(f"  - {better} has a significant statistical advantage")

        if soft["edge_margin"] > 8:
            soft_winner = soft["edge"].replace("team_a", name_a).replace("team_b", name_b)
            lines.append(f"  - {soft_winner} holds notable intangible advantages")

        if upset_prob > 0.35:
            lines.append(f"  - HIGH upset alert. This game has significant chaos potential.")
        elif upset_prob > 0.25:
            lines.append(f"  - Moderate upset risk. Don't sleep on the underdog.")

        lines.append("")
        lines.append(f"MIROFISH SIMULATION RECOMMENDED: {'YES' if upset_prob > 0.25 else 'Optional'}")
        lines.append(f"  Close matchups benefit most from agent-based simulation")
        lines.append(f"  to capture emergent dynamics that pure math misses.")

        return "\n".join(lines)

    def _print_summary(self, result, name_a, name_b):
        """Print a clean summary to console."""
        console.print(f"\n[bold green]  PICK: {result['pick']}[/bold green]")
        console.print(f"  Win Prob: {result['win_probability']['team_a']*100:.1f}% - {result['win_probability']['team_b']*100:.1f}%")
        console.print(f"  Score: {name_a} {result['predicted_score']['team_a']} - {name_b} {result['predicted_score']['team_b']}")
        console.print(f"  Confidence: {result['confidence']*100:.0f}%")
        console.print(f"  Upset Prob: {result['pillar_scores']['chaos']['upset_probability']*100:.1f}%")
        console.print(f"  Hard: {result['pillar_scores']['hard']['team_a']:.1f} vs {result['pillar_scores']['hard']['team_b']:.1f}")
        console.print(f"  Soft: {result['pillar_scores']['soft']['team_a']:.1f} vs {result['pillar_scores']['soft']['team_b']:.1f}")
