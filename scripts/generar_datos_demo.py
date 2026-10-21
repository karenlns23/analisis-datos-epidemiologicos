"""
Genera datos SINTÉTICOS con la misma estructura de un archivo de notificación
de vigilancia epidemiológica. Ningún dato es real: municipios, veredas,
coordenadas e identificadores son ficticios.
"""
import hashlib
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)

DEPARTAMENTO = "DEPARTAMENTO DEMO"
LUGARES = {
    "VILLA ALEGRE": {"veredas": ["LA CEIBA", "EL ROBLE", "LOS MANGOS"], "barrios": ["CENTRO", "EL PRADO"]},
    "LAS PALMAS":   {"veredas": ["EL PORVENIR", "LA ESPERANZA", "BUENOS AIRES"], "barrios": ["CENTRO", "LA PAZ"]},
    "EL CAMINO":    {"veredas": ["SAN JOSE", "LA UNION", "EL CARMEN"], "barrios": ["CENTRO", "LOS PINOS"]},
    "SAN ISIDRO":   {"veredas": ["LA PALMA", "EL RECREO", "MONTE VERDE"], "barrios": ["CENTRO", "LA FLORESTA"]},
}
PESOS_MUNICIPIO = [0.55, 0.25, 0.12, 0.08]


def crear_catalogo():
    """Catálogo de lugares con coordenadas ficticias (cerca de 0,0)."""
    filas = []
    for i, (mun, lugares) in enumerate(LUGARES.items()):
        for j, vereda in enumerate(lugares["veredas"]):
            filas.append([mun, "", vereda, f"VEREDA {vereda}", "", round(0.01 * (i + 1) + 0.002 * j, 5), round(0.01 * (i + 1) - 0.002 * j, 5)])
        for j, barrio in enumerate(lugares["barrios"]):
            filas.append([mun, barrio, "", f"BARRIO {barrio}", "", round(0.05 + 0.01 * i + 0.002 * j, 5), round(0.05 + 0.01 * i - 0.002 * j, 5)])
    return pd.DataFrame(filas, columns=["MUNICIPIO", "BARRIO", "VEREDA", "LUGAR_LIMPIO", "MICROAREA", "LATITUD", "LONGITUD"])


def id_anonimo(n):
    return [hashlib.sha1(str(rng.integers(0, 10**12)).encode()).hexdigest()[:10].upper() for _ in range(n)]


def generar_casos(anio, semana, n):
    """Crea n casos sintéticos para una semana epidemiológica."""
    municipios = rng.choice(list(LUGARES), size=n, p=PESOS_MUNICIPIO)
    areas, barrios, veredas = [], [], []
    for m in municipios:
        if rng.random() < 0.7:  # rural
            areas.append(3)
            v = rng.choice(LUGARES[m]["veredas"])
            veredas.append(v if rng.random() > 0.03 else "VEREDA NUEVA")  # algunos lugares fuera del catálogo
            barrios.append("")
        else:  # cabecera
            areas.append(1)
            barrios.append(rng.choice(LUGARES[m]["barrios"]))
            veredas.append("")
    # Variaciones de escritura, como en un archivo real
    veredas = [v.lower() + " " if v and rng.random() < 0.1 else v for v in veredas]
    return pd.DataFrame({
        "id_caso": id_anonimo(n),
        "semana": semana,
        "año": anio,
        "ndep_proce": DEPARTAMENTO,
        "nmun_proce": municipios,
        "area_": areas,
        "bar_ver_": barrios,
        "vereda_": veredas,
        "edad_": np.clip(rng.gamma(2.0, 12.0, n).astype(int), 0, 90),
        "sexo_": rng.choice(["M", "F"], size=n, p=[0.55, 0.45]),
        "per_etn_": rng.choice([1, 5, 6], size=n, p=[0.2, 0.1, 0.7]),
        "tip_cas_": rng.choice([1, 2, 3, 4, 5], size=n, p=[0.05, 0.1, 0.7, 0.1, 0.05]),
        "clas_caso": rng.choice([1, 2], size=n, p=[0.9, 0.1]),
        "esp_pla": rng.choice([1, 2, 3, 4], size=n, p=[0.6, 0.34, 0.01, 0.05]),
        "nom_eve": "EVENTO DEMO",
    })


def main():
    bloques = []
    for anio in (2023, 2024, 2025):
        for semana in range(1, 53):
            # Estacionalidad simple: más casos en dos épocas del año
            media = 12 + 6 * np.sin(2 * np.pi * (semana - 8) / 52) + (anio - 2023) * 2
            bloques.append(generar_casos(anio, semana, max(int(rng.poisson(media)), 1)))
    historico = pd.concat(bloques, ignore_index=True)
    historico.to_csv("data/notificacion_demo.csv", sep=";", index=False, encoding="latin1")

    # Archivo de una semana nueva: repite 30 casos ya enviados y agrega 15 nuevos
    repetidos = historico.tail(30)
    nuevos = generar_casos(2026, 1, 15)
    pd.concat([repetidos, nuevos], ignore_index=True).to_csv(
        "data/notificacion_demo_semana_nueva.csv", sep=";", index=False, encoding="latin1")

    crear_catalogo().to_csv("data/catalogo_lugares_demo.csv", index=False)
    print(f"Histórico: {len(historico)} casos | Semana nueva: {len(repetidos) + len(nuevos)} filas (30 repetidas, 15 nuevas)")


if __name__ == "__main__":
    main()
