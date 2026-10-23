<!-- GENERADO por notebooks/03_modelos.ipynb — no editar; se reescribe al re-ejecutar. -->
# Tablas del notebook 03_modelos

Datos: `mediciones_raw_2026-10-23.csv` (sólo lo medido por la placa). Modelo: `arbol-p3-f03-ee3419`.

## Conteo de filas y episodios

|           |   ('todos', 'filas') |   ('todos', 'episodios') |   ('sin dudosos', 'filas') |   ('sin dudosos', 'episodios') |
|:----------|---------------------:|-------------------------:|---------------------------:|-------------------------------:|
| saludable |             2452.000 |                    7.000 |                   2425.000 |                          6.000 |
| estresada |             2446.000 |                   11.000 |                   2092.000 |                          9.000 |
| marchita  |              765.000 |                    6.000 |                    654.000 |                          5.000 |
| total     |             5663.000 |                   24.000 |                   5171.000 |                         20.000 |

## Episodios

|   episodio_id | clase     | origen    | dudoso   |   filas | desde       |   suelo_mv_mediana |   temp_c_mediana |   luz_mv_mediana |
|--------------:|:----------|:----------|:---------|--------:|:------------|-------------------:|-----------------:|-----------------:|
|         1.000 | marchita  | corregida | False    |     132 | 13/09 00:55 |           2832.000 |            8.500 |          189.250 |
|         3.000 | estresada | manual    | False    |      24 | 15/09 13:35 |           2766.500 |           34.200 |         2037.500 |
|         6.000 | estresada | manual    | False    |      74 | 16/09 17:55 |           2048.000 |           14.600 |         2892.250 |
|         8.000 | marchita  | manual    | True     |     111 | 01/10 01:40 |           1518.000 |           20.600 |          142.000 |
|         9.000 | estresada | manual    | True     |      52 | 01/10 10:55 |           1454.000 |           19.000 |         2299.500 |
|        10.000 | saludable | manual    | False    |     140 | 02/10 01:55 |           1504.000 |           18.600 |         1976.750 |
|        11.000 | saludable | propagada | True     |      27 | 19/10 00:35 |           1785.500 |           20.200 |          142.000 |
|        12.000 | marchita  | manual    | False    |      90 | 19/10 02:50 |           1758.000 |           20.200 |          142.000 |
|        13.000 | estresada | manual    | False    |     146 | 19/10 10:20 |           1927.000 |           19.400 |         1674.500 |
|        14.000 | estresada | propagada | True     |     302 | 19/10 22:40 |           1445.000 |           19.800 |          919.750 |
|        15.000 | saludable | manual    | False    |     259 | 20/10 23:50 |           1453.000 |           20.200 |          879.000 |
|        16.000 | saludable | manual    | False    |     412 | 03/10 21:40 |           1570.000 |           20.200 |          850.500 |
|        17.000 | estresada | manual    | False    |     552 | 05/10 08:00 |           1838.000 |           19.700 |         1111.000 |
|        18.000 | marchita  | manual    | False    |     144 | 07/10 06:00 |           1941.000 |           20.500 |         1587.000 |
|        19.000 | estresada | manual    | False    |      60 | 07/10 18:00 |           1488.000 |           20.000 |         1046.500 |
|        20.000 | saludable | manual    | False    |     672 | 07/10 23:00 |           1573.500 |           20.100 |          946.000 |
|        21.000 | estresada | manual    | False    |     552 | 10/10 08:00 |           1842.500 |           19.900 |         1113.000 |
|        22.000 | marchita  | manual    | False    |     144 | 12/10 06:00 |           1962.000 |           20.200 |         1557.500 |
|        23.000 | estresada | manual    | False    |      72 | 12/10 18:00 |           1523.500 |           19.800 |         1050.500 |
|        24.000 | saludable | manual    | False    |     660 | 13/10 01:00 |           1610.500 |           20.400 |          892.500 |
|        25.000 | estresada | manual    | False    |     552 | 15/10 08:00 |           1872.500 |           20.200 |         1102.500 |
|        26.000 | marchita  | manual    | False    |     144 | 17/10 06:00 |           1960.000 |           20.300 |         1590.000 |
|        27.000 | estresada | manual    | False    |      60 | 17/10 18:00 |           1519.000 |           19.800 |         1036.000 |
|        28.000 | saludable | manual    | False    |     282 | 17/10 23:00 |           1505.500 |           20.500 |         1182.000 |

## Fuga: partición aleatoria vs por episodio (exactitud balanceada)

|               |   aleatoria (filas mezcladas) |   por episodio |
|:--------------|------------------------------:|---------------:|
| RF 7 features |                         0.968 |          0.646 |

## Partición por episodio, fuera de fold (± desvío bootstrap por episodio)

|                         | ('todos', 'exactitud_bal')   | ('todos', 'f1_macro')   | ('todos', 'recall_marchita')   | ('sin dudosos', 'exactitud_bal')   | ('sin dudosos', 'f1_macro')   | ('sin dudosos', 'recall_marchita')   | ('todos', 'roc_auc_ovr')   | ('sin dudosos', 'roc_auc_ovr')   |
|:------------------------|:-----------------------------|:------------------------|:-------------------------------|:-----------------------------------|:------------------------------|:-------------------------------------|:---------------------------|:---------------------------------|
| Clase mayoritaria       | 0.192 ± 0.076                | 0.151 ± 0.055           | 0.000 ± 0.000                  | 0.165 ± 0.082                      | 0.128 ± 0.061                 | 0.000 ± 0.000                        | 0.376                      | 0.352                            |
| Umbral único (suelo_mv) | 0.456 ± 0.073                | 0.421 ± 0.079           | 0.188 ± 0.158                  | 0.482 ± 0.090                      | 0.461 ± 0.091                 | 0.220 ± 0.195                        | 0.703                      | 0.785                            |
| Dos umbrales (suelo_mv) | 0.742 ± 0.078                | 0.751 ± 0.075           | 0.609 ± 0.176                  | 0.818 ± 0.067                      | 0.822 ± 0.060                 | 0.713 ± 0.159                        | n/d                        | n/d                              |
| Regresión logística     | 0.547 ± 0.062                | 0.529 ± 0.054           | 0.370 ± 0.155                  | 0.594 ± 0.068                      | 0.578 ± 0.053                 | 0.433 ± 0.178                        | 0.690                      | 0.786                            |
| Árbol de decisión       | 0.719 ± 0.074                | 0.711 ± 0.068           | 0.625 ± 0.176                  | 0.792 ± 0.064                      | 0.779 ± 0.054                 | 0.731 ± 0.158                        | 0.771                      | 0.834                            |
| Random Forest           | 0.655 ± 0.063                | 0.634 ± 0.060           | 0.557 ± 0.146                  | 0.718 ± 0.057                      | 0.692 ± 0.052                 | 0.651 ± 0.130                        | 0.803                      | 0.876                            |
| Naive Bayes             | 0.380 ± 0.069                | 0.371 ± 0.072           | 0.000 ± 0.000                  | 0.401 ± 0.076                      | 0.408 ± 0.072                 | 0.000 ± 0.000                        | 0.587                      | 0.653                            |
| k-NN                    | 0.691 ± 0.061                | 0.688 ± 0.058           | 0.475 ± 0.163                  | 0.739 ± 0.063                      | 0.734 ± 0.058                 | 0.555 ± 0.181                        | 0.824                      | 0.864                            |
| SVM RBF                 | 0.625 ± 0.072                | 0.597 ± 0.066           | 0.544 ± 0.187                  | 0.665 ± 0.081                      | 0.628 ± 0.072                 | 0.636 ± 0.208                        | n/d                        | n/d                              |
| MLP                     | 0.542 ± 0.067                | 0.540 ± 0.071           | 0.186 ± 0.156                  | 0.589 ± 0.073                      | 0.590 ± 0.074                 | 0.217 ± 0.192                        | 0.665                      | 0.742                            |

