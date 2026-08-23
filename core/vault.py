import os
import json
import base64
from pathlib import Path

VAULT_PATH = Path("core/vault_store.json")

def _load_vault() -> dict:
    if not VAULT_PATH.exists():
        return {}
    try:
        with open(VAULT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_vault(data: dict):
    with open(VAULT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def get_secret(key: str, default=None):
    """Recupera uma chave ou credencial do cofre."""
    data = _load_vault()
    return data.get(key, os.getenv(key, default))

def set_secret(key: str, value: str):
    """Guarda uma credencial ou token no cofre local."""
    data = _load_vault()
    data[key] = value
    _save_vault(data)
    print(f"🔑 [Vault] Credencial registada: {key}")

def get_or_create_wallet(chain: str = "solana") -> dict:
    """Retorna uma wallet guardada ou gera um novo par de chaves localmente."""
    vault_key = f"wallet_{chain.lower()}"
    existing = get_secret(vault_key)
    if existing:
        return json.loads(existing)

    # Autogeração básica de par de chaves para autonomia sem KYC
    if chain.lower() == "solana":
        import secrets
        raw_seed = secrets.token_bytes(32)
        pubkey_mock = "SOL_" + base64.b58encode(raw_seed[:16]).decode('utf-8')
        wallet_data = {
            "address": pubkey_mock,
            "private_key": base64.b58encode(raw_seed).decode('utf-8')
        }
    else:
        import secrets
        wallet_data = {
            "address": "0x" + secrets.token_hex(20),
            "private_key": "0x" + secrets.token_hex(32)
        }

    set_secret(vault_key, json.dumps(wallet_data))
    print(f"💳 [Vault] Nova Wallet {chain.upper()} criada com sucesso: {wallet_data['address']}")
    return wallet_data