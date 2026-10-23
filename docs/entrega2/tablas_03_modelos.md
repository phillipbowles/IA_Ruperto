<!-- GENERADO por notebooks/03_modelos.ipynb — no editar; se reescribe al re-ejecutar. -->
# Tablas del notebook 03_modelos

Datos: `mediciones_raw_2026-10-23.csv`. Modelo: `regla-p3-f07-79b556`.

## Conteo

|           |   ('todos', 'filas') |   ('todos', 'episodios') |   ('sin dudosos', 'filas') |   ('sin dudosos', 'episodios') |
|:----------|---------------------:|-------------------------:|---------------------------:|-------------------------------:|
| saludable |             2452.000 |                    7.000 |                   2425.000 |                          6.000 |
| estresada |             2446.000 |                   11.000 |                   2092.000 |                          9.000 |
| marchita  |              765.000 |                    6.000 |                    654.000 |                          5.000 |

## Episodios

|   episodio_id | clase     | origen    | dudoso   |   filas | desde       |   suelo_mv |   temp_c |   hum_aire_pct |   h_riego_min |   h_riego_max |
|--------------:|:----------|:----------|:---------|--------:|:------------|-----------:|---------:|---------------:|--------------:|--------------:|
|         1.000 | marchita  | corregida | False    |     132 | 13/09 00:55 |   2832.000 |    8.500 |         61.500 |        96.000 |        96.000 |
|         3.000 | estresada | manual    | False    |      24 | 15/09 13:35 |   2766.500 |   34.200 |         22.750 |        96.000 |        96.000 |
|         6.000 | estresada | manual    | False    |      74 | 16/09 17:55 |   2048.000 |   14.600 |         43.000 |        96.000 |        96.000 |
|         8.000 | marchita  | manual    | True     |     111 | 01/10 01:40 |   1518.000 |   20.600 |         50.000 |        96.000 |        96.000 |
|         9.000 | estresada | manual    | True     |      52 | 01/10 10:55 |   1454.000 |   19.000 |         46.000 |        96.000 |        96.000 |
|        10.000 | saludable | manual    | False    |     140 | 02/10 01:55 |   1504.000 |   18.600 |         54.000 |        96.000 |        96.000 |
|        11.000 | saludable | propagada | True     |      27 | 19/10 00:35 |   1785.500 |   20.200 |         47.000 |        30.583 |        32.750 |
|        12.000 | marchita  | manual    | False    |      90 | 19/10 02:50 |   1758.000 |   20.200 |         45.000 |        32.833 |        40.250 |
|        13.000 | estresada | manual    | False    |     146 | 19/10 10:20 |   1927.000 |   19.400 |         43.000 |        40.333 |        52.583 |
|        14.000 | estresada | propagada | True     |     302 | 19/10 22:40 |   1445.000 |   19.800 |         48.000 |         0.000 |        25.083 |
|        15.000 | saludable | manual    | False    |     259 | 20/10 23:50 |   1453.000 |   20.200 |         48.000 |        25.167 |        46.667 |
|        16.000 | saludable | manual    | False    |     412 | 03/10 21:40 |   1570.000 |   20.200 |         48.000 |        96.000 |        96.000 |
|        17.000 | estresada | manual    | False    |     552 | 05/10 08:00 |   1838.000 |   19.700 |         48.000 |        96.000 |        96.000 |
|        18.000 | marchita  | manual    | False    |     144 | 07/10 06:00 |   1941.000 |   20.500 |         46.000 |        96.000 |        96.000 |
|        19.000 | estresada | manual    | False    |      60 | 07/10 18:00 |   1488.000 |   20.000 |         50.000 |         0.000 |         4.917 |
|        20.000 | saludable | manual    | False    |     672 | 07/10 23:00 |   1573.500 |   20.100 |         48.000 |         5.000 |        61.917 |
|        21.000 | estresada | manual    | False    |     552 | 10/10 08:00 |   1842.500 |   19.900 |         47.000 |        62.000 |        96.000 |
|        22.000 | marchita  | manual    | False    |     144 | 12/10 06:00 |   1962.000 |   20.200 |         45.000 |        96.000 |        96.000 |
|        23.000 | estresada | manual    | False    |      72 | 12/10 18:00 |   1523.500 |   19.800 |         50.000 |         0.000 |         5.917 |
|        24.000 | saludable | manual    | False    |     660 | 13/10 01:00 |   1610.500 |   20.400 |         48.000 |         7.000 |        61.917 |
|        25.000 | estresada | manual    | False    |     552 | 15/10 08:00 |   1872.500 |   20.200 |         47.000 |        62.000 |        96.000 |
|        26.000 | marchita  | manual    | False    |     144 | 17/10 06:00 |   1960.000 |   20.300 |         47.000 |        96.000 |        96.000 |
|        27.000 | estresada | manual    | False    |      60 | 17/10 18:00 |   1519.000 |   19.800 |         50.500 |         0.000 |         4.917 |
|        28.000 | saludable | manual    | False    |     282 | 17/10 23:00 |   1505.500 |   20.500 |         48.000 |         5.000 |        29.417 |