## Costo estimado en la ESP32

|                         | config                                                                    |   flash_B |   ram_B |   ops |   exps |   t_us_est | exportable                           |
|:------------------------|:--------------------------------------------------------------------------|----------:|--------:|------:|-------:|-----------:|:-------------------------------------|
| Clase mayoritaria       | [suelo_mv+suelo_delta_1h+temp_c+hum_aire_pct+vpd_kpa+luz_mv+luz_media_1h] |         4 |       0 |     0 |      0 |      0.000 | sí (constante)                       |
| Umbral único (suelo_mv) | [suelo]                                                                   |        51 |      16 |     2 |      0 |      0.083 | sí (if/else o tablas)                |
| Dos umbrales (suelo_mv) | [suelo]                                                                   |         8 |       0 |     2 |      0 |      0.083 | sí (dos if)                          |
| Regresión logística     | [suelo+delta+temp] C=1.0                                                  |        72 |      24 |    33 |      3 |      4.375 | sí (producto matriz-vector)          |
| Árbol de decisión       | [suelo+hr] max_depth=3, min_samples_leaf=20                               |       231 |      16 |     6 |      0 |      0.250 | sí (if/else o tablas)                |
| Random Forest           | [suelo+hr] max_depth=5, min_samples_leaf=20                               |     18510 |      28 |   390 |      0 |     16.250 | sí (tablas)                          |
| Naive Bayes             | [suelo+temp+hr]                                                           |        84 |      12 |    39 |      3 |      4.625 | sí (fórmula cerrada)                 |
| k-NN                    | [suelo+delta+vpd] n_neighbors=5                                           |     73643 |      56 | 62299 |      0 |   2595.792 | sí, pero guarda todo el train        |
| SVM RBF                 | [suelo+hr+vpd] C=1.0                                                      |     58276 |      28 | 37862 |   2912 |   4489.583 | sí, pero guarda los vectores soporte |
| MLP                     | [suelo+delta+temp] alpha=0.001, hidden_layer_sizes=(16, 8)                |       932 |     128 |   460 |      3 |     22.167 | sí (capas densas)                    |

## Sensibilidad a dudosos y al ep. 13 — exactitud_bal

| modelo                  |   todos |   sin dudosos |   sin el 13 |   sin dudosos ni el 13 |
|:------------------------|--------:|--------------:|------------:|-----------------------:|
| Clase mayoritaria       |   0.192 |         0.165 |       0.182 |                  0.151 |
| Umbral único (suelo_mv) |   0.456 |         0.482 |       0.461 |                  0.489 |
| Dos umbrales (suelo_mv) |   0.742 |         0.818 |       0.740 |                  0.818 |
| Regresión logística     |   0.547 |         0.594 |       0.548 |                  0.597 |
| Árbol de decisión       |   0.719 |         0.792 |       0.719 |                  0.794 |
| Random Forest           |   0.655 |         0.718 |       0.653 |                  0.718 |
| Naive Bayes             |   0.380 |         0.401 |       0.366 |                  0.384 |
| k-NN                    |   0.691 |         0.739 |       0.691 |                  0.741 |
| SVM RBF                 |   0.625 |         0.665 |       0.622 |                  0.662 |
| MLP                     |   0.542 |         0.589 |       0.538 |                  0.586 |

## Sensibilidad a dudosos y al ep. 13 — f1_macro

| modelo                  |   todos |   sin dudosos |   sin el 13 |   sin dudosos ni el 13 |
|:------------------------|--------:|--------------:|------------:|-----------------------:|
| Clase mayoritaria       |   0.151 |         0.128 |       0.141 |                  0.116 |
| Umbral único (suelo_mv) |   0.421 |         0.461 |       0.430 |                  0.472 |
| Dos umbrales (suelo_mv) |   0.751 |         0.822 |       0.754 |                  0.827 |
| Regresión logística     |   0.529 |         0.578 |       0.532 |                  0.583 |
| Árbol de decisión       |   0.711 |         0.779 |       0.717 |                  0.788 |
| Random Forest           |   0.634 |         0.692 |       0.636 |                  0.697 |
| Naive Bayes             |   0.371 |         0.408 |       0.355 |                  0.391 |
| k-NN                    |   0.688 |         0.734 |       0.691 |                  0.739 |
| SVM RBF                 |   0.597 |         0.628 |       0.597 |                  0.628 |
| MLP                     |   0.540 |         0.590 |       0.536 |                  0.588 |

## Sensibilidad a dudosos y al ep. 13 — recall_marchita

| modelo                  |   todos |   sin dudosos |   sin el 13 |   sin dudosos ni el 13 |
|:------------------------|--------:|--------------:|------------:|-----------------------:|
| Clase mayoritaria       |   0.000 |         0.000 |       0.000 |                  0.000 |
| Umbral único (suelo_mv) |   0.188 |         0.220 |       0.188 |                  0.220 |
| Dos umbrales (suelo_mv) |   0.609 |         0.713 |       0.609 |                  0.713 |
| Regresión logística     |   0.370 |         0.433 |       0.370 |                  0.433 |
| Árbol de decisión       |   0.625 |         0.731 |       0.625 |                  0.731 |
| Random Forest           |   0.557 |         0.651 |       0.557 |                  0.651 |
| Naive Bayes             |   0.000 |         0.000 |       0.000 |                  0.000 |
| k-NN                    |   0.475 |         0.555 |       0.475 |                  0.555 |
| SVM RBF                 |   0.544 |         0.636 |       0.544 |                  0.636 |
| MLP                     |   0.186 |         0.217 |       0.186 |                  0.217 |

## Selección (criterio §5.3)

|                         |   puntaje |   puntaje_desvío |   f1_todos |   exactitud_bal_sd |   recall_marchita_sd |   flash_B |   ram_B |   t_us_est |   interpretabilidad | baseline   | restricciones_ok   | puntaje_ok   | cumple   |
|:------------------------|----------:|-----------------:|-----------:|-------------------:|---------------------:|----------:|--------:|-----------:|--------------------:|:-----------|:-------------------|:-------------|:---------|
| Clase mayoritaria       |     0.128 |            0.061 |      0.151 |              0.165 |                0.000 |         4 |       0 |      0.000 |                   1 | True       | True               | False        | False    |
| Umbral único (suelo_mv) |     0.461 |            0.091 |      0.421 |              0.482 |                0.220 |        51 |      16 |      0.083 |                   1 | True       | True               | False        | False    |
| Dos umbrales (suelo_mv) |     0.822 |            0.060 |      0.751 |              0.818 |                0.713 |         8 |       0 |      0.083 |                   1 | True       | True               | True         | False    |
| Regresión logística     |     0.578 |            0.053 |      0.529 |              0.594 |                0.433 |        72 |      24 |      4.375 |                   2 | False      | True               | False        | False    |
| Árbol de decisión       |     0.779 |            0.054 |      0.711 |              0.792 |                0.731 |       231 |      16 |      0.250 |                   1 | False      | True               | True         | True     |
| Random Forest           |     0.692 |            0.052 |      0.634 |              0.718 |                0.651 |     18510 |      28 |     16.250 |                   3 | False      | True               | False        | False    |
| Naive Bayes             |     0.408 |            0.072 |      0.371 |              0.401 |                0.000 |        84 |      12 |      4.625 |                   2 | False      | True               | False        | False    |
| k-NN                    |     0.734 |            0.058 |      0.688 |              0.739 |                0.555 |     73643 |      56 |   2595.792 |                   4 | False      | False              | True         | False    |
| SVM RBF                 |     0.628 |            0.072 |      0.597 |              0.665 |                0.636 |     58276 |      28 |   4489.583 |                   5 | False      | False              | False        | False    |
| MLP                     |     0.590 |            0.074 |      0.540 |              0.589 |                0.217 |       932 |     128 |     22.167 |                   5 | False      | True               | False        | False    |

## Elegido vs baselines

|                         |   puntaje |   puntaje_desvío |   f1_todos |   exactitud_bal_sd |   recall_marchita_sd |   flash_B |
|:------------------------|----------:|-----------------:|-----------:|-------------------:|---------------------:|----------:|
| Árbol de decisión       |     0.779 |            0.054 |      0.711 |              0.792 |                0.731 |   231.000 |
| Dos umbrales (suelo_mv) |     0.822 |            0.060 |      0.751 |              0.818 |                0.713 |     8.000 |
| Umbral único (suelo_mv) |     0.461 |            0.091 |      0.421 |              0.482 |                0.220 |    51.000 |
| Clase mayoritaria       |     0.128 |            0.061 |      0.151 |              0.165 |                0.000 |     4.000 |

## Restricción de diseño — configuraciones probadas (compuerta de influencia ambiental)

|    | config                                         |   F1 interno |   desvío | dentro_1_desvío   |   flash_B |   % filas que cambian (ambiental → mediana) | cumple   |
|---:|:-----------------------------------------------|-------------:|---------:|:------------------|----------:|--------------------------------------------:|:---------|
|  0 | [suelo+hr] max_depth=2, min_samples_leaf=20    |        0.709 |    0.139 | True              |       111 |                                       0.000 | False    |
|  1 | [suelo+temp] max_depth=2, min_samples_leaf=100 |        0.704 |    0.139 | True              |       111 |                                       0.000 | False    |
|  2 | [suelo+hr] max_depth=2, min_samples_leaf=100   |        0.704 |    0.139 | True              |       111 |                                       0.000 | False    |
|  3 | [suelo+vpd] max_depth=2, min_samples_leaf=100  |        0.704 |    0.139 | True              |       111 |                                       0.000 | False    |
|  4 | [suelo+temp] max_depth=2, min_samples_leaf=20  |        0.680 |    0.143 | True              |       111 |                                       0.000 | False    |
|  5 | [suelo+vpd] max_depth=2, min_samples_leaf=20   |        0.674 |    0.145 | True              |       111 |                                       0.000 | False    |
|  6 | [suelo+hr] max_depth=3, min_samples_leaf=20    |        0.710 |    0.110 | True              |       231 |                                       1.148 | True     |

## Condición de seguridad — embudo por tipo

| tipo                |   configuraciones |   costo |   seguridad |   costo + influencia |   costo + influencia + seguridad |   max_recall_marchita |   max_ep12 |
|:--------------------|------------------:|--------:|------------:|---------------------:|---------------------------------:|----------------------:|-----------:|
| Naive Bayes         |             6.000 |   6.000 |       0.000 |                6.000 |                            0.000 |                 0.156 |      0.000 |
| Random Forest       |            24.000 |  24.000 |       0.000 |               23.000 |                            0.000 |                 0.760 |      0.000 |
| Regresión logística |            18.000 |  18.000 |       0.000 |               18.000 |                            0.000 |                 0.719 |      0.000 |
| Árbol de decisión   |            18.000 |  18.000 |       0.000 |                9.000 |                            0.000 |                 0.731 |      0.000 |

## Condición de seguridad — todas las configuraciones

|                                                                             |   puntaje |   f1_todos |   recall_marchita_sd |   ep12 |   exactitud_bal_sd |   pct_influencia |   pct_marchita_sonda_mojada |   flash_B | costo_ok   | influencia_ok   | seguridad_ok   |
|:----------------------------------------------------------------------------|----------:|-----------:|---------------------:|-------:|-------------------:|-----------------:|----------------------------:|----------:|:-----------|:----------------|:---------------|
| ('Árbol de decisión', '[suelo+temp] max_depth=2, min_samples_leaf=100')     |     0.773 |      0.708 |                0.731 |  0.000 |              0.788 |            0.000 |                       0.000 |       111 | True       | False           | False          |
| ('Árbol de decisión', '[suelo+hr] max_depth=2, min_samples_leaf=100')       |     0.773 |      0.708 |                0.731 |  0.000 |              0.788 |            0.000 |                       0.000 |       111 | True       | False           | False          |
| ('Árbol de decisión', '[suelo+vpd] max_depth=2, min_samples_leaf=100')      |     0.773 |      0.708 |                0.731 |  0.000 |              0.788 |            0.000 |                       0.000 |       111 | True       | False           | False          |
| ('Árbol de decisión', '[suelo+temp+hr] max_depth=2, min_samples_leaf=100')  |     0.773 |      0.708 |                0.731 |  0.000 |              0.788 |            0.000 |                       0.000 |       111 | True       | False           | False          |
| ('Árbol de decisión', '[suelo+temp+vpd] max_depth=2, min_samples_leaf=100') |     0.773 |      0.708 |                0.731 |  0.000 |              0.788 |            0.000 |                       0.000 |       111 | True       | False           | False          |
| ('Árbol de decisión', '[suelo+hr+vpd] max_depth=2, min_samples_leaf=100')   |     0.773 |      0.708 |                0.731 |  0.000 |              0.788 |            0.000 |                       0.000 |       111 | True       | False           | False          |
| ('Árbol de decisión', '[suelo+vpd] max_depth=4, min_samples_leaf=100')      |     0.735 |      0.673 |                0.731 |  0.000 |              0.763 |            5.668 |                       0.000 |       381 | True       | True            | False          |
| ('Random Forest', '[suelo+hr] max_depth=3, min_samples_leaf=100')           |     0.733 |      0.672 |                0.751 |  0.000 |              0.762 |            0.812 |                       0.000 |      5340 | True       | False           | False          |
| ('Random Forest', '[suelo+vpd] max_depth=5, min_samples_leaf=20')           |     0.728 |      0.665 |                0.538 |  0.000 |              0.723 |            9.977 |                       0.000 |     18840 | True       | True            | False          |
| ('Árbol de decisión', '[suelo+hr+vpd] max_depth=4, min_samples_leaf=100')   |     0.725 |      0.664 |                0.690 |  0.000 |              0.749 |            5.668 |                       0.000 |       381 | True       | True            | False          |
| ('Random Forest', '[suelo+vpd] max_depth=5, min_samples_leaf=100')          |     0.723 |      0.663 |                0.760 |  0.000 |              0.760 |            8.388 |                       0.000 |     14340 | True       | True            | False          |
| ('Random Forest', '[suelo+vpd] max_depth=3, min_samples_leaf=100')          |     0.720 |      0.660 |                0.760 |  0.000 |              0.761 |            5.598 |                       0.000 |      5430 | True       | True            | False          |
| ('Árbol de decisión', '[suelo+vpd] max_depth=3, min_samples_leaf=100')      |     0.712 |      0.652 |                0.731 |  0.000 |              0.743 |            0.000 |                       0.000 |       231 | True       | False           | False          |
| ('Random Forest', '[suelo+hr+vpd] max_depth=5, min_samples_leaf=100')       |     0.710 |      0.651 |                0.702 |  0.000 |              0.737 |           11.143 |                       0.000 |     13440 | True       | True            | False          |
| ('Random Forest', '[suelo+hr] max_depth=5, min_samples_leaf=100')           |     0.709 |      0.650 |                0.723 |  0.000 |              0.740 |            6.763 |                       0.000 |     13650 | True       | True            | False          |
| ('Random Forest', '[suelo+temp] max_depth=3, min_samples_leaf=100')         |     0.706 |      0.647 |                0.760 |  0.000 |              0.750 |            7.381 |                       0.000 |      5400 | True       | True            | False          |
| ('Árbol de decisión', '[suelo+hr+vpd] max_depth=3, min_samples_leaf=100')   |     0.702 |      0.644 |                0.690 |  0.000 |              0.729 |            0.000 |                       0.000 |       231 | True       | False           | False          |
| ('Árbol de decisión', '[suelo+hr] max_depth=3, min_samples_leaf=100')       |     0.699 |      0.641 |                0.690 |  0.000 |              0.728 |            0.000 |                       0.000 |       231 | True       | False           | False          |
| ('Random Forest', '[suelo+temp+vpd] max_depth=5, min_samples_leaf=100')     |     0.696 |      0.644 |                0.719 |  0.000 |              0.731 |           20.731 |                       0.000 |     13920 | True       | True            | False          |
| ('Random Forest', '[suelo+temp+vpd] max_depth=3, min_samples_leaf=100')     |     0.694 |      0.637 |                0.728 |  0.000 |              0.730 |           11.902 |                       0.000 |      5100 | True       | True            | False          |
| ('Random Forest', '[suelo+temp] max_depth=5, min_samples_leaf=100')         |     0.689 |      0.632 |                0.751 |  0.000 |              0.733 |           10.383 |                       0.000 |     13890 | True       | True            | False          |
| ('Árbol de decisión', '[suelo+hr] max_depth=4, min_samples_leaf=100')       |     0.687 |      0.628 |                0.690 |  0.000 |              0.721 |            7.417 |                       0.000 |       381 | True       | True            | False          |
| ('Árbol de decisión', '[suelo+temp+hr] max_depth=4, min_samples_leaf=100')  |     0.676 |      0.617 |                0.690 |  0.000 |              0.713 |            5.898 |                       0.000 |       351 | True       | True            | False          |
| ('Random Forest', '[suelo+hr] max_depth=3, min_samples_leaf=20')            |     0.676 |      0.618 |                0.508 |  0.000 |              0.684 |            1.148 |                       0.000 |      6240 | True       | True            | False          |
| ('Random Forest', '[suelo+temp+hr] max_depth=5, min_samples_leaf=100')      |     0.674 |      0.622 |                0.697 |  0.000 |              0.711 |           11.319 |                       0.000 |     13560 | True       | True            | False          |
| ('Random Forest', '[suelo+temp+hr] max_depth=3, min_samples_leaf=100')      |     0.674 |      0.617 |                0.719 |  0.000 |              0.714 |            6.640 |                       0.000 |      4980 | True       | True            | False          |
| ('Árbol de decisión', '[suelo+temp+hr] max_depth=3, min_samples_leaf=100')  |     0.674 |      0.617 |                0.690 |  0.000 |              0.709 |            2.525 |                       0.000 |       231 | True       | True            | False          |
| ('Random Forest', '[suelo+temp] max_depth=5, min_samples_leaf=20')          |     0.671 |      0.615 |                0.506 |  0.000 |              0.680 |            9.818 |                       0.000 |     17610 | True       | True            | False          |
| ('Árbol de decisión', '[suelo+temp] max_depth=4, min_samples_leaf=100')     |     0.671 |      0.612 |                0.485 |  0.000 |              0.680 |            5.898 |                       0.000 |       381 | True       | True            | False          |
| ('Random Forest', '[suelo+hr] max_depth=5, min_samples_leaf=20')            |     0.670 |      0.612 |                0.505 |  0.000 |              0.677 |            7.681 |                       0.000 |     18510 | True       | True            | False          |
| ('Random Forest', '[suelo+vpd] max_depth=3, min_samples_leaf=20')           |     0.664 |      0.608 |                0.558 |  0.000 |              0.687 |            4.715 |                       0.000 |      6270 | True       | True            | False          |
| ('Árbol de decisión', '[suelo+temp+vpd] max_depth=4, min_samples_leaf=100') |     0.663 |      0.605 |                0.485 |  0.000 |              0.674 |            5.898 |                       0.000 |       351 | True       | True            | False          |
| ('Regresión logística', '[suelo+vpd] C=0.1')                                |     0.662 |      0.607 |                0.717 |  0.000 |              0.706 |            2.719 |                       0.000 |        52 | True       | True            | False          |
| ('Regresión logística', '[suelo+vpd] C=1.0')                                |     0.662 |      0.606 |                0.719 |  0.000 |              0.705 |            2.702 |                       0.000 |        52 | True       | True            | False          |
| ('Regresión logística', '[suelo+hr] C=0.01')                                |     0.657 |      0.602 |                0.703 |  0.000 |              0.703 |            5.227 |                       0.000 |        52 | True       | True            | False          |
| ('Random Forest', '[suelo+temp] max_depth=3, min_samples_leaf=20')          |     0.657 |      0.601 |                0.558 |  0.000 |              0.680 |            7.010 |                       0.000 |      5430 | True       | True            | False          |
| ('Random Forest', '[suelo+temp+hr] max_depth=5, min_samples_leaf=20')       |     0.656 |      0.603 |                0.537 |  0.000 |              0.671 |           14.056 |                       0.000 |     17160 | True       | True            | False          |
| ('Random Forest', '[suelo+hr+vpd] max_depth=3, min_samples_leaf=100')       |     0.655 |      0.600 |                0.514 |  0.000 |              0.671 |           10.683 |                       0.000 |      5100 | True       | True            | False          |
| ('Regresión logística', '[suelo+vpd] C=0.01')                               |     0.655 |      0.600 |                0.717 |  0.000 |              0.704 |            2.825 |                       0.000 |        52 | True       | True            | False          |
| ('Random Forest', '[suelo+hr+vpd] max_depth=5, min_samples_leaf=20')        |     0.654 |      0.599 |                0.502 |  0.000 |              0.665 |           12.184 |                       0.000 |     17880 | True       | True            | False          |
| ('Regresión logística', '[suelo+hr] C=1.0')                                 |     0.651 |      0.596 |                0.709 |  0.000 |              0.695 |            5.033 |                       0.000 |        52 | True       | True            | False          |
| ('Random Forest', '[suelo+temp+vpd] max_depth=5, min_samples_leaf=20')      |     0.650 |      0.598 |                0.485 |  0.000 |              0.662 |           14.127 |                       0.000 |     16890 | True       | True            | False          |
| ('Regresión logística', '[suelo+hr] C=0.1')                                 |     0.649 |      0.595 |                0.709 |  0.000 |              0.694 |            5.033 |                       0.000 |        52 | True       | True            | False          |
| ('Regresión logística', '[suelo+hr+vpd] C=0.01')                            |     0.648 |      0.593 |                0.716 |  0.000 |              0.697 |            3.638 |                       0.000 |        72 | True       | True            | False          |
| ('Random Forest', '[suelo+temp+vpd] max_depth=3, min_samples_leaf=20')      |     0.642 |      0.589 |                0.469 |  0.000 |              0.654 |           17.553 |                       0.000 |      5490 | True       | True            | False          |
| ('Random Forest', '[suelo+hr+vpd] max_depth=3, min_samples_leaf=20')        |     0.641 |      0.586 |                0.492 |  0.000 |              0.659 |           20.678 |                       0.000 |      6180 | True       | True            | False          |
| ('Regresión logística', '[suelo+hr+vpd] C=0.1')                             |     0.636 |      0.582 |                0.716 |  0.000 |              0.684 |            2.666 |                       0.000 |        72 | True       | True            | False          |
| ('Regresión logística', '[suelo+hr+vpd] C=1.0')                             |     0.635 |      0.581 |                0.716 |  0.000 |              0.682 |            2.702 |                       0.000 |        72 | True       | True            | False          |
| ('Árbol de decisión', '[suelo+temp+vpd] max_depth=3, min_samples_leaf=100') |     0.627 |      0.573 |                0.485 |  0.000 |              0.641 |            2.525 |                       0.000 |       231 | True       | True            | False          |
| ('Árbol de decisión', '[suelo+temp] max_depth=3, min_samples_leaf=100')     |     0.625 |      0.572 |                0.485 |  0.000 |              0.641 |            2.525 |                       0.000 |       231 | True       | True            | False          |
| ('Random Forest', '[suelo+temp+hr] max_depth=3, min_samples_leaf=20')       |     0.608 |      0.558 |                0.482 |  0.000 |              0.626 |            7.452 |                       0.000 |      5520 | True       | True            | False          |
| ('Naive Bayes', '[suelo+temp+vpd]')                                         |     0.599 |      0.546 |                0.156 |  0.000 |              0.600 |            5.810 |                      92.946 |        84 | True       | True            | False          |
| ('Naive Bayes', '[suelo+temp+hr]')                                          |     0.584 |      0.534 |                0.090 |  0.000 |              0.595 |            4.309 |                      82.988 |        84 | True       | True            | False          |
| ('Regresión logística', '[suelo+temp] C=0.01')                              |     0.582 |      0.532 |                0.454 |  0.000 |              0.601 |            1.183 |                       0.000 |        52 | True       | True            | False          |
| ('Regresión logística', '[suelo+temp+hr] C=0.01')                           |     0.576 |      0.526 |                0.451 |  0.000 |              0.595 |            9.288 |                       0.000 |        72 | True       | True            | False          |
| ('Naive Bayes', '[suelo+hr+vpd]')                                           |     0.570 |      0.521 |                0.069 |  0.000 |              0.585 |            3.691 |                     100.000 |        84 | True       | True            | False          |
| ('Regresión logística', '[suelo+temp] C=0.1')                               |     0.570 |      0.521 |                0.454 |  0.000 |              0.588 |            1.625 |                       0.000 |        52 | True       | True            | False          |
| ('Regresión logística', '[suelo+temp] C=1.0')                               |     0.569 |      0.520 |                0.454 |  0.000 |              0.587 |            2.119 |                       0.000 |        52 | True       | True            | False          |
| ('Regresión logística', '[suelo+temp+hr] C=1.0')                            |     0.564 |      0.515 |                0.420 |  0.000 |              0.578 |           10.436 |                       0.000 |        72 | True       | True            | False          |
| ('Regresión logística', '[suelo+temp+hr] C=0.1')                            |     0.563 |      0.514 |                0.420 |  0.000 |              0.577 |           10.242 |                       0.000 |        72 | True       | True            | False          |
| ('Regresión logística', '[suelo+temp+vpd] C=0.01')                          |     0.560 |      0.511 |                0.472 |  0.000 |              0.583 |            6.851 |                       0.000 |        72 | True       | True            | False          |
| ('Regresión logística', '[suelo+temp+vpd] C=1.0')                           |     0.543 |      0.496 |                0.419 |  0.000 |              0.558 |           11.107 |                       0.000 |        72 | True       | True            | False          |
| ('Naive Bayes', '[suelo+hr]')                                               |     0.542 |      0.497 |                0.000 |  0.000 |              0.577 |            1.960 |                     100.000 |        60 | True       | True            | False          |
| ('Regresión logística', '[suelo+temp+vpd] C=0.1')                           |     0.541 |      0.494 |                0.419 |  0.000 |              0.557 |           10.648 |                       0.000 |        72 | True       | True            | False          |
| ('Naive Bayes', '[suelo+vpd]')                                              |     0.537 |      0.492 |                0.000 |  0.000 |              0.573 |            2.031 |                     100.000 |        60 | True       | True            | False          |
| ('Naive Bayes', '[suelo+temp]')                                             |     0.532 |      0.488 |                0.000 |  0.000 |              0.564 |            3.090 |                      93.776 |        60 | True       | True            | False          |

## Configuraciones del tipo elegido

|                                                                                                 |   F1 macro fuera de fold, sin dudosos |   F1 macro fuera de fold, todos |   exactitud bal. fuera de fold, todos |   % filas predichas marchita (modelo con todo) |   % marchita en la ventana post-arranque descartada |
|:------------------------------------------------------------------------------------------------|--------------------------------------:|--------------------------------:|--------------------------------------:|-----------------------------------------------:|----------------------------------------------------:|
| CONFIG_FINAL: Árbol de decisión [suelo+hr] max_depth=3, min_samples_leaf=20                     |                                 0.711 |                           0.651 |                                 0.669 |                                         10.984 |                                              12.245 |
| criterio de §5.5 (sin seguridad): Árbol de decisión [suelo+hr] max_depth=3, min_samples_leaf=20 |                                 0.711 |                           0.651 |                                 0.669 |                                         10.984 |                                              12.245 |

## Restricción de diseño — sólo suelo vs criterio §5.5 vs final vs dos umbrales — exactitud_bal

| modelo                              |   todos |   sin dudosos |   sin el 13 |   sin dudosos ni el 13 |
|:------------------------------------|--------:|--------------:|------------:|-----------------------:|
| criterio §5.5 (arbol-p3-f03-ee3419) |   0.669 |         0.737 |       0.668 |                  0.737 |
| dos umbrales (baseline)             |   0.742 |         0.818 |       0.740 |                  0.818 |
| final (arbol-p3-f03-ee3419)         |   0.669 |         0.737 |       0.668 |                  0.737 |
| sólo suelo (rf-f0-532763)           |   0.628 |         0.687 |       0.629 |                  0.691 |

## Restricción de diseño — sólo suelo vs criterio §5.5 vs final vs dos umbrales — f1_macro

| modelo                              |   todos |   sin dudosos |   sin el 13 |   sin dudosos ni el 13 |
|:------------------------------------|--------:|--------------:|------------:|-----------------------:|
| criterio §5.5 (arbol-p3-f03-ee3419) |   0.651 |         0.711 |       0.655 |                  0.716 |
| dos umbrales (baseline)             |   0.751 |         0.822 |       0.754 |                  0.827 |
| final (arbol-p3-f03-ee3419)         |   0.651 |         0.711 |       0.655 |                  0.716 |
| sólo suelo (rf-f0-532763)           |   0.621 |         0.678 |       0.627 |                  0.686 |

## Restricción de diseño — sólo suelo vs criterio §5.5 vs final vs dos umbrales — recall_marchita

| modelo                              |   todos |   sin dudosos |   sin el 13 |   sin dudosos ni el 13 |
|:------------------------------------|--------:|--------------:|------------:|-----------------------:|
| criterio §5.5 (arbol-p3-f03-ee3419) |   0.590 |         0.690 |       0.590 |                  0.690 |
| dos umbrales (baseline)             |   0.609 |         0.713 |       0.609 |                  0.713 |
| final (arbol-p3-f03-ee3419)         |   0.590 |         0.690 |       0.590 |                  0.690 |
| sólo suelo (rf-f0-532763)           |   0.442 |         0.517 |       0.442 |                  0.517 |

## Restricción de diseño — resumen

|                                     |   puntaje (F1 sin dudosos) |   desvío bootstrap |   flash estimada (costo_esp32, float, B) |   flash del header exportado (B) |   recall marchita sin dudosos |   ep. 12 | features               |
|:------------------------------------|---------------------------:|-------------------:|-----------------------------------------:|---------------------------------:|------------------------------:|---------:|:-----------------------|
| sólo suelo (rf-f0-532763)           |                      0.678 |              0.063 |                                    24000 |                        24060.000 |                         0.517 |    0.000 | suelo_mv               |
| criterio §5.5 (arbol-p3-f03-ee3419) |                      0.711 |              0.053 |                                      231 |                          231.000 |                         0.690 |    0.000 | suelo_mv, hum_aire_pct |
| final (arbol-p3-f03-ee3419)         |                      0.711 |              0.053 |                                      231 |                          231.000 |                         0.690 |    0.000 | suelo_mv, hum_aire_pct |
| dos umbrales (baseline)             |                      0.822 |              0.060 |                                        8 |                          nan     |                         0.713 |    0.000 | suelo_mv               |

## Influencia ambiental — importancia por permutación

| feature      |   caída exactitud bal. (media) |   desvío |   % predicciones que cambian (media) |
|:-------------|-------------------------------:|---------:|-------------------------------------:|
| suelo_mv     |                          0.466 |    0.006 |                               58.096 |
| hum_aire_pct |                          0.015 |    0.001 |                                1.473 |

## Influencia ambiental — ambiental en la mediana

| ambiental → mediana   |   % filas que cambian |   filas |   episodios afectados |   % de los cambios de noche (22–8 h) |
|:----------------------|----------------------:|--------:|----------------------:|-------------------------------------:|
| hum_aire_pct          |                 1.148 |  65.000 |                 3.000 |                                0.000 |

## Influencia ambiental — por episodio

