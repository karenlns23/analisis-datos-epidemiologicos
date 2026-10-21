"""
Procesamiento semanal de un archivo de notificación de vigilancia epidemiológica.

Flujo:
  1. Lee el archivo semanal (.csv o .xlsx)
  2. Filtra el departamento de interés
  3. Traduce los códigos a categorías legibles
  4. Calcula variables derivadas (grupo de edad, periodo de 4 semanas)
  5. Asigna lugar limpio y coordenadas con un catálogo de veredas y barrios
  6. Detecta duplicados y agrega a la base maestra solo los casos nuevos
  7. Guarda la base maestra y la lista de lugares pendientes

Uso:
  python scripts/procesar_vigilancia.py data/notificacion_demo.csv
"""
import argparse
import os

import pandas as pd

DEPARTAMENTO = "DEPARTAMENTO DEMO"
CATALOGO = "data/catalogo_lugares_demo.csv"
MAESTRO = "resultados/base_maestra.csv"
PENDIENTES = "resultados/lugares_pendientes.csv"

# ---- Diccionarios de traducción (código -> significado) ----
AREA = {1: "Cabecera municipal", 2: "Centro poblado", 3: "Rural disperso"}
SEXO = {"M": "Masculino", "F": "Femenino", "I": "Indeterminado"}
ORIGEN = {1: "Autóctono", 2: "Importado"}
ETNIA = {1: "Indígena", 2: "Rom/Gitano", 3: "Raizal", 4: "Palenquero", 5: "Afrocolombiano", 6: "Otro"}
TIPO_CASO = {1: "Sospechoso", 2: "Probable", 3: "Conf. laboratorio", 4: "Conf. clínica", 5: "Conf. nexo epidemiológico"}
ESPECIE = {1: "P. vivax", 2: "P. falciparum", 3: "P. malariae", 4: "Infección mixta"}

# Límites superiores (exclusivos) de cada grupo de edad
GRUPOS_EDAD = [(1, "Menor de 1 año"), (5, "1 a 4 años"), (10, "5 a 9 años"), (15, "10 a 14 años"),
               (18, "15 a 17 años"), (28, "18 a 27 años"), (60, "28 a 59 años")]


def clasificar_edad(edad):
    if pd.isna(edad):
        return "Sin dato"
    for limite, nombre in GRUPOS_EDAD:
        if edad < limite:
            return nombre
    return "60 años o más"


def periodo_de_cuatro_semanas(semana):
    """Agrupa las semanas epidemiológicas en 13 periodos de 4 semanas."""
    return min((int(semana) - 1) // 4 + 1, 13)


def texto_limpio(serie):
    """Texto en mayúsculas, sin espacios sobrantes y sin NAN."""
    return serie.fillna("").astype(str).str.strip().str.upper().replace("NAN", "")


def leer_notificacion(ruta):
    if ruta.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(ruta)
    return pd.read_csv(ruta, sep=";", encoding="latin1")


def transformar(df_crudo):
    """Filtra, traduce códigos y calcula variables derivadas."""
    df = df_crudo[df_crudo["ndep_proce"] == DEPARTAMENTO].copy()
    out = pd.DataFrame({
        "ID_CASO": df["id_caso"].astype(str),
        "ANIO": df["año"].astype(int).astype(str),
        "SEMANA": df["semana"].astype(int).astype(str),
        "PERIODO": df["semana"].apply(periodo_de_cuatro_semanas),
        "MUNICIPIO": texto_limpio(df["nmun_proce"]),
        "TIPO_ZONA": df["area_"].map(AREA),
        "BARRIO": texto_limpio(df["bar_ver_"]),
        "VEREDA": texto_limpio(df["vereda_"]),
        "EDAD": df["edad_"],
        "GRUPO_EDAD": df["edad_"].apply(clasificar_edad),
        "MENOR_10_ANOS": df["edad_"].apply(lambda e: "Sí" if e < 10 else "No"),
        "SEXO": df["sexo_"].map(SEXO),
        "PERTENENCIA_ETNICA": df["per_etn_"].map(ETNIA),
        "TIPO_CASO": df["tip_cas_"].map(TIPO_CASO),
        "ORIGEN": df["clas_caso"].map(ORIGEN),
        "ESPECIE": df["esp_pla"].map(ESPECIE),
    })
    return out.reset_index(drop=True)


def asignar_coordenadas(df, ruta_catalogo):
    """Busca cada caso en el catálogo, primero por vereda y luego por barrio."""
    cat = pd.read_csv(ruta_catalogo)
    for col in ("MUNICIPIO", "BARRIO", "VEREDA"):
        cat[col] = texto_limpio(cat[col])
    por_vereda = {(r.MUNICIPIO, r.VEREDA): (r.LUGAR_LIMPIO, r.LATITUD, r.LONGITUD)
                  for r in cat[cat["VEREDA"] != ""].itertuples()}
    por_barrio = {(r.MUNICIPIO, r.BARRIO): (r.LUGAR_LIMPIO, r.LATITUD, r.LONGITUD)
                  for r in cat[cat["BARRIO"] != ""].itertuples()}

    def buscar(fila):
        if fila.VEREDA and (fila.MUNICIPIO, fila.VEREDA) in por_vereda:
            return por_vereda[(fila.MUNICIPIO, fila.VEREDA)]
        if fila.BARRIO and (fila.MUNICIPIO, fila.BARRIO) in por_barrio:
            return por_barrio[(fila.MUNICIPIO, fila.BARRIO)]
        return (None, None, None)

    resultado = [buscar(f) for f in df.itertuples()]
    df = df.copy()
    df["LUGAR_LIMPIO"] = [r[0] for r in resultado]
    df["LATITUD"] = [r[1] for r in resultado]
    df["LONGITUD"] = [r[2] for r in resultado]
    return df


def llave(df):
    return df["ID_CASO"] + "_" + df["SEMANA"] + "_" + df["ANIO"]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("archivo", help="archivo de notificación (.csv o .xlsx)")
    parser.add_argument("--catalogo", default=CATALOGO)
    parser.add_argument("--maestro", default=MAESTRO)
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.maestro), exist_ok=True)

    nuevo = transformar(leer_notificacion(args.archivo))
    print(f"Casos del departamento en el archivo: {len(nuevo)}")

    nuevo = asignar_coordenadas(nuevo, args.catalogo)
    sin_coords = nuevo[nuevo["LATITUD"].isna()]
    print(f"Con coordenadas: {len(nuevo) - len(sin_coords)} | Sin coordenadas: {len(sin_coords)}")
    if len(sin_coords):
        sin_coords[["MUNICIPIO", "BARRIO", "VEREDA"]].drop_duplicates().to_csv(PENDIENTES, index=False)

    if os.path.exists(args.maestro):
        maestro = pd.read_csv(args.maestro, dtype={"ID_CASO": str, "ANIO": str, "SEMANA": str})
    else:
        maestro = pd.DataFrame(columns=nuevo.columns)

    es_nuevo = ~llave(nuevo).isin(set(llave(maestro))) if len(maestro) else pd.Series(True, index=nuevo.index)
    agregados = nuevo[es_nuevo]
    print(f"Ya existían (duplicados): {len(nuevo) - len(agregados)} | Casos nuevos agregados: {len(agregados)}")

    final = pd.concat([maestro, agregados], ignore_index=True)
    final.to_csv(args.maestro, index=False)
    print(f"Base maestra: {len(final)} casos -> {args.maestro}")


if __name__ == "__main__":
    main()
