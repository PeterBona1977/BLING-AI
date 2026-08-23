import os
import time
import json
import logging
import requests
from decimal import Decimal, ROUND_DOWN

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RAYDIUM_API = "https://api.raydium.io/v2/main/pairs"
SOLANA_RPC = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
WALLET_PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY")  # base64 or hex string
TOTAL_CAPITAL_USD = Decimal(os.getenv("TOTAL_CAPITAL_USD", "1000"))  # exemplo

TOKEN_MINT = "CATALORIAN_MINT_ADDRESS_PLACEHOLDER"
TARGET_PRICE = Decimal("0.0145")
STOP_LOSS = Decimal("0.0125")
TARGET_SELL = Decimal("0.0163")
RISK_PERCENT_MIN = Decimal("0.02")
RISK_PERCENT_MAX = Decimal("0.03")


def _fetch_token_price():
    """
    Busca o preço atual do token CATALORIAN via API pública da Raydium.
    Retorna Decimal ou None.
    """
    try:
        resp = requests.get(RAYDIUM_API, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        for pair in data.get("data", []):
            if pair.get("baseMint") == TOKEN_MINT:
                # price = quote amount (USDC) / base amount (token)
                price = Decimal(str(pair.get("price", 0)))
                return price.quantize(Decimal("0.00000001"))
    except Exception as e:
        logger.error(f"Erro ao obter preço do token: {e}")
    return None


def _fetch_sol_price():
    """
    Busca preço do SOL em USD usando Coingecko.
    """
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": "solana", "vs_currencies": "usd"}
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        price = Decimal(str(resp.json()["solana"]["usd"]))
        return price.quantize(Decimal("0.01"))
    except Exception as e:
        logger.error(f"Erro ao obter preço do SOL: {e}")
    return None


def _calculate_order_amount(capital_usd, price):
    """
    Calcula a quantidade de token a comprar usando 2‑3% do capital.
    Retorna tuple (token_amount, usd_spent)
    """
    try:
        risk_pct = (RISK_PERCENT_MIN + RISK_PERCENT_MAX) / 2
        usd_to_spend = (capital_usd * risk_pct).quantize(Decimal("0.01"))
        token_amount = (usd_to_spend / price).quantize(Decimal("0.000001"), rounding=ROUND_DOWN)
        return token_amount, usd_to_spend
    except Exception as e:
        logger.error(f"Erro ao calcular quantidade de ordem: {e}")
        return Decimal("0"), Decimal("0")


def _place_limit_order(token_amount, limit_price):
    """
    Simula envio de ordem limite para Raydium.
    Na prática, seria necessário usar a SDK Solana ou RPC customizado.
    Retorna dict com detalhes da ordem ou None em falha.
    """
    try:
        # Payload fictício – substituir por chamada real à blockchain
        payload = {
            "wallet": "placeholder_wallet_address",
            "mint": TOKEN_MINT,
            "side": "buy",
            "price": str(limit_price),
            "amount": str(token_amount),
            "type": "limit"
        }
        # Simulação de resposta
        fake_response = {
            "orderId": f"order_{int(time.time())}",
            "status": "submitted",
            "timestamp": int(time.time()),
            "details": payload
        }
        logger.info(f"Ordem limite simulada enviada: {json.dumps(fake_response)}")
        return fake_response
    except Exception as e:
        logger.error(f"Erro ao enviar ordem limite: {e}")
        return None


def scan_elons_space_cat_catalorian():
    """
    Executa a estratégia de compra do token $CATALORIAN.
    Retorna dicionário estruturado com o resultado da operação.
    """
    result = {
        "timestamp": int(time.time()),
        "success": False,
        "message": "",
        "order": None,
        "price_usd": None,
        "token_amount": None,
        "usd_spent": None,
        "stop_loss": str(STOP_LOSS),
        "target_sell": str(TARGET_SELL)
    }

    try:
        price = _fetch_token_price()
        if price is None:
            result["message"] = "Não foi possível obter o preço do token."
            return result
        result["price_usd"] = str(price)

        sol_price = _fetch_sol_price()
        if sol_price is None:
            result["message"] = "Não foi possível obter o preço do SOL."
            return result

        token_amount, usd_spent = _calculate_order_amount(TOTAL_CAPITAL_USD, price)
        if token_amount == 0:
            result["message"] = "Cálculo de quantidade falhou."
            return result

        result["token_amount"] = str(token_amount)
        result["usd_spent"] = str(usd_spent)

        order = _place_limit_order(token_amount, TARGET_PRICE)
        if order is None:
            result["message"] = "Falha ao enviar ordem limite."
            return result

        result["order"] = order
        result["success"] = True
        result["message"] = "Ordem limite enviada com sucesso."
        return result

    except Exception as exc:
        logger.exception("Exceção inesperada na estratégia.")
        result["message"] = f"Exceção inesperada: {exc}"
        return result

if __name__ == "__main__":
    # Execução rápida para testes locais
    output = scan_elons_space_cat_catalorian()
    print(json.dumps(output, indent=2))