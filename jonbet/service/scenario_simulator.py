from dataclasses import dataclass, field
from typing import Callable, Optional
from datetime import datetime

from jonbet.db.postgre_client import PostgresClient
from logger import AppLogger

logger = AppLogger.get_logger("ScenarioSimulator")


@dataclass
class Bet:
    """Representa uma aposta feita"""
    spin_id: str
    bet_color: int
    result_color: int
    won: bool
    amount: float = 1.0


@dataclass
class ScenarioResult:
    """Resultado da simulação de um cenário"""
    scenario_name: str
    description: str
    total_spins_analyzed: int = 0
    total_bets: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    total_profit: float = 0.0
    roi_percentage: float = 0.0
    max_win_streak: int = 0
    max_loss_streak: int = 0
    bets: list[Bet] = field(default_factory=list)


class ScenarioSimulator:

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
            ORDER BY created_at ASC
            LIMIT %s
        """
        return await self.postgres.fetch_all(query, (limit,))

    def simulate(
        self,
        spins: list[dict],
        trigger_condition: Callable[[list[dict], int], bool],
        bet_color: int,
        scenario_name: str,
        description: str
    ) -> ScenarioResult:
        """
        Simula um cenário com base em uma condição de trigger.

        Args:
            spins: Lista de spins históricos (ordenados por tempo)
            trigger_condition: Função que recebe (spins, index) e retorna True se deve apostar
            bet_color: Cor para apostar quando o trigger for ativado (0=branco, 1=verde, 2=preto)
            scenario_name: Nome do cenário
            description: Descrição do cenário

        Returns:
            ScenarioResult com estatísticas da simulação
        """
        result = ScenarioResult(
            scenario_name=scenario_name,
            description=description,
            total_spins_analyzed=len(spins)
        )

        current_win_streak = 0
        current_loss_streak = 0

        for i in range(len(spins)):
            if not trigger_condition(spins, i):
                continue

            if i >= len(spins) - 1:
                break

            current_spin = spins[i]
            next_spin = spins[i + 1]

            bet = Bet(
                spin_id=current_spin["id"],
                bet_color=bet_color,
                result_color=next_spin["color"],
                won=(next_spin["color"] == bet_color)
            )

            result.bets.append(bet)
            result.total_bets += 1

            if bet.won:
                result.wins += 1
                current_win_streak += 1
                current_loss_streak = 0
            else:
                result.losses += 1
                current_loss_streak += 1
                current_win_streak = 0

            result.max_win_streak = max(result.max_win_streak, current_win_streak)
            result.max_loss_streak = max(result.max_loss_streak, current_loss_streak)

        if result.total_bets > 0:
            result.win_rate = (result.wins / result.total_bets) * 100
            result.total_profit = (result.wins * 2) - result.losses
            result.roi_percentage = (result.total_profit / result.total_bets) * 100

        return result

    async def simulate_white_after_white(self, limit: int = 10000) -> ScenarioResult:
        """
        Cenário: Se saiu BRANCO, apostar no próximo para BRANCO
        """
        spins = await self.get_all_spins(limit)

        def trigger(spins: list[dict], index: int) -> bool:
            return spins[index]["color"] == 0

        return self.simulate(
            spins=spins,
            trigger_condition=trigger,
            bet_color=0,
            scenario_name="BRANCO após BRANCO",
            description="Sempre que sair BRANCO (0), apostar que o próximo será BRANCO"
        )

    async def simulate_longest_black_streak(self, limit: int = 10000) -> ScenarioResult:
        """Analisa o maior streak consecutivo de PRETO (2)"""
        spins = await self.get_all_spins(limit)
        spins.reverse()

        longest_streak = 0
        current_streak = 0
        start_index = None
        end_index = None
        temp_start = None

        for i, spin in enumerate(spins):
            if spin["color"] == 2:
                current_streak += 1
                if temp_start is None:
                    temp_start = i
                if current_streak > longest_streak:
                    longest_streak = current_streak
                    start_index = temp_start
                    end_index = i
            else:
                current_streak = 0
                temp_start = None

        return ScenarioResult(
            scenario_name="Maior sequência de PRETO",
            description="Analisa o maior streak consecutivo de PRETO (2)",
            total_spins_analyzed=len(spins),
            total_bets=0,
            wins=0,
            losses=0,
            max_win_streak=longest_streak,
            bets=[]
        )

    async def simulate_longest_green_streak(self, limit: int = 10000) -> ScenarioResult:
        """Analisa o maior streak consecutivo de VERDE (1)"""
        spins = await self.get_all_spins(limit)
        spins.reverse()

        longest_streak = 0
        current_streak = 0
        start_index = None
        end_index = None
        temp_start = None

        for i, spin in enumerate(spins):
            if spin["color"] == 1:
                current_streak += 1
                if temp_start is None:
                    temp_start = i
                if current_streak > longest_streak:
                    longest_streak = current_streak
                    start_index = temp_start
                    end_index = i
            else:
                current_streak = 0
                temp_start = None

        return ScenarioResult(
            scenario_name="Maior sequência de VERDE",
            description="Analisa o maior streak consecutivo de VERDE (1)",
            total_spins_analyzed=len(spins),
            total_bets=0,
            wins=0,
            losses=0,
            max_win_streak=longest_streak,
            bets=[]
        )


    async def simulate_white_after_white_stop_on_win(self, limit: int = 10000) -> ScenarioResult:
        """
        Cenário: Se saiu BRANCO, apostar no próximo para BRANCO.
        Se ganhar (veio BRANCO), PARA e só volta a apostar após sair cor diferente.

        Estratégia: Saiu BRANCO → Entra no próximo para BRANCO → Se ganhou, para e espera sair outra cor
        """
        spins = await self.get_all_spins(limit)

        result = ScenarioResult(
            scenario_name="BRANCO após BRANCO (Stop on Win)",
            description="Saiu BRANCO → aposta no próximo BRANCO → Se ganhar, PARA e espera sair cor diferente",
            total_spins_analyzed=len(spins)
        )

        current_win_streak = 0
        current_loss_streak = 0
        is_waiting_non_white = False  # True após ganhar, esperando sair cor != branco

        for i in range(len(spins) - 1):
            current_spin = spins[i]
            next_spin = spins[i + 1]

            # Se está esperando sair cor diferente de branco, pula
            if is_waiting_non_white:
                if current_spin["color"] != 0:
                    # Saiu cor diferente, pode voltar a apostar
                    is_waiting_non_white = False
                else:
                    # Ainda é branco, continua esperando
                    continue

            # Trigger: saiu branco, aposta no próximo
            if current_spin["color"] == 0:
                bet = Bet(
                    spin_id=current_spin["id"],
                    bet_color=0,
                    result_color=next_spin["color"],
                    won=(next_spin["color"] == 0)
                )

                result.bets.append(bet)
                result.total_bets += 1

                if bet.won:
                    result.wins += 1
                    current_win_streak += 1
                    current_loss_streak = 0
                    # Ganhou → PARA e espera sair cor diferente de branco
                    is_waiting_non_white = True
                else:
                    result.losses += 1
                    current_loss_streak += 1
                    current_win_streak = 0
                    # Perdeu → continua apostando se sair branco novamente

                result.max_win_streak = max(result.max_win_streak, current_win_streak)
                result.max_loss_streak = max(result.max_loss_streak, current_loss_streak)

        if result.total_bets > 0:
            result.win_rate = (result.wins / result.total_bets) * 100
            result.total_profit = (result.wins * 2) - result.losses
            result.roi_percentage = (result.total_profit / result.total_bets) * 100

        return result

    async def simulate_black_after_6_green(self, limit: int = 10000) -> ScenarioResult:
        """
        Cenário: Após 6 VERDES seguidos, apostar no PRETO
        """
        spins = await self.get_all_spins(limit)

        def trigger(spins: list[dict], index: int) -> bool:
            if index < 5:
                return False
            last_6 = [spins[i]["color"] for i in range(index - 5, index + 1)]
            return all(c == 1 for c in last_6)

        return self.simulate(
            spins=spins,
            trigger_condition=trigger,
            bet_color=2,
            scenario_name="PRETO após 6x VERDE",
            description="Após 6 giros VERDES (1) seguidos, apostar que o próximo será PRETO (2)"
        )

    async def simulate_opposite_after_streak(
        self, color: int, streak_length: int, bet_color: int, limit: int = 10000
    ) -> ScenarioResult:
        """
        Cenário genérico: Após N cores seguidas, apostar na cor oposta

        Args:
            color: Cor da sequência (0=branco, 1=verde, 2=preto)
            streak_length: Tamanho da sequência necessária
            bet_color: Cor para apostar
            limit: Quantidade de spins para analisar
        """
        spins = await self.get_all_spins(limit)

        def trigger(spins: list[dict], index: int) -> bool:
            if index < streak_length - 1:
                return False
            last_n = [spins[i]["color"] for i in range(index - streak_length + 1, index + 1)]
            return all(c == color for c in last_n)

        color_name = self.COLOR_MAP.get(color, str(color))
        bet_color_name = self.COLOR_MAP.get(bet_color, str(bet_color))

        return self.simulate(
            spins=spins,
            trigger_condition=trigger,
            bet_color=bet_color,
            scenario_name=f"{bet_color_name} após {streak_length}x {color_name}",
            description=f"Após {streak_length} giros {color_name} seguidos, apostar em {bet_color_name}"
        )

    async def simulate_martingale(
        self,
        base_bet_color: int,
        max_doublings: int = 5,
        limit: int = 10000
    ) -> ScenarioResult:
        """
        Simula estratégia Martingale: dobra aposta após perder, volta ao base após ganhar.

        Args:
            base_bet_color: Cor base para apostar
            max_doublings: Quantidade máxima de dobras (limita prejuízo)
            limit: Spins para analisar
        """
        spins = await self.get_all_spins(limit)

        result = ScenarioResult(
            scenario_name=f"Martingale ({self.COLOR_MAP.get(base_bet_color, base_bet_color)})",
            description=f"Estratégia Martingale: dobra após perder, limita em {max_doublings} dobras",
            total_spins_analyzed=len(spins)
        )

        current_streak_loss = 0
        current_bet_amount = 1.0
        total_profit = 0.0

        for i in range(len(spins) - 1):
            current_spin = spins[i]
            next_spin = spins[i + 1]

            bet = Bet(
                spin_id=current_spin["id"],
                bet_color=base_bet_color,
                result_color=next_spin["color"],
                won=(next_spin["color"] == base_bet_color),
                amount=current_bet_amount
            )

            result.bets.append(bet)
            result.total_bets += 1

            if bet.won:
                result.wins += 1
                total_profit += current_bet_amount
                current_streak_loss = 0
                current_bet_amount = 1.0
            else:
                result.losses += 1
                total_profit -= current_bet_amount
                current_streak_loss += 1
                if current_streak_loss <= max_doublings:
                    current_bet_amount *= 2

        result.total_profit = total_profit
        if result.total_bets > 0:
            result.win_rate = (result.wins / result.total_bets) * 100
            result.roi_percentage = (total_profit / result.total_bets) * 100

        return result

    async def run_all_scenarios(self, limit: int = 10000) -> list[ScenarioResult]:
        """Executa todos os cenários disponíveis e retorna resultados"""
        scenarios = [
            await self.simulate_white_after_white(limit),
            await self.simulate_black_after_6_green(limit),
            await self.simulate_opposite_after_streak(0, 3, 2, limit),
            await self.simulate_opposite_after_streak(2, 5, 0, limit),
            await self.simulate_opposite_after_streak(1, 4, 0, limit),
            await self.simulate_martingale(0, 5, limit),
        ]
        return scenarios

    def print_result(self, result: ScenarioResult, show_bets: bool = False):
        """Imprime resultado formatado"""
        print(f"\n{'='*60}")
        print(f"CENÁRIO: {result.scenario_name}")
        print(f"DESCRIÇÃO: {result.description}")
        print(f"{'='*60}")
        print(f"Spins analisados: {result.total_spins_analyzed}")
        print(f"Total de apostas: {result.total_bets}")
        print(f"Vitórias: {result.wins} | Derrotas: {result.losses}")
        print(f"Win Rate: {result.win_rate:.2f}%")
        print(f"Lucro/Prejuízo: {result.total_profit:+.2f}")
        print(f"ROI: {result.roi_percentage:+.2f}%")
        print(f"Maior sequência de vitórias: {result.max_win_streak}")
        print(f"Maior sequência de derrotas: {result.max_loss_streak}")
        print(f"{'='*60}")

        if show_bets and result.bets:
            print("\n📋 DETALHE DAS APOSTAS:")
            print(f"{'#':<4} {'Spin ID':<20} {'Aposta':<10} {'Resultado':<10} {'Próximo':<10} {'Status':<8}")
            print("-" * 70)
            for idx, bet in enumerate(result.bets[:50], 1):  # Mostra até 50 primeiras
                status = "✅ WIN" if bet.won else "❌ LOSS"
                print(f"{idx:<4} {bet.spin_id:<20} {self.COLOR_MAP.get(bet.bet_color, bet.bet_color):<10} {self.COLOR_MAP.get(bet.result_color, bet.result_color):<10} {self.COLOR_MAP.get(bet.result_color, bet.result_color):<10} {status:<8}")
            if len(result.bets) > 50:
                print(f"... e mais {len(result.bets) - 50} apostas")
