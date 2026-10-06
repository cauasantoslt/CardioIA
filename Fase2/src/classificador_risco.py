import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

def carregar_dados(caminho_csv: str) -> pd.DataFrame:
    """Carrega o dataset e valida a integridade das colunas."""
    if not os.path.exists(caminho_csv):
        raise FileNotFoundError(f"Arquivo não localizado em: {caminho_csv}")
    df = pd.read_csv(caminho_csv)
    print(f"Dataset carregado com {len(df)} amostras.")
    print("Distribuição das classes:\n", df['situacao'].value_counts())
    return df

def treinar_modelo(df: pd.DataFrame):
    """Executa a divisão de dados, vetorização TF-IDF e treino com Regressão Logística."""
    X = df['frase']
    y = df['situacao']

    # Divisão estratificada para manter 50% de cada classe no treino e no teste
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    # TF-IDF considerando palavras isoladas e pares de palavras (bigramas para captar termos como 'dor peito')
    stopwords_pt = [
        'a', 'ao', 'aos', 'aquela', 'as', 'com', 'da', 'das', 'de', 'do', 'dos', 'e', 
        'em', 'no', 'na', 'nos', 'nas', 'o', 'os', 'para', 'por', 'que', 'se', 'um', 'uma'
    ]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words=stopwords_pt, min_df=1)
    
    X_train_tfidf = vectorizer.fit_transform(X_train)
    X_test_tfidf = vectorizer.transform(X_test)

    # Regressão Logística: excelente para dados lineares esparsos de texto
    modelo = LogisticRegression(random_state=42, C=1.0)
    modelo.fit(X_train_tfidf, y_train)

    # Avaliação com o conjunto de teste
    y_pred = modelo.predict(X_test_tfidf)
    acc = accuracy_score(y_test, y_pred)

    print("\n" + "=" * 70)
    print("CARDIOIA - DESEMPENHO DO MODELO DE TRIAGEM TEXTUAL")
    print("=" * 70)
    print(f"Acurácia no Teste: {acc * 100:.2f}%\n")
    print("Matriz de Confusão:")
    print(confusion_matrix(y_test, y_pred, labels=['alto risco', 'baixo risco']))
    print("\nRelatório de Classificação (Precision, Recall, F1-Score):")
    print(classification_report(y_test, y_pred, labels=['alto risco', 'baixo risco']))

    return vectorizer, modelo

def analisar_palavras_chave(vectorizer, modelo, top_n=8):
    """Exibe os termos de maior relevância estatística para cada risco."""
    nomes_features = np.array(vectorizer.get_feature_names_out())
    coeficientes = modelo.coef_[0]
    
    # Se a classe positiva for 'baixo risco', os coeficientes positivos indicam baixo risco e vice-versa
    classe_pos = modelo.classes_[1]
    classe_neg = modelo.classes_[0]

    top_pos = nomes_features[np.argsort(coeficientes)[-top_n:]]
    top_neg = nomes_features[np.argsort(coeficientes)[:top_n]]

    print("\n" + "=" * 70)
    print("INTERPRETABILIDADE DO MODELO (PESOS LÉXICOS DO TF-IDF)")
    print("=" * 70)
    print(f"Termos mais associados a [{classe_pos.upper()}]:")
    print(", ".join(reversed(top_pos)))
    print(f"\nTermos mais associados a [{classe_neg.upper()}]:")
    print(", ".join(top_neg))

def testar_inferencia(vectorizer, modelo):
    """Testa frases inéditas, incluindo apresentações atípicas e queixas ambulatoriais."""
    casos_clinicos = [
        "Estou sentindo um aperto forte no peito e muito suor frio",
        "Apenas uma dor leve nas costas que apareceu apos correr",
        "Muita falta de ar ao deitar e o peito parece estar pesado",
        "Tive azia depois de jantar pizza e beber refrigerante",
        "Estou com nausea e muita fraqueza sem conseguir levantar da cama"  # Caso crítico/atípico
    ]

    print("\n" + "=" * 70)
    print("SIMULAÇÃO DE TRIAGEM EM TEMPO REAL (CASOS INÉDITOS)")
    print("=" * 70)

    X_novos = vectorizer.transform(casos_clinicos)
    predicoes = modelo.predict(X_novos)
    probabilidades = modelo.predict_proba(X_novos)

    for frase, pred, probs in zip(casos_clinicos, predicoes, probabilidades):
        idx_classe = list(modelo.classes_).index(pred)
        confianca = probs[idx_classe] * 100
        print(f"Relato: \"{frase}\"")
        print(f"-> Classificação: [{pred.upper()}] (Grau de Certeza: {confianca:.2f}%)\n")

if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    caminho_csv = os.path.join(BASE_DIR, "data", "triagem_risco.csv")

    df = carregar_dados(caminho_csv)
    vectorizer, modelo = treinar_modelo(df)
    analisar_palavras_chave(vectorizer, modelo)
    testar_inferencia(vectorizer, modelo)