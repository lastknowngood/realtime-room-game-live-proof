from pydantic import BaseModel


class PlayerState(BaseModel):
    occupied: bool
    connected: bool


class RoomState(BaseModel):
    room_id: str
    board: list[str]
    current_turn: str
    winner: str | None
    draw: bool
    your_seat: str | None
    players: dict[str, PlayerState]
    connection_count: int


class CreateRoomResponse(BaseModel):
    room_id: str
    room_url: str


class HealthzRecord(BaseModel):
    status: str
    project: str
    build_revision: str
    proof_mode: bool
