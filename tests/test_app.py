from fastapi.testclient import TestClient

from app.asgi import app
from app.store import generate_room_id


def create_room(client: TestClient, token: str) -> str:
    response = client.post('/api/rooms', params={'player_token': token})
    assert response.status_code == 200
    return response.json()['room_id']


def get_snapshot(client: TestClient, room_id: str, token: str):
    return client.get(f'/api/rooms/{room_id}', params={'player_token': token})


def test_healthz_and_root() -> None:
    client = TestClient(app)
    root = client.get('/')
    assert root.status_code == 200
    assert 'REALTIME-ROOM-GAME-LIVE-PROOF OK' in root.text
    assert root.headers['x-robots-tag'] == 'noindex, nofollow, noarchive, noimageindex, nosnippet'

    health = client.get('/healthz')
    assert health.status_code == 200
    assert health.json()['build_revision'] == 'development'


def test_room_create_join_and_room_full() -> None:
    client = TestClient(app)
    room_id = create_room(client, 'player-x')

    first = get_snapshot(client, room_id, 'player-x')
    assert first.status_code == 200
    assert first.json()['your_seat'] == 'X'

    second = get_snapshot(client, room_id, 'player-o')
    assert second.status_code == 200
    assert second.json()['your_seat'] == 'O'

    full = get_snapshot(client, room_id, 'spectator')
    assert full.status_code == 409
    assert full.json()['detail'] == 'room_full'


def test_turn_enforcement_duplicate_move_and_win_sequence() -> None:
    client = TestClient(app)
    room_id = create_room(client, 'player-x')
    get_snapshot(client, room_id, 'player-o')

    with client.websocket_connect(f'/ws/rooms/{room_id}?player_token=player-x') as ws_x:
        ws_x.receive_json()
        ws_x.receive_json()
        with client.websocket_connect(f'/ws/rooms/{room_id}?player_token=player-o') as ws_o:
            ws_o.receive_json()
            ws_x.receive_json()
            ws_o.receive_json()

            ws_o.send_json({'action': 'make_move', 'cell_index': 3})
            error = ws_o.receive_json()
            assert error['event'] == 'error'
            assert error['error_code'] == 'not_your_turn'

            ws_x.send_json({'action': 'make_move', 'cell_index': 0})
            latest_x = ws_x.receive_json()
            latest_o = ws_o.receive_json()
            assert latest_x['room_state']['your_seat'] == 'X'
            assert latest_o['room_state']['your_seat'] == 'O'
            assert latest_x['room_state']['board'][0] == 'X'
            assert latest_o['room_state']['board'][0] == 'X'

            ws_o.send_json({'action': 'make_move', 'cell_index': 3})
            ws_x.receive_json()
            ws_o.receive_json()

            ws_x.send_json({'action': 'make_move', 'cell_index': 0})
            occupied = ws_x.receive_json()
            assert occupied['error_code'] == 'cell_occupied'

            ws_x.send_json({'action': 'make_move', 'cell_index': 1})
            ws_x.receive_json()
            ws_o.receive_json()

            ws_o.send_json({'action': 'make_move', 'cell_index': 4})
            ws_x.receive_json()
            ws_o.receive_json()

            ws_x.send_json({'action': 'make_move', 'cell_index': 2})
            end_x = ws_x.receive_json()
            end_o = ws_o.receive_json()
            assert end_x['room_state']['winner'] == 'X'
            assert end_o['room_state']['winner'] == 'X'


def test_resync_for_same_token() -> None:
    client = TestClient(app)
    room_id = create_room(client, 'same-player')
    get_snapshot(client, room_id, 'other-player')

    with client.websocket_connect(f'/ws/rooms/{room_id}?player_token=same-player') as ws_x:
        ws_x.receive_json()
        ws_x.receive_json()
        with client.websocket_connect(f'/ws/rooms/{room_id}?player_token=other-player') as ws_o:
            ws_o.receive_json()
            ws_x.receive_json()
            ws_o.receive_json()
            ws_x.send_json({'action': 'make_move', 'cell_index': 0})
            ws_x.receive_json()
            ws_o.receive_json()

    resync = get_snapshot(client, room_id, 'same-player')
    assert resync.status_code == 200
    payload = resync.json()
    assert payload['your_seat'] == 'X'
    assert payload['board'][0] == 'X'


def test_room_ids_are_128_bit_hex_strings() -> None:
    room_id = generate_room_id()
    assert len(room_id) == 32
    int(room_id, 16)