## Fuga

|            |   aleatoria (filas mezcladas) |   por episodio |
|:-----------|------------------------------:|---------------:|
| RF sin luz |                         0.991 |          0.753 |

## Partición por episodio, fuera de fold

|                         | ('todos', 'f1_macro')   | ('todos', 'exactitud_bal')   | ('todos', 'recall_marchita')   | ('sin dudosos', 'f1_macro')   | ('sin dudosos', 'exactitud_bal')   | ('sin dudosos', 'recall_marchita')   | ('todos', 'roc_auc')   | ('sin dudosos', 'roc_auc')   |
|:------------------------|:------------------------|:-----------------------------|:-------------------------------|:------------------------------|:-----------------------------------|:-------------------------------------|:-----------------------|:-----------------------------|
| Regla sonda + riego     | 0.795 ± 0.062           | 0.786 ± 0.066                | 0.654 ± 0.169                  | 0.858 ± 0.049                 | 0.860 ± 0.054                      | 0.765 ± 0.145                        | 0.834                  | 0.904                        |
| Dos umbrales (suelo_mv) | 0.762 ± 0.073           | 0.755 ± 0.076                | 0.654 ± 0.169                  | 0.833 ± 0.057                 | 0.834 ± 0.064                      | 0.765 ± 0.145                        | n/d                    | n/d                          |
| Árbol de decisión       | 0.742 ± 0.064           | 0.748 ± 0.071                | 0.631 ± 0.174                  | 0.801 ± 0.055                 | 0.815 ± 0.064                      | 0.739 ± 0.155                        | 0.831                  | 0.889                        |
| Regresión logística     | 0.726 ± 0.068           | 0.748 ± 0.075                | 0.727 ± 0.169                  | 0.791 ± 0.057                 | 0.827 ± 0.064                      | 0.850 ± 0.136                        | 0.805                  | 0.914                        |
| Random Forest           | 0.701 ± 0.074           | 0.694 ± 0.076                | 0.482 ± 0.178                  | 0.758 ± 0.075                 | 0.753 ± 0.080                      | 0.564 ± 0.197                        | 0.817                  | 0.870                        |
| k-NN                    | 0.700 ± 0.058           | 0.690 ± 0.057                | 0.421 ± 0.150                  | 0.744 ± 0.058                 | 0.734 ± 0.059                      | 0.492 ± 0.164                        | 0.807                  | 0.851                        |
| SVM RBF                 | 0.684 ± 0.068           | 0.703 ± 0.072                | 0.565 ± 0.193                  | 0.731 ± 0.077                 | 0.756 ± 0.083                      | 0.661 ± 0.215                        | n/d                    | n/d                          |
| MLP                     | 0.615 ± 0.075           | 0.612 ± 0.066                | 0.254 ± 0.152                  | 0.672 ± 0.079                 | 0.663 ± 0.071                      | 0.297 ± 0.186                        | 0.802                  | 0.845                        |
| Naive Bayes             | 0.513 ± 0.092           | 0.511 ± 0.081                | 0.123 ± 0.108                  | 0.564 ± 0.090                 | 0.561 ± 0.074                      | 0.144 ± 0.117                        | 0.668                  | 0.750                        |
| Umbral único (suelo_mv) | 0.394 ± 0.046           | 0.566 ± 0.057                | 0.737 ± 0.171                  | 0.425 ± 0.043                 | 0.612 ± 0.046                      | 0.862 ± 0.138                        | 0.721                  | 0.764                        |
| Clase mayoritaria       | 0.219 ± 0.084           | 0.238 ± 0.095                | 0.000 ± 0.000                  | 0.188 ± 0.089                 | 0.203 ± 0.102                      | 0.000 ± 0.000                        | 0.416                  | 0.385                        |

