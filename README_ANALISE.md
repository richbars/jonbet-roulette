# Análise e Simulação de Cenários - Roleta

Este módulo fornece ferramentas para análise estatística, simulação de estratégias e detecção de padrões nos spins da roleta.

## Estrutura de Cores

```
0 = BRANCO
1 = VERDE
2 = PRETO
```

## Comandos Disponíveis

### 1. Coletar Spins (Polling)
```bash
python main.py poll
```
Inicia o polling contínuo que busca spins da API e salva no banco de dados PostgreSQL.

### 2. Análise Estatística
```bash
python main.py analytics
```
Exibe:
- Frequência de cada cor
- Números quentes (mais saíram) e frios (menos saíram)
- Detecção de padrões atuais

### 3. Simulação de Cenários
```bash
python main.py simulate
```
Simula estratégias históricas:
- **Branco após Branco**: Sempre que saiu branco, aposta no próximo branco
- **Preto após 6x Verde**: Após 6 verdes seguidos, aposta no preto
- **Preto após 3x Branco**: Após 3 brancos, aposta no preto
- **Branco após 5x Preto**: Após 5 pretos, aposta no branco
- **Martingale**: Dobra aposta após perder

### 4. Monitor de Regras em Tempo Real
```bash
python main.py rules
```
Monitora os últimos spins e ativa regras quando padrões são detectados.

### 5. Executar Tudo
```bash
python main.py all
```
Roda análise + simulações.

---

## Estratégias Implementadas

### Regra: Branco após Branco
**Descrição**: Sempre que sair BRANCO (0), apostar que o próximo será BRANCO.

### Regra: Preto após 6 Verdes
**Descrição**: Após 6 giros VERDES (1) seguidos, apostar que o próximo será PRETO (2).

### Regra: Oposta após Sequência
**Descrição**: Após N cores iguais seguidas, apostar na cor oposta.

### Estratégia Martingale
**Descrição**: Dobra o valor da aposta após cada perda, volta ao valor base após ganhar.
**Limite**: Máximo de 5 dobras consecutivas.

---

## Como Adicionar Nova Regra

No arquivo `jonbet/service/rule_engine.py`, adicione um método:

```python
def check_minha_regra(self, colors: list[int]) -> Optional[RuleTrigger]:
    """
    Minha nova regra personalizada
    """
    # Lógica de detecção
    if condicao_ativada:
        return RuleTrigger(
            rule_name="minha_regra",
            triggered_at=datetime.now(),
            spin_id="pending",
            predicted_color=2,  # Cor prevista
            confidence=0.75
        )
    return None
```

E registre no método `evaluate_ruleses`:
```python
trigger = self.check_minha_regra(colors)
if trigger:
    triggers.append(trigger)
```

---

## Como Adicionar Nova Simulação

No arquivo `jonbet/service/scenario_simulator.py`, adicione um método:

```python
async def simulate_minha_estrategia(self, limit: int = 10000) -> ScenarioResult:
    """
    Simula minha estratégia personalizada
    """
    spins = await self.get_all_spins(limit)

    def trigger(spins: list[dict], index: int) -> bool:
        # Condição para ativar aposta
        return spins[index]["color"] == 1

    return self.simulate(
        spins=spins,
        trigger_condition=trigger,
        bet_color=2,  # Cor para apostar
        scenario_name="Nome da Estratégia",
        description="Descrição da estratégia"
    )
```

---

## Interpretação dos Resultados

### Métricas da Simulação

| Métrica | Descrição |
|---------|-----------|
| `total_spins_analyzed` | Quantidade total de spins analisados |
| `total_bets` | Quantas apostas foram feitas |
| `wins` | Quantas ganhou |
| `losses` | Quantas perdeu |
| `win_rate` | Porcentagem de acertos |
| `total_profit` | Lucro/prejuízo total (2x por vitória - 1x por derrota) |
| `roi_percentage` | Retorno sobre investimento em % |
| `max_win_streak` | Maior sequência de vitórias |
| `max_loss_streak` | Maior sequência de derrotas |

### ROI Positivo vs Negativo

- **ROI > 0%**: Estratégia lucrativa no período analisado
- **ROI < 0%**: Estratégia deu prejuízo
- **ROI = 0%**: Break-even (sem lucro nem prejuízo)

---

## Avisos Importantes

⚠️ **Roleta é um jogo de azar** - Eventos passados não influenciam eventos futuros em um jogo justo.

⚠️ **Estas simulações são para fins educacionais** - Não garantem lucros reais.

⚠️ **Jogue com responsabilidade** - Nunca aposte dinheiro que não pode perder.

---

## Exemplo de Saída

```
============================================================
SIMULAÇÃO DE CENÁRIOS
============================================================

============================================================
CENÁRIO: Preto após 6x VERDE
DESCRIÇÃO: Após 6 giros VERDES (1) seguidos, apostar que o próximo será PRETO (2)
============================================================
Spins analisados: 5420
Total de apostas: 23
Vitórias: 11 | Derrotas: 12
Win Rate: 47.83%
Lucro/Prejuízo: +10.00
ROI: +43.48%
Maior sequência de vitórias: 4
Maior sequência de derrotas: 3
============================================================
```
