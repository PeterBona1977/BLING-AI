import os
import re

# Modelo ativo e recomendado na Groq
TARGET_MODEL = "openai/gpt-oss-120b"

# Modelos antigos/descontinuados a substituir
DEPRECATED_MODELS = [
    r"llama3-70b-8192",
    r"llama-3\.3-70b-versatile",
    r"llama-3\.1-8b-instant",
    r"deepseek-r1-distill-llama-70b",
    r"qwen/qwen3-32b"
]

project_dir = os.path.dirname(os.path.abspath(__file__))
count = 0

print(f"🔄 A atualizar ficheiros .py para usar o modelo ativo: {TARGET_MODEL}...\n")

for root, dirs, files in os.walk(project_dir):
    for file in files:
        if file.endswith(".py") and file != "fix_models.py":
            filepath = os.path.join(root, file)
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            new_content = content
            for deprecated in DEPRECATED_MODELS:
                new_content = re.sub(deprecated, TARGET_MODEL, new_content)

            if new_content != content:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"✅ Atualizado: {os.path.relpath(filepath, project_dir)}")
                count += 1

print(f"\n✨ Concluído! {count} ficheiro(s) atualizados.")