import os
import json
import time
import logging
import asyncio
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional

# Optional: solana-py (install via pip if missing)
try:
    from solana.rpc.async_api import AsyncClient
    from solana.publickey import PublicKey
    from solana.transaction import Transaction
    from solana.system_program import TransferParams, transfer
    from solana.keypair import Keypair
    from spl.token.async_client import AsyncToken
except Exception as e:
    # If solana libraries are not available, we will still allow the module to load.
    AsyncClient = None
    PublicKey = None
    Transaction = None
    TransferParams = None
    transfer = None
    Keypair = None
    AsyncToken = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("cybercat_bot")

RAYDIUM_API_POOL = "https://api.raydium.io/v2/main/pairs"
SERUM_MARKET_INFO = "https://serum-api.bonfida.com/pair/CYBERCAT/USDC"

# ------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------
def _safe_request(url: str, params: Optional[Dict] = None, timeout: int = 10) -> Optional[Dict]:
    try:
        resp = requests.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        LOGGER.error(f"Request error for {url}: {exc}")
        return None


def _load_keypair() -> Optional[Keypair]:
    """Load Solana wallet from environment variable SOLANA_PRIVATE_KEY (base58 or hex)."""
    try:
        secret = os.getenv("SOLANA_PRIVATE_KEY")
        if not secret:
            raise ValueError("SOLANA_PRIVATE_KEY not set")
        # Support both JSON array of ints and base58 string
        if secret.startswith("["):
            secret_bytes = json.loads(secret)
            return Keypair.from_secret_key(bytes(secret_bytes))
        else:
            # base58
            from base58 import b58decode

            return Keypair.from_secret_key(b58decode(secret))
    except Exception as exc:
        LOGGER.error(f"Failed to load keypair: {exc}")
        return None


async def _get_current_price() -> Optional[float]:
    """Fetch the latest price from Serum (or fallback to Raydium)."""
    data = _safe_request(SERUM_MARKET_INFO)
    if data and "price" in data:
        try:
            return float(data["price"])
        except Exception:
            pass
    # Fallback to Raydium pool ticker
    pool_data = _safe_request(RAYDIUM_API_POOL)
    if pool_data:
        for pair in pool_data:
            if pair.get("symbol") == "CYBERCAT/USDC":
                try:
                    return float(pair["price"])
                except Exception:
                    continue
    return None


def _fetch_pool_stats() -> Dict[str, Any]:
    """Obtain liquidity, volume and other stats for CYBERCAT/USDC pair."""
    result = {"liquidity": None, "volume_1h": None, "price": None}
    try:
        pool_data = _safe_request(RAYDIUM_API_POOL)
        if not pool_data:
            return result
        for pair in pool_data:
            if pair.get("symbol") == "CYBERCAT/USDC":
                result["liquidity"] = float(pair.get("liquidity", 0))
                result["volume_1h"] = float(pair.get("volume_1h", 0))
                result["price"] = float(pair.get("price", 0))
                break
    except Exception as exc:
        LOGGER.error(f"Error fetching pool stats: {exc}")
    return result


# ------------------------------------------------------------
# Core execution functions
# ------------------------------------------------------------
async def _place_limit_order(
    client: AsyncClient,
    wallet: Keypair,
    side: str,
    price: float,
    amount_usd: float,
    market_address: str,
) -> Dict[str, Any]:
    """
    Simplified placeholder for placing a limit order on Serum.
    Returns a dict with order details or error.
    """
    try:
        # Convert USD amount to token amount based on price
        token_amount = amount_usd / price
        # In a real implementation you would:
        # 1. Load the Serum market
        # 2. Create a NewOrderV3 instruction with side, price, size, order_type=LIMIT
        # 3. Send transaction and await confirmation
        # Here we only simulate success.
        order_id = f"sim-{int(time.time())}"
        LOGGER.info(
            f"Placed {side.upper()} limit order: price={price:.8f}, amount={token_amount:.4f} ({amount_usd}$) -> id={order_id}"
        )
        return {"status": "submitted", "order_id": order_id, "side": side, "price": price, "amount": token_amount}
    except Exception as exc:
        LOGGER.error(f"Failed to place limit order: {exc}")
        return {"status": "error", "error": str(exc)}


