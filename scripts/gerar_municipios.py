"""Gera a lista de municípios do IBGE e as coordenadas de cada um (duas consultas ao IBGE).

Uso: python scripts/gerar_municipios.py

- frontend/src/constants/municipios.json: {"SP": ["Adamantina", ...], ...}, a lista do seletor.
- services/municipios_coordenadas.json: {"SP": {"Adamantina": [lat, lon], ...}, ...}, centroide
  oficial, usado quando o geocodificador do Open-Meteo não reconhece um município da lista.
"""
import json
from collections import defaultdict
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
MUNICIPALITIES_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios?view=nivelado"
CENTROIDS_URL = "https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR/metadados?intrarregiao=municipio"
CITIES_OUTPUT = ROOT / "frontend" / "src" / "constants" / "municipios.json"
COORDINATES_OUTPUT = ROOT / "services" / "municipios_coordenadas.json"

# Municípios recentes, sem malha publicada pelo IBGE. Coordenadas do Open-Meteo/GeoNames.
MANUAL_COORDINATES = {
    "5101837": [-13.50829, -55.15235],  # Boa Esperança do Norte/MT: a sede, antigo distrito de Sorriso
}


def _get_json(url: str) -> list[dict]:
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    return response.json()


def _dump(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main() -> None:
    centroids = {
        str(row["id"]): [row["centroide"]["latitude"], row["centroide"]["longitude"]]
        for row in _get_json(CENTROIDS_URL)
    }

    names: dict[str, list[str]] = defaultdict(list)
    coordinates: dict[str, dict[str, list[float]]] = defaultdict(dict)
    for row in _get_json(MUNICIPALITIES_URL):
        municipality_id, city, uf = str(row["municipio-id"]), row["municipio-nome"], row["UF-sigla"]
        point = centroids.get(municipality_id) or MANUAL_COORDINATES.get(municipality_id)
        if point is None:
            # Fica fora da lista: sem coordenada, a opção resultaria em erro para o usuário.
            print(f"SEM COORDENADAS, fora da lista: {city}/{uf} ({municipality_id})")
            continue
        names[uf].append(city)
        coordinates[uf][city] = point

    _dump(CITIES_OUTPUT, {uf: sorted(names[uf]) for uf in sorted(names)})
    _dump(COORDINATES_OUTPUT, {uf: coordinates[uf] for uf in sorted(coordinates)})
    print(f"{sum(map(len, names.values()))} municípios em {len(names)} UFs")


if __name__ == "__main__":
    main()
