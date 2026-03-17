"""
/api/predict_game - Vercel serverless function
Simulates a single NCAA game matchup using the Swarm Predictor engine
"""
import sys
import os
import json
import contextlib
import io as _io
from http.server import BaseHTTPRequestHandler

# Add engine to path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine.prediction_engine import PredictionEngine

_engine = None
def get_engine():
    global _engine
    if _engine is None:
        _engine = PredictionEngine()
    return _engine

def to_engine_format(td, adj_o_mod=0, adj_d_mod=0):
    return {
        'team': td.get('name', 'Team'),
        'conf': td.get('conf', '?'),
        'seed': int(td.get('seed', 8)),
        'adj_o': float(td.get('adj_o', 108)) + float(adj_o_mod),
        'adj_d': float(td.get('adj_d', 104)) + float(adj_d_mod),
        'barthag': max(0.05, min(0.99, float(td.get('barthag', 0.55)))),
        'adj_t': float(td.get('adj_t', 68)),
        'sos': float(td.get('sos', 0)),
        'wab': float(td.get('wab', 0)),
        'ft_pct': 0.72,
        'streak': td.get('streak', 'W3'),
        'win_pct': float(td.get('win_pct', 0.75)),
        'conf_tourney_champ': bool(td.get('conf_champ', False)),
        'avg_height_inches': 76.5,
    }

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length) or b'{}')
        except:
            body = {}

        team_a = body.get('team_a', {})
        team_b = body.get('team_b', {})
        round_name = body.get('round', 'Round of 64')
        a_o_mod = float(body.get('team_a_adj_o_mod', 0))
        b_o_mod = float(body.get('team_b_adj_o_mod', 0))

        try:
            eng = get_engine()
            ea = to_engine_format(team_a, adj_o_mod=a_o_mod)
            eb = to_engine_format(team_b, adj_o_mod=b_o_mod)

            with contextlib.redirect_stdout(_io.StringIO()):
                res = eng.predict_matchup(ea, eb, {'round': round_name, 'neutral_site': True})

            winner = team_a.get('name') if res['pick_key'] == 'team_a' else team_b.get('name')
            result = {
                'winner': winner,
                'pick_key': res['pick_key'],
                'score_a': res['predicted_score']['team_a'],
                'score_b': res['predicted_score']['team_b'],
                'win_probability_a': res['win_probability'].get('team_a', 0.5),
                'win_probability_b': res['win_probability'].get('team_b', 0.5),
                'pillar_scores': res.get('pillar_scores', {}),
                'confidence': res.get('confidence', 0.5),
                'round': round_name,
            }
            self._send_json(200, result)
        except Exception as e:
            import traceback
            self._send_json(500, {'error': str(e), 'trace': traceback.format_exc()})

    def do_OPTIONS(self):
        self._send_json(200, {})

    def _send_json(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass
