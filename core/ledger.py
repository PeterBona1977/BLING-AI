import json
import os
from pathlib import Path

LEDGER_FILE = Path(__file__).parent.parent / "ledger.json"

def init_ledger():
    """Garante a existência do ficheiro de saldo inicial do agente."""
    if not os.path.exists(LEDGER_FILE):
        data = {
            "balance_usd": 100.0,  # Capital inicial de teste
            "total_profits": 0.0,
            "opportunities_executed": 0,
            "history": []
        }
        with open(LEDGER_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

def get_balance() -> dict:
    """Retorna o estado financeiro atual do agente."""
    init_ledger()
    with open(LEDGER_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def record_profit(amount: float, source: str, description: str):
    """Regista o lucro de uma oportunidade executada com sucesso."""
    ledger = get_balance()
    ledger["balance_usd"] += amount
    ledger["total_profits"] += amount
    ledger["opportunities_executed"] += 1
    
    ledger["history"].append({
        "type": "PROFIT",
        "amount": amount,
        "source": source,
        "description": description
    })
    
    with open(LEDGER_FILE, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=4)
        
    print(f"💰 [LEDGER] Lucro registado: +${amount:.2f} | Saldo Atual: ${ledger['balance_usd']:.2f}")