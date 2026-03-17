"""
/api/predict_tournament - Vercel serverless function
Runs N tournament simulations and returns champion odds + bracket picks
"""
import sys, os, json, contextlib, io as _io, random
from collections import defaultdict
from http.server import BaseHTTPRequestHandler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from engine.prediction_engine import PredictionEngine

_engine = None
def get_engine():
    global _engine
    if _engine is None:
        _engine = PredictionEngine()
    return _engine

BRACKET_2026 = {
    'East': {
        1:'Duke', 2:'UConn', 3:'Michigan St.', 4:'Kansas',
        5:"St. John's", 6:'Louisville', 7:'UCLA', 8:'Ohio St.',
        9:'TCU', 10:'UCF', 11:'South Florida', 12:'Northern Iowa',
        13:'Cal Baptist', 14:'North Dakota St.', 15:'Furman', 16:'Siena'
    },
    'South': {
        1:'Florida', 2:'Houston', 3:'Illinois', 4:'Nebraska',
        5:'Vanderbilt', 6:'North Carolina', 7:"Saint Mary's", 8:'Clemson',
        9:'Iowa', 10:'Texas A&M', 11:'VCU', 12:'McNeese St.',
        13:'Troy', 14:'Penn', 15:'Idaho', 16:'Lehigh'
    },
    'West': {
        1:'Arizona', 2:'Purdue', 3:'Gonzaga', 4:'Arkansas',
        5:'Wisconsin', 6:'BYU', 7:'Miami FL', 8:'Villanova',
        9:'Utah St.', 10:'Missouri', 11:'Texas', 12:'High Point',
        13:'Hawaii', 14:'Kennesaw St.', 15:'Queens', 16:'LIU'
    },
    'Midwest': {
        1:'Michigan', 2:'Iowa St.', 3:'Virginia', 4:'Alabama',
        5:'Texas Tech', 6:'Tennessee', 7:'Kentucky', 8:'Georgia',
        9:'Saint Louis', 10:'Santa Clara', 11:'SMU', 12:'Akron',
        13:'Hofstra', 14:'Wright St.', 15:'Tennessee St.', 16:'UMBC'
    }
}

SEED_MATCHUPS = [(1,16),(8,9),(5,12),(4,13),(6,11),(3,14),(7,10),(2,15)]

# Torvik-based fallback stats
TEAM_STATS = {
    'Duke':         {'adj_o':120.5,'adj_d':91.8,'barthag':0.948,'adj_t':69,'sos':9.2,'wab':8.1},
    'UConn':        {'adj_o':118.2,'adj_d':93.1,'barthag':0.931,'adj_t':67,'sos':7.8,'wab':6.9},
    'Michigan St.': {'adj_o':117.1,'adj_d':93.8,'barthag':0.920,'adj_t':68,'sos':7.1,'wab':6.2},
    'Kansas':       {'adj_o':116.8,'adj_d':94.2,'barthag':0.914,'adj_t':70,'sos':8.1,'wab':7.0},
    "St. John's":   {'adj_o':115.9,'adj_d':94.8,'barthag':0.905,'adj_t':67,'sos':6.8,'wab':5.8},
    'Louisville':   {'adj_o':114.2,'adj_d':96.1,'barthag':0.886,'adj_t':69,'sos':5.9,'wab':4.8},
    'UCLA':         {'adj_o':113.8,'adj_d':96.5,'barthag':0.880,'adj_t':68,'sos':5.4,'wab':4.2},
    'Ohio St.':     {'adj_o':113.1,'adj_d':97.2,'barthag':0.871,'adj_t':70,'sos':6.1,'wab':5.0},
    'Florida':      {'adj_o':121.2,'adj_d':92.4,'barthag':0.952,'adj_t':70,'sos':9.8,'wab':8.9},
    'Houston':      {'adj_o':118.9,'adj_d':91.2,'barthag':0.945,'adj_t':68,'sos':8.4,'wab':7.5},
    'Illinois':     {'adj_o':116.4,'adj_d':93.5,'barthag':0.918,'adj_t':69,'sos':7.5,'wab':6.4},
    'Nebraska':     {'adj_o':115.1,'adj_d':95.0,'barthag':0.900,'adj_t':70,'sos':6.9,'wab':5.9},
    'Vanderbilt':   {'adj_o':114.5,'adj_d':95.8,'barthag':0.890,'adj_t':68,'sos':6.2,'wab':5.1},
    'North Carolina':{'adj_o':113.9,'adj_d':96.4,'barthag':0.882,'adj_t':71,'sos':5.8,'wab':4.6},
    "Saint Mary's": {'adj_o':113.2,'adj_d':97.0,'barthag':0.874,'adj_t':66,'sos':4.8,'wab':3.8},
    'Clemson':      {'adj_o':112.8,'adj_d':97.5,'barthag':0.868,'adj_t':69,'sos':5.5,'wab':4.3},
    'Arizona':      {'adj_o':120.1,'adj_d':92.8,'barthag':0.942,'adj_t':71,'sos':9.1,'wab':8.0},
    'Purdue':       {'adj_o':118.5,'adj_d':92.1,'barthag':0.938,'adj_t':68,'sos':8.6,'wab':7.6},
    'Gonzaga':      {'adj_o':117.8,'adj_d':93.2,'barthag':0.928,'adj_t':70,'sos':7.2,'wab':6.3},
    'Arkansas':     {'adj_o':116.1,'adj_d':94.5,'barthag':0.910,'adj_t':70,'sos':7.8,'wab':6.7},
    'Wisconsin':    {'adj_o':115.0,'adj_d':95.2,'barthag':0.898,'adj_t':67,'sos':6.5,'wab':5.4},
    'BYU':          {'adj_o':114.1,'adj_d':96.2,'barthag':0.887,'adj_t':69,'sos':5.7,'wab':4.7},
    'Miami FL':     {'adj_o':113.5,'adj_d':96.8,'barthag':0.877,'adj_t':68,'sos':5.2,'wab':4.0},
    'Villanova':    {'adj_o':113.0,'adj_d':97.3,'barthag':0.870,'adj_t':67,'sos':5.0,'wab':3.9},
    'Michigan':     {'adj_o':122.1,'adj_d':91.0,'barthag':0.958,'adj_t':70,'sos':10.1,'wab':9.2},
    'Iowa St.':     {'adj_o':119.5,'adj_d':92.2,'barthag':0.944,'adj_t':70,'sos':8.9,'wab':7.9},
    'Virginia':     {'adj_o':116.7,'adj_d':93.4,'barthag':0.921,'adj_t':65,'sos':7.4,'wab':6.3},
    'Alabama':      {'adj_o':121.0,'adj_d':97.0,'barthag':0.920,'adj_t':70,'sos':8.0,'wab':6.0},
    'Texas Tech':   {'adj_o':118.0,'adj_d':95.0,'barthag':0.905,'adj_t':68,'sos':6.0,'wab':5.0},
    'Tennessee':    {'adj_o':115.5,'adj_d':94.0,'barthag':0.900,'adj_t':68,'sos':7.0,'wab':6.0},
    'Kentucky':     {'adj_o':114.8,'adj_d':95.5,'barthag':0.892,'adj_t':69,'sos':6.8,'wab':5.7},
    'Georgia':      {'adj_o':113.7,'adj_d':96.6,'barthag':0.879,'adj_t':70,'sos':6.0,'wab':4.9},
}

