import asyncio
import selectors
import sys

from jonbet.service.polling_roulette import Polling
from jonbet.service.analytics_service import AnalyticsService
from jonbet.service.scenario_simulator import ScenarioSimulator
from jonbet.service.rule_engine import RuleEngine
from logger import AppLogger

logger = AppLogger.get_logger("Main")


async def run_polling():
    """Executa o polling de spins da roleta"""
    print("Iniciando polling de spins...")
    polling = Polling()
    await polling.process_spins()


async def run_analytics():
    print("\n" + "=" * 60)
    print("ANÁLISE ESTATÍSTICA DOS SPINS")
    print("=" * 60)

    analytics = AnalyticsService()
    await analytics.connect()

    try:
        print("\n📊 FREQUÊNCIA DE CORES")
        frequency = await analytics.get_color_frequency(1000)
        for color, stats in frequency.items():
            print(f"  {color}: {stats['count']} ({stats['percentage']:.2f}%)")

        print("\n🔥 NÚMEROS QUENTES E FRIOS")
        hot_cold = await analytics.get_hot_cold_numbers(1000)
        hot_list = [f"{h['roll']}({h['count']})" for h in hot_cold['hot']]
        cold_list = [f"{c['roll']}({c['count']})" for c in hot_cold['cold']]
        print(f"  Hot: {hot_list}")
        print(f"  Cold: {cold_list}")

        print("\n🔍 DETECÇÃO DE PADRÕES")
        green_6 = await analytics.detect_pattern_green_sequence(6)
        status = 'ATIVADO' if green_6.triggered else 'inativo'
        print(f"  6x VERDE seguidos: {status}")
        if green_6.triggered:
            print(f"    → Previsão: {green_6.next_prediction}")

    finally:
        await analytics.close()


async def run_simulations(show_details: bool = True):
    """Executa simulações de cenários"""
    print("\n" + "=" * 60)
    print("SIMULAÇÃO DE CENÁRIOS")
    print("=" * 60)

    simulator = ScenarioSimulator()
    await simulator.connect()

    try:
        # Lista de cenários para simular
        scenarios = [
            ("Branco após Branco", lambda: simulator.simulate_white_after_white()),
            ("Branco após Branco (Stop on Win)", lambda: simulator.simulate_white_after_white_stop_on_win()),
            ("Maior número de PRETOS em sequência", lambda: simulator.simulate_longest_black_streak()),
            ("Maior número de VERDE em sequência", lambda: simulator.simulate_longest_green_streak())
            # ("Preto após 6x Verde", lambda: simulator.simulate_black_after_6_green()),
            # ("Preto após 3x Branco", lambda: simulator.simulate_opposite_after_streak(0, 3, 2)),
            # ("Branco após 5x Preto", lambda: simulator.simulate_opposite_after_streak(2, 5, 0)),
            # ("Preto após 4x Verde", lambda: simulator.simulate_opposite_after_streak(1, 4, 2)),
        ]

        for name, scenario_fn in scenarios:
            result = await scenario_fn()
            simulator.print_result(result, show_bets=show_details)

        # Martingale
        print("\n" + "=" * 60)
        print("ESTRATÉGIA MARTINGALE")
        print("=" * 60)
        martingale_white = await simulator.simulate_martingale(0, max_doublings=5)
        simulator.print_result(martingale_white, show_bets=show_details)

    finally:
        await simulator.close()


async def run_rules_monitor():
    """Monitora regras em tempo real"""
    print("\n" + "=" * 60)
    print("MONITOR DE REGRAS EM TEMPO REAL")
    print("=" * 60)

    engine = RuleEngine()
    await engine.connect()

    try:
        while True:
            print(f"\n📡 Verificando regras...")
            triggers = await engine.evaluate_ruleses()
            engine.print_status()

            if not triggers:
                print("Aguardando próximos spins para ativar regras...\n")

            await asyncio.sleep(5)

    except KeyboardInterrupt:
        print("\nMonitor encerrado.")
    finally:
        await engine.close()


async def main():
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "poll":
            await run_polling()
        elif command == "analytics":
            await run_analytics()
        elif command == "simulate":
            await run_simulations()
        elif command == "rules":
            await run_rules_monitor()
        elif command == "all":
            await run_analytics()
            await run_simulations()
        else:
            print(f"Comando desconhecido: {command}")
            print("Use: poll | analytics | simulate | rules | all")
    else:
        print("Uso: python main.py [poll | analytics | simulate | rules | all]")
        print("Executando tudo...")
        await run_analytics()
        await run_simulations()


if __name__ == "__main__":
    asyncio.run(main(), loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()))
