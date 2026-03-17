"""
/api/chat - OpenRouter LLM chat endpoint
Uses free model (deepseek-r1:free or qwen3-235b:free) for NCAA basketball analysis
"""
import json
import os
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler

OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')

SYSTEM_PROMPT = """You are Swarm, an elite NCAA basketball analyst AI powering the Swarm Predictor platform.

You have deep knowledge of:
- The 2026 NCAA Tournament bracket (all 68 teams, seeds, regions)
- Advanced metrics: adjOE (offensive efficiency), adjDE (defensive efficiency), Barthag (power rating), SOS (strength of schedule)
- Our 3-pillar prediction model: Hard Score (analytics), Soft Score (momentum/intangibles), Chaos Score (upset probability)
- The Aden Holloway situation: Alabama's 2nd-leading scorer (16.8 PPG) was arrested on felony charges 3/16/26 and suspended. We adjusted Alabama's adjOE by -4.5 points.
- Our picks: Duke (East), Florida (South), Arizona (West), Michigan (Midwest) as region champions
- National Champion pick: DUKE over Michigan 77-74

Current bracket context:
- EAST: Duke 1-seed, UConn 2, Michigan St. 3, Kansas 4, St. John's 5
- SOUTH: Florida 1-seed, Houston 2, Illinois 3, Nebraska 4, Vanderbilt 5
- WEST: Arizona 1-seed, Purdue 2, Gonzaga 3, Arkansas 4, Wisconsin 5  
- MIDWEST: Michigan 1-seed, Iowa St. 2, Virginia 3, Alabama 4 (⚠️ Holloway out), Texas Tech 5

Key upset picks:
- Utah St. over Villanova (9 over 8, West)
- St. John's over Kansas (5 over 4, East) 
- UCLA over UConn (7 over 2, East) 🚨
- Vanderbilt over Nebraska (5 over 4, South)
- Arkansas over Wisconsin (4 over 5, West)
- Texas Tech over Alabama (5 over 4, Midwest - Holloway suspended)

Be concise, confident, and data-driven. Use basketball terminology naturally. Reference specific stats when asked. You can give opinions on bracket picks and strategy."""

FREE_MODELS = [
    'deepseek/deepseek-r1:free',
    'qwen/qwen3-235b-a22b:free',
    'meta-llama/llama-4-maverick:free',
    'google/gemma-3-27b-it:free',
]

def call_openrouter(messages, model=FREE_MODELS[0]):
    if not OPENROUTER_API_KEY:
        return None, "No OpenRouter API key configured"

    payload = json.dumps({
        'model': model,
        'messages': messages,
        'max_tokens': 600,
        'temperature': 0.7,
    }).encode()

    req = urllib.request.Request(
        'https://openrouter.ai/api/v1/chat/completions',
        data=payload,
        headers={
            'Authorization': f'Bearer {OPENROUTER_API_KEY}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://swarm-predictor.vercel.app',
            'X-Title': 'Swarm Predictor',
        },
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read())
            return data['choices'][0]['message']['content'], None
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        # Try fallback model
        if model == FREE_MODELS[0] and len(FREE_MODELS) > 1:
            return call_openrouter(messages, FREE_MODELS[1])
        return None, f"API error {e.code}: {err_body[:200]}"
    except Exception as e:
        return None, str(e)

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length) or b'{}')
        except:
            body = {}

        user_message = body.get('message', '').strip()
        history = body.get('history', [])

        if not user_message:
            self._send_json(400, {'error': 'No message provided'})
            return

        # Build messages array
        messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]
        for msg in history[-8:]:  # Last 8 for context
            if msg.get('role') in ('user', 'assistant') and msg.get('content'):
                messages.append({'role': msg['role'], 'content': msg['content']})
        messages.append({'role': 'user', 'content': user_message})

        reply, error = call_openrouter(messages)

        if error:
            # Fallback: simple rule-based response
            reply = self._fallback_response(user_message)

        self._send_json(200, {
            'reply': reply,
            'model': FREE_MODELS[0],
        })

    def _fallback_response(self, msg):
        msg_lower = msg.lower()
        if 'champion' in msg_lower or 'winner' in msg_lower:
            return "Our Swarm model projects **Duke** as the 2026 champion (17.1% title odds across 49,999 simulations). Key path: Michigan St. in E8, Florida in F4, Michigan in the championship (77-74)."
        if 'holloway' in msg_lower or 'alabama' in msg_lower:
            return "Aden Holloway's suspension is massive. He was Alabama's 2nd scorer at 16.8 PPG / 44% from three. We dropped their adjOE by 4.5 points, which flips their R32 matchup — now projecting Texas Tech over Alabama."
        if 'upset' in msg_lower:
            return "Top upset picks: UCLA over UConn (7v2), Utah St. over Villanova (9v8), Texas Tech over Alabama (Holloway suspended), Vanderbilt over Nebraska (5v4). The Chaos Score flags these as 40-54% upset probability."
        if 'duke' in msg_lower:
            return "Duke is our 1-seed with the highest title odds (17.1%). Cameron Boozer is elite. Path: Siena → Ohio St. → St. John's → Michigan St. → Florida → Michigan. Toughest game likely vs Florida in Final Four."
        return "Ask me about any team's chances, upset picks, the Holloway situation, or bracket strategy. I'm running on 49,999 simulations of the 2026 tournament."

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