## Costo estimado en la ESP32

|                         | config                                                                                  |   flash_B |   ram_B |   ops |   exps |   t_us_est | exportable                           |
|:------------------------|:----------------------------------------------------------------------------------------|----------:|--------:|------:|-------:|-----------:|:-------------------------------------|
| Regla sonda + riego     | [suelo+riego]                                                                           |       111 |      16 |     6 |      0 |      0.250 | sí (if/else o tablas)                |
| Dos umbrales (suelo_mv) | [suelo]                                                                                 |         8 |       0 |     2 |      0 |      0.083 | sí (dos if)                          |
| Árbol de decisión       | [suelo+riego] max_depth=2, min_samples_leaf=20                                          |       111 |      16 |     4 |      0 |      0.167 | sí (if/else o tablas)                |
| Regresión logística     | [suelo+delta] C=0.01                                                                    |        52 |      20 |    25 |      3 |      4.042 | sí (producto matriz-vector)          |
| Random Forest           | [suelo+riego] max_depth=3, min_samples_leaf=20                                          |      6270 |      28 |   270 |      0 |     11.250 | sí (tablas)                          |
| k-NN                    | [suelo+riego+vpd] n_neighbors=5                                                         |     67247 |      56 | 56887 |      0 |   2370.292 | sí, pero guarda todo el train        |
| SVM RBF                 | [suelo+riego+vpd] C=10.0                                                                |     12756 |      28 |  8274 |    636 |    980.750 | sí, pero guarda los vectores soporte |
| MLP                     | [sin luz] alpha=0.001, hidden_layer_sizes=(16, 8)                                       |      1148 |     128 |   562 |      3 |     26.417 | sí (capas densas)                    |
| Naive Bayes             | [suelo+delta]                                                                           |        60 |      12 |    27 |      3 |      4.125 | sí (fórmula cerrada)                 |
| Umbral único (suelo_mv) | [suelo]                                                                                 |        51 |      16 |     2 |      0 |      0.083 | sí (if/else o tablas)                |
| Clase mayoritaria       | [suelo_mv+suelo_delta_1h+temp_c+hum_aire_pct+vpd_kpa+luz_mv+luz_media_1h+h_desde_riego] |         4 |       0 |     0 |      0 |      0.000 | sí (constante)                       |

## Selección

