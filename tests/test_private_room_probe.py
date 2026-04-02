import importlib.util
import pathlib

MODULE_PATH = (
    pathlib.Path(__file__).resolve().parents[1] / 'tools' / 'proof' / 'private_room_probe.py'
)
SPEC = importlib.util.spec_from_file_location('private_room_probe', MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_ws_connect_target_preserves_logical_host_and_overrides_tcp_target() -> None:
    ws_target = MODULE.ws_connect_target(
        'http://100.68.237.47',
        'play.dental-school.education',
    )
    assert ws_target.room_host == 'play.dental-school.education'
    assert ws_target.tcp_host == '100.68.237.47'
    assert ws_target.tcp_port == 80


def test_ws_url_for_host_uses_room_host_for_websocket_authority() -> None:
    ws_url = MODULE.ws_url_for_host(
        'play.dental-school.education',
        'http://100.68.237.47',
        'room-123',
        'token-456',
    )
    assert ws_url == (
        'ws://play.dental-school.education/ws/rooms/room-123?player_token=token-456'
    )