|   episodio_id | clase     | dudoso   |   filas |   % cambia |   acierto con ambiente |   acierto ambiental en mediana |
|--------------:|:----------|:---------|--------:|-----------:|-----------------------:|-------------------------------:|
|         1.000 | marchita  | False    |     132 |      0.000 |                  1.000 |                          1.000 |
|         3.000 | estresada | False    |      24 |    100.000 |                  1.000 |                          0.000 |
|         6.000 | estresada | False    |      74 |     45.946 |                  0.514 |                          0.054 |
|         8.000 | marchita  | True     |     111 |      0.000 |                  0.000 |                          0.000 |
|         9.000 | estresada | True     |      52 |      0.000 |                  0.000 |                          0.000 |
|        10.000 | saludable | False    |     140 |      0.000 |                  0.950 |                          0.950 |
|        11.000 | saludable | True     |      27 |      0.000 |                  0.000 |                          0.000 |
|        12.000 | marchita  | False    |      90 |      0.000 |                  0.000 |                          0.000 |
|        13.000 | estresada | False    |     146 |      4.795 |                  0.815 |                          0.767 |
|        14.000 | estresada | True     |     302 |      0.000 |                  0.507 |                          0.507 |
|        15.000 | saludable | False    |     259 |      0.000 |                  1.000 |                          1.000 |
|        16.000 | saludable | False    |     412 |      0.000 |                  1.000 |                          1.000 |
|        17.000 | estresada | False    |     552 |      0.000 |                  0.931 |                          0.931 |
|        18.000 | marchita  | False    |     144 |      0.000 |                  0.653 |                          0.653 |
|        19.000 | estresada | False    |      60 |      0.000 |                  0.000 |                          0.000 |
|        20.000 | saludable | False    |     672 |      0.000 |                  0.999 |                          0.999 |
|        21.000 | estresada | False    |     552 |      0.000 |                  0.993 |                          0.993 |
|        22.000 | marchita  | False    |     144 |      0.000 |                  1.000 |                          1.000 |
|        23.000 | estresada | False    |      72 |      0.000 |                  0.000 |                          0.000 |
|        24.000 | saludable | False    |     660 |      0.000 |                  0.898 |                          0.898 |
|        25.000 | estresada | False    |     552 |      0.000 |                  0.926 |                          0.926 |
|        26.000 | marchita  | False    |     144 |      0.000 |                  1.000 |                          1.000 |
|        27.000 | estresada | False    |      60 |      0.000 |                  0.000 |                          0.000 |
|        28.000 | saludable | False    |     282 |      0.000 |                  1.000 |                          1.000 |

## Influencia ambiental — barrido con suelo de octubre

|                                                       | rango medido   | cambia la clase   | clases que recorre   |
|:------------------------------------------------------|:---------------|:------------------|:---------------------|
| ('hum_aire_pct', '1550 (saludable oct. (mediana))')   | 40.31–62       | False             | 40.31–62: saludable  |
| ('hum_aire_pct', '1758 (marchita ep. 12 (mediana))')  | 40.31–62       | False             | 40.31–62: estresada  |
| ('hum_aire_pct', '1927 (estresada ep. 13 (mediana))') | 40.31–62       | False             | 40.31–62: estresada  |
| ('hum_aire_pct', '1654 (entre saludable y marchita)') | 40.31–62       | False             | 40.31–62: saludable  |

## ¿Proxy de la hora? (V de Cramér con la franja)

|                                                    |   V de Cramér con la franja de 3 h |
|:---------------------------------------------------|-----------------------------------:|
| clase                                              |                              0.242 |
| predicción sólo suelo (rf-f0-532763)               |                              0.155 |
| predicción criterio §5.5 (arbol-p3-f03-ee3419)     |                              0.133 |
| predicción final (arbol-p3-f03-ee3419)             |                              0.133 |
| predicción final con las ambientales en la mediana |                              0.127 |
| hum_aire_pct (en terciles)                         |                              0.592 |

## Luz como proxy de la hora — regresiones logísticas con luz

|                                       |   F1 sin dudosos |   recall marchita sin dudosos |   ep. 12 |   % marchita en saludables de noche (train) |   % marchita, datos nuevos de noche |   % marchita, datos nuevos de día |
|:--------------------------------------|-----------------:|------------------------------:|---------:|--------------------------------------------:|------------------------------------:|----------------------------------:|
| [suelo_mv+luz_media_1h] C=0.01        |            0.619 |                         0.645 |    0.867 |                                       8.605 |                               0.000 |                             0.000 |
| [suelo_mv+luz_media_1h] C=0.1         |            0.608 |                         0.604 |    0.544 |                                       6.975 |                               0.000 |                             0.000 |
| [suelo_mv+luz_media_1h] C=1.0         |            0.607 |                         0.601 |    0.511 |                                       6.884 |                               0.000 |                             0.000 |
| [suelo_mv+luz_mv+luz_media_1h] C=0.01 |            0.612 |                         0.607 |    0.556 |                                       7.337 |                               0.000 |                             0.000 |
| [suelo_mv+luz_mv+luz_media_1h] C=0.1  |            0.607 |                         0.566 |    0.333 |                                       4.167 |                               0.000 |                             0.000 |
| [suelo_mv+luz_mv+luz_media_1h] C=1.0  |            0.605 |                         0.557 |    0.322 |                                       3.080 |                               0.000 |                             1.316 |
| [suelo_mv+luz_mv] C=0.01              |            0.602 |                         0.560 |    0.111 |                                       4.620 |                               0.000 |                             0.000 |
| [suelo_mv+luz_mv] C=0.1               |            0.597 |                         0.552 |    0.044 |                                       2.446 |                               0.000 |                             0.000 |
| [suelo_mv+luz_mv] C=1.0               |            0.598 |                         0.552 |    0.044 |                                       2.174 |                               0.000 |                             0.000 |

## Modelo final por episodio

