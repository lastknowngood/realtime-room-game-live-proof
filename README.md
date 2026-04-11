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

Klarstellung: `lifecycle.mode: live` beschreibt hier die Proof-/Deploy-Contract-Klasse. Ob aus diesem Repo aktuell ein Dienst, DNS oder Host-Ressourcen retained sind, steht in den folgenden Bulletpoints und in den `notes` des Deploy-Contracts.

- der erste Realtime-/WSS-Proof auf `coolify-01` ist erfolgreich belegt
- `main` und `proof/realtime-room-game-live-proof-private-20260402-r1` sind
  nach GitHub publiziert
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

- erster gruener Proof-Ref:
  - `proof/realtime-room-game-live-proof-private-20260402-r1`
- belegter Proof-Claim:
  - single-instance browser room gameplay ueber HTTP(S)+WebSocket(S) hinter
    Coolify
  - shared authoritative state, turn enforcement, reload/resync und kurzer
    agent-only Public-Proof in zwei isolierten Browserkontexten
- gruene Evidence:
  - private HTTP-Readiness auf `http://play.dental-school.education`
  - privater browserloser Room-/WebSocket-Probe
  - Same-Ref-Redeploy auf demselben Commit
  - kurzer Public-Proof auf `https://play.dental-school.education`
  - browserloser `wss://`-Probe
  - Browser-Proof in zwei isolierten Kontexten:
    - Seat-Zuweisung `X` und `O`
    - illegaler Move sichtbar abgelehnt
    - Reload/Resync mid-round gruenerzwungen
    - konsistenter Winner-State in beiden Kontexten
- Cleanup-Endzustand:
  - `A` und `AAAA` fuer `play.dental-school.education` wieder entfernt
  - Coolify-App entfernt
  - forced-host negativ:
    - `HTTP 404`
    - `HTTPS 503`
- gefixter echter Defekt im Proof-Block:
  - das Produktionsimage enthielt zuerst keine WebSocket-Runtime-Dependency
  - Ursache:
    - `websockets` lag nur in Dev-Dependencies
  - Fix:
    - `websockets` in Runtime-Dependencies gezogen
  - kleine Regression-Checks:
    - Packaging-Test
    - Probe-Helfer-Test
- bewusste Nicht-Claims:
  - kein WebRTC
  - keine horizontale Realtime-Skalierung
  - keine Persistenz aktiver Spiele ueber Restart oder Redeploy
  - kein Twitch-/Low-Latency-Claim
  - kein retained Live-Dienst nach dem Proof
