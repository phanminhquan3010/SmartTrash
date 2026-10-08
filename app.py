import os
import random
import secrets
import time
from flask import Flask, jsonify, render_template, request, session
from database import new_player, player_transaction, rankings, setup_database
from generator import BINS, ITEMS, MODES, QUESTIONS, question
app = Flask(__name__)
if os.getenv('RENDER') and (not os.getenv('SECRET_KEY') or not os.getenv('DATABASE_URL')):
    raise RuntimeError('Set SECRET_KEY and DATABASE_URL on Render to preserve sessions and database.')
app.secret_key = os.getenv('SECRET_KEY', 'local-development-only-change-for-production')
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
                  SESSION_COOKIE_SECURE=bool(os.getenv('RENDER')), MAX_CONTENT_LENGTH=16384,
                  PERMANENT_SESSION_LIFETIME=60*60*24*365)
setup_database()

@app.get('/')
@app.get('/leaderboard')
@app.get('/guide')
@app.get('/quiz')
@app.get('/quick_sort')
@app.get('/true_false')
@app.get('/timed')
def home():
    return render_template('index.html', modes=MODES, bins=BINS)

@app.get('/health')
def health():
    return {'ok': True}

def view(p):
    result = {k: v for k, v in p.items() if k not in ('seen', 'games')}
    result['games'] = {}
    for mode, g in p['games'].items():
        public = {k: v for k, v in g.items() if k != 'ids'}
        if g['index'] < len(g['ids']):
            q = question(g['ids'][g['index']], mode, g['round'])
            q.pop('answer')
            public['question'] = q
        result['games'][mode] = public
    return result

@app.route('/api/game', methods=['GET', 'POST'])
def game():
    if 'pid' not in session:
        session['pid'] = secrets.token_urlsafe(32)
        session.permanent = True
    if request.method == 'POST' and request.headers.get('X-SmartTrash') != '1':
        return jsonify(error='Yêu cầu không hợp lệ'), 403
    data = request.get_json(silent=True) or {} if request.method == 'POST' else {}
    if not isinstance(data, dict):
        return jsonify(error='Yêu cầu không hợp lệ'), 400
    action = data.get('action', '')
    mode = data.get('mode', 'quiz')
    feedback = None
    with player_transaction(session['pid']) as p:
        if action == 'name':
            name = data.get('name', '')
            if not isinstance(name, str) or not 1 <= len(name.strip()) <= 40:
                return jsonify(error='Tên cần từ 1 đến 40 ký tự'), 400
            p['name'] = name.strip()
        elif action == 'reset':
            if data.get('confirm') is not True:
                return jsonify(error='Cần xác nhận đặt lại'), 400
            name = p['name']
            p.clear()
            p.update(new_player())
            p['name'] = name
        elif action in ('start', 'answer'):
            if mode not in MODES:
                return jsonify(error='Chế độ không hợp lệ'), 400
            config = MODES[mode]
            g = p['games'].get(mode)
            if action == 'start':
                if not g or g['index'] == len(g['ids']):
                    seen = set(p['seen'].get(mode, []))
                    candidates = [i for i in range(len(ITEMS)) if any(i*3+v not in seen for v in range(3))]
                    if len(candidates) < config['length']:
                        seen = set()
                        candidates = list(range(len(ITEMS)))
                    ids = [random.choice([i*3+v for v in range(3) if i*3+v not in seen]) for i in random.sample(candidates, config['length'])]
                    p['seen'][mode] = sorted(seen | set(ids))
                    g = {'ids': ids, 'index': 0, 'score': 0, 'correct': 0, 'streak': 0, 'best': 0,
                         'round': (g['round']+1 if g else 1), 'token': secrets.token_hex(16),
                         'deadline': time.time()+config['seconds'] if config['seconds'] else None}
                    p['games'][mode] = g
            else:
                if not g or g['index'] >= len(g['ids']) or data.get('token') != g['token']:
                    return jsonify(player=view(p), error='Câu đã đổi. Hãy thử lại.'), 409
                q = question(g['ids'][g['index']], mode, g['round'])
                late = bool(g['deadline'] and time.time() > g['deadline'])
                choice = data.get('answer')
                if choice is None and not late:
                    return jsonify(error='Chưa hết giờ'), 400
                correct = not late and choice == q['answer']
                g['index'] += 1
                g['streak'] = g['streak']+1 if correct else 0
                g['best'] = max(g['best'], g['streak'])
                g['correct'] += int(correct)
                g['score'] += 10*int(correct)
                p['score'] += 10*int(correct)
                p['items'] += 1
                stats = p['stats'].setdefault(mode, {'score': 0, 'items': 0, 'best': 0})
                stats['score'] += 10*int(correct)
                stats['items'] += 1
                stats['best'] = max(stats['best'], g['best'])
                feedback = {'correct': correct, 'late': late, 'answer': next(o['label'] for o in q['options'] if o['id'] == q['answer']), 'tip': q['tip']}
                g['token'] = secrets.token_hex(16)
                g['deadline'] = time.time()+config['seconds'] if config['seconds'] and g['index'] < len(g['ids']) else None
                if g['index'] == len(g['ids']):
                    p['history'] = ([{'mode': mode, 'score': g['score'], 'best': g['best'], 'time': time.time()}]+p['history'])[:30]
        result = view(p)
    return jsonify(player=result, feedback=feedback, ranking=rankings(request.args.get('mode', 'all'), request.args.get('sort', 'score')), serverTime=time.time())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=False)