def make_team(name, seed):
    s = TEAM_STATS.get(name, {})
    seed_bonus = max(0, (9 - seed) * 0.5)
    return {
        'name': name, 'seed': seed, 'conf': '?',
        'adj_o': s.get('adj_o', 105 + seed_bonus),
        'adj_d': s.get('adj_d', 104 - seed_bonus * 0.5),
        'barthag': s.get('barthag', 0.45 + seed_bonus * 0.02),
        'adj_t': s.get('adj_t', 68), 'sos': s.get('sos', 0), 'wab': s.get('wab', 0),
    }

def to_e(td, adj_o_mod=0, barthag_mod=0):
    return {
        'team': td['name'], 'conf': td.get('conf','?'), 'seed': td['seed'],
        'adj_o': td['adj_o'] + adj_o_mod,
        'adj_d': td['adj_d'],
        'barthag': max(0.05, min(0.99, td['barthag'] + barthag_mod)),
        'adj_t': td.get('adj_t', 68), 'sos': td.get('sos', 0), 'wab': td.get('wab', 0),
        'ft_pct': 0.72, 'streak': 'W3', 'win_pct': 0.76,
        'conf_tourney_champ': False, 'avg_height_inches': 76.5,
    }

def sim_game(ta, tb, rnd, adjustments, eng):
    adj_a = adjustments.get(ta['name'], {})
    adj_b = adjustments.get(tb['name'], {})
    ea = to_e(ta, float(adj_a.get('adj_o_mod', 0)), float(adj_a.get('barthag_mod', 0)))
    eb = to_e(tb, float(adj_b.get('adj_o_mod', 0)), float(adj_b.get('barthag_mod', 0)))
    with contextlib.redirect_stdout(_io.StringIO()):
        res = eng.predict_matchup(ea, eb, {'round': rnd, 'neutral_site': True})
    wp_a = res['win_probability'].get('team_a', 0.5)
    wp_a = max(0.02, min(0.98, wp_a + random.gauss(0, 0.035)))
    return ta if random.random() < wp_a else tb

def det_game(ta, tb, rnd, adjustments, eng):
    """Deterministic pick (no noise) for bracket view"""
    adj_a = adjustments.get(ta['name'], {})
    adj_b = adjustments.get(tb['name'], {})
    ea = to_e(ta, float(adj_a.get('adj_o_mod', 0)), float(adj_a.get('barthag_mod', 0)))
    eb = to_e(tb, float(adj_b.get('adj_o_mod', 0)), float(adj_b.get('barthag_mod', 0)))
    with contextlib.redirect_stdout(_io.StringIO()):
        res = eng.predict_matchup(ea, eb, {'round': rnd, 'neutral_site': True})
    w = ta if res['pick_key'] == 'team_a' else tb
    l = tb if res['pick_key'] == 'team_a' else ta
    sa, sb = res['predicted_score']['team_a'], res['predicted_score']['team_b']
    ws = sa if res['pick_key'] == 'team_a' else sb
    ls = sb if res['pick_key'] == 'team_a' else sa
    up = res['pillar_scores'].get('chaos', {}).get('upset_probability', 0.2)
    return w, l, ws, ls, w['seed'] > l['seed'], up

