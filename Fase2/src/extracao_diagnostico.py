import csv
import os
import unicodedata

def normalizar_texto(texto: str) -> str:
    """Remove caracteres acentuados e converte o texto para caixa baixa."""
    nfkd = unicodedata.normalize('NFKD', texto)
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return sem_acento.lower().strip()

def carregar_mapa_conhecimento(caminho_csv: str) -> list:
    """Lê o arquivo CSV de regras ontológicas."""
    regras = []
    with open(caminho_csv, mode='r', encoding='utf-8') as f:
        leitor = csv.DictReader(f)
        for linha in leitor:
            regras.append({
                "s1_norm": normalizar_texto(linha["Sintoma 1"]),
                "s2_norm": normalizar_texto(linha["Sintoma 2"]),
                "s1_label": linha["Sintoma 1"],
                "s2_label": linha["Sintoma 2"],
                "diagnostico": linha["Doenca Associada"]
            })
    return regras

def processar_relatos(caminho_txt: str, regras: list):
    """Analisa cada relato clínico e associa hipóteses diagnósticas."""
    if not os.path.exists(caminho_txt):
        raise FileNotFoundError(f"Arquivo não localizado em: {caminho_txt}")

    with open(caminho_txt, mode='r', encoding='utf-8') as f:
        relatos = [linha.strip() for linha in f if linha.strip()]

    print("=" * 80)
    print("CARDIOIA - EXTRAÇÃO BASEADA EM CONHECIMENTO CLÍNICO (FASE 2)")
    print("=" * 80)

    for idx, relato in enumerate(relatos, start=1):
        relato_norm = normalizar_texto(relato)
        sintomas_detectados = []
        diagnosticos_provaveis = set()

        for r in regras:
            match_s1 = r["s1_norm"] in relato_norm
            match_s2 = r["s2_norm"] in relato_norm

            if match_s1:
                sintomas_detectados.append(r["s1_label"])
            if match_s2:
                sintomas_detectados.append(r["s2_label"])

            # Associação diagnóstica ativada por qualquer um dos termos correspondentes
            if match_s1 or match_s2:
                diagnosticos_provaveis.add(r["diagnostico"])

        sintomas_unicos = sorted(list(set(sintomas_detectados)))
        diagnosticos_unicos = sorted(list(diagnosticos_provaveis))

        print(f"\n[Paciente {idx:02d}]")
        print(f"Relato: \"{relato}\"")
        print(f"Sintomas Identificados: {sintomas_unicos if sintomas_unicos else 'Nenhum sintoma mapeado'}")
        print(f"Diagnóstico(s) Sugerido(s): {diagnosticos_unicos if diagnosticos_unicos else 'Triagem médica presencial'}")
        print("-" * 80)

if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    caminho_csv = os.path.join(BASE_DIR, "data", "mapa_conhecimento.csv")
    caminho_txt = os.path.join(BASE_DIR, "data", "frases_sintomas.txt")

    regras = carregar_mapa_conhecimento(caminho_csv)
    processar_relatos(caminho_txt, regras)