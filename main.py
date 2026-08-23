import os
import sys
import json
import glob
import asyncio
import importlib.util
from datetime import datetime

from core.brain import evaluate_opportunity
from core.notifier import send_telegram_alert
from core.auto_integrator import auto_build_and_deploy_module

MODULES_DIR = os.path.join(os.path.dirname(__file__), "modules")

def load_and_run_modules():
    """Varre e executa dinamicamente todos os scripts presentes na pasta modules/."""
    results = {}
    
    if not os.path.exists(MODULES_DIR):
        os.makedirs(MODULES_DIR)
        return results

    module_files = glob.glob(os.path.join(MODULES_DIR, "*.py"))
    
    for file_path in module_files:
        module_name = os.path.basename(file_path).replace(".py", "")
        if module_name.startswith("__"):
            continue

        try:
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            # Procura por funções de rastreio/varredura (ex: scan_solana_market, scan_live_web)
            scan_func = None
            for attr in dir(mod):
                if attr.startswith("scan_") or attr.startswith("execute_"):
                    scan_func = getattr(mod, attr)
                    break

            if scan_func and callable(scan_func):
                print(f"🔍 A executar módulo: {module_name} -> {scan_func.__name__}()")
                res = scan_func()
                results[module_name] = res
            else:
                print(f"⚠️ Nenhuma função scan_ ou execute_ encontrada em [{module_name}]")

        except Exception as e:
            print(f"❌ Erro ao executar o módulo [{module_name}]: {e}")

    return results

async def run_multimarket_agent():
    """Ciclo principal de rastreio, análise pela Groq, notificação e auto-integração de código."""
    print("🚀 BLING AI — Agente Multimercado Autónomo Iniciado.")
    print("-" * 50)

    while True:
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n🔄 [{timestamp}] Ciclo de Varredura Multimercado...")

        # 1. Executa todos os módulos de varredura (incluindo os novos criados autonomamente)
        market_data = load_and_run_modules()

        # 2. Avalia cada mercado recolhido
        for market, data in market_data.items():
            if not data:
                continue

            print(f"🧠 Groq a analisar oportunidade do módulo [{market}]...")
            decision = evaluate_opportunity(market, json.dumps(data))

            # TRATAMENTO ANTI-CRASH: Garante conversão de lista para dicionário
            if isinstance(decision, list):
                decision = decision[0] if len(decision) > 0 else {"viable": False}

            # 3. Processa a decisão
            if isinstance(decision, dict) and decision.get("viable"):
                print(f"🔥 OPORTUNIDADE DETETADA em {market}! A enviar para o Telegram...")
                
                # Envia alerta para o Telegram
                await send_telegram_alert(decision)
                print("✅ Alerta enviado para o Telegram!")

                # 🤖 AUTONOMIA TOTAL: Escreve, valida e instala o novo módulo em modules/
                auto_build_and_deploy_module(decision)
            else:
                print(f"ℹ️ [{market}] Nenhuma oportunidade cumpre os parâmetros de margem.")

        # Aguarda 60 segundos antes da próxima ronda de varredura
        await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(run_multimarket_agent())
    except KeyboardInterrupt:
        print("\n🛑 BLING AI suspenso pelo utilizador.")
        sys.exit(0)