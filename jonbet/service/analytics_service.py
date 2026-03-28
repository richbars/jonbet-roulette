from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from collections import defaultdict

from jonbet.db.postgre_client import PostgresClient
from jonbet.schema.roulette_spin_schema import RouletteSpinSchema
from logger import AppLogger

logger = AppLogger.get_logger("AnalyticsService")


@dataclass
class PatternResult:
    """Resultado da detecção de um padrão"""
    pattern_name: str
    triggered: bool
    last_occurrence: Optional[datetime] = None
    occurrences_count: int = 0
    next_prediction: Optional[str] = None
    confidence: float = 0.0


@dataclass
class SimulationResult:
    """Resultado da simulação de uma estratégia"""
    strategy_name: str
    total_spins: int = 0
    total_bets: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    profit: float = 0.0
    roi: float = 0.0


class AnalyticsService:

    COLOR_MAP = {0: "BRANCO", 1: "VERDE", 2: "PRETO"}

    def __init__(self):
        self.postgres = PostgresClient()

    async def connect(self):
        await self.postgres.connect()

    async def close(self):
        await self.postgres.close()

    async def get_all_spins(self, limit: int = 10000) -> list[dict]:
        query = """
            SELECT id, created_at, color, roll
            FROM roulette_spins
            ORDER BY created_at DESC
            LIMIT %s
        """
        return await self.postgres.fetch_all(query, (limit,))

    async def get_last_n_spins(self, n: int = 10) -> list[dict]:
        query = """
            SELECT id, created_at, color, roll
            FROM roulette_spins
            ORDER BY created_at DESC
            LIMIT %s
        """
        return await self.postgres.fetch_all(query, (n,))

    async def detect_pattern_green_sequence(self, sequence_length: int = 6) -> PatternResult:
        """
        Detecta se houve uma sequência de N verdes seguidos.
        Se detectado, prevê que a próxima será PRETO.
        """
        spins = await self.get_last_n_spins(sequence_length + 1)

        if len(spins) < sequence_length:
            return PatternResult(
                pattern_name=f"{sequence_length}x VERDE seguidos",
                triggered=False
            )

        colors = [s["color"] for s in spins[:sequence_length]]
        all_green = all(c == 1 for c in colors)

        if all_green:
            next_color = spins[sequence_length]["color"] if len(spins) > sequence_length else None
            hit = next_color == 2

            return PatternResult(
                pattern_name=f"{sequence_length}x VERDE seguidos",
                triggered=True,
                last_occurrence=spins[0]["created_at"],
                occurrences_count=1,
                next_prediction="PRETO (2)",
                confidence=1.0 if hit else 0.0
            )

        return PatternResult(
            pattern_name=f"{sequence_length}x VERDE seguidos",
            triggered=False
        )

    async def detect_pattern_color_streak(self, color: int, streak_length: int) -> PatternResult:
        """
        Detecta sequência de N cores iguais seguidas.
        """
        spins = await self.get_last_n_spins(streak_length + 1)

        if len(spins) < streak_length:
            return PatternResult(
                pattern_name=f"{streak_length}x {self.COLOR_MAP.get(color, color)} seguidos",
                triggered=False
            )

        colors = [s["color"] for s in spins[:streak_length]]
        all_same = all(c == color for c in colors)

        if all_same:
            next_color = spins[streak_length]["color"] if len(spins) > streak_length else None
            prediction = "oposta"

            return PatternResult(
                pattern_name=f"{streak_length}x {self.COLOR_MAP.get(color, color)} seguidos",
                triggered=True,
                last_occurrence=spins[0]["created_at"],
                occurrences_count=1,
                next_prediction=prediction,
                confidence=0.0
            )

        return PatternResult(
            pattern_name=f"{streak_length}x {self.COLOR_MAP.get(color, color)} seguidos",
            triggered=False
        )

    async def get_color_frequency(self, limit: int = 1000) -> dict:
        """Retorna frequência de cada cor nos últimos N spins"""
        spins = await self.get_all_spins(limit)

        frequency = defaultdict(int)
        for spin in spins:
            frequency[spin["color"]] += 1

        total = len(spins)
        return {
            self.COLOR_MAP.get(color, color): {
                "count": count,
                "percentage": (count / total * 100) if total > 0 else 0
            }
            for color, count in sorted(frequency.items())
        }

    async def simulate_strategy_white_after_white(self, limit: int = 1000) -> SimulationResult:
        """
        Simula estratégia: "Se saiu BRANCO, apostar no próximo para BRANCO"
        """
        spins = await self.get_all_spins(limit)
        spins.reverse()

        result = SimulationResult(strategy_name="BRANCO após BRANCO", total_spins=len(spins))

        for i in range(len(spins) - 1):
            current = spins[i]
            next_spin = spins[i + 1]

            if current["color"] == 0:
                result.total_bets += 1
                if next_spin["color"] == 0:
                    result.wins += 1
                else:
                    result.losses += 1

        if result.total_bets > 0:
            result.win_rate = result.wins / result.total_bets * 100
            result.profit = (result.wins * 2) - result.losses
            result.roi = (result.profit / result.total_bets) * 100

        return result

    async def simulate_strategy_opposite_after_streak(
        self, color: int, streak_length: int, bet_color: int, limit: int = 1000
    ) -> SimulationResult:
        """
        Simula estratégia: "Após N cores seguidas, apostar na cor oposta"

        Args:
            color: Cor da sequência (0=branco, 1=verde, 2=preto)
            streak_length: Tamanho da sequência necessária
            bet_color: Cor para apostar
            limit: Quantidade de spins para analisar
        """
        spins = await self.get_all_spins(limit)
        spins.reverse()

        result = SimulationResult(
            strategy_name=f"Oposta após {streak_length}x {self.COLOR_MAP.get(color, color)}"
        )
        result.total_spins = len(spins)

        consecutive = 0
        for i in range(len(spins)):
            if spins[i]["color"] == color:
                consecutive += 1
                if consecutive == streak_length and i < len(spins) - 1:
                    result.total_bets += 1
                    next_spin = spins[i + 1]
                    if next_spin["color"] == bet_color:
                        result.wins += 1
                    else:
                        result.losses += 1
                    consecutive = 0
            else:
                consecutive = 0

        if result.total_bets > 0:
            result.win_rate = result.wins / result.total_bets * 100
            result.profit = (result.wins * 2) - result.losses
            result.roi = (result.profit / result.total_bets) * 100

        return result

    async def get_hot_cold_numbers(self, limit: int = 1000) -> dict:
        """Retorna números que mais saíram (hot) e menos saíram (cold)"""
        spins = await self.get_all_spins(limit)

        roll_frequency = defaultdict(int)
        for spin in spins:
            roll_frequency[spin["roll"]] += 1

        sorted_rolls = sorted(roll_frequency.items(), key=lambda x: x[1], reverse=True)

        return {
            "hot": [{"roll": roll, "count": count} for roll, count in sorted_rolls[:5]],
            "cold": [{"roll": roll, "count": count} for roll, count in sorted_rolls[-5:]]
        }

    async def get_pattern_history(self, pattern_type: str, limit: int = 1000) -> list[dict]:
        """
        Retorna histórico de ocorrências de um padrão específico.

        pattern_type: "green_6", "white_after_white", "streak_3", etc.
        """
        spins = await self.get_all_spins(limit)
        spins.reverse()

        occurrences = []

        if pattern_type == "green_6":
            consecutive_green = 0
            for i, spin in enumerate(spins):
                if spin["color"] == 1:
                    consecutive_green += 1
                    if consecutive_green == 6:
                        next_spin = spins[i + 1] if i < len(spins) - 1 else None
                        occurrences.append({
                            "index": i,
                            "created_at": spin["created_at"],
                            "next_color": next_spin["color"] if next_spin else None,
                            "next_roll": next_spin["roll"] if next_spin else None,
                            "hit": next_spin["color"] == 2 if next_spin else None
                        })
                        consecutive_green = 0
                else:
                    consecutive_green = 0

        return occurrences