def run_sims(n, adjustments):
    eng = get_engine()
    region_order = ['East', 'South', 'West', 'Midwest']
    title_count = defaultdict(int)
    ff_count = defaultdict(int)
    s16_count = defaultdict(int)
    r32_count = defaultdict(int)

    for _ in range(n):
        region_champs = {}
        for region in region_order:
            seeds = BRACKET_2026[region]
            r64_pool = []
            for sa, sb in SEED_MATCHUPS:
                ta, tb = make_team(seeds[sa], sa), make_team(seeds[sb], sb)
                w = sim_game(ta, tb, 'Round of 64', adjustments, eng)
                r32_count[w['name']] += 1
                r64_pool.append(w)
            r32_pool = []
            for i in range(0, 8, 2):
                w = sim_game(r64_pool[i], r64_pool[i+1], 'Round of 32', adjustments, eng)
                s16_count[w['name']] += 1
                r32_pool.append(w)
            s16_pool = []
            for i in range(0, 4, 2):
                w = sim_game(r32_pool[i], r32_pool[i+1], 'Sweet 16', adjustments, eng)
                s16_pool.append(w)
            champ = sim_game(s16_pool[0], s16_pool[1], 'Elite 8', adjustments, eng)
            ff_count[champ['name']] += 1
            region_champs[region] = champ
        ff1 = sim_game(region_champs['East'], region_champs['South'], 'Final Four', adjustments, eng)
        ff2 = sim_game(region_champs['West'], region_champs['Midwest'], 'Final Four', adjustments, eng)
        champ = sim_game(ff1, ff2, 'Championship', adjustments, eng)
        title_count[champ['name']] += 1

    total = n
    all_names = set()
    for region in region_order:
        all_names.update(BRACKET_2026[region].values())

    odds = sorted([{
        'team': name,
        'title_pct': round(title_count[name]/total*100, 1),
        'final_four_pct': round(ff_count[name]/total*100, 1),
        'sweet_16_pct': round(s16_count[name]/total*100, 1),
        'round_32_pct': round(r32_count[name]/total*100, 1),
    } for name in all_names], key=lambda x: -x['title_pct'])

    # Deterministic bracket picks
    bracket_picks = {}
    for region in region_order:
        seeds = BRACKET_2026[region]
        pool = []
        r64 = []
        for sa, sb in SEED_MATCHUPS:
            ta, tb = make_team(seeds[sa], sa), make_team(seeds[sb], sb)
            w, l, ws, ls, upset, up = det_game(ta, tb, 'Round of 64', adjustments, eng)
            r64.append({'winner': w['name'], 'loser': l['name'], 'winner_seed': w['seed'], 'loser_seed': l['seed'], 'ws': ws, 'ls': ls, 'upset': upset, 'upset_prob': round(up, 3)})
            pool.append(w)
        r32 = []
        r32_pool = []
        for i in range(0, 8, 2):
            w, l, ws, ls, upset, up = det_game(pool[i], pool[i+1], 'Round of 32', adjustments, eng)
            r32.append({'winner': w['name'], 'loser': l['name'], 'winner_seed': w['seed'], 'loser_seed': l['seed'], 'ws': ws, 'ls': ls, 'upset': upset, 'upset_prob': round(up, 3)})
            r32_pool.append(w)
        s16 = []
        s16_pool = []
        for i in range(0, 4, 2):
            w, l, ws, ls, upset, up = det_game(r32_pool[i], r32_pool[i+1], 'Sweet 16', adjustments, eng)
            s16.append({'winner': w['name'], 'loser': l['name'], 'upset': upset})
            s16_pool.append(w)
        e8_w, e8_l, e8_ws, e8_ls, e8_up, _ = det_game(s16_pool[0], s16_pool[1], 'Elite 8', adjustments, eng)
        bracket_picks[region] = {
            'r64': r64, 'r32': r32, 's16': s16,
            'e8_winner': e8_w['name'], 'e8_winner_seed': e8_w['seed'],
            'e8_score': f"{e8_ws}-{e8_ls}"
        }

    return {
        'simulations': total,
        'champion_odds': odds[:20],
        'bracket_picks': bracket_picks,
        'adjustments_applied': list(adjustments.keys()),
    }

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length) or b'{}')
        except:
            body = {}

        n = min(int(body.get('simulations', 5000)), 20000)
        player_adj = body.get('player_adjustments', {})

        default_adj = {
            'Alabama': {'adj_o_mod': -4.5, 'barthag_mod': -0.05}
        }
        effective = dict(default_adj)
        for team, adj in player_adj.items():
            if adj.get('enabled', True):
                effective[team] = adj
            elif team in effective:
                del effective[team]

        try:
            result = run_sims(n, effective)
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

    def log_message(self, f, *a): pass
