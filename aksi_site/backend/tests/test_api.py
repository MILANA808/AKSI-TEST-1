import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[2]))

from backend.app import app, init_db  # noqa: E402


def test_health():
    init_db()
    client = TestClient(app)
    r = client.get('/health')
    assert r.status_code == 200
    assert r.json()['status'] == 'ok'


def test_notes_and_todos_and_export():
    init_db()
    client = TestClient(app)

    note = client.post('/api/notes', json={'text': 'тест заметка'})
    assert note.status_code == 200

    todo = client.post('/api/todos', json={'title': 'тест задача'})
    assert todo.status_code == 200
    todo_id = todo.json()['id']

    upd = client.patch(f'/api/todos/{todo_id}', json={'done': True})
    assert upd.status_code == 200
    assert upd.json()['done'] is True

    export = client.get('/api/export')
    assert export.status_code == 200
    payload = export.json()
    assert 'notes' in payload
    assert 'todos' in payload
