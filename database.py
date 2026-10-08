"""SQLite locally; PostgreSQL when DATABASE_URL is set. Independent new table."""
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
URL = os.getenv('DATABASE_URL', '')

def connect():
    if URL:
        import psycopg2
        return psycopg2.connect(URL, connect_timeout=15)
    db = sqlite3.connect(os.getenv('SQLITE_PATH', str(Path(__file__).with_name('smarttrash.db'))), timeout=30)
    db.execute('PRAGMA journal_mode=WAL')
    return db

def sql(text):
    return text.replace('?', '%s') if URL else text

def setup_database():
    with connect() as db:
        db.cursor().execute('CREATE TABLE IF NOT EXISTS smarttrash_v3_players (id TEXT PRIMARY KEY, data TEXT NOT NULL)')

def new_player():
    return {'name': 'Người chơi', 'score': 0, 'items': 0, 'games': {}, 'history': [], 'stats': {}, 'seen': {}}

@contextmanager
def player_transaction(pid):
    db = connect()
    try:
        cur = db.cursor()
        if not URL:
            cur.execute('BEGIN IMMEDIATE')
        cur.execute(sql('INSERT INTO smarttrash_v3_players (id,data) VALUES (?,?) ON CONFLICT(id) DO NOTHING'), (pid, json.dumps(new_player())))
        cur.execute(sql('SELECT data FROM smarttrash_v3_players WHERE id=?') + (' FOR UPDATE' if URL else ''), (pid,))
        player = json.loads(cur.fetchone()[0])
        yield player
        cur.execute(sql('UPDATE smarttrash_v3_players SET data=? WHERE id=?'), (json.dumps(player, ensure_ascii=False), pid))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def rankings(mode='all', sort='score'):
    db = connect()
    try:
        cur = db.cursor()
        cur.execute('SELECT data FROM smarttrash_v3_players')
        rows = []
        for (data,) in cur.fetchall():
            p = json.loads(data)
            stats = p['stats'].get(mode, {}) if mode != 'all' else {}
            rows.append({'name': p['name'], 'score': p['score'] if mode == 'all' else stats.get('score', 0),
                         'items': p['items'] if mode == 'all' else stats.get('items', 0),
                         'best': max([s.get('best', 0) for s in p['stats'].values()] or [0]) if mode == 'all' else stats.get('best', 0)})
        return sorted(rows, key=lambda p: (p['best'] if sort == 'streak' else p['score'], p['score']), reverse=True)[:50]
    finally:
        db.close()