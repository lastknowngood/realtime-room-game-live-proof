import secrets
import threading
from dataclasses import dataclass, field

from .models import PlayerState, RoomState

WIN_LINES = (
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6),
)


class RoomError(Exception):
    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


@dataclass
class Room:
    room_id: str
    seats: dict[str, str] = field(default_factory=dict)
    board: list[str] = field(default_factory=lambda: [''] * 9)
    current_turn: str = 'X'
    winner: str | None = None
    draw: bool = False
    connected_tokens: set[str] = field(default_factory=set)

    def resolve_seat(self, player_token: str) -> str:
        for seat, token in self.seats.items():
            if token == player_token:
                return seat
        if 'X' not in self.seats:
            self.seats['X'] = player_token
            return 'X'
        if 'O' not in self.seats:
            self.seats['O'] = player_token
            return 'O'
        raise RoomError('room_full', 'room is already full')

    def connect(self, player_token: str) -> str:
        seat = self.resolve_seat(player_token)
        self.connected_tokens.add(player_token)
        return seat

    def disconnect(self, player_token: str) -> None:
        self.connected_tokens.discard(player_token)

    def make_move(self, player_token: str, cell_index: int) -> None:
        seat = self.resolve_seat(player_token)
        if self.winner is not None or self.draw:
            raise RoomError('game_finished', 'game already finished')
        if seat != self.current_turn:
            raise RoomError('not_your_turn', 'move rejected because it is not your turn')
        if not 0 <= cell_index <= 8:
            raise RoomError('invalid_cell', 'cell index must be between 0 and 8')
        if self.board[cell_index]:
            raise RoomError('cell_occupied', 'selected cell is already occupied')
        self.board[cell_index] = seat
        self._advance_game()

    def _advance_game(self) -> None:
        for a, b, c in WIN_LINES:
            mark = self.board[a]
            if mark and mark == self.board[b] == self.board[c]:
                self.winner = mark
                return
        if all(self.board):
            self.draw = True
            return
        self.current_turn = 'O' if self.current_turn == 'X' else 'X'

    def snapshot_for(self, player_token: str | None) -> RoomState:
        your_seat = None
        if player_token is not None:
            for seat, token in self.seats.items():
                if token == player_token:
                    your_seat = seat
                    break
        return RoomState(
            room_id=self.room_id,
            board=list(self.board),
            current_turn=self.current_turn,
            winner=self.winner,
            draw=self.draw,
            your_seat=your_seat,
            players={
                'X': PlayerState(
                    occupied='X' in self.seats,
                    connected=self.seats.get('X') in self.connected_tokens,
                ),
                'O': PlayerState(
                    occupied='O' in self.seats,
                    connected=self.seats.get('O') in self.connected_tokens,
                ),
            },
            connection_count=len(self.connected_tokens),
        )


def generate_room_id() -> str:
    return secrets.token_hex(16)


class RoomStore:
    def __init__(self) -> None:
        self._rooms: dict[str, Room] = {}
        self._lock = threading.Lock()

    def create_room(self, creator_token: str) -> RoomState:
        with self._lock:
            room = Room(room_id=generate_room_id())
            room.connect(creator_token)
            self._rooms[room.room_id] = room
            return room.snapshot_for(creator_token)

    def get_snapshot(self, room_id: str, player_token: str) -> RoomState:
        with self._lock:
            room = self._rooms.get(room_id)
            if room is None:
                raise RoomError('room_not_found', 'room was not found')
            room.resolve_seat(player_token)
            return room.snapshot_for(player_token)

    def connect_player(self, room_id: str, player_token: str) -> RoomState:
        with self._lock:
            room = self._rooms.get(room_id)
            if room is None:
                raise RoomError('room_not_found', 'room was not found')
            room.connect(player_token)
            return room.snapshot_for(player_token)

    def disconnect_player(self, room_id: str, player_token: str) -> RoomState | None:
        with self._lock:
            room = self._rooms.get(room_id)
            if room is None:
                return None
            room.disconnect(player_token)
            return room.snapshot_for(player_token)

    def make_move(self, room_id: str, player_token: str, cell_index: int) -> RoomState:
        with self._lock:
            room = self._rooms.get(room_id)
            if room is None:
                raise RoomError('room_not_found', 'room was not found')
            room.make_move(player_token, cell_index)
            return room.snapshot_for(player_token)
