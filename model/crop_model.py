import os

import joblib
import numpy as np
import pandas as pd

MODEL_PATH = os.path.join(os.path.dirname(__file__), "modelo_recomendacao_safra.joblib")

# Features usadas no treino, na ordem de `model.feature_names_in_`.
# O modelo NÃO usa pH: qualquer pH recebido pela API é ignorado.
# Unidades esperadas (as do dataset de treino):
#   N, P, K      -> mg/kg
#   temperature  -> °C (média, não leitura instantânea)
#   humidity     -> % de umidade relativa (média)
#   rainfall     -> mm/mês (chuva média mensal; o menor corte das árvores é ~30 mm)
FEATURES = ("N", "P", "K", "temperature", "humidity", "rainfall")

_model = None


def get_model():
    global _model
    if _model is None:
        _model = joblib.load(MODEL_PATH)
    return _model


def crop_prev(data: dict) -> dict:
    """Recomenda a cultura a partir das 6 features de FEATURES.

    Todas as features são obrigatórias. Não há valor padrão escondido:
    uma entrada faltando é erro de quem chamou, não algo a ser preenchido
    em silêncio.
    """
    missing = [name for name in FEATURES if data.get(name) is None]
    if missing:
        raise ValueError(f"Features ausentes para o modelo: {', '.join(missing)}")

    features = {name: float(data[name]) for name in FEATURES}

    model = get_model()
    input_df = pd.DataFrame([features], columns=list(FEATURES))
    probabilities = model.predict_proba(input_df)[0]

    # RandomForestClassifier.predict é exatamente o argmax de predict_proba;
    # usar o argmax evita uma segunda passada pelas 100 árvores.
    best_idx = int(np.argmax(probabilities))

    top_indices = np.argsort(probabilities)[::-1][:3]
    top_recommendations = [
        {"crop": str(model.classes_[idx]), "probability": round(float(probabilities[idx]) * 100, 2)}
        for idx in top_indices
        if probabilities[idx] > 0.01
    ]

    return {
        "crop_recommendation": str(model.classes_[best_idx]),
        "confidence": round(float(probabilities[best_idx]) * 100, 2),
        "top_recommendations": top_recommendations,
        # Todas as classes, em %: a recomendação cruzada compara culturas fora do top 3.
        "probabilities": {
            str(crop): round(float(probability) * 100, 2)
            for crop, probability in zip(model.classes_, probabilities, strict=True)
        },
        "features": features,
    }