async def _monitor_and_exit(
    client: AsyncClient,
    wallet: Keypair,
    market_address: str,
    entry_price: float,
    target_price: float,
    stop_price: float,
    order_id: str,
) -> Dict[str, Any]:
    """
    Monitor price until target or stop is hit, then place market sell.
    Returns final action dict.
    """
    try:
        while True:
            current_price = await _get_current_price()
            if current_price is None:
                await asyncio.sleep(5)
                continue

            LOGGER.info(f"Current price: {current_price:.8f}")

            if current_price >= target_price:
                LOGGER.info(f"Target reached ({current_price:.8f} >= {target_price:.8f}). Selling.")
                sell_result = await _place_limit_order(
                    client, wallet, "sell", current_price, amount_usd=0, market_address=market_address
                )
                return {"action": "sell_target", "price": current_price, "order": sell_result}

            if current_price <= stop_price:
                LOGGER.info(f"Stop‑loss triggered ({current_price:.8f} <= {stop_price:.8f}). Selling.")
                sell_result = await _place_limit_order(
                    client, wallet, "sell", current_price, amount_usd=0, market_address=market_address
                )
                return {"action": "sell_stop", "price": current_price, "order": sell_result}

            await asyncio.sleep(10)
    except Exception as exc:
        LOGGER.error(f"Error during monitoring: {exc}")
        return {"action": "error", "error": str(exc)}


# ------------------------------------------------------------
# Public entry point
# ------------------------------------------------------------
def scan_cybercat_opportunity() -> List[Dict[str, Any]]:
    """
    Main entry point. Gathers market data, decides if the trade should be executed,
    places a limit buy order and starts monitoring for exit conditions.
    Returns a list of step‑by‑step results.
    """
    steps: List[Dict[str, Any]] = []
    try:
        # 1️⃣ Gather market data
        stats = _fetch_pool_stats()
        steps.append({"step": "fetch_stats", "data": stats})

        if not all([stats["liquidity"], stats["volume_1h"], stats["price"]]):
            steps.append({"step": "validation", "status": "insufficient_data"})
            return steps

        # 2️⃣ Simple heuristic: volume > 3 * liquidity && price drop > 30%
        price_drop = (stats["price"] - 0.0006424) / 0.0006424 * 100  # using reference price from description
        if stats["volume_1h"] > 3 * stats["liquidity"] and price_drop < -30:
            steps.append({"step": "validation", "status": "opportunity_detected"})
        else:
            steps.append({"step": "validation", "status": "no_opportunity"})
            return steps

        # 3️⃣ Connect to Solana
        if AsyncClient is None:
            raise RuntimeError("solana-py library not available")
        client = AsyncClient("https://api.mainnet-beta.solana.com")
        wallet = _load_keypair()
        if not wallet:
            raise RuntimeError("Wallet not loaded")
        steps.append({"step": "wallet_loaded", "public_key": str(wallet.public_key)})

        # 4️⃣ Place limit BUY order between 0.00060 and 0.00062
        buy_price = 0.00061  # midpoint of the desired range
        amount_usd = 100  # example capital allocation
        market_address = "CYBERCAT/USDC"  # placeholder; in real code use Serum market address

        loop = asyncio.get_event_loop()
        buy_result = loop.run_until_complete(
            _place_limit_order(client, wallet, "buy", buy_price, amount_usd, market_address)
        )
        steps.append({"step": "place_buy", "result": buy_result})

        if buy_result.get("status") != "submitted":
            steps.append({"step": "buy_failed", "status": "abort"})
            return steps

        # 5️⃣ Monitor price for exit conditions
        target_price = 0.0010
        stop_price = 0.00055
        monitor_result = loop.run_until_complete(
            _monitor_and_exit(
                client,
                wallet,
                market_address,
                entry_price=buy_price,
                target_price=target_price,
                stop_price=stop_price,
                order_id=buy_result.get("order_id", ""),
            )
        )
        steps.append({"step": "monitoring", "result": monitor_result})

        # 6️⃣ Clean up
        loop.run_until_complete(client.close())
        steps.append({"step": "cleanup", "status": "completed"})
        return steps

    except Exception as exc:
        LOGGER.error(f"Unexpected error in scan_cybercat_opportunity: {exc}")
        steps.append({"step": "exception", "error": str(exc)})
        return steps