|                         |   puntaje |   desvío |   f1_todos |   recall_marchita |   flash_B |   t_us_est |   interpretabilidad | baseline   | restricciones_ok   | cumple   |
|:------------------------|----------:|---------:|-----------:|------------------:|----------:|-----------:|--------------------:|:-----------|:-------------------|:---------|
| Regla sonda + riego     |     0.858 |    0.049 |      0.795 |             0.765 |       111 |      0.250 |                   1 | False      | True               | True     |
| Dos umbrales (suelo_mv) |     0.833 |    0.057 |      0.762 |             0.765 |         8 |      0.083 |                   1 | True       | True               | False    |
| Árbol de decisión       |     0.801 |    0.055 |      0.742 |             0.739 |       111 |      0.167 |                   1 | False      | True               | False    |
| Regresión logística     |     0.791 |    0.057 |      0.726 |             0.850 |        52 |      4.042 |                   2 | False      | True               | False    |
| Random Forest           |     0.758 |    0.075 |      0.701 |             0.564 |      6270 |     11.250 |                   3 | False      | True               | False    |
| k-NN                    |     0.744 |    0.058 |      0.700 |             0.492 |     67247 |   2370.292 |                   4 | False      | False              | False    |
| SVM RBF                 |     0.731 |    0.077 |      0.684 |             0.661 |     12756 |    980.750 |                   5 | False      | True               | False    |
| MLP                     |     0.672 |    0.079 |      0.615 |             0.297 |      1148 |     26.417 |                   5 | False      | True               | False    |
| Naive Bayes             |     0.564 |    0.090 |      0.513 |             0.144 |        60 |      4.125 |                   2 | False      | True               | False    |
| Umbral único (suelo_mv) |     0.425 |    0.043 |      0.394 |             0.862 |        51 |      0.083 |                   1 | True       | True               | False    |
| Clase mayoritaria       |     0.188 |    0.089 |      0.219 |             0.000 |         4 |      0.000 |                   1 | True       | True               | False    |

## Aporte de cada variable (árbol p3)

|                  |   F1 sin dudosos |     ± |   post-riego (eps 19/23/27) |
|:-----------------|-----------------:|------:|----------------------------:|
| suelo+riego+hr   |            0.805 | 0.050 |                       0.689 |
| sin luz          |            0.805 | 0.050 |                       0.689 |
| suelo+hr         |            0.774 | 0.047 |                       0.000 |
| suelo+riego+temp |            0.751 | 0.068 |                       0.689 |
| suelo+delta      |            0.742 | 0.054 |                       0.357 |
| suelo+riego      |            0.741 | 0.066 |                       0.689 |
| suelo+riego+vpd  |            0.741 | 0.066 |                       0.689 |
| suelo            |            0.710 | 0.064 |                       0.000 |
| suelo+temp       |            0.638 | 0.062 |                       0.000 |
| suelo+vpd        |            0.637 | 0.055 |                       0.000 |

## Modelo final por episodio

|   episodio | clase     | dudoso   |   filas |   suelo_mv |   h_riego_min |   acierto fuera de fold | predicción más común   |
|-----------:|:----------|:---------|--------:|-----------:|--------------:|------------------------:|:-----------------------|
|          1 | marchita  | False    |     132 |   2832.000 |        96.000 |                   1.000 | marchita               |
|          3 | estresada | False    |      24 |   2766.500 |        96.000 |                   0.000 | marchita               |
|          6 | estresada | False    |      74 |   2048.000 |        96.000 |                   0.095 | marchita               |
|          8 | marchita  | True     |     111 |   1518.000 |        96.000 |                   0.000 | saludable              |
|          9 | estresada | True     |      52 |   1454.000 |        96.000 |                   0.000 | saludable              |
|         10 | saludable | False    |     140 |   1504.000 |        96.000 |                   1.000 | saludable              |
|         11 | saludable | True     |      27 |   1785.500 |        30.583 |                   0.000 | estresada              |
|         12 | marchita  | False    |      90 |   1758.000 |        32.833 |                   0.000 | estresada              |
|         13 | estresada | False    |     146 |   1927.000 |        40.333 |                   0.808 | estresada              |
|         14 | estresada | True     |     302 |   1445.000 |         0.000 |                   0.222 | saludable              |
|         15 | saludable | False    |     259 |   1453.000 |        25.167 |                   1.000 | saludable              |
|         16 | saludable | False    |     412 |   1570.000 |        96.000 |                   1.000 | saludable              |
|         17 | estresada | False    |     552 |   1838.000 |        96.000 |                   0.864 | estresada              |
|         18 | marchita  | False    |     144 |   1941.000 |        96.000 |                   0.556 | marchita               |
|         19 | estresada | False    |      60 |   1488.000 |         0.000 |                   1.000 | estresada              |
|         20 | saludable | False    |     672 |   1573.500 |         5.000 |                   0.990 | saludable              |
|         21 | estresada | False    |     552 |   1842.500 |        62.000 |                   0.966 | estresada              |
|         22 | marchita  | False    |     144 |   1962.000 |        96.000 |                   1.000 | marchita               |
|         23 | estresada | False    |      72 |   1523.500 |         0.000 |                   0.764 | estresada              |
|         24 | saludable | False    |     660 |   1610.500 |         7.000 |                   0.815 | saludable              |
|         25 | estresada | False    |     552 |   1872.500 |        62.000 |                   0.926 | estresada              |
|         26 | marchita  | False    |     144 |   1960.000 |        96.000 |                   1.000 | marchita               |
|         27 | estresada | False    |      60 |   1519.000 |         0.000 |                   1.000 | estresada              |
|         28 | saludable | False    |     282 |   1505.500 |         5.000 |                   0.975 | saludable              |

