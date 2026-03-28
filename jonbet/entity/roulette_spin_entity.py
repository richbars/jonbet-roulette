from dataclasses import dataclass
from datetime import datetime


@dataclass
class RouletteSpinEntity:
    id: str
    created_at: datetime
    color: int
    roll: int
