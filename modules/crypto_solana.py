import requests

def scan_solana_market() -> str:
    """Procura tokens voláteis na Solana via DexScreener Boosts/Trending."""
    url = "https://api.dexscreener.com/token-boosts/top/v1"
    
    try:
        response = requests.get(url, timeout=10)
        boosted_tokens = response.json() if response.status_code == 200 else []
        
        solana_addresses = [
            t.get("tokenAddress") for t in boosted_tokens 
            if t.get("chainId") == "solana" and t.get("tokenAddress")
        ][:10]
        
        pairs = []
        if solana_addresses:
            addrs_str = ",".join(solana_addresses)
            pairs_res = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{addrs_str}", timeout=10)
            if pairs_res.status_code == 200:
                pairs = pairs_res.json().get("pairs", [])
        
        if not pairs:
            fallback_res = requests.get("https://api.dexscreener.com/latest/dex/search?q=solana", timeout=10)
            if fallback_res.status_code == 200:
                pairs = fallback_res.json().get("pairs", [])

        summary_list = []
        for pair in pairs:
            if pair.get("chainId") != "solana":
                continue

            liquidity = pair.get("liquidity", {}).get("usd", 0)
            volume_1h = pair.get("volume", {}).get("h1", 0)
            
            if liquidity < 5000 or volume_1h < 1000:
                continue

            base_token = pair.get("baseToken", {})
            token_name = base_token.get("name", "N/A")
            token_symbol = base_token.get("symbol", "N/A")
            token_address = base_token.get("address", "N/A")
            price_usd = pair.get("priceUsd", "0")
            price_change_1h = pair.get("priceChange", {}).get("h1", 0)
            pair_url = pair.get("url", "")
            
            summary_list.append(
                f"- Token: {token_name} (${token_symbol})\n"
                f"  Endereço: {token_address}\n"
                f"  Preço USD: ${price_usd} | Variação 1h: {price_change_1h}%\n"
                f"  Liquidez: ${liquidity:,.2f} | Volume 1h: ${volume_1h:,.2f}\n"
                f"  Link: {pair_url}"
            )
            
            if len(summary_list) >= 8:
                break
            
        return "\n\n".join(summary_list) if summary_list else ""
        
    except Exception as e:
        return f"Erro na recolha Solana: {e}"