## Deriva de la sonda (mediana suelo_mv)

| clase     |   13–17/09 |   01–03/10 |   03–18/10 |   19–21/10 |
|:----------|-----------:|-----------:|-----------:|-----------:|
| saludable |    nan     |   1504.000 |   1569.500 |   1456.250 |
| estresada |   2064.000 |   1454.000 |   1836.500 |   1461.000 |
| marchita  |   2832.000 |   1518.000 |   1954.000 |   1758.000 |

## Riegos y observación siguiente

|    | riego       | observación siguiente   |   horas después | clase     |   episodio | dudoso   |
|---:|:------------|:------------------------|----------------:|:----------|-----------:|:---------|
|  0 | 07/10 18:00 | 07/10 23:00             |           5.000 | saludable |         20 | False    |
|  1 | 12/10 18:00 | 13/10 00:00             |           6.000 | saludable |         24 | False    |
|  2 | 17/10 18:00 | 17/10 23:00             |           5.000 | saludable |         28 | False    |
|  3 | 19/10 22:40 | 20/10 23:50             |          25.169 | saludable |         15 | False    |

## Hora del día

|                       |   V de Cramér con la franja horaria |
|:----------------------|------------------------------------:|
| clase                 |                               0.242 |
| predicción del modelo |                               0.131 |

## Números clave

|                                                   | valor                                                                                                       |
|:--------------------------------------------------|:------------------------------------------------------------------------------------------------------------|
| snapshot                                          | mediciones_raw_2026-10-23.csv                                                                               |
| filas / episodios (sin dudosos)                   | 5,663 / 24 (5,171 / 20)                                                                                     |
| fuga: aleatoria vs por episodio (exactitud bal.)  | 0.991 vs 0.753                                                                                              |
| mejor candidato / piso                            | Regla sonda + riego 0.858 / 0.809                                                                           |
| elegido                                           | Regla sonda + riego ([suelo+riego])                                                                         |
| coincide con CONFIG_FINAL                         | True                                                                                                        |
| versión / header al día                           | regla-p3-f07-79b556 / True                                                                                  |
| regla                                             | h_desde_riego ≤ 5.5 → estresada; suelo ≤ 1716.0 saludable; ≤ 1939.9 estresada; si no marchita               |
| config. fija: F1 macro (sin dud. / todos)         | 0.858 ± 0.049 / 0.795                                                                                       |
| config. fija: exactitud bal. (sin dud. / todos)   | 0.860 / 0.786                                                                                               |
| config. fija: recall marchita (sin dud. / todos)  | 0.765 / 0.654                                                                                               |
| dos umbrales: F1 macro sin dud.                   | 0.833                                                                                                       |
| costo                                             | {'flash_B': 111, 'ram_B': 16, 'ops': 6, 'exps': 0, 't_us_est': 0.25, 'exportable': 'sí (if/else o tablas)'} |
| condición de seguridad (recall marchita / ep. 12) | 0.765 / 0%                                                                                                  |
| V de Cramér franja ~ clase / predicción           | 0.242 / 0.131                                                                                               |
| datos sin etiqueta 21–22/10                       | 272 filas → {'saludable': 272}                                                                              |
