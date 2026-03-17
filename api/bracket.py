"""
/api/bracket - Returns 2026 NCAA bracket structure + player alerts
"""
import json
from http.server import BaseHTTPRequestHandler

BRACKET_2026 = {
    'East': {
        'seeds': {
            '1':'Duke','2':'UConn','3':'Michigan St.','4':'Kansas',
            '5':"St. John's",'6':'Louisville','7':'UCLA','8':'Ohio St.',
            '9':'TCU','10':'UCF','11':'South Florida','12':'Northern Iowa',
            '13':'Cal Baptist','14':'North Dakota St.','15':'Furman','16':'Siena'
        }
    },
    'South': {
        'seeds': {
            '1':'Florida','2':'Houston','3':'Illinois','4':'Nebraska',
            '5':'Vanderbilt','6':'North Carolina','7':"Saint Mary's",'8':'Clemson',
            '9':'Iowa','10':'Texas A&M','11':'VCU','12':'McNeese St.',
            '13':'Troy','14':'Penn','15':'Idaho','16':'Lehigh'
        }
    },
    'West': {
        'seeds': {
            '1':'Arizona','2':'Purdue','3':'Gonzaga','4':'Arkansas',
            '5':'Wisconsin','6':'BYU','7':'Miami FL','8':'Villanova',
            '9':'Utah St.','10':'Missouri','11':'Texas','12':'High Point',
            '13':'Hawaii','14':'Kennesaw St.','15':'Queens','16':'LIU'
        }
    },
    'Midwest': {
        'seeds': {
            '1':'Michigan','2':'Iowa St.','3':'Virginia','4':'Alabama',
            '5':'Texas Tech','6':'Tennessee','7':'Kentucky','8':'Georgia',
            '9':'Saint Louis','10':'Santa Clara','11':'SMU','12':'Akron',
            '13':'Hofstra','14':'Wright St.','15':'Tennessee St.','16':'UMBC'
        }
    }
}

PLAYER_ALERTS = {
    'Alabama': {
        'note': 'Aden Holloway suspended — felony arrest 3/16/26',
        'adj_o_mod': -4.5,
        'barthag_mod': -0.05,
        'severity': 'high',
        'source': 'ESPN / CBS Sports'
    }
}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._send_json(200, {'bracket': BRACKET_2026, 'player_alerts': PLAYER_ALERTS})

    def _send_json(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, f, *a): pass
