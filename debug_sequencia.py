"""
Script para debugar a sequência de cores e entender as apostas
"""
import asyncio
from jonbet.db.postgre_client import PostgresClient

COLOR_MAP = {0: "BRANCO", 1: "VERDE", 2: "PRETO"}


async def main():
    postgres = PostgresClient()
    await postgres.connect()

    # Pega últimos 50 spins
    spins = await postgres.fetch_all(
        "SELECT id, created_at, color, roll FROM roulette_spins ORDER BY created_at DESC LIMIT 50"
    )
    spins.reverse()  # Ordena cronologicamente

    print("=" * 70)
    print("SEQUÊNCIA DE CORES (últimos 50 spins)")
    print("=" * 70)

    # Imprime sequência
    sequencia = [s["color"] for s in spins]
    print("\nCores:", " → ".join(COLOR_MAP[c] for c in sequencia))

    print("\n" + "=" * 70)
    print("ANÁLISE: BRANCO após BRANCO")
    print("=" * 70)

    wins = 0
    losses = 0

    print(f"\n{'#':<4} {'ID':<20} {'Cor':<10} {'Próxima':<10} {'Resultado':<10}")
    print("-" * 70)

    for i, spin in enumerate(spins[:-1]):
        if spin["color"] == 0:  # Se é BRANCO
            proxima_cor = spins[i + 1]["color"]
            resultado = "✅ WIN" if proxima_cor == 0 else "❌ LOSS"

            if proxima_cor == 0:
                wins += 1
            else:
                losses += 1

            print(f"{i:<4} {spin['id']:<20} {'BRANCO':<10} {COLOR_MAP[proxima_cor]:<10} {resultado:<10}")

    print("-" * 70)
    print(f"TOTAL: {wins} wins, {losses} losses")
    if wins + losses > 0:
        win_rate = wins / (wins + losses) * 100
        print(f"WIN RATE: {win_rate:.2f}%")

    await postgres.close()


if __name__ == "__main__":
    asyncio.run(main())
