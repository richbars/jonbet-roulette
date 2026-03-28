from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from jonbet.db.postgre_client import PostgresClient
from logger import AppLogger

logger = AppLogger.get_logger("RuleEngine")


@dataclass
class RuleTrigger:
    """Representa um trigger de regra ativado"""
    rule_name: str
    triggered_at: datetime
    spin_id: str
    predicted_color: int
    confidence: float = 1.0


class RuleEngine:
    """
    Motor de regras em tempo real para detecção de padrões durante o polling.

    Regras disponíveis:
    - white_after_white: Se saiu branco, próxima é branco
    - black_after_6_green: Após 6 verdes, próxima é preto
    - opposite_after_streak: Após N cores, aposta na oposta
    """

    COLOR_MAP = {0: "BRANCO", 1: "VERDE", 2: "PRETO"}
    OPPOSITE_COLORS = {0: 2, 1: 0, 2: 0}

    def __init__(self):
        self.postgres = PostgresClient()
        self.active_triggers: list[RuleTrigger] = []

    async def connect(self):
        await self.postgres.connect()

    async def close(self):
        await self.postgres.close()

    async def get_last_spins(self, n: int = 10) -> list[dict]:
        query = """
            SELECT id, created_at, color, roll
            FROM roulette_spins
            ORDER BY created_at DESC
            LIMIT %s
        """
        return await self.postgres.fetch_all(query, (n,))

    def check_white_after_white(self, last_color: int) -> Optional[RuleTrigger]:
        """
        Regra: Se saiu BRANCO, apostar no próximo para BRANCO
        """
        if last_color == 0:
            return RuleTrigger(
                rule_name="white_after_white",
                triggered_at=datetime.now(),
                spin_id="pending",
                predicted_color=0,
                confidence=0.33
            )
        return None

    def check_black_after_6_green(self, colors: list[int]) -> Optional[RuleTrigger]:
        """
        Regra: Após 6 VERDES seguidos, apostar no PRETO
        """
        if len(colors) >= 6:
            last_6 = colors[:6]
            if all(c == 1 for c in last_6):
                return RuleTrigger(
                    rule_name="black_after_6_green",
                    triggered_at=datetime.now(),
                    spin_id="pending",
                    predicted_color=2,
                    confidence=0.50
                )
        return None

    def check_streak_opposite(self, colors: list[int], streak_length: int = 3) -> Optional[RuleTrigger]:
        """
        Regra: Após N cores iguais, apostar na cor oposta
        """
        if len(colors) < streak_length:
            return None

        first_color = colors[0]
        streak = 0
        for c in colors:
            if c == first_color:
                streak += 1
            else:
                break

        if streak >= streak_length:
            opposite = self.OPPOSITE_COLORS.get(first_color, 0)
            return RuleTrigger(
                rule_name=f"streak_{streak_length}_opposite",
                triggered_at=datetime.now(),
                spin_id="pending",
                predicted_color=opposite,
                confidence=0.40
            )
        return None

    async def evaluate_ruleses(self) -> list[RuleTrigger]:
        """
        Avalia todas as regras com base nos últimos spins.
        Retorna lista de triggers ativados.
        """
        spins = await self.get_last_spins(10)
        colors = [s["color"] for s in spins]
        triggers = []

        if not colors:
            return triggers

        last_color = colors[0]

        # Regra 1: Branco após Branco
        trigger = self.check_white_after_white(last_color)
        if trigger:
            triggers.append(trigger)
            logger.info(f"🎯 REGRA ATIVADA: {trigger.rule_name} → APOSTAR EM {self.COLOR_MAP[trigger.predicted_color]}")

        # Regra 2: Preto após 6 Verdes
        trigger = self.check_black_after_6_green(colors)
        if trigger:
            triggers.append(trigger)
            logger.info(f"🎯 REGRA ATIVADA: {trigger.rule_name} → APOSTAR EM {self.COLOR_MAP[trigger.predicted_color]}")

        # Regra 3: Oposta após sequência de 3
        trigger = self.check_streak_opposite(colors, 3)
        if trigger:
            triggers.append(trigger)
            logger.info(f"🎯 REGRA ATIVADA: {trigger.rule_name} → APOSTAR EM {self.COLOR_MAP[trigger.predicted_color]}")

        # Regra 4: Oposta após sequência de 5
        trigger = self.check_streak_opposite(colors, 5)
        if trigger:
            triggers.append(trigger)
            logger.info(f"🎯 REGRA ATIVADA: {trigger.rule_name} → APOSTAR EM {self.COLOR_MAP[trigger.predicted_color]}")

        self.active_triggers = triggers
        return triggers

    def get_next_bet_recommendation(self) -> Optional[dict]:
        """
        Retorna recomendação de aposta baseada nas regras ativadas.
        """
        if not self.active_triggers:
            return None

        # Agrupa por cor prevista
        color_votes = {}
        for trigger in self.active_triggers:
            if trigger.predicted_color not in color_votes:
                color_votes[trigger.predicted_color] = []
            color_votes[trigger.predicted_color].append(trigger)

        # Retorna cor com mais votos
        best_color = max(color_votes.keys(), key=lambda c: len(color_votes[c]))
        triggers_for_color = color_votes[best_color]

        return {
            "bet_color": best_color,
            "bet_color_name": self.COLOR_MAP[best_color],
            "confidence": sum(t.confidence for t in triggers_for_color) / len(triggers_for_color),
            "rules_triggered": [t.rule_name for t in triggers_for_color],
            "total_triggers": len(triggers_for_color)
        }

    def print_status(self):
        """Imprime status atual das regras"""
        print("\n" + "=" * 40)
        print("MOTOR DE REGRAS - STATUS")
        print("=" * 40)
        if self.active_triggers:
            for trigger in self.active_triggers:
                print(f"  ✅ {trigger.rule_name}")
                print(f"     → Previsão: {self.COLOR_MAP.get(trigger.predicted_color, trigger.predicted_color)}")
                print(f"     → Confiança: {trigger.confidence:.0%}")
        else:
            print("  Nenhuma regra ativada no momento")
        print("=" * 40)

        recommendation = self.get_next_bet_recommendation()
        if recommendation:
            print(f"\n🎲 RECOMENDAÇÃO: APOSTAR EM {recommendation['bet_color_name']}")
            print(f"   Confiança: {recommendation['confidence']:.0%}")
            print(f"   Regras: {', '.join(recommendation['rules_triggered'])}")