|   episodio | clase     | dudoso   |   filas |   suelo_mv_mediana |   final→salud |   final→estre |   final→march |   acierto final (train) |   acierto fuera de fold |
|-----------:|:----------|:---------|--------:|-------------------:|--------------:|--------------:|--------------:|------------------------:|------------------------:|
|          1 | marchita  | False    |     132 |           2832.000 |         0.000 |         0.000 |         1.000 |                   1.000 |                   1.000 |
|          3 | estresada | False    |      24 |           2766.500 |         0.000 |         1.000 |         0.000 |                   1.000 |                   1.000 |
|          6 | estresada | False    |      74 |           2048.000 |         0.000 |         0.514 |         0.486 |                   0.514 |                   0.270 |
|          8 | marchita  | True     |     111 |           1518.000 |         1.000 |         0.000 |         0.000 |                   0.000 |                   0.000 |
|          9 | estresada | True     |      52 |           1454.000 |         1.000 |         0.000 |         0.000 |                   0.000 |                   0.000 |
|         10 | saludable | False    |     140 |           1504.000 |         0.950 |         0.050 |         0.000 |                   0.950 |                   0.771 |
|         11 | saludable | True     |      27 |           1785.500 |         0.000 |         1.000 |         0.000 |                   0.000 |                   0.000 |
|         12 | marchita  | False    |      90 |           1758.000 |         0.000 |         1.000 |         0.000 |                   0.000 |                   0.000 |
|         13 | estresada | False    |     146 |           1927.000 |         0.000 |         0.815 |         0.185 |                   0.815 |                   0.616 |
|         14 | estresada | True     |     302 |           1445.000 |         0.493 |         0.507 |         0.000 |                   0.507 |                   0.000 |
|         15 | saludable | False    |     259 |           1453.000 |         1.000 |         0.000 |         0.000 |                   1.000 |                   0.332 |
|         16 | saludable | False    |     412 |           1570.000 |         1.000 |         0.000 |         0.000 |                   1.000 |                   1.000 |
|         17 | estresada | False    |     552 |           1838.000 |         0.069 |         0.931 |         0.000 |                   0.931 |                   0.830 |
|         18 | marchita  | False    |     144 |           1941.000 |         0.000 |         0.347 |         0.653 |                   0.653 |                   0.403 |
|         19 | estresada | False    |      60 |           1488.000 |         1.000 |         0.000 |         0.000 |                   0.000 |                   0.000 |
|         20 | saludable | False    |     672 |           1573.500 |         0.999 |         0.001 |         0.000 |                   0.999 |                   1.000 |
|         21 | estresada | False    |     552 |           1842.500 |         0.000 |         0.993 |         0.007 |                   0.993 |                   0.707 |
|         22 | marchita  | False    |     144 |           1962.000 |         0.000 |         0.000 |         1.000 |                   1.000 |                   0.812 |
|         23 | estresada | False    |      72 |           1523.500 |         1.000 |         0.000 |         0.000 |                   0.000 |                   0.000 |
|         24 | saludable | False    |     660 |           1610.500 |         0.898 |         0.102 |         0.000 |                   0.898 |                   0.900 |
|         25 | estresada | False    |     552 |           1872.500 |         0.000 |         0.926 |         0.074 |                   0.926 |                   0.616 |
|         26 | marchita  | False    |     144 |           1960.000 |         0.000 |         0.000 |         1.000 |                   1.000 |                   1.000 |
|         27 | estresada | False    |      60 |           1519.000 |         1.000 |         0.000 |         0.000 |                   0.000 |                   0.000 |
|         28 | saludable | False    |     282 |           1505.500 |         1.000 |         0.000 |         0.000 |                   1.000 |                   1.000 |

## Binario requiere cuidado

|                         |   exactitud_bal (todos) |   recall_cuidado (todos) |   roc_auc (todos) |   exactitud_bal (sin dudosos) |   recall_cuidado (sin dudosos) |   roc_auc (sin dudosos) |
|:------------------------|------------------------:|-------------------------:|------------------:|------------------------------:|-------------------------------:|------------------------:|
| Clase mayoritaria       |                   0.328 |                    0.599 |             0.328 |                         0.315 |                          0.572 |                   0.315 |
| Umbral único (suelo_mv) |                   0.856 |                    0.749 |             0.846 |                         0.924 |                          0.876 |                   0.926 |
| Árbol de decisión       |                   0.821 |                    0.814 |             0.870 |                         0.873 |                          0.908 |                   0.926 |
| Regresión logística     |                   0.818 |                    0.789 |             0.785 |                         0.887 |                          0.918 |                   0.907 |
| Naive Bayes             |                   0.786 |                    0.683 |             0.799 |                         0.847 |                          0.795 |                   0.878 |

## Números clave

|                                                                                 | valor                                                                                                             |
|:--------------------------------------------------------------------------------|:------------------------------------------------------------------------------------------------------------------|
| snapshot                                                                        | mediciones_raw_2026-10-23.csv                                                                                     |
| filas / episodios                                                               | 5,663 / 24                                                                                                        |
| filas / episodios sin dudosos                                                   | 5,171 / 20                                                                                                        |
| episodios dudosos                                                               | [8, 9, 11, 14]                                                                                                    |
| fuga: RF 7 features, aleatoria vs por episodio                                  | 0.968 vs 0.646                                                                                                    |
| criterio §5.3 en el espacio restringido (sin seguridad)                         | Árbol de decisión [suelo+hr] max_depth=3, min_samples_leaf=20                                                     |
| elegido tras la condición de seguridad                                          | Árbol de decisión [suelo+hr] max_depth=3, min_samples_leaf=20 (ninguna configuración la cumple: queda la de §5.5) |
| config final                                                                    | Árbol de decisión [suelo+hr] max_depth=3, min_samples_leaf=20                                                     |
| coincide con CONFIG_FINAL                                                       | True                                                                                                              |
| versión                                                                         | arbol-p3-f03-ee3419                                                                                               |
| header al día                                                                   | True                                                                                                              |
| F1 macro sin dudosos, búsqueda anidada del tipo final                           | 0.779 ± 0.054                                                                                                     |
| F1 macro sin dudosos, dos umbrales                                              | 0.822 ± 0.060                                                                                                     |
| config. final fija: F1 macro (todos / sin dudosos)                              | 0.651 / 0.711                                                                                                     |
| config. final fija: exactitud bal. (todos / sin dudosos)                        | 0.669 / 0.737                                                                                                     |
| config. final fija: recall marchita (todos / sin dudosos)                       | 0.590 / 0.690                                                                                                     |
| config. final fija: exactitud bal. (todos / sin dud. / sin 13 / sin dud. ni 13) | 0.669 / 0.737 / 0.668 / 0.737                                                                                     |
| costo elegido                                                                   | {'flash_B': 231, 'ram_B': 16, 'ops': 6, 'exps': 0, 't_us_est': 0.25, 'exportable': 'sí (if/else o tablas)'}       |
| restricción de diseño                                                           | suelo_mv + al menos una ambiental en todos los candidatos con selección                                           |
| features del modelo final                                                       | suelo_mv, hum_aire_pct                                                                                            |
| % filas que cambian con la ambiental en la mediana                              | 1.148                                                                                                             |
| configuraciones exploradas / que pasan costo + influencia + seguridad           | 66 / 0                                                                                                            |
| puntaje config. fija: sólo suelo / criterio §5.5 / final / dos umbrales         | 0.678 / 0.711 / 0.711 / 0.822                                                                                     |
| V de Cramér franja ~ clase / predicción final / sólo suelo                      | 0.242 / 0.133 / 0.155                                                                                             |
| datos sin etiqueta 21–22/10: filas / predicción                                 | 272 / {'saludable': 272}                                                                                          |
