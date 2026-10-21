"""Resumen y gráfico de la base maestra (casos por año y por periodo de 4 semanas)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

maestro = pd.read_csv("resultados/base_maestra.csv", dtype={"ANIO": str})

por_anio = maestro.groupby("ANIO").size().rename("Casos")
menores = maestro[maestro["MENOR_10_ANOS"] == "Sí"].groupby("ANIO").size().rename("Menores de 10 años")
resumen = pd.concat([por_anio, menores], axis=1).fillna(0).astype(int)
resumen.to_csv("resultados/resumen_por_anio.csv")
print(resumen)

por_periodo = maestro.pivot_table(index="PERIODO", columns="ANIO", values="ID_CASO", aggfunc="count").fillna(0)
ax = por_periodo.plot(kind="bar", figsize=(10, 5), width=0.85)
ax.set_title("Casos por periodo de 4 semanas (datos sintéticos)")
ax.set_xlabel("Periodo (1 = semanas 1-4, ..., 13 = semanas 49-52)")
ax.set_ylabel("Casos")
ax.legend(title="Año")
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig("resultados/casos_por_periodo.png", dpi=130)
print("Gráfico guardado")
