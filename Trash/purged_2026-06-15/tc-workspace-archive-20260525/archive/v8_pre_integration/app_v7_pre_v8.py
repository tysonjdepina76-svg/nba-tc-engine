#!/usr/bin/env python3
"""Sports TC - Flask Dashboard v7.0"""
from flask import Flask, render_template_string, request
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__)

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Sports TC Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; max-width: 1320px; margin: 0 auto; padding: 20px; background: #0f1419; color: #fff; }
        h1, h2 { color: #00d4aa; }
        .card { background: #1a1f26; border-radius: 14px; padding: 20px; margin: 16px 0; border: 1px solid #26313d; }
        .formula { background: #242d38; padding: 12px; border-radius: 8px; margin: 10px 0; font-family: monospace; color: #d7fff5; }
        input, select { background: #242d38; color: #fff; border: 1px solid #38444d; padding: 10px; border-radius: 6px; width: 100%; margin: 6px 0 14px; box-sizing: border-box; }
        label { color: #aab8c2; font-size: 12px; text-transform: uppercase; font-weight: bold; }
        button { background: #00d4aa; color: #000; padding: 12px 24px; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; width: 100%; }
        button:hover { background: #00e8bb; }
        pre { background: #050607; padding: 16px; border-radius: 8px; white-space: pre-wrap; overflow-x: auto; max-height: 760px; font-size: 12px; line-height: 1.35; }
        .grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
        .pill { background: #101820; padding: 10px; border-radius: 8px; border: 1px solid #26313d; }
        .small { color: #8899a6; font-size: 12px; }
        .warn { color: #ffcc66; }
    </style>
</head>
<body>
    <h1>Sports TC Dashboard</h1>
    <div class="formula">
        TC Core = player prop floor model only: PTS×0.85 | REB×0.80 | AST×0.75 | 3PM×0.70 | Q×0.55 | OUT=0<br>
        Separate totals models: Raw / NFRI / Pace / Full. These are not TC totals.
    </div>

    <div class="grid">
      <div class="pill"><b>TC Core</b><br><span class="small">Player prop floors</span></div>
      <div class="pill"><b>NFRI</b><br><span class="small">Health/location floor rating</span></div>
      <div class="pill"><b>Pace</b><br><span class="small">Tempo-adjusted totals</span></div>
      <div class="pill"><b>Backtest Seed</b><br><span class="small">Logs pending picks</span></div>
    </div>

    <div class="card">
        <form method="POST">
            <label>Sport</label>
            <select name="sport">
                <option value="WNBA" {{ 'selected' if sport=='WNBA' else '' }}>WNBA</option>
                <option value="NBA" {{ 'selected' if sport=='NBA' else '' }}>NBA</option>
            </select>
            <label>Game</label>
            <input type="text" name="game" value="{{ game }}" placeholder="DAL @ ATL">
            <label>Model for separate totals</label>
            <select name="model">
                <option value="tc" {{ 'selected' if model=='tc' else '' }}>TC Core only / Raw totals</option>
                <option value="nfri" {{ 'selected' if model=='nfri' else '' }}>NFRI totals</option>
                <option value="pace" {{ 'selected' if model=='pace' else '' }}>Pace totals</option>
                <option value="full" {{ 'selected' if model=='full' else '' }}>Full model totals</option>
            </select>
            <label>Market Total (optional, separate from TC)</label>
            <input type="text" name="total" value="{{ total }}" placeholder="172.5">
            <label>Market Spread (optional, separate from TC)</label>
            <input type="text" name="spread" value="{{ spread }}" placeholder="-5.5">
            <label>Mode</label>
            <select name="mode">
                <option value="report" {{ 'selected' if mode=='report' else '' }}>Generate Report</option>
                <option value="save" {{ 'selected' if mode=='save' else '' }}>Generate + Save Backtest Seed</option>
                <option value="diagnostics" {{ 'selected' if mode=='diagnostics' else '' }}>Run Diagnostics</option>
            </select>
            <button type="submit">Run Pipeline</button>
        </form>
    </div>

    {% if output %}
    <div class="card">
        <h2>Output</h2>
        <pre>{{ output }}</pre>
    </div>
    {% endif %}

    <p class="small warn">Use prop candidates as a watchlist only until sportsbook lines are checked. Team/game totals are model outputs, not TC prop floors.</p>
</body>
</html>
'''


def as_float(value):
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


@app.route('/', methods=['GET', 'POST'])
def home():
    sport = request.form.get('sport', 'WNBA') if request.method == 'POST' else 'WNBA'
    game = request.form.get('game', 'DAL @ ATL') if request.method == 'POST' else 'DAL @ ATL'
    total = request.form.get('total', '172.5') if request.method == 'POST' else '172.5'
    spread = request.form.get('spread', '-5.5') if request.method == 'POST' else '-5.5'
    model = request.form.get('model', 'tc') if request.method == 'POST' else 'tc'
    mode = request.form.get('mode', 'report') if request.method == 'POST' else 'report'
    output = ''

    if request.method == 'POST':
        cmd = ['python3', str(BASE_DIR / 'tc_pipeline.py')]
        if mode == 'diagnostics':
            cmd.append('--diagnostics')
        else:
            cmd += ['--sport', sport, '--game', game, '--model', model]
            if as_float(total) is not None:
                cmd += ['--total', str(as_float(total))]
            if as_float(spread) is not None:
                cmd += ['--spread', str(as_float(spread))]
            if mode == 'save':
                cmd.append('--save')
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(BASE_DIR), timeout=30)
        output = (result.stdout + result.stderr)[:35000]

    return render_template_string(HTML, sport=sport, game=game, total=total, spread=spread, model=model, mode=mode, output=output)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8507, debug=False)
