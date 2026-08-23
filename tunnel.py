import os
import re
import sys
import time
import subprocess

def start_tunnel():
    """Inicia um túnel encriptado HTTPS via Cloudflare para aceder à dashboard/API no telemóvel a partir de qualquer lugar."""
    if not os.path.exists("cloudflared.exe"):
        print("⚠️ [Tunnel] Ficheiro cloudflared.exe não encontrado na pasta do projeto.")
        print("💡 A descarregar o executável oficial da Cloudflare...")
        curl_cmd = "curl -L -o cloudflared.exe https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        os.system(curl_cmd)

    print("🚀 A iniciar Cloudflare Tunnel para acesso remoto no telemóvel...")

    # Inicia o processo do cloudflared a direcionar o tráfego externo para a API local (porta 8000)
    process = subprocess.Popen(
        ["cloudflared.exe", "tunnel", "--url", "http://localhost:8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    tunnel_url = None

    # Captura o URL público HTTPS gerado dinamicamente
    for line in iter(process.stdout.readline, ''):
        match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
        if match:
            tunnel_url = match.group(0)
            break

    if tunnel_url:
        print("\n" + "="*65)
        print("🌍 TÚNEL REMOTO ATIVO COM SUCESSO!")
        print(f"📱 LINK HTTPS PARA O TELEMÓVEL: {tunnel_url}")
        print("="*65 + "\n")
        
        # Tenta desenhar um QR Code no terminal para leitura instantânea com a câmara do telemóvel
        try:
            import qrcode
            qr = qrcode.QRCode()
            qr.add_data(tunnel_url)
            qr.print_ascii(invert=True)
        except ImportError:
            print("💡 Dica: podes instalar 'pip install qrcode' para ver o QR Code diretamente no terminal.")
            
    else:
        print("❌ Não foi possível capturar o URL do túnel.")

    process.wait()

if __name__ == "__main__":
    start_tunnel()