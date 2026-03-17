#!/usr/bin/env python3
"""
Swarm Predictor Web App — Flask Backend
NCAA 2026 Basketball Tournament Prediction Engine
"""

import sys
import json
import contextlib
import io as _io
import csv
import io
import threading
import time
from flask import Flask, jsonify, request, send_from_directory

sys.path.insert(0, '/tmp/mirofish/swarm-predictor')

from engine.prediction_engine import PredictionEngine

app = Flask(__name__, static_folder='.')
eng = PredictionEngine()

# ─── Team Data ──────────────────────────────────────────────────────────────
_torvik_cache = {}
_torvik_lock = threading.Lock()

def load_torvik():
    global _torvik_cache
    try:
        import requests
        r = requests.get('https://barttorvik.com/2026_team_results.csv',
                         headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        data = {row['team'].strip(): row for row in csv.DictReader(io.StringIO(r.text))}
        with _torvik_lock:
            _torvik_cache = data
        print(f"[Torvik] Loaded {len(data)} teams")
    except Exception as e:
        print(f"[Torvik] Failed to load: {e}")

# Load in background
threading.Thread(target=load_torvik, daemon=True).start()

def get_team_stats(name):
    with _torvik_lock:
        data = _torvik_cache
    if name in data:
        return data[name]
    for k, v in data.items():
        if name.lower() in k.lower():
            return v
    return {}

def build_team(name, seed, fallback=None):
    d = fallback or get_team_stats(name) or {}
    return {
        'name': name, 'seed': seed,
        'conf': d.get('conf', '?'),
        'adj_o': float(d.get('adjoe', 108) or 108),
        'adj_d': float(d.get('adjde', 104) or 104),
        'barthag': float(d.get('barthag', 0.55) or 0.55),
        'adj_t': float(d.get('adjt', 68) or 68),
        'sos': float(d.get('sos', 0) or 0),
        'wab': float(d.get('WAB', 0) or 0),
    }

def to_engine(td, streak='W3', win_pct=0.75, conf_champ=False, adj_o_mod=0, barthag_mod=0):
    return {
        'team': td['name'], 'conf': td.get('conf', '?'), 'seed': td['seed'],
        'adj_o': td['adj_o'] + adj_o_mod,
        'adj_d': td['adj_d'],
        'barthag': max(0.05, min(0.99, td['barthag'] + barthag_mod)),
        'adj_t': td.get('adj_t', 68),
        'sos': td.get('sos', 0), 'wab': td.get('wab', 0),
        'ft_pct': 0.72, 'streak': streak, 'win_pct': win_pct,
        'conf_tourney_champ': conf_champ, 'avg_height_inches': 76.5,
    }

def run_prediction(team_a_data, team_b_data, round_name='Round of 64',
                   a_adj_o_mod=0, a_barthag_mod=0, b_adj_o_mod=0, b_barthag_mod=0):
    ea = to_engine(team_a_data, adj_o_mod=a_adj_o_mod, barthag_mod=a_barthag_mod)
    eb = to_engine(team_b_data, adj_o_mod=b_adj_o_mod, barthag_mod=b_barthag_mod)
    with contextlib.redirect_stdout(_io.StringIO()):
        res = eng.predict_matchup(ea, eb, {'round': round_name, 'neutral_site': True})
    return res

# ─── 2026 Bracket ────────────────────────────────────────────────────────────
BRACKET_2026 = {
    'East': {
        'seeds': {
            1: 'Duke', 2: 'UConn', 3: 'Michigan St.', 4: 'Kansas',
            5: "St. John's", 6: 'Louisville', 7: 'UCLA', 8: 'Ohio St.',
            9: 'TCU', 10: 'UCF', 11: 'South Florida', 12: 'Northern Iowa',
            13: 'Cal Baptist', 14: 'North Dakota St.', 15: 'Furman', 16: 'Siena'
        },
        'matchups': [
            {'team_a_seed': 1, 'team_b_seed': 16},
            {'team_a_seed': 8, 'team_b_seed': 9},
            {'team_a_seed': 5, 'team_b_seed': 12},
            {'team_a_seed': 4, 'team_b_seed': 13},
            {'team_a_seed': 6, 'team_b_seed': 11},
            {'team_a_seed': 3, 'team_b_seed': 14},
            {'team_a_seed': 7, 'team_b_seed': 10},
            {'team_a_seed': 2, 'team_b_seed': 15},
        ]
    },
    'South': {
        'seeds': {
            1: 'Florida', 2: 'Houston', 3: 'Illinois', 4: 'Nebraska',
            5: 'Vanderbilt', 6: 'North Carolina', 7: "Saint Mary's", 8: 'Clemson',
            9: 'Iowa', 10: 'Texas A&M', 11: 'VCU', 12: 'McNeese St.',
            13: 'Troy', 14: 'Penn', 15: 'Idaho', 16: 'Lehigh'
        },
        'matchups': [
            {'team_a_seed': 1, 'team_b_seed': 16},
            {'team_a_seed': 8, 'team_b_seed': 9},
            {'team_a_seed': 5, 'team_b_seed': 12},
            {'team_a_seed': 4, 'team_b_seed': 13},
            {'team_a_seed': 6, 'team_b_seed': 11},
            {'team_a_seed': 3, 'team_b_seed': 14},
            {'team_a_seed': 7, 'team_b_seed': 10},
            {'team_a_seed': 2, 'team_b_seed': 15},
        ]
    },
    'West': {
        'seeds': {
            1: 'Arizona', 2: 'Purdue', 3: 'Gonzaga', 4: 'Arkansas',
            5: 'Wisconsin', 6: 'BYU', 7: 'Miami FL', 8: 'Villanova',
            9: 'Utah St.', 10: 'Missouri', 11: 'Texas', 12: 'High Point',
            13: 'Hawaii', 14: 'Kennesaw St.', 15: 'Queens', 16: 'LIU'
        },
        'matchups': [
            {'team_a_seed': 1, 'team_b_seed': 16},
            {'team_a_seed': 8, 'team_b_seed': 9},
            {'team_a_seed': 5, 'team_b_seed': 12},
            {'team_a_seed': 4, 'team_b_seed': 13},
            {'team_a_seed': 6, 'team_b_seed': 11},
            {'team_a_seed': 3, 'team_b_seed': 14},
            {'team_a_seed': 7, 'team_b_seed': 10},
            {'team_a_seed': 2, 'team_b_seed': 15},
        ]
    },
    'Midwest': {
        'seeds': {
            1: 'Michigan', 2: 'Iowa St.', 3: 'Virginia', 4: 'Alabama',
            5: 'Texas Tech', 6: 'Tennessee', 7: 'Kentucky', 8: 'Georgia',
            9: 'Saint Louis', 10: 'Santa Clara', 11: 'SMU', 12: 'Akron',
            13: 'Hofstra', 14: 'Wright St.', 15: 'Tennessee St.', 16: 'UMBC'
        },
        'matchups': [
            {'team_a_seed': 1, 'team_b_seed': 16},
            {'team_a_seed': 8, 'team_b_seed': 9},
            {'team_a_seed': 5, 'team_b_seed': 12},
            {'team_a_seed': 4, 'team_b_seed': 13},
            {'team_a_seed': 6, 'team_b_seed': 11},
            {'team_a_seed': 3, 'team_b_seed': 14},
            {'team_a_seed': 7, 'team_b_seed': 10},
            {'team_a_seed': 2, 'team_b_seed': 15},
        ]
    }
}

PLAYER_ALERTS = {
    'Alabama': {
        'note': 'Aden Holloway suspended (felony arrest)',
        'adj_o_mod': -4.5,
        'barthag_mod': -0.05,
        'severity': 'high'
    }
}

# ─── API Routes ──────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/bracket/2026')
def bracket_2026():
    return jsonify({'bracket': BRACKET_2026, 'player_alerts': PLAYER_ALERTS})

@app.route('/api/teams')
def teams():
    with _torvik_lock:
        data = dict(_torvik_cache)
    teams_list = []
    for name, row in list(data.items())[:200]:
        try:
            teams_list.append({
                'name': name,
                'conf': row.get('conf', '?'),
                'adj_o': float(row.get('adjoe', 108) or 108),
                'adj_d': float(row.get('adjde', 104) or 104),
                'barthag': float(row.get('barthag', 0.55) or 0.55),
                'record': row.get('record', ''),
            })
        except:
            pass
    teams_list.sort(key=lambda x: -x.get('barthag', 0))
    return jsonify({'teams': teams_list})

@app.route('/api/predict/game', methods=['POST'])
def predict_game():
    body = request.json or {}
    team_a = body.get('team_a', {})
    team_b = body.get('team_b', {})
    round_name = body.get('round', 'Round of 64')
    a_adj_o_mod = float(body.get('team_a_adj_o_mod', 0))
    a_barthag_mod = float(body.get('team_a_barthag_mod', 0))
    b_adj_o_mod = float(body.get('team_b_adj_o_mod', 0))
    b_barthag_mod = float(body.get('team_b_barthag_mod', 0))

    try:
        res = run_prediction(team_a, team_b, round_name,
                             a_adj_o_mod, a_barthag_mod, b_adj_o_mod, b_barthag_mod)
        winner_name = team_a['name'] if res['pick_key'] == 'team_a' else team_b['name']
        return jsonify({
            'winner': winner_name,
            'score_a': res['predicted_score']['team_a'],
            'score_b': res['predicted_score']['team_b'],
            'win_probability_a': res['win_probability'].get('team_a', 0.5),
            'win_probability_b': res['win_probability'].get('team_b', 0.5),
            'pillar_scores': {
                'hard': res['pillar_scores'].get('hard', {}),
                'soft': res['pillar_scores'].get('soft', {}),
                'chaos': res['pillar_scores'].get('chaos', {}),
            },
            'confidence': res.get('confidence', 0.5),
            'round': round_name,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/predict/tournament', methods=['POST'])
def predict_tournament():
    body = request.json or {}
    n_sims = min(int(body.get('simulations', 10000)), 50000)
    player_adjustments = body.get('player_adjustments', {})

    # Merge default alerts with user overrides
    effective_adjustments = dict(PLAYER_ALERTS)
    for team, adj in player_adjustments.items():
        if adj.get('enabled', True):
            effective_adjustments[team] = adj
        elif team in effective_adjustments:
            del effective_adjustments[team]

    try:
        results = run_tournament_sims(n_sims, effective_adjustments)
        return jsonify(results)
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

def run_tournament_sims(n_sims, adjustments):
    """Run N tournament simulations and return aggregated stats."""
    from collections import defaultdict
    import random

    region_order = ['East', 'South', 'West', 'Midwest']
    ff_pairs = [('East', 'South'), ('West', 'Midwest')]

    # Build team objects for all 64 teams
    all_teams = {}
    for region, region_data in BRACKET_2026.items():
        for seed, name in region_data['seeds'].items():
            stats = build_team(name, seed)
            all_teams[(region, seed)] = stats

    title_count = defaultdict(int)
    ff_count = defaultdict(int)
    s16_count = defaultdict(int)
    r32_count = defaultdict(int)
    total = 0

    def sim_game(ta, tb, rnd, adjustments):
        adj_a = adjustments.get(ta['name'], {})
        adj_b = adjustments.get(tb['name'], {})
        res = run_prediction(
            ta, tb, rnd,
            float(adj_a.get('adj_o_mod', 0)), float(adj_a.get('barthag_mod', 0)),
            float(adj_b.get('adj_o_mod', 0)), float(adj_b.get('barthag_mod', 0)),
        )
        # Add variance for simulation
        wp_a = res['win_probability'].get('team_a', 0.5)
        # Add small random noise to avoid determinism
        wp_a = max(0.02, min(0.98, wp_a + random.gauss(0, 0.04)))
        return ta if random.random() < wp_a else tb

    for _ in range(n_sims):
        region_champs = {}

        for region in region_order:
            region_data = BRACKET_2026[region]
            seeds = region_data['seeds']
            matchups = region_data['matchups']

            # Build pool from matchup pairings
            r64_pool = []
            for m in matchups:
                ta = dict(all_teams[(region, m['team_a_seed'])])
                tb = dict(all_teams[(region, m['team_b_seed'])])
                w = sim_game(ta, tb, 'Round of 64', adjustments)
                r64_pool.append(w)
                r32_count[w['name']] += 1

            r32_pool = []
            for i in range(0, len(r64_pool), 2):
                w = sim_game(r64_pool[i], r64_pool[i+1], 'Round of 32', adjustments)
                r32_pool.append(w)
                s16_count[w['name']] += 1

            s16_pool = []
            for i in range(0, len(r32_pool), 2):
                w = sim_game(r32_pool[i], r32_pool[i+1], 'Sweet 16', adjustments)
                s16_pool.append(w)

            champ = sim_game(s16_pool[0], s16_pool[1], 'Elite 8', adjustments)
            ff_count[champ['name']] += 1
            region_champs[region] = champ

        # Final Four
        ff1_w = sim_game(region_champs['East'], region_champs['South'], 'Final Four', adjustments)
        ff2_w = sim_game(region_champs['West'], region_champs['Midwest'], 'Final Four', adjustments)
        champ = sim_game(ff1_w, ff2_w, 'Championship', adjustments)
        title_count[champ['name']] += 1
        total += 1

    # Build results
    all_team_names = set()
    for region, region_data in BRACKET_2026.items():
        all_team_names.update(region_data['seeds'].values())

    champion_odds = []
    for name in all_team_names:
        champion_odds.append({
            'team': name,
            'title_pct': round(title_count[name] / total * 100, 1),
            'final_four_pct': round(ff_count[name] / total * 100, 1),
            'sweet_16_pct': round(s16_count[name] / total * 100, 1),
            'round_32_pct': round(r32_count[name] / total * 100, 1),
        })
    champion_odds.sort(key=lambda x: -x['title_pct'])

    # Deterministic bracket picks
    bracket_picks = {}
    for region, region_data in BRACKET_2026.items():
        seeds = region_data['seeds']
        matchups = region_data['matchups']
        pool = []
        picks_r64 = []
        for m in matchups:
            ta = dict(all_teams[(region, m['team_a_seed'])])
            tb = dict(all_teams[(region, m['team_b_seed'])])
            res = run_prediction(ta, tb, 'Round of 64',
                a_adj_o_mod=float(adjustments.get(ta['name'], {}).get('adj_o_mod', 0)),
                a_barthag_mod=float(adjustments.get(ta['name'], {}).get('barthag_mod', 0)),
                b_adj_o_mod=float(adjustments.get(tb['name'], {}).get('adj_o_mod', 0)),
                b_barthag_mod=float(adjustments.get(tb['name'], {}).get('barthag_mod', 0)),
            )
            w = ta if res['pick_key'] == 'team_a' else tb
            l = tb if res['pick_key'] == 'team_a' else ta
            picks_r64.append({
                'winner': w['name'], 'loser': l['name'],
                'score_a': res['predicted_score']['team_a'],
                'score_b': res['predicted_score']['team_b'],
                'upset': w['seed'] > l['seed'],
                'upset_prob': res['pillar_scores'].get('chaos', {}).get('upset_probability', 0),
            })
            pool.append(w)

        picks_r32 = []
        r32_pool = []
        for i in range(0, len(pool), 2):
            res = run_prediction(pool[i], pool[i+1], 'Round of 32')
            w = pool[i] if res['pick_key'] == 'team_a' else pool[i+1]
            l = pool[i+1] if res['pick_key'] == 'team_a' else pool[i]
            picks_r32.append({
                'winner': w['name'], 'loser': l['name'],
                'score_a': res['predicted_score']['team_a'],
                'score_b': res['predicted_score']['team_b'],
                'upset': w['seed'] > l['seed'],
            })
            r32_pool.append(w)

        picks_s16 = []
        s16_pool = []
        for i in range(0, len(r32_pool), 2):
            res = run_prediction(r32_pool[i], r32_pool[i+1], 'Sweet 16')
            w = r32_pool[i] if res['pick_key'] == 'team_a' else r32_pool[i+1]
            l = r32_pool[i+1] if res['pick_key'] == 'team_a' else r32_pool[i]
            picks_s16.append({'winner': w['name'], 'loser': l['name'], 'upset': w['seed'] > l['seed']})
            s16_pool.append(w)

        res = run_prediction(s16_pool[0], s16_pool[1], 'Elite 8')
        e8_winner = s16_pool[0] if res['pick_key'] == 'team_a' else s16_pool[1]

        bracket_picks[region] = {
            'r64': picks_r64, 'r32': picks_r32, 's16': picks_s16,
            'e8_winner': e8_winner['name'], 'e8_winner_seed': e8_winner['seed'],
        }

    return {
        'simulations': total,
        'champion_odds': champion_odds[:20],
        'bracket_picks': bracket_picks,
        'adjustments_applied': list(adjustments.keys()),
    }

if __name__ == '__main__':
    print("🏀 Swarm Predictor starting on http://0.0.0.0:5050")
    app.run(host='0.0.0.0', port=5050, debug=False)
