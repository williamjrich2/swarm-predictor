"""
Bracket Predictor

Simulates the entire NCAA tournament bracket from Round of 64
through the Championship game.

Takes the 68-team field, runs predictions for every matchup,
advances winners, and produces a complete bracket prediction.

Can also run Monte Carlo simulations to produce probability
distributions for each team's tournament ceiling.
"""

import json
import random
import numpy as np
from pathlib import Path
class Console:
    def print(self, *a, **kw): pass
class Table:
    def __init__(self, *a, **kw): self.columns=[]
    def add_column(self, *a, **kw): pass
    def add_row(self, *a, **kw): pass
from .prediction_engine import PredictionEngine

console = Console()


# Standard tournament bracket structure
# Seeds paired in each region: 1v16, 8v9, 5v12, 4v13, 6v11, 3v14, 7v10, 2v15
FIRST_ROUND_MATCHUPS = [
    (1, 16), (8, 9), (5, 12), (4, 13),
    (6, 11), (3, 14), (7, 10), (2, 15),
]

ROUND_NAMES = [
    "Round of 64",
    "Round of 32",
    "Sweet 16",
    "Elite 8",
    "Final Four",
    "Championship",
]

REGIONS = ["South", "East", "West", "Midwest"]


class BracketPredictor:
    """
    Simulates the full NCAA tournament bracket.

    Can run single prediction or Monte Carlo simulation
    for probability distributions.
    """

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.engine = PredictionEngine(config)
        self.output_dir = Path("./output/brackets")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def predict_bracket(self, teams_by_region: dict, context: dict = None) -> dict:
        """
        Predict the entire tournament bracket.

        Args:
            teams_by_region: dict like {
                "South": {1: team_data, 2: team_data, ...},
                "East": {...},
                "West": {...},
                "Midwest": {...},
            }
            context: venue info, etc.

        Returns:
            Complete bracket with predictions for every game
        """
        context = context or {}
        bracket = {"regions": {}, "final_four": [], "championship": None}

        console.print("\n[bold magenta]{'='*60}[/bold magenta]")
        console.print("[bold magenta]  NCAA TOURNAMENT BRACKET PREDICTION[/bold magenta]")
        console.print(f"[bold magenta]{'='*60}[/bold magenta]")

        # ===== REGIONAL ROUNDS =====
        regional_winners = {}

        for region in REGIONS:
            if region not in teams_by_region:
                console.print(f"[yellow]Skipping {region} region (no data)[/yellow]")
                continue

            console.print(f"\n[bold blue]{'='*40}[/bold blue]")
            console.print(f"[bold blue]  {region.upper()} REGION[/bold blue]")
            console.print(f"[bold blue]{'='*40}[/bold blue]")

            region_teams = teams_by_region[region]
            region_results = self._simulate_region(region_teams, region, context)
            bracket["regions"][region] = region_results

            if region_results.get("winner"):
                regional_winners[region] = region_results["winner"]
                winner_name = region_results["winner"].get("team", "Unknown")
                console.print(f"\n[bold green]{region} Champion: {winner_name}[/bold green]")

        # ===== FINAL FOUR =====
        if len(regional_winners) >= 2:
            console.print(f"\n[bold magenta]{'='*40}[/bold magenta]")
            console.print(f"[bold magenta]  FINAL FOUR[/bold magenta]")
            console.print(f"[bold magenta]{'='*40}[/bold magenta]")

            # Traditional Final Four pairings
            # South vs East, West vs Midwest (varies by year)
            ff_matchups = [
                ("South", "East"),
                ("West", "Midwest"),
            ]

            ff_winners = []
            for r1, r2 in ff_matchups:
                if r1 in regional_winners and r2 in regional_winners:
                    ctx = {**context, "round": "Final Four"}
                    result = self.engine.predict_matchup(
                        regional_winners[r1],
                        regional_winners[r2],
                        ctx
                    )
                    bracket["final_four"].append(result)

                    winner_key = result["pick_key"]
                    winner_data = regional_winners[r1] if winner_key == "team_a" else regional_winners[r2]
                    ff_winners.append(winner_data)

            # ===== CHAMPIONSHIP =====
            if len(ff_winners) == 2:
                console.print(f"\n[bold magenta]{'='*40}[/bold magenta]")
                console.print(f"[bold magenta]  NATIONAL CHAMPIONSHIP[/bold magenta]")
                console.print(f"[bold magenta]{'='*40}[/bold magenta]")

                ctx = {**context, "round": "Championship"}
                championship = self.engine.predict_matchup(
                    ff_winners[0], ff_winners[1], ctx
                )
                bracket["championship"] = championship

                console.print(f"\n[bold green]NATIONAL CHAMPION: {championship['pick']}[/bold green]")
                console.print(f"[bold green]Win Probability: {max(championship['win_probability'].values())*100:.1f}%[/bold green]")

        # Save bracket
        self._save_bracket(bracket)

        return bracket

    def _simulate_region(self, teams: dict, region: str, context: dict) -> dict:
        """
        Simulate all rounds within a single region.
        teams: {seed: team_data_dict}
        """
        results = {"rounds": [], "winner": None}

        # Build first round matchups
        current_round = []
        for high_seed, low_seed in FIRST_ROUND_MATCHUPS:
            if high_seed in teams and low_seed in teams:
                current_round.append((teams[high_seed], teams[low_seed]))

        # Simulate each round
        for round_idx, round_name in enumerate(ROUND_NAMES[:4]):  # Up to Elite 8
            if not current_round:
                break

            console.print(f"\n  [cyan]{round_name}:[/cyan]")
            round_results = []
            next_round = []

            for team_a, team_b in current_round:
                ctx = {**context, "round": round_name, "region": region}
                result = self.engine.predict_matchup(team_a, team_b, ctx)
                round_results.append(result)

                # Advance the winner
                winner_key = result["pick_key"]
                winner = team_a if winner_key == "team_a" else team_b
                next_round.append(winner)

            results["rounds"].append({
                "round_name": round_name,
                "games": round_results,
            })

            # Pair winners for next round
            current_round = []
            for i in range(0, len(next_round) - 1, 2):
                current_round.append((next_round[i], next_round[i + 1]))

        # The last remaining team is the regional winner
        if next_round:
            results["winner"] = next_round[0] if len(next_round) == 1 else next_round[0]

        return results

    def monte_carlo_bracket(self, teams_by_region: dict, simulations: int = 1000,
                           context: dict = None) -> dict:
        """
        Run Monte Carlo simulation of the bracket.

        Instead of always picking the higher probability team,
        this uses the win probabilities to randomly determine
        outcomes, then aggregates across many simulations.

        Produces: probability each team reaches each round.
        """
        context = context or {}
        console.print(f"\n[bold magenta]Running {simulations} Monte Carlo bracket simulations...[/bold magenta]")

        # Track how far each team goes across all sims
        team_results = {}  # team_name -> {round: count}

        for sim in range(simulations):
            if sim % 100 == 0:
                console.print(f"  [dim]Simulation {sim}/{simulations}...[/dim]")

            # Run one bracket simulation with randomized outcomes
            bracket = self._run_single_mc_sim(teams_by_region, context)

            # Record results
            for region, results in bracket.get("regions", {}).items():
                for round_data in results.get("rounds", []):
                    for game in round_data.get("games", []):
                        winner = game.get("pick", "")
                        round_name = round_data.get("round_name", "")
                        if winner not in team_results:
                            team_results[winner] = {}
                        team_results[winner][round_name] = team_results[winner].get(round_name, 0) + 1

            # Final Four and Championship
            if bracket.get("championship"):
                champ = bracket["championship"].get("pick", "")
                if champ:
                    if champ not in team_results:
                        team_results[champ] = {}
                    team_results[champ]["Champion"] = team_results[champ].get("Champion", 0) + 1

        # Convert counts to probabilities
        prob_results = {}
        for team, rounds in team_results.items():
            prob_results[team] = {
                round_name: count / simulations
                for round_name, count in rounds.items()
            }

        # Sort by championship probability
        sorted_results = dict(sorted(
            prob_results.items(),
            key=lambda x: x[1].get("Champion", 0),
            reverse=True
        ))

        # Print top contenders
        self._print_mc_results(sorted_results, simulations)

        return sorted_results

    def _run_single_mc_sim(self, teams_by_region: dict, context: dict) -> dict:
        """Run one Monte Carlo bracket simulation with randomized outcomes."""
        bracket = {"regions": {}, "final_four": [], "championship": None}
        regional_winners = {}

        for region in REGIONS:
            if region not in teams_by_region:
                continue

            teams = teams_by_region[region]
            current_round = []
            for high_seed, low_seed in FIRST_ROUND_MATCHUPS:
                if high_seed in teams and low_seed in teams:
                    current_round.append((teams[high_seed], teams[low_seed]))

            region_results = {"rounds": [], "winner": None}
            next_round = []

            for round_name in ROUND_NAMES[:4]:
                if not current_round:
                    break

                round_games = []
                next_round = []

                for team_a, team_b in current_round:
                    ctx = {**context, "round": round_name}
                    result = self.engine.predict_matchup(team_a, team_b, ctx)
                    round_games.append(result)

                    # RANDOMIZED outcome based on win probability
                    prob_a = result["win_probability"]["team_a"]
                    if random.random() < prob_a:
                        next_round.append(team_a)
                    else:
                        next_round.append(team_b)

                region_results["rounds"].append({
                    "round_name": round_name,
                    "games": round_games,
                })

                current_round = []
                for i in range(0, len(next_round) - 1, 2):
                    current_round.append((next_round[i], next_round[i + 1]))

            if next_round:
                region_results["winner"] = next_round[0]
                regional_winners[region] = next_round[0]

            bracket["regions"][region] = region_results

        # Final Four + Championship (simplified for MC speed)
        ff_matchups = [("South", "East"), ("West", "Midwest")]
        ff_winners = []

        for r1, r2 in ff_matchups:
            if r1 in regional_winners and r2 in regional_winners:
                ctx = {**context, "round": "Final Four"}
                result = self.engine.predict_matchup(
                    regional_winners[r1], regional_winners[r2], ctx
                )
                bracket["final_four"].append(result)

                prob_a = result["win_probability"]["team_a"]
                if random.random() < prob_a:
                    ff_winners.append(regional_winners[r1])
                else:
                    ff_winners.append(regional_winners[r2])

        if len(ff_winners) == 2:
            ctx = {**context, "round": "Championship"}
            result = self.engine.predict_matchup(ff_winners[0], ff_winners[1], ctx)
            bracket["championship"] = result

        return bracket

    def _print_mc_results(self, results: dict, sims: int):
        """Print Monte Carlo results as a table."""
        table = Table(title=f"Tournament Probabilities ({sims} simulations)")
        table.add_column("Team", style="bold")
        table.add_column("Sweet 16", justify="right")
        table.add_column("Elite 8", justify="right")
        table.add_column("Final Four", justify="right")
        table.add_column("Champion", justify="right", style="bold green")

        for team, probs in list(results.items())[:20]:
            table.add_row(
                team,
                f"{probs.get('Sweet 16', 0)*100:.1f}%",
                f"{probs.get('Elite 8', 0)*100:.1f}%",
                f"{probs.get('Final Four', 0)*100:.1f}%",
                f"{probs.get('Champion', 0)*100:.1f}%",
            )

        console.print(table)

    def _save_bracket(self, bracket: dict):
        """Save bracket prediction to disk."""
        output_path = self.output_dir / "bracket_prediction.json"
        try:
            # Convert non-serializable items
            clean = json.loads(json.dumps(bracket, default=str))
            with open(output_path, "w") as f:
                json.dump(clean, f, indent=2)
            console.print(f"\n[green]Bracket saved to: {output_path}[/green]")
        except Exception as e:
            console.print(f"[red]Error saving bracket: {e}[/red]")
