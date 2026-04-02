import argparse
import asyncio
import json
import uuid

import httpx
from websockets.asyncio.client import connect


def ws_url_from_base(base_url: str, room_id: str, token: str) -> str:
    http_scheme = 'https://' if base_url.startswith('https://') else 'http://'
    ws_scheme = 'wss://' if http_scheme == 'https://' else 'ws://'
    host = base_url.removeprefix(http_scheme).rstrip('/')
    return f'{ws_scheme}{host}/ws/rooms/{room_id}?player_token={token}'


async def expect_room_state(websocket) -> dict[str, object]:
    payload = json.loads(await websocket.recv())
    if payload.get('event') != 'room_state':
        raise RuntimeError(f'expected room_state, got {payload}')
    return payload['room_state']


async def expect_error(websocket, error_code: str) -> None:
    payload = json.loads(await websocket.recv())
    if payload.get('event') != 'error' or payload.get('error_code') != error_code:
        raise RuntimeError(f'expected error {error_code}, got {payload}')


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--host-header')
    args = parser.parse_args()

    headers = {}
    if args.host_header:
        headers['Host'] = args.host_header

    async with httpx.AsyncClient(
        base_url=args.base_url,
        headers=headers,
        follow_redirects=True,
        timeout=20.0,
    ) as client:
        root = await client.get('/')
        root.raise_for_status()
        if 'REALTIME-ROOM-GAME-LIVE-PROOF OK' not in root.text:
            raise RuntimeError('missing root marker')

        x_token = str(uuid.uuid4())
        o_token = str(uuid.uuid4())

        create_room = await client.post('/api/rooms', params={'player_token': x_token})
        create_room.raise_for_status()
        room_payload = create_room.json()
        room_id = room_payload['room_id']
        room_url = room_payload['room_url']
        if room_url != f'/rooms/{room_id}':
            raise RuntimeError(f'unexpected room_url: {room_url}')

        join_room = await client.get(f'/api/rooms/{room_id}', params={'player_token': o_token})
        join_room.raise_for_status()
        if join_room.json()['your_seat'] != 'O':
            raise RuntimeError('second player did not become O')

        room_shell = await client.get(room_url)
        room_shell.raise_for_status()
        if room_id not in room_shell.text:
            raise RuntimeError('room shell missing room id')

        async with connect(
            ws_url_from_base(args.base_url, room_id, x_token),
            additional_headers=headers,
        ) as ws_x:
            await expect_room_state(ws_x)
            await expect_room_state(ws_x)
            async with connect(
                ws_url_from_base(args.base_url, room_id, o_token),
                additional_headers=headers,
            ) as ws_o:
                await expect_room_state(ws_o)
                join_state_x = await expect_room_state(ws_x)
                join_state_o = await expect_room_state(ws_o)
                if join_state_x['your_seat'] != 'X' or join_state_o['your_seat'] != 'O':
                    raise RuntimeError(
                        f'unexpected seats after join: X={join_state_x} O={join_state_o}'
                    )

                await ws_o.send(json.dumps({'action': 'make_move', 'cell_index': 3}))
                await expect_error(ws_o, 'not_your_turn')

                for actor, cell_index in (
                    (ws_x, 0),
                    (ws_o, 3),
                    (ws_x, 1),
                    (ws_o, 4),
                    (ws_x, 2),
                ):
                    await actor.send(json.dumps({'action': 'make_move', 'cell_index': cell_index}))
                    state_x = await expect_room_state(ws_x)
                    state_o = await expect_room_state(ws_o)
                    if state_x['your_seat'] != 'X' or state_o['your_seat'] != 'O':
                        raise RuntimeError(
                            f'unexpected per-client seat broadcast: X={state_x} O={state_o}'
                        )
                    if state_x['board'] != state_o['board']:
                        raise RuntimeError('board drift across websocket clients')

                if state_x['winner'] != 'X':
                    raise RuntimeError(f'expected winner X, got {state_x}')

        resync = await client.get(f'/api/rooms/{room_id}', params={'player_token': x_token})
        resync.raise_for_status()
        snapshot = resync.json()
        if snapshot['your_seat'] != 'X' or snapshot['winner'] != 'X':
            raise RuntimeError(f'unexpected resync snapshot: {snapshot}')

    print(json.dumps({'status': 'ok', 'room_id': room_id}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
