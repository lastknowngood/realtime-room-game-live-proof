# realtime-room-game-live-proof

Kleines separates Demo-Repo fuer den ersten browserbasierten Realtime-/
Online-Spiel-Pfad auf `coolify-01`.

## Charakter

- `lifecycle.mode: live`
- stateless
- single-instance
- server-authoritative Zwei-Spieler-Room-Game
- Vanilla-JS-Browserclient plus FastAPI-WebSocket-Backend
- `operations.backup_class: stateless`
- Proof-Hostname: `play.dental-school.education`
- Default-Endzustand des ersten Public-Proofs: Cleanup nach Evidence

## Aktueller Zustand

- das Repo ist lokal angelegt
- Runtime, Contract und privater Probe-Helfer sind vorhanden
- der erste Proof-Ref ist noch nicht publiziert
- es gibt aktuell keinen Live-Dienst aus diesem Repo auf `coolify-01`
- `play.dental-school.education` hat aktuell oeffentlich weder `A` noch `AAAA`
- dieses Repo fuehrt bewusst keine Datenbank, keinen Object Storage und keine
  Runtime-Secrets ein

## Lokale Entwicklung

Voraussetzungen:

- Python `3.12`
- `uv`

Schnellstart:

```powershell
uv sync
uv run pytest --cov=app
uv run ruff check .
uv run pyright
```

Lokaler App-Start:

```powershell
uv run uvicorn app.asgi:app --host 127.0.0.1 --port 8000
```

Project-Closeout:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File tools/repo/check-project-closeout.ps1
git status --short --ignored
```

## Laufzeitverhalten

- `GET /` liefert Marker, Anti-Indexing und einen kleinen Browserclient
- `POST /api/rooms` erzeugt einen neuen unlistbaren Room
- `GET /rooms/{room_id}` bootstrappt im Browser einen anonymen `player_token`
  in `sessionStorage`, wenn noch keiner existiert
- `GET /api/rooms/{room_id}?player_token=...` liefert Snapshot fuer Initial-
  Render und Resync
- `/ws/rooms/{room_id}?player_token=...` traegt `room_state`-Snapshots und
  `error`-Events
- der erste Spieler wird `X`, der zweite `O`, weitere Joiner erhalten
  `room_full`
- `GET /healthz` read-backt Status und `build_revision`
- sichtbarer Root-Marker:
  - `REALTIME-ROOM-GAME-LIVE-PROOF OK`

## Proof-Status

- lokaler Code- und Testpfad ist angelegt, aber noch nicht gruenerzwungen
- der geplante erste Proof-Ref ist:
  - `proof/realtime-room-game-live-proof-private-20260402-r1`
- beabsichtigter Proof-Claim:
  - single-instance browser room gameplay ueber HTTP(S)+WebSocket(S) hinter
    Coolify
  - shared authoritative state, turn enforcement, reload/resync und kurzer
    agent-only Public-Proof in zwei isolierten Browserkontexten
- bewusste Nicht-Claims:
  - kein WebRTC
  - keine horizontale Realtime-Skalierung
  - keine Persistenz aktiver Spiele ueber Restart oder Redeploy
  - kein Twitch-/Low-Latency-Claim
  - kein retained Live-Dienst nach dem Proof
