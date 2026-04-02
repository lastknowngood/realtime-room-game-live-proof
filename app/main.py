import json

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, PlainTextResponse

from .build_info import get_build_revision
from .models import CreateRoomResponse, HealthzRecord, RoomState
from .store import RoomError, RoomStore

MARKER = 'REALTIME-ROOM-GAME-LIVE-PROOF OK'
PROJECT_NAME = 'realtime-room-game-live-proof'


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, dict[WebSocket, str]] = {}

    async def connect(self, room_id: str, websocket: WebSocket, player_token: str) -> None:
        await websocket.accept()
        self._connections.setdefault(room_id, {})[websocket] = player_token

    def disconnect(self, room_id: str, websocket: WebSocket) -> None:
        room_connections = self._connections.get(room_id)
        if room_connections is None:
            return
        room_connections.pop(websocket, None)
        if not room_connections:
            self._connections.pop(room_id, None)

    async def broadcast_room_state(self, room_id: str, store: RoomStore) -> None:
        for websocket, player_token in list(self._connections.get(room_id, {}).items()):
            room_state = store.get_snapshot(room_id, player_token)
            envelope = {'event': 'room_state', 'room_state': room_state.model_dump(mode='json')}
            await websocket.send_json(envelope)


def parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def build_room_html(room_id: str) -> str:
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="robots" content="noindex,nofollow,noarchive,noimageindex,nosnippet">
    <title>{PROJECT_NAME} room</title>
    <style>
      body {{
        font-family: Georgia, 'Times New Roman', serif;
        background: linear-gradient(145deg, #efe4d0, #f7f3ea);
        color: #211b14;
        margin: 0;
      }}
      main {{
        max-width: 900px;
        margin: 0 auto;
        padding: 2rem 1rem 3rem;
      }}
      .shell {{
        display: grid;
        gap: 1rem;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      }}
      .panel {{
        background: rgba(255, 252, 247, 0.92);
        border: 1px solid #c9b89b;
        border-radius: 18px;
        padding: 1rem;
        box-shadow: 0 10px 30px rgba(49, 31, 9, 0.08);
      }}
      .board {{
        display: grid;
        grid-template-columns: repeat(3, 90px);
        gap: 0.5rem;
        justify-content: center;
      }}
      button.cell {{
        width: 90px;
        height: 90px;
        font-size: 2rem;
        border-radius: 16px;
        border: 1px solid #8d6d48;
        background: #fffdfa;
      }}
      .banner {{
        min-height: 1.5rem;
        color: #8a1f11;
      }}
      code {{
        word-break: break-all;
      }}
    </style>
  </head>
  <body>
    <main>
      <h1>{MARKER}</h1>
      <p>Single-instance server-authoritative roomed WSS proof.</p>
      <div class="shell">
        <section class="panel">
          <h2>Room</h2>
          <p><strong>Room ID:</strong> <code id="room-id">{room_id}</code></p>
          <p><strong>Seat:</strong> <span id="seat">pending</span></p>
          <p><strong>Connection:</strong> <span id="connection">connecting</span></p>
          <p><strong>Current turn:</strong> <span id="turn">pending</span></p>
          <p><strong>Outcome:</strong> <span id="outcome">in progress</span></p>
          <p><strong>Share URL:</strong> <code id="share-url"></code></p>
          <p class="banner" id="error-banner"></p>
        </section>
        <section class="panel">
          <h2>Board</h2>
          <div class="board" id="board"></div>
        </section>
      </div>
    </main>
    <script>
      const roomId = {json.dumps(room_id)};
      const tokenKey = `realtime-room-game:${{roomId}}:player-token`;
      const urlState = new URL(window.location.href);
      const bootstrapToken = urlState.searchParams.get('bootstrap_token');
      let playerToken = window.sessionStorage.getItem(tokenKey);
      if (bootstrapToken) {{
        playerToken = bootstrapToken;
        window.sessionStorage.setItem(tokenKey, playerToken);
        urlState.searchParams.delete('bootstrap_token');
        window.history.replaceState(null, '', urlState.pathname);
      }} else if (!playerToken) {{
        playerToken = crypto.randomUUID();
        window.sessionStorage.setItem(tokenKey, playerToken);
      }}
      document.getElementById('share-url').textContent = window.location.href;

      const boardEl = document.getElementById('board');
      const seatEl = document.getElementById('seat');
      const connectionEl = document.getElementById('connection');
      const turnEl = document.getElementById('turn');
      const outcomeEl = document.getElementById('outcome');
      const errorBannerEl = document.getElementById('error-banner');
      let socket = null;

      function setBanner(message) {{
        errorBannerEl.textContent = message;
      }}

      function clearBanner() {{
        errorBannerEl.textContent = '';
      }}

      function render(state) {{
        seatEl.textContent = state.your_seat || 'spectator';
        turnEl.textContent = state.current_turn;
        if (state.winner) {{
          outcomeEl.textContent = `winner ${{state.winner}}`;
        }} else if (state.draw) {{
          outcomeEl.textContent = 'draw';
        }} else {{
          outcomeEl.textContent = 'in progress';
        }}

        boardEl.innerHTML = '';
        state.board.forEach((value, index) => {{
          const button = document.createElement('button');
          button.className = 'cell';
          button.type = 'button';
          button.textContent = value;
          button.addEventListener('click', () => {{
            clearBanner();
            if (!socket || socket.readyState !== WebSocket.OPEN) {{
              setBanner('websocket not connected');
              return;
            }}
            socket.send(JSON.stringify({{ action: 'make_move', cell_index: index }}));
          }});
          boardEl.appendChild(button);
        }});
      }}

      async function loadSnapshot() {{
        const response = await fetch(
          `/api/rooms/${{roomId}}?player_token=${{encodeURIComponent(playerToken)}}`
        );
        if (!response.ok) {{
          const payload = await response.json().catch(() => ({{ detail: response.statusText }}));
          throw new Error(payload.detail || 'snapshot_failed');
        }}
        render(await response.json());
      }}

      function connectSocket() {{
        const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        socket = new WebSocket(`${{protocol}}://${{window.location.host}}/ws/rooms/${{roomId}}?player_token=${{encodeURIComponent(playerToken)}}`);
        socket.addEventListener('open', () => {{
          connectionEl.textContent = 'connected';
          clearBanner();
        }});
        socket.addEventListener('close', () => {{
          connectionEl.textContent = 'disconnected';
        }});
        socket.addEventListener('message', (event) => {{
          const payload = JSON.parse(event.data);
          if (payload.event === 'room_state' && payload.room_state) {{
            render(payload.room_state);
            clearBanner();
            return;
          }}
          if (payload.event === 'error') {{
            setBanner(payload.message || payload.error_code || 'room_error');
          }}
        }});
      }}

      loadSnapshot().then(connectSocket).catch((error) => {{
        connectionEl.textContent = 'error';
        setBanner(error.message);
      }});
    </script>
  </body>
</html>"""


def create_app(*, store: RoomStore | None = None, proof_mode: bool | None = None) -> FastAPI:
    selected_store = store or RoomStore()
    selected_proof_mode = proof_mode if proof_mode is not None else parse_bool(None, default=False)
    build_revision = get_build_revision()
    connections = ConnectionManager()
    app = FastAPI(title=PROJECT_NAME)

    @app.middleware('http')
    async def add_anti_indexing_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers['X-Robots-Tag'] = (
            'noindex, nofollow, noarchive, noimageindex, nosnippet'
        )
        return response

    @app.get('/healthz', response_model=HealthzRecord)
    def healthz() -> HealthzRecord:
        return HealthzRecord(
            status='ok',
            project=PROJECT_NAME,
            build_revision=build_revision,
            proof_mode=selected_proof_mode,
        )

    @app.get('/robots.txt', response_class=PlainTextResponse)
    def robots_txt() -> PlainTextResponse:
        return PlainTextResponse('User-agent: *\nDisallow: /\n')

    @app.get('/', response_class=HTMLResponse)
    def index() -> HTMLResponse:
        return HTMLResponse(
            f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="robots" content="noindex,nofollow,noarchive,noimageindex,nosnippet">
    <title>{PROJECT_NAME}</title>
  </head>
  <body>
    <main>
      <h1>{MARKER}</h1>
      <p>Single-instance browser room game proof.</p>
      <button id="create-room" type="button">Create Room</button>
      <p id="room-url"></p>
    </main>
    <script>
      const button = document.getElementById('create-room');
      const roomUrl = document.getElementById('room-url');
      button.addEventListener('click', async () => {{
        const token = crypto.randomUUID();
        const response = await fetch(`/api/rooms?player_token=${{encodeURIComponent(token)}}`, {{
          method: 'POST'
        }});
        const payload = await response.json();
        window.sessionStorage.setItem(
          `realtime-room-game:${{payload.room_id}}:player-token`,
          token
        );
        roomUrl.textContent = payload.room_url;
        const creatorUrl = `${{payload.room_url}}?bootstrap_token=${{encodeURIComponent(token)}}`;
        window.location.href = creatorUrl;
      }});
    </script>
  </body>
</html>"""
        )

    @app.post('/api/rooms', response_model=CreateRoomResponse)
    def create_room(player_token: str = Query(..., min_length=1)) -> CreateRoomResponse:
        room_state = selected_store.create_room(player_token)
        return CreateRoomResponse(
            room_id=room_state.room_id,
            room_url=f'/rooms/{room_state.room_id}',
        )

    @app.get('/rooms/{room_id}', response_class=HTMLResponse)
    def room_shell(room_id: str) -> HTMLResponse:
        return HTMLResponse(build_room_html(room_id))

    @app.get('/api/rooms/{room_id}', response_model=RoomState)
    def room_snapshot(room_id: str, player_token: str = Query(..., min_length=1)) -> RoomState:
        try:
            return selected_store.get_snapshot(room_id, player_token)
        except RoomError as exc:
            status = 404 if exc.error_code == 'room_not_found' else 409
            raise HTTPException(status_code=status, detail=exc.error_code) from exc

    @app.websocket('/ws/rooms/{room_id}')
    async def room_socket(
        websocket: WebSocket,
        room_id: str,
        player_token: str = Query(...),
    ) -> None:
        try:
            snapshot = selected_store.connect_player(room_id, player_token)
        except RoomError as exc:
            await websocket.accept()
            await websocket.send_json(
                {'event': 'error', 'error_code': exc.error_code, 'message': exc.message}
            )
            await websocket.close(code=1008)
            return

        await connections.connect(room_id, websocket, player_token)
        await websocket.send_json(
            {'event': 'room_state', 'room_state': snapshot.model_dump(mode='json')}
        )
        await connections.broadcast_room_state(room_id, selected_store)

        try:
            while True:
                payload = await websocket.receive_json()
                if payload.get('action') != 'make_move':
                    await websocket.send_json(
                        {
                            'event': 'error',
                            'error_code': 'unsupported_action',
                            'message': 'unsupported action',
                        }
                    )
                    continue
                try:
                    selected_store.make_move(
                        room_id,
                        player_token,
                        int(payload.get('cell_index')),
                    )
                except (TypeError, ValueError):
                    await websocket.send_json(
                        {
                            'event': 'error',
                            'error_code': 'invalid_cell',
                            'message': 'invalid cell index',
                        }
                    )
                    continue
                except RoomError as exc:
                    await websocket.send_json(
                        {'event': 'error', 'error_code': exc.error_code, 'message': exc.message}
                    )
                    continue
                await connections.broadcast_room_state(room_id, selected_store)
        except WebSocketDisconnect:
            connections.disconnect(room_id, websocket)
            snapshot = selected_store.disconnect_player(room_id, player_token)
            if snapshot is not None:
                await connections.broadcast_room_state(room_id, selected_store)

    return app
