<!-- GENERADO por notebooks/03_modelos.ipynb — no editar; se reescribe al re-ejecutar. -->
# Tablas del notebook 03_modelos

Relleno: data/sintetico/payloads_relleno.jsonl (2026-10-21 23:58 UTC). Modelo: `rf-f04-7734f6`.

## Conteo de filas y episodios

|           |   ('real (placa)', 'filas') |   ('real (placa)', 'episodios') |   ('relleno simulado', 'filas') |   ('relleno simulado', 'episodios') |   ('serie completa', 'filas') |   ('serie completa', 'episodios') |
|:----------|----------------------------:|--------------------------------:|--------------------------------:|------------------------------------:|------------------------------:|----------------------------------:|
| saludable |                     423.000 |                           3.000 |                        5178.000 |                              10.000 |                      5601.000 |                            12.000 |
| estresada |                     576.000 |                           5.000 |                        2112.000 |                              20.000 |                      2688.000 |                            20.000 |
| marchita  |                     322.000 |                           3.000 |                        2440.000 |                              15.000 |                      2762.000 |                            15.000 |
| total     |                    1321.000 |                          11.000 |                        9730.000 |                              45.000 |                     11051.000 |                            47.000 |

## Fuga: partición aleatoria vs por episodio (exactitud balanceada)

|                                | aleatoria (filas mezcladas)   | por episodio   |
|:-------------------------------|:------------------------------|:---------------|
| serie completa · RF 7 features | 0.887 ± 0.009                 | 0.681 ± 0.133  |
| sólo reales · RF 7 features    | 0.947 ± 0.012                 | 0.291 ± 0.356  |

## Serie completa, CV por episodio (media ± desvío)

|                         | exactitud_bal   | f1_macro      | recall_marchita   | roc_auc_ovr   |
|:------------------------|:----------------|:--------------|:------------------|:--------------|
| Clase mayoritaria       | 0.333 ± 0.000   | 0.232 ± 0.036 | 0.000 ± 0.000     | 0.500 ± 0.000 |
| Umbral único (suelo_mv) | 0.601 ± 0.060   | 0.523 ± 0.058 | 0.823 ± 0.183     | 0.760 ± 0.089 |
| Dos umbrales (suelo_mv) | 0.751 ± 0.118   | 0.749 ± 0.123 | 0.811 ± 0.184     | n/d           |
| Regresión logística     | 0.614 ± 0.142   | 0.606 ± 0.157 | 0.422 ± 0.266     | 0.834 ± 0.065 |
| Árbol de decisión       | 0.728 ± 0.136   | 0.706 ± 0.183 | 0.775 ± 0.171     | 0.817 ± 0.090 |
| Random Forest           | 0.688 ± 0.123   | 0.664 ± 0.150 | 0.797 ± 0.181     | 0.820 ± 0.103 |
| Naive Bayes             | 0.556 ± 0.110   | 0.534 ± 0.109 | 0.415 ± 0.282     | 0.771 ± 0.123 |
| k-NN                    | 0.671 ± 0.124   | 0.652 ± 0.144 | 0.687 ± 0.261     | 0.821 ± 0.085 |
| SVM RBF                 | 0.600 ± 0.163   | 0.601 ± 0.165 | 0.487 ± 0.233     | n/d           |
| MLP                     | 0.625 ± 0.176   | 0.628 ± 0.174 | 0.457 ± 0.244     | 0.793 ± 0.091 |

## Costo estimado en la ESP32

|                         | config                                                   |   flash_B |   ram_B |    ops |   exps |   t_us_est | exportable                           |
|:------------------------|:---------------------------------------------------------|----------:|--------:|-------:|-------:|-----------:|:-------------------------------------|
| Clase mayoritaria       | [todas]                                                  |         4 |       0 |      0 |      0 |      0.000 | sí (constante)                       |
| Umbral único (suelo_mv) | [suelo]                                                  |        51 |      16 |      2 |      0 |      0.083 | sí (if/else o tablas)                |
| Dos umbrales (suelo_mv) | [suelo]                                                  |         8 |       0 |      2 |      0 |      0.083 | sí (dos if)                          |
| Regresión logística     | [suelo+delta+luz1h] C=0.01                               |        72 |      24 |     33 |      3 |      4.375 | sí (producto matriz-vector)          |
| Árbol de decisión       | [suelo+delta+luz1h] max_depth=4, min_samples_leaf=100    |       441 |      16 |      8 |      0 |      0.333 | sí (if/else o tablas)                |
| Random Forest           | [suelo+luz1h] max_depth=5, min_samples_leaf=100          |     17790 |      28 |    390 |      0 |     16.250 | sí (tablas)                          |
| Naive Bayes             | [suelo+luz1h]                                            |        60 |      12 |     27 |      3 |      4.125 | sí (fórmula cerrada)                 |
| k-NN                    | [suelo+delta+luz1h] n_neighbors=5                        |    143687 |      56 | 121567 |      0 |   5065.292 | sí, pero guarda todo el train        |
| SVM RBF                 | [suelo+delta+luz1h] C=1.0                                |    117956 |      28 |  76654 |   5896 |   9089.917 | sí, pero guarda los vectores soporte |
| MLP                     | [suelo+delta+luz1h] alpha=0.001, hidden_layer_sizes=(8,) |       260 |      64 |    124 |      3 |      8.167 | sí (capas densas)                    |

## Selección (criterio §5.3 con puntaje real)

|                         |   f1_macro |   f1_desvío |   exactitud_bal |   recall_marchita |   f1_reales_oof_sd |   f1_sim2real_sd |   puntaje_real |   flash_B |   ram_B |   t_us_est |   interpretabilidad | baseline   | restricciones_ok   | cv_ok   | real_ok   | cumple   |
|:------------------------|-----------:|------------:|----------------:|------------------:|-------------------:|-----------------:|---------------:|----------:|--------:|-----------:|--------------------:|:-----------|:-------------------|:--------|:----------|:---------|
| Clase mayoritaria       |      0.232 |       0.036 |           0.333 |             0.000 |              0.213 |            0.213 |          0.213 |         4 |       0 |      0.000 |                   1 | True       | True               | False   | False     | False    |
| Umbral único (suelo_mv) |      0.523 |       0.058 |           0.601 |             0.823 |              0.550 |            0.557 |          0.553 |        51 |      16 |      0.083 |                   1 | True       | True               | False   | True      | False    |
| Dos umbrales (suelo_mv) |      0.749 |       0.123 |           0.751 |             0.811 |              0.551 |            0.551 |          0.551 |         8 |       0 |      0.083 |                   1 | True       | True               | True    | True      | False    |
| Regresión logística     |      0.606 |       0.157 |           0.614 |             0.422 |              0.564 |            0.539 |          0.551 |        72 |      24 |      4.375 |                   2 | False      | True               | True    | True      | True     |
| Árbol de decisión       |      0.706 |       0.183 |           0.728 |             0.775 |              0.502 |            0.542 |          0.522 |       441 |      16 |      0.333 |                   1 | False      | True               | True    | False     | False    |
| Random Forest           |      0.664 |       0.150 |           0.688 |             0.797 |              0.483 |            0.462 |          0.473 |     17790 |      28 |     16.250 |                   3 | False      | True               | True    | False     | False    |
| Naive Bayes             |      0.534 |       0.109 |           0.556 |             0.415 |              0.731 |            0.634 |          0.682 |        60 |      12 |      4.125 |                   2 | False      | True               | True    | True      | True     |
| k-NN                    |      0.652 |       0.144 |           0.671 |             0.687 |              0.481 |            0.654 |          0.567 |    143687 |      56 |   5065.292 |                   4 | False      | False              | True    | True      | False    |
| SVM RBF                 |      0.601 |       0.165 |           0.600 |             0.487 |              0.571 |            0.499 |          0.535 |    117956 |      28 |   9089.917 |                   5 | False      | False              | True    | True      | False    |
| MLP                     |      0.628 |       0.174 |           0.625 |             0.457 |              0.540 |            0.514 |          0.527 |       260 |      64 |      8.167 |                   5 | False      | True               | True    | False     | False    |

## Elegido vs baselines

|                         |   f1_macro |   exactitud_bal |   recall_marchita |   f1_reales_oof_sd |   f1_sim2real_sd |   puntaje_real |   flash_B |
|:------------------------|-----------:|----------------:|------------------:|-------------------:|-----------------:|---------------:|----------:|
| Naive Bayes             |      0.534 |           0.556 |             0.415 |              0.731 |            0.634 |          0.682 |    60.000 |
| Dos umbrales (suelo_mv) |      0.749 |           0.751 |             0.811 |              0.551 |            0.551 |          0.551 |     8.000 |
| Umbral único (suelo_mv) |      0.523 |           0.601 |             0.823 |              0.550 |            0.557 |          0.553 |    51.000 |
| Clase mayoritaria       |      0.232 |           0.333 |             0.000 |              0.213 |            0.213 |          0.213 |     4.000 |

## Configuraciones del tipo elegido

|                                                                          |   F1 macro serie (CV) |   F1 macro reales fuera de fold, sin dudosos |   exactitud bal. reales fuera de fold |   % reales predichas marchita |   % marchita en la ventana post-arranque descartada |
|:-------------------------------------------------------------------------|----------------------:|---------------------------------------------:|--------------------------------------:|------------------------------:|----------------------------------------------------:|
| CONFIG_FINAL: Random Forest [suelo+vpd] max_depth=5, min_samples_leaf=20 |                 0.720 |                                        0.663 |                                 0.557 |                        23.164 |                                              42.647 |
| criterio original (sin seguridad): Naive Bayes [suelo+temp]              |                 0.589 |                                        0.741 |                                 0.529 |                        16.578 |                                              53.676 |

## Control con reales — exactitud_bal

| modelo                  |   reales fuera de fold |   reales fuera de fold, sin dudosos |   sim → real |   sim → real, sin dudosos |   sólo reales (CV por episodio) |   sólo reales, sin dudosos |
|:------------------------|-----------------------:|------------------------------------:|-------------:|--------------------------:|--------------------------------:|---------------------------:|
| Clase mayoritaria       |                  0.333 |                               0.333 |        0.333 |                     0.333 |                           0.092 |                      0.232 |
| Umbral único (suelo_mv) |                  0.534 |                               0.664 |        0.442 |                     0.664 |                           0.144 |                      0.212 |
| Dos umbrales (suelo_mv) |                  0.536 |                               0.666 |        0.536 |                     0.666 |                           0.314 |                      0.495 |
| Regresión logística     |                  0.452 |                               0.575 |        0.433 |                     0.549 |                           0.311 |                      0.534 |
| Árbol de decisión       |                  0.411 |                               0.561 |        0.532 |                     0.654 |                           0.202 |                      0.371 |
| Random Forest           |                  0.408 |                               0.546 |        0.436 |                     0.544 |                           0.089 |                      0.143 |
| Naive Bayes             |                  0.524 |                               0.731 |        0.488 |                     0.641 |                           0.219 |                      0.407 |
| k-NN                    |                  0.413 |                               0.537 |        0.556 |                     0.717 |                           0.104 |                      0.159 |
| SVM RBF                 |                  0.414 |                               0.575 |        0.415 |                     0.542 |                           0.164 |                      0.238 |
| MLP                     |                  0.460 |                               0.570 |        0.489 |                     0.602 |                           0.166 |                      0.232 |

## Control con reales — f1_macro

| modelo                  |   reales fuera de fold |   reales fuera de fold, sin dudosos |   sim → real |   sim → real, sin dudosos |   sólo reales (CV por episodio) |   sólo reales, sin dudosos |
|:------------------------|-----------------------:|------------------------------------:|-------------:|--------------------------:|--------------------------------:|---------------------------:|
| Clase mayoritaria       |                  0.162 |                               0.213 |        0.162 |                     0.213 |                           0.072 |                      0.106 |
| Umbral único (suelo_mv) |                  0.388 |                               0.550 |        0.351 |                     0.557 |                           0.130 |                      0.225 |
| Dos umbrales (suelo_mv) |                  0.389 |                               0.551 |        0.389 |                     0.551 |                           0.320 |                      0.479 |
| Regresión logística     |                  0.374 |                               0.564 |        0.365 |                     0.539 |                           0.313 |                      0.488 |
| Árbol de decisión       |                  0.328 |                               0.502 |        0.386 |                     0.542 |                           0.195 |                      0.299 |
| Random Forest           |                  0.329 |                               0.483 |        0.323 |                     0.462 |                           0.082 |                      0.115 |
| Naive Bayes             |                  0.476 |                               0.731 |        0.416 |                     0.634 |                           0.205 |                      0.335 |
| k-NN                    |                  0.332 |                               0.481 |        0.436 |                     0.654 |                           0.089 |                      0.141 |
| SVM RBF                 |                  0.370 |                               0.571 |        0.331 |                     0.499 |                           0.144 |                      0.224 |
| MLP                     |                  0.363 |                               0.540 |        0.365 |                     0.514 |                           0.176 |                      0.175 |

## Control con reales — recall_marchita

| modelo                  |   reales fuera de fold |   reales fuera de fold, sin dudosos |   sim → real |   sim → real, sin dudosos |   sólo reales (CV por episodio) |   sólo reales, sin dudosos |
|:------------------------|-----------------------:|------------------------------------:|-------------:|--------------------------:|--------------------------------:|---------------------------:|
| Clase mayoritaria       |                  0.000 |                               0.000 |        0.000 |                     0.000 |                           0.000 |                      0.000 |
| Umbral único (suelo_mv) |                  0.674 |                               1.000 |        0.000 |                     0.000 |                           0.000 |                      0.000 |
| Dos umbrales (suelo_mv) |                  0.674 |                               1.000 |        0.674 |                     1.000 |                           0.407 |                      0.604 |
| Regresión logística     |                  0.422 |                               0.604 |        0.422 |                     0.604 |                           0.236 |                      0.350 |
| Árbol de decisión       |                  0.652 |                               0.968 |        0.696 |                     1.000 |                           0.000 |                      0.000 |
| Random Forest           |                  0.674 |                               1.000 |        0.593 |                     0.866 |                           0.006 |                      0.009 |
| Naive Bayes             |                  0.407 |                               0.604 |        0.407 |                     0.604 |                           0.000 |                      0.000 |
| k-NN                    |                  0.621 |                               0.922 |        0.671 |                     0.995 |                           0.000 |                      0.000 |
| SVM RBF                 |                  0.432 |                               0.641 |        0.575 |                     0.829 |                           0.000 |                      0.000 |
| MLP                     |                  0.457 |                               0.654 |        0.649 |                     0.931 |                           0.121 |                      0.000 |

## Control con reales — roc_auc_ovr

| modelo                  |   reales fuera de fold |   reales fuera de fold, sin dudosos |   sim → real |   sim → real, sin dudosos |   sólo reales (CV por episodio) |   sólo reales, sin dudosos |
|:------------------------|-----------------------:|------------------------------------:|-------------:|--------------------------:|--------------------------------:|---------------------------:|
| Clase mayoritaria       |                  0.500 |                               0.500 |        0.500 |                     0.500 |                           0.302 |                      0.424 |
| Umbral único (suelo_mv) |                  0.504 |                               0.802 |        0.651 |                     0.877 |                           0.241 |                      0.508 |
| Dos umbrales (suelo_mv) |                nan     |                             nan     |      nan     |                   nan     |                         nan     |                    nan     |
| Regresión logística     |                  0.577 |                               0.853 |        0.626 |                     0.828 |                           0.453 |                      0.737 |
| Árbol de decisión       |                  0.588 |                               0.750 |        0.652 |                     0.872 |                           0.273 |                      0.533 |
| Random Forest           |                  0.589 |                               0.812 |        0.625 |                     0.795 |                           0.271 |                      0.412 |
| Naive Bayes             |                  0.525 |                               0.850 |        0.603 |                     0.812 |                           0.400 |                      0.637 |
| k-NN                    |                  0.662 |                               0.764 |        0.685 |                     0.856 |                           0.240 |                      0.344 |
| SVM RBF                 |                nan     |                             nan     |      nan     |                   nan     |                         nan     |                    nan     |
| MLP                     |                  0.506 |                               0.836 |        0.626 |                     0.819 |                           0.327 |                      0.322 |

## Modelo final por episodio real

|   episodio | clase     | dudoso   |   filas |   suelo_mv_mediana |   final→salud |   final→estre |   final→march |   acierto final (train) |   acierto fuera de fold |   acierto sim→real |
|-----------:|:----------|:---------|--------:|-------------------:|--------------:|--------------:|--------------:|------------------------:|------------------------:|-------------------:|
|          1 | marchita  | False    |     131 |           2832.000 |         0.000 |         0.000 |         1.000 |                   1.000 |                   1.000 |              1.000 |
|          3 | estresada | False    |      23 |           2769.500 |         0.000 |         0.000 |         1.000 |                   0.000 |                   0.000 |              0.000 |
|          6 | estresada | False    |      69 |           2050.000 |         0.000 |         0.913 |         0.087 |                   0.913 |                   0.580 |              0.551 |
|          8 | marchita  | True     |     105 |           1512.000 |         1.000 |         0.000 |         0.000 |                   0.000 |                   0.000 |              0.000 |
|          9 | estresada | True     |      51 |           1454.000 |         1.000 |         0.000 |         0.000 |                   0.000 |                   0.000 |              0.000 |
|         10 | saludable | False    |     137 |           1504.000 |         0.978 |         0.022 |         0.000 |                   0.978 |                   0.978 |              0.978 |
|         11 | saludable | True     |      27 |           1785.500 |         0.000 |         0.074 |         0.926 |                   0.000 |                   0.000 |              0.000 |
|         12 | marchita  | False    |      86 |           1758.000 |         0.000 |         0.000 |         1.000 |                   1.000 |                   1.000 |              1.000 |
|         13 | estresada | False    |     136 |           1929.750 |         0.000 |         0.743 |         0.257 |                   0.743 |                   0.000 |              0.000 |
|         14 | estresada | True     |     297 |           1443.500 |         1.000 |         0.000 |         0.000 |                   0.000 |                   0.000 |              0.000 |
|         15 | saludable | False    |     259 |           1453.000 |         1.000 |         0.000 |         0.000 |                   1.000 |                   1.000 |              1.000 |

## Sensibilidad al ep. 13 — exactitud_bal reales fuera de fold

| modelo                  |   todos |   sin dudosos |   sin el 13 |   sin dudosos ni el 13 |
|:------------------------|--------:|--------------:|------------:|-----------------------:|
| Clase mayoritaria       |   0.333 |         0.333 |       0.333 |                  0.333 |
| Umbral único (suelo_mv) |   0.534 |         0.664 |       0.534 |                  0.664 |
| Dos umbrales (suelo_mv) |   0.536 |         0.666 |       0.536 |                  0.666 |
| Regresión logística     |   0.452 |         0.575 |       0.424 |                  0.503 |
| Árbol de decisión       |   0.411 |         0.561 |       0.418 |                  0.641 |
| Random Forest           |   0.408 |         0.546 |       0.412 |                  0.589 |
| Naive Bayes             |   0.524 |         0.731 |       0.445 |                  0.532 |
| k-NN                    |   0.413 |         0.537 |       0.410 |                  0.539 |
| SVM RBF                 |   0.414 |         0.575 |       0.381 |                  0.529 |
| MLP                     |   0.460 |         0.570 |       0.459 |                  0.599 |

## Sensibilidad al ep. 13 — F1 macro reales fuera de fold

| modelo                  |   todos |   sin dudosos |   sin el 13 |   sin dudosos ni el 13 |
|:------------------------|--------:|--------------:|------------:|-----------------------:|
| Clase mayoritaria       |   0.162 |         0.213 |       0.175 |                  0.240 |
| Umbral único (suelo_mv) |   0.388 |         0.550 |       0.425 |                  0.606 |
| Dos umbrales (suelo_mv) |   0.389 |         0.551 |       0.427 |                  0.608 |
| Regresión logística     |   0.374 |         0.564 |       0.350 |                  0.513 |
| Árbol de decisión       |   0.328 |         0.502 |       0.365 |                  0.608 |
| Random Forest           |   0.329 |         0.483 |       0.369 |                  0.554 |
| Naive Bayes             |   0.476 |         0.731 |       0.367 |                  0.531 |
| k-NN                    |   0.332 |         0.481 |       0.359 |                  0.523 |
| SVM RBF                 |   0.370 |         0.571 |       0.341 |                  0.530 |
| MLP                     |   0.363 |         0.540 |       0.389 |                  0.599 |

## Sensibilidad al ep. 13 — exactitud_bal sim → real

| modelo                  |   todos |   sin dudosos |   sin el 13 |   sin dudosos ni el 13 |
|:------------------------|--------:|--------------:|------------:|-----------------------:|
| Clase mayoritaria       |   0.333 |         0.333 |       0.333 |                  0.333 |
| Umbral único (suelo_mv) |   0.442 |         0.664 |       0.379 |                  0.664 |
| Dos umbrales (suelo_mv) |   0.536 |         0.666 |       0.536 |                  0.666 |
| Regresión logística     |   0.433 |         0.549 |       0.413 |                  0.509 |
| Árbol de decisión       |   0.532 |         0.654 |       0.532 |                  0.654 |
| Random Forest           |   0.436 |         0.544 |       0.436 |                  0.544 |
| Naive Bayes             |   0.488 |         0.641 |       0.444 |                  0.530 |
| k-NN                    |   0.556 |         0.717 |       0.562 |                  0.795 |
| SVM RBF                 |   0.415 |         0.542 |       0.399 |                  0.507 |
| MLP                     |   0.489 |         0.602 |       0.489 |                  0.602 |

## Sensibilidad al ep. 13 — F1 macro sim → real

| modelo                  |   todos |   sin dudosos |   sin el 13 |   sin dudosos ni el 13 |
|:------------------------|--------:|--------------:|------------:|-----------------------:|
| Clase mayoritaria       |   0.162 |         0.213 |       0.175 |                  0.240 |
| Umbral único (suelo_mv) |   0.351 |         0.557 |       0.285 |                  0.484 |
| Dos umbrales (suelo_mv) |   0.389 |         0.551 |       0.427 |                  0.608 |
| Regresión logística     |   0.365 |         0.539 |       0.360 |                  0.524 |
| Árbol de decisión       |   0.386 |         0.542 |       0.422 |                  0.596 |
| Random Forest           |   0.323 |         0.462 |       0.350 |                  0.502 |
| Naive Bayes             |   0.416 |         0.634 |       0.366 |                  0.530 |
| k-NN                    |   0.436 |         0.654 |       0.489 |                  0.812 |
| SVM RBF                 |   0.331 |         0.499 |       0.324 |                  0.475 |
| MLP                     |   0.365 |         0.514 |       0.399 |                  0.566 |

## Sensibilidad al ep. 13 — recall marchita sim → real

| modelo                  |   todos |   sin dudosos |   sin el 13 |   sin dudosos ni el 13 |
|:------------------------|--------:|--------------:|------------:|-----------------------:|
| Clase mayoritaria       |   0.000 |         0.000 |       0.000 |                  0.000 |
| Umbral único (suelo_mv) |   0.000 |         0.000 |       0.000 |                  0.000 |
| Dos umbrales (suelo_mv) |   0.674 |         1.000 |       0.674 |                  1.000 |
| Regresión logística     |   0.422 |         0.604 |       0.422 |                  0.604 |
| Árbol de decisión       |   0.696 |         1.000 |       0.696 |                  1.000 |
| Random Forest           |   0.593 |         0.866 |       0.593 |                  0.866 |
| Naive Bayes             |   0.407 |         0.604 |       0.407 |                  0.604 |
| k-NN                    |   0.671 |         0.995 |       0.671 |                  0.995 |
| SVM RBF                 |   0.575 |         0.829 |       0.575 |                  0.829 |
| MLP                     |   0.649 |         0.931 |       0.649 |                  0.931 |

## Binario requiere cuidado

|                         | exactitud_bal   | f1_cuidado    | recall_cuidado   | roc_auc       |   exactitud_bal reales fuera de fold (sin dudosos) |   recall_cuidado reales fuera de fold (sin dudosos) |   exactitud_bal sim → real (sin dudosos) |   recall_cuidado sim → real (sin dudosos) |
|:------------------------|:----------------|:--------------|:-----------------|:--------------|---------------------------------------------------:|----------------------------------------------------:|-----------------------------------------:|------------------------------------------:|
| Clase mayoritaria       | 0.500 ± 0.000   | 0.061 ± 0.122 | 0.200 ± 0.400    | 0.500 ± 0.000 |                                              0.097 |                                               0.193 |                                    0.500 |                                     0.000 |
| Umbral único (suelo_mv) | 0.879 ± 0.073   | 0.859 ± 0.093 | 0.779 ± 0.139    | 0.879 ± 0.073 |                                              0.996 |                                               1.000 |                                    0.996 |                                     1.000 |
| Árbol de decisión       | 0.845 ± 0.076   | 0.785 ± 0.163 | 0.826 ± 0.134    | 0.878 ± 0.100 |                                              0.784 |                                               1.000 |                                    0.981 |                                     1.000 |
| Regresión logística     | 0.873 ± 0.056   | 0.845 ± 0.093 | 0.832 ± 0.124    | 0.899 ± 0.065 |                                              0.966 |                                               1.000 |                                    0.962 |                                     1.000 |
| Naive Bayes             | 0.823 ± 0.126   | 0.811 ± 0.117 | 0.737 ± 0.099    | 0.850 ± 0.135 |                                              1.000 |                                               1.000 |                                    1.000 |                                     1.000 |

## Restricción de diseño — configuraciones probadas (compuerta de influencia ambiental)

|    | config        |   F1 interno |   desvío | dentro_1_desvío   |   flash_B |   % reales que cambian (ambiental → mediana) | cumple   |
|---:|:--------------|-------------:|---------:|:------------------|----------:|---------------------------------------------:|:---------|
|  0 | [suelo+luz1h] |        0.549 |    0.086 | True              |        60 |                                        0.984 | False    |
|  1 | [suelo+luz]   |        0.548 |    0.087 | True              |        60 |                                        0.984 | False    |
|  2 | [suelo+hr]    |        0.514 |    0.118 | True              |        60 |                                        0.908 | False    |
|  3 | [suelo+temp]  |        0.496 |    0.134 | True              |        60 |                                        2.120 | True     |

## Condición de seguridad — embudo por tipo

| tipo                |   configuraciones |   costo |   seguridad |   costo + influencia |   costo + influencia + seguridad |   max_recall_marchita |   max_ep12 |
|:--------------------|------------------:|--------:|------------:|---------------------:|---------------------------------:|----------------------:|-----------:|
| Naive Bayes         |            15.000 |  15.000 |       0.000 |               12.000 |                            0.000 |                 0.604 |      0.000 |
| Random Forest       |            60.000 |  60.000 |      54.000 |               40.000 |                           36.000 |                 1.000 |      1.000 |
| Regresión logística |            45.000 |  45.000 |       0.000 |               42.000 |                            0.000 |                 0.604 |      0.000 |
| Árbol de decisión   |            45.000 |  45.000 |      35.000 |                0.000 |                            0.000 |                 1.000 |      1.000 |

## Condición de seguridad — las 165 configuraciones

|                                                                               |   f1_serie |   f1_desvío |   puntaje_real |   recall_marchita_oof_sd |   ep12_oof |   pct_influencia |   pct_marchita_sonda_mojada |   flash_B | costo_ok   | influencia_ok   | seguridad_ok   |
|:------------------------------------------------------------------------------|-----------:|------------:|---------------:|-------------------------:|-----------:|-----------------:|----------------------------:|----------:|:-----------|:----------------|:---------------|
| ('Random Forest', '[suelo+hr+vpd] max_depth=3, min_samples_leaf=100')         |      0.726 |       0.131 |          0.682 |                    1.000 |      1.000 |            6.737 |                       0.000 |      6690 | True       | True            | True           |
| ('Random Forest', '[suelo+temp+vpd] max_depth=5, min_samples_leaf=20')        |      0.699 |       0.119 |          0.663 |                    1.000 |      1.000 |            6.132 |                       0.000 |     22200 | True       | True            | True           |
| ('Random Forest', '[suelo+vpd] max_depth=5, min_samples_leaf=20')             |      0.720 |       0.141 |          0.661 |                    1.000 |      1.000 |            2.498 |                       0.000 |     23730 | True       | True            | True           |
| ('Random Forest', '[suelo+temp] max_depth=5, min_samples_leaf=20')            |      0.692 |       0.144 |          0.660 |                    1.000 |      1.000 |           11.128 |                       0.000 |     22440 | True       | True            | True           |
| ('Random Forest', '[suelo+temp] max_depth=5, min_samples_leaf=100')           |      0.715 |       0.133 |          0.656 |                    1.000 |      1.000 |            9.235 |                       0.000 |     17040 | True       | True            | True           |
| ('Random Forest', '[suelo+vpd] max_depth=5, min_samples_leaf=100')            |      0.747 |       0.125 |          0.654 |                    1.000 |      1.000 |            6.283 |                       0.000 |     18180 | True       | True            | True           |
| ('Random Forest', '[suelo+temp+luz] max_depth=5, min_samples_leaf=20')        |      0.729 |       0.118 |          0.649 |                    1.000 |      1.000 |            3.861 |                       0.000 |     22230 | True       | True            | True           |
| ('Random Forest', '[suelo+temp+luz] max_depth=5, min_samples_leaf=100')       |      0.705 |       0.134 |          0.647 |                    1.000 |      1.000 |            5.526 |                       0.000 |     17550 | True       | True            | True           |
| ('Random Forest', '[suelo+temp] max_depth=3, min_samples_leaf=100')           |      0.729 |       0.126 |          0.644 |                    1.000 |      1.000 |            2.498 |                       0.000 |      6720 | True       | True            | True           |
| ('Random Forest', '[suelo+temp+vpd] max_depth=5, min_samples_leaf=100')       |      0.700 |       0.149 |          0.644 |                    1.000 |      1.000 |            3.936 |                       0.000 |     16020 | True       | True            | True           |
| ('Random Forest', '[suelo+temp] max_depth=3, min_samples_leaf=20')            |      0.752 |       0.125 |          0.642 |                    1.000 |      1.000 |            2.498 |                       0.000 |      6930 | True       | True            | True           |
| ('Random Forest', '[suelo+vpd+luz] max_depth=5, min_samples_leaf=20')         |      0.735 |       0.100 |          0.641 |                    1.000 |      1.000 |            5.375 |                       0.000 |     23310 | True       | True            | True           |
| ('Random Forest', '[suelo+hr] max_depth=5, min_samples_leaf=100')             |      0.738 |       0.124 |          0.635 |                    1.000 |      1.000 |            8.100 |                       0.000 |     18390 | True       | True            | True           |
| ('Random Forest', '[suelo+temp+hr] max_depth=5, min_samples_leaf=100')        |      0.703 |       0.138 |          0.635 |                    1.000 |      1.000 |            3.861 |                       0.000 |     17280 | True       | True            | True           |
| ('Random Forest', '[suelo+temp+vpd] max_depth=3, min_samples_leaf=20')        |      0.723 |       0.118 |          0.634 |                    1.000 |      1.000 |            2.195 |                       0.000 |      6900 | True       | True            | True           |
| ('Random Forest', '[suelo+temp+vpd] max_depth=3, min_samples_leaf=100')       |      0.710 |       0.145 |          0.634 |                    1.000 |      1.000 |            2.195 |                       0.000 |      6510 | True       | True            | True           |
| ('Random Forest', '[suelo+vpd+luz1h] max_depth=5, min_samples_leaf=100')      |      0.752 |       0.118 |          0.634 |                    1.000 |      1.000 |            3.104 |                       0.000 |     18150 | True       | True            | True           |
| ('Random Forest', '[suelo+vpd] max_depth=3, min_samples_leaf=20')             |      0.755 |       0.121 |          0.632 |                    1.000 |      1.000 |            1.741 |                       0.000 |      6870 | True       | True            | True           |
| ('Random Forest', '[suelo+vpd] max_depth=3, min_samples_leaf=100')            |      0.751 |       0.120 |          0.632 |                    1.000 |      1.000 |            1.741 |                       0.000 |      6660 | True       | True            | True           |
| ('Random Forest', '[suelo+hr+vpd] max_depth=5, min_samples_leaf=100')         |      0.729 |       0.129 |          0.632 |                    1.000 |      1.000 |            4.391 |                       0.000 |     17340 | True       | True            | True           |
| ('Random Forest', '[suelo+vpd+luz] max_depth=5, min_samples_leaf=100')        |      0.747 |       0.113 |          0.632 |                    1.000 |      1.000 |            3.861 |                       0.000 |     18930 | True       | True            | True           |
| ('Random Forest', '[suelo+hr+vpd] max_depth=3, min_samples_leaf=20')          |      0.727 |       0.127 |          0.630 |                    1.000 |      1.000 |            6.889 |                       0.000 |      6900 | True       | True            | True           |
| ('Random Forest', '[suelo+temp+luz1h] max_depth=5, min_samples_leaf=100')     |      0.719 |       0.121 |          0.630 |                    1.000 |      1.000 |            1.211 |                       0.000 |     17040 | True       | True            | True           |
| ('Random Forest', '[suelo+hr] max_depth=5, min_samples_leaf=20')              |      0.736 |       0.127 |          0.623 |                    1.000 |      1.000 |            7.949 |                       0.000 |     23100 | True       | True            | True           |
| ('Random Forest', '[suelo+temp+hr] max_depth=3, min_samples_leaf=20')         |      0.711 |       0.126 |          0.616 |                    1.000 |      1.000 |            1.438 |                       0.000 |      6930 | True       | True            | True           |
| ('Random Forest', '[suelo+temp+hr] max_depth=3, min_samples_leaf=100')        |      0.722 |       0.120 |          0.616 |                    1.000 |      1.000 |            1.741 |                       0.000 |      6540 | True       | True            | True           |
| ('Random Forest', '[suelo+hr+luz] max_depth=5, min_samples_leaf=20')          |      0.718 |       0.123 |          0.613 |                    1.000 |      1.000 |            7.419 |                       0.000 |     23850 | True       | True            | True           |
| ('Random Forest', '[suelo+hr+luz] max_depth=5, min_samples_leaf=100')         |      0.735 |       0.103 |          0.609 |                    1.000 |      1.000 |            1.514 |                       0.000 |     18270 | True       | True            | True           |
| ('Random Forest', '[suelo+luz] max_depth=5, min_samples_leaf=100')            |      0.742 |       0.092 |          0.579 |                    1.000 |      1.000 |            2.498 |                       0.000 |     20520 | True       | True            | True           |
| ('Random Forest', '[suelo+temp+hr] max_depth=5, min_samples_leaf=20')         |      0.715 |       0.136 |          0.578 |                    1.000 |      1.000 |            8.478 |                       0.000 |     22470 | True       | True            | True           |
| ('Random Forest', '[suelo+luz] max_depth=5, min_samples_leaf=20')             |      0.721 |       0.100 |          0.577 |                    1.000 |      1.000 |            9.160 |                       0.000 |     25680 | True       | True            | True           |
| ('Random Forest', '[suelo+luz1h] max_depth=5, min_samples_leaf=20')           |      0.734 |       0.106 |          0.569 |                    0.995 |      0.988 |            5.072 |                       0.000 |     21540 | True       | True            | True           |
| ('Random Forest', '[suelo+luz+luz1h] max_depth=5, min_samples_leaf=20')       |      0.719 |       0.118 |          0.562 |                    0.995 |      0.988 |            5.072 |                       0.000 |     23100 | True       | True            | True           |
| ('Random Forest', '[suelo+luz+luz1h] max_depth=5, min_samples_leaf=100')      |      0.743 |       0.104 |          0.541 |                    1.000 |      1.000 |            1.060 |                       0.000 |     18000 | True       | True            | True           |
| ('Random Forest', '[suelo+luz1h] max_depth=5, min_samples_leaf=100')          |      0.734 |       0.098 |          0.529 |                    1.000 |      1.000 |            2.044 |                       0.000 |     17790 | True       | True            | True           |
| ('Random Forest', '[suelo+hr+luz1h] max_depth=5, min_samples_leaf=100')       |      0.737 |       0.102 |          0.523 |                    0.935 |      0.837 |            3.482 |                       0.000 |     17850 | True       | True            | True           |
| ('Naive Bayes', '[suelo+temp]')                                               |      0.589 |       0.156 |          0.736 |                    0.604 |      0.000 |            2.120 |                      99.170 |        60 | True       | True            | False          |
| ('Naive Bayes', '[suelo+temp+vpd]')                                           |      0.551 |       0.117 |          0.735 |                    0.604 |      0.000 |            3.936 |                      81.328 |        84 | True       | True            | False          |
| ('Naive Bayes', '[suelo+vpd]')                                                |      0.588 |       0.136 |          0.735 |                    0.604 |      0.000 |            1.968 |                      93.776 |        60 | True       | True            | False          |
| ('Naive Bayes', '[suelo+hr+vpd]')                                             |      0.572 |       0.129 |          0.735 |                    0.604 |      0.000 |            3.407 |                      87.137 |        84 | True       | True            | False          |
| ('Naive Bayes', '[suelo+vpd+luz]')                                            |      0.587 |       0.136 |          0.731 |                    0.604 |      0.000 |            2.498 |                      92.531 |        84 | True       | True            | False          |
| ('Naive Bayes', '[suelo+vpd+luz1h]')                                          |      0.586 |       0.136 |          0.731 |                    0.604 |      0.000 |            2.650 |                      92.531 |        84 | True       | True            | False          |
| ('Naive Bayes', '[suelo+temp+hr]')                                            |      0.597 |       0.162 |          0.731 |                    0.604 |      0.000 |            3.785 |                      92.116 |        84 | True       | True            | False          |
| ('Naive Bayes', '[suelo+temp+luz1h]')                                         |      0.589 |       0.157 |          0.730 |                    0.604 |      0.000 |            2.650 |                      97.510 |        84 | True       | True            | False          |
| ('Naive Bayes', '[suelo+temp+luz]')                                           |      0.590 |       0.156 |          0.730 |                    0.604 |      0.000 |            2.650 |                      97.510 |        84 | True       | True            | False          |
| ('Naive Bayes', '[suelo+hr]')                                                 |      0.615 |       0.165 |          0.686 |                    0.604 |      0.000 |            0.908 |                     100.000 |        60 | True       | False           | False          |
| ('Naive Bayes', '[suelo+hr+luz]')                                             |      0.613 |       0.166 |          0.676 |                    0.604 |      0.000 |            1.211 |                     100.000 |        84 | True       | True            | False          |
| ('Naive Bayes', '[suelo+hr+luz1h]')                                           |      0.612 |       0.166 |          0.673 |                    0.604 |      0.000 |            1.438 |                     100.000 |        84 | True       | True            | False          |
| ('Naive Bayes', '[suelo+luz]')                                                |      0.593 |       0.142 |          0.660 |                    0.604 |      0.000 |            0.984 |                     100.000 |        60 | True       | False           | False          |
| ('Naive Bayes', '[suelo+luz1h]')                                              |      0.592 |       0.141 |          0.656 |                    0.604 |      0.000 |            0.984 |                     100.000 |        60 | True       | False           | False          |
| ('Árbol de decisión', '[suelo+luz] max_depth=4, min_samples_leaf=100')        |      0.745 |       0.078 |          0.656 |                    1.000 |      1.000 |            0.000 |                       0.000 |       411 | True       | False           | True           |
| ('Árbol de decisión', '[suelo+luz1h] max_depth=4, min_samples_leaf=100')      |      0.745 |       0.078 |          0.651 |                    1.000 |      1.000 |            0.000 |                       0.000 |       411 | True       | False           | True           |
| ('Árbol de decisión', '[suelo+luz+luz1h] max_depth=4, min_samples_leaf=100')  |      0.742 |       0.077 |          0.651 |                    1.000 |      1.000 |            0.000 |                       0.000 |       411 | True       | False           | True           |
| ('Árbol de decisión', '[suelo+hr] max_depth=4, min_samples_leaf=100')         |      0.739 |       0.085 |          0.632 |                    1.000 |      1.000 |            0.984 |                       0.000 |       411 | True       | False           | True           |
| ('Árbol de decisión', '[suelo+hr+luz] max_depth=4, min_samples_leaf=100')     |      0.741 |       0.089 |          0.632 |                    1.000 |      1.000 |            0.984 |                       0.000 |       411 | True       | False           | True           |
| ('Árbol de decisión', '[suelo+hr+luz1h] max_depth=4, min_samples_leaf=100')   |      0.741 |       0.088 |          0.632 |                    1.000 |      1.000 |            0.984 |                       0.000 |       411 | True       | False           | True           |
| ('Naive Bayes', '[suelo+luz+luz1h]')                                          |      0.591 |       0.143 |          0.631 |                    0.604 |      0.000 |            1.136 |                     100.000 |        84 | True       | True            | False          |
| ('Random Forest', '[suelo+hr+vpd] max_depth=5, min_samples_leaf=20')          |      0.725 |       0.126 |          0.610 |                    0.788 |      1.000 |            6.737 |                       0.000 |     23160 | True       | True            | False          |
| ('Random Forest', '[suelo+temp+luz1h] max_depth=5, min_samples_leaf=20')      |      0.725 |       0.117 |          0.609 |                    0.774 |      1.000 |            5.678 |                       0.000 |     21000 | True       | True            | False          |
| ('Random Forest', '[suelo+hr] max_depth=3, min_samples_leaf=20')              |      0.739 |       0.116 |          0.608 |                    1.000 |      1.000 |            0.000 |                       0.000 |      6930 | True       | False           | True           |
| ('Random Forest', '[suelo+vpd+luz1h] max_depth=5, min_samples_leaf=20')       |      0.737 |       0.098 |          0.594 |                    0.770 |      1.000 |            4.769 |                       0.000 |     23160 | True       | True            | False          |
| ('Regresión logística', '[suelo+temp+vpd] C=1.0')                             |      0.586 |       0.159 |          0.574 |                    0.604 |      0.000 |            5.678 |                       0.000 |        72 | True       | True            | False          |
| ('Árbol de decisión', '[suelo+vpd] max_depth=4, min_samples_leaf=100')        |      0.728 |       0.060 |          0.571 |                    1.000 |      1.000 |            0.000 |                       0.000 |       411 | True       | False           | True           |
| ('Árbol de decisión', '[suelo+vpd+luz] max_depth=4, min_samples_leaf=100')    |      0.731 |       0.062 |          0.571 |                    1.000 |      1.000 |            0.000 |                       0.000 |       411 | True       | False           | True           |
| ('Árbol de decisión', '[suelo+vpd+luz1h] max_depth=4, min_samples_leaf=100')  |      0.731 |       0.062 |          0.571 |                    1.000 |      1.000 |            0.000 |                       0.000 |       411 | True       | False           | True           |
| ('Regresión logística', '[suelo+temp+vpd] C=0.1')                             |      0.591 |       0.161 |          0.569 |                    0.604 |      0.000 |            5.148 |                       0.000 |        72 | True       | True            | False          |
| ('Árbol de decisión', '[suelo+hr+vpd] max_depth=4, min_samples_leaf=100')     |      0.725 |       0.071 |          0.568 |                    1.000 |      1.000 |            0.984 |                       0.000 |       411 | True       | False           | True           |
| ('Random Forest', '[suelo+temp+luz1h] max_depth=3, min_samples_leaf=20')      |      0.723 |       0.137 |          0.567 |                    1.000 |      1.000 |            0.000 |                       0.000 |      6660 | True       | False           | True           |
| ('Random Forest', '[suelo+temp+luz] max_depth=3, min_samples_leaf=20')        |      0.721 |       0.142 |          0.566 |                    1.000 |      1.000 |            0.000 |                       0.000 |      6810 | True       | False           | True           |
| ('Random Forest', '[suelo+hr+luz1h] max_depth=5, min_samples_leaf=20')        |      0.709 |       0.117 |          0.565 |                    0.774 |      1.000 |            6.056 |                       0.000 |     22320 | True       | True            | False          |
| ('Random Forest', '[suelo+vpd+luz1h] max_depth=3, min_samples_leaf=20')       |      0.727 |       0.133 |          0.563 |                    1.000 |      1.000 |            0.000 |                       0.000 |      6780 | True       | False           | True           |
| ('Regresión logística', '[suelo+vpd+luz] C=1.0')                              |      0.595 |       0.173 |          0.563 |                    0.604 |      0.000 |            3.558 |                       0.000 |        72 | True       | True            | False          |
| ('Regresión logística', '[suelo+temp+hr] C=1.0')                              |      0.574 |       0.139 |          0.560 |                    0.604 |      0.000 |           10.598 |                       0.000 |        72 | True       | True            | False          |
| ('Regresión logística', '[suelo+vpd] C=1.0')                                  |      0.588 |       0.172 |          0.560 |                    0.604 |      0.000 |            0.984 |                       0.000 |        52 | True       | False           | False          |
| ('Regresión logística', '[suelo+vpd+luz] C=0.1')                              |      0.596 |       0.173 |          0.560 |                    0.604 |      0.000 |            3.482 |                       0.000 |        72 | True       | True            | False          |
| ('Random Forest', '[suelo+temp+luz] max_depth=3, min_samples_leaf=100')       |      0.739 |       0.127 |          0.558 |                    1.000 |      1.000 |            0.000 |                       0.000 |      6660 | True       | False           | True           |
| ('Random Forest', '[suelo+vpd+luz] max_depth=3, min_samples_leaf=20')         |      0.733 |       0.126 |          0.558 |                    1.000 |      1.000 |            0.000 |                       0.000 |      6840 | True       | False           | True           |
| ('Regresión logística', '[suelo+temp+hr] C=0.1')                              |      0.578 |       0.140 |          0.558 |                    0.604 |      0.000 |           10.220 |                       0.000 |        72 | True       | True            | False          |
| ('Regresión logística', '[suelo+vpd] C=0.1')                                  |      0.590 |       0.170 |          0.557 |                    0.604 |      0.000 |            0.984 |                       0.000 |        52 | True       | False           | False          |
| ('Regresión logística', '[suelo+vpd+luz1h] C=1.0')                            |      0.592 |       0.168 |          0.557 |                    0.604 |      0.000 |            4.693 |                       0.000 |        72 | True       | True            | False          |
| ('Regresión logística', '[suelo+vpd+luz] C=0.01')                             |      0.596 |       0.168 |          0.556 |                    0.604 |      0.000 |            3.028 |                       0.000 |        72 | True       | True            | False          |
| ('Regresión logística', '[suelo+vpd+luz1h] C=0.1')                            |      0.592 |       0.167 |          0.555 |                    0.604 |      0.000 |            4.693 |                       0.000 |        72 | True       | True            | False          |
| ('Regresión logística', '[suelo+temp+luz] C=0.1')                             |      0.595 |       0.163 |          0.554 |                    0.604 |      0.000 |            6.132 |                       0.000 |        72 | True       | True            | False          |
| ('Random Forest', '[suelo+vpd+luz] max_depth=3, min_samples_leaf=100')        |      0.747 |       0.123 |          0.553 |                    1.000 |      1.000 |            0.000 |                       0.000 |      6600 | True       | False           | True           |
| ('Random Forest', '[suelo+temp+luz1h] max_depth=3, min_samples_leaf=100')     |      0.702 |       0.160 |          0.553 |                    0.779 |      0.442 |            0.000 |                       0.000 |      6510 | True       | False           | False          |
| ('Regresión logística', '[suelo+temp+luz] C=1.0')                             |      0.591 |       0.163 |          0.552 |                    0.604 |      0.000 |            6.359 |                       0.000 |        72 | True       | True            | False          |
| ('Regresión logística', '[suelo+vpd] C=0.01')                                 |      0.601 |       0.168 |          0.552 |                    0.604 |      0.000 |            1.060 |                       0.000 |        52 | True       | True            | False          |
| ('Regresión logística', '[suelo+temp+luz] C=0.01')                            |      0.600 |       0.162 |          0.552 |                    0.604 |      0.000 |            5.148 |                       0.000 |        72 | True       | True            | False          |
| ('Regresión logística', '[suelo+temp] C=0.01')                                |      0.608 |       0.172 |          0.551 |                    0.604 |      0.000 |            0.227 |                       0.000 |        52 | True       | False           | False          |
| ('Regresión logística', '[suelo+temp+luz1h] C=0.1')                           |      0.592 |       0.156 |          0.551 |                    0.604 |      0.000 |            8.024 |                       0.000 |        72 | True       | True            | False          |
| ('Regresión logística', '[suelo+temp+luz1h] C=1.0')                           |      0.587 |       0.155 |          0.551 |                    0.604 |      0.000 |            8.024 |                       0.000 |        72 | True       | True            | False          |
| ('Árbol de decisión', '[suelo+temp] max_depth=2, min_samples_leaf=100')       |      0.748 |       0.124 |          0.551 |                    1.000 |      1.000 |            0.000 |                       0.000 |       111 | True       | False           | True           |
| ('Árbol de decisión', '[suelo+hr] max_depth=2, min_samples_leaf=100')         |      0.748 |       0.124 |          0.551 |                    1.000 |      1.000 |            0.000 |                       0.000 |       111 | True       | False           | True           |
| ('Árbol de decisión', '[suelo+hr] max_depth=3, min_samples_leaf=100')         |      0.764 |       0.114 |          0.551 |                    1.000 |      1.000 |            0.000 |                       0.000 |       231 | True       | False           | True           |
| ('Random Forest', '[suelo+hr] max_depth=3, min_samples_leaf=100')             |      0.740 |       0.113 |          0.551 |                    1.000 |      1.000 |            0.000 |                       0.000 |      6630 | True       | False           | True           |
| ('Árbol de decisión', '[suelo+vpd] max_depth=2, min_samples_leaf=100')        |      0.748 |       0.124 |          0.551 |                    1.000 |      1.000 |            0.000 |                       0.000 |       111 | True       | False           | True           |
| ('Árbol de decisión', '[suelo+luz] max_depth=2, min_samples_leaf=100')        |      0.748 |       0.124 |          0.551 |                    1.000 |      1.000 |            0.000 |                       0.000 |       111 | True       | False           | True           |
| ('Árbol de decisión', '[suelo+luz] max_depth=3, min_samples_leaf=100')        |      0.760 |       0.113 |          0.551 |                    1.000 |      1.000 |            0.000 |                       0.000 |       231 | True       | False           | True           |
| ('Random Forest', '[suelo+luz] max_depth=3, min_samples_leaf=20')             |      0.747 |       0.115 |          0.551 |                    1.000 |      1.000 |            0.000 |                       0.000 |      6900 | True       | False           | True           |
| ('Random Forest', '[suelo+luz] max_depth=3, min_samples_leaf=100')            |      0.747 |       0.115 |          0.551 |                    1.000 |      1.000 |            0.000 |                       0.000 |      6900 | True       | False           | True           |
| ('Árbol de decisión', '[suelo+luz1h] max_depth=2, min_samples_leaf=100')      |      0.748 |       0.124 |          0.551 |                    1.000 |      1.000 |            0.000 |                       0.000 |       111 | True       | False           | True           |
| ('Árbol de decisión', '[suelo+luz1h] max_depth=3, min_samples_leaf=100')      |      0.761 |       0.113 |          0.551 |                    1.000 |      1.000 |            0.000 |                       0.000 |       231 | True       | False           | True           |
| ('Random Forest', '[suelo+luz1h] max_depth=3, min_samples_leaf=20')           |      0.738 |       0.106 |          0.551 |                    1.000 |      1.000 |            0.000 |                       0.000 |      6360 | True       | False           | True           |
| ('Árbol de decisión', '[suelo+temp+hr] max_depth=2, min_samples_leaf=100')    |      0.748 |       0.124 |          0.551 |                    1.000 |      1.000 |            0.000 |                       0.000 |       111 | True       | False           | True           |
| ('Árbol de decisión', '[suelo+temp+vpd] max_depth=2, min_samples_leaf=100')   |      0.748 |       0.124 |          0.551 |                    1.000 |      1.000 |            0.000 |                       0.000 |       111 | True       | False           | True           |
| ('Árbol de decisión', '[suelo+temp+luz] max_depth=2, min_samples_leaf=100')   |      0.748 |       0.124 |          0.551 |                    1.000 |      1.000 |            0.000 |                       0.000 |       111 | True       | False           | True           |
| ('Árbol de decisión', '[suelo+temp+luz1h] max_depth=2, min_samples_leaf=100') |      0.748 |       0.124 |          0.551 |                    1.000 |      1.000 |            0.000 |                       0.000 |       111 | True       | False           | True           |
| ('Árbol de decisión', '[suelo+hr+vpd] max_depth=2, min_samples_leaf=100')     |      0.748 |       0.124 |          0.551 |                    1.000 |      1.000 |            0.000 |                       0.000 |       111 | True       | False           | True           |
| ('Árbol de decisión', '[suelo+hr+luz] max_depth=2, min_samples_leaf=100')     |      0.748 |       0.124 |          0.551 |                    1.000 |      1.000 |            0.000 |                       0.000 |       111 | True       | False           | True           |
| ('Árbol de decisión', '[suelo+hr+luz] max_depth=3, min_samples_leaf=100')     |      0.764 |       0.114 |          0.551 |                    1.000 |      1.000 |            0.000 |                       0.000 |       231 | True       | False           | True           |
| ('Árbol de decisión', '[suelo+hr+luz1h] max_depth=2, min_samples_leaf=100')   |      0.748 |       0.124 |          0.551 |                    1.000 |      1.000 |            0.000 |                       0.000 |       111 | True       | False           | True           |
| ('Árbol de decisión', '[suelo+hr+luz1h] max_depth=3, min_samples_leaf=100')   |      0.764 |       0.114 |          0.551 |                    1.000 |      1.000 |            0.000 |                       0.000 |       231 | True       | False           | True           |
| ('Árbol de decisión', '[suelo+vpd+luz] max_depth=2, min_samples_leaf=100')    |      0.748 |       0.124 |          0.551 |                    1.000 |      1.000 |            0.000 |                       0.000 |       111 | True       | False           | True           |
| ('Árbol de decisión', '[suelo+vpd+luz1h] max_depth=2, min_samples_leaf=100')  |      0.748 |       0.124 |          0.551 |                    1.000 |      1.000 |            0.000 |                       0.000 |       111 | True       | False           | True           |
| ('Árbol de decisión', '[suelo+luz+luz1h] max_depth=2, min_samples_leaf=100')  |      0.748 |       0.124 |          0.551 |                    1.000 |      1.000 |            0.000 |                       0.000 |       111 | True       | False           | True           |
| ('Árbol de decisión', '[suelo+luz+luz1h] max_depth=3, min_samples_leaf=100')  |      0.761 |       0.113 |          0.551 |                    1.000 |      1.000 |            0.000 |                       0.000 |       231 | True       | False           | True           |
| ('Random Forest', '[suelo+hr+luz] max_depth=3, min_samples_leaf=20')          |      0.725 |       0.119 |          0.550 |                    1.000 |      1.000 |            0.000 |                       0.000 |      6930 | True       | False           | True           |
| ('Regresión logística', '[suelo+hr+luz] C=0.01')                              |      0.591 |       0.163 |          0.549 |                    0.604 |      0.000 |            1.817 |                       0.000 |        72 | True       | True            | False          |
| ('Regresión logística', '[suelo+vpd+luz1h] C=0.01')                           |      0.595 |       0.163 |          0.549 |                    0.604 |      0.000 |            3.936 |                       0.000 |        72 | True       | True            | False          |
| ('Regresión logística', '[suelo+hr] C=0.01')                                  |      0.601 |       0.168 |          0.547 |                    0.604 |      0.000 |            1.741 |                       0.000 |        52 | True       | True            | False          |
| ('Regresión logística', '[suelo+temp] C=0.1')                                 |      0.600 |       0.172 |          0.547 |                    0.604 |      0.000 |            1.590 |                       0.000 |        52 | True       | True            | False          |
| ('Random Forest', '[suelo+vpd+luz1h] max_depth=3, min_samples_leaf=100')      |      0.744 |       0.126 |          0.547 |                    0.917 |      0.791 |            0.000 |                       0.000 |      6540 | True       | False           | True           |
| ('Regresión logística', '[suelo+temp+luz1h] C=0.01')                          |      0.593 |       0.153 |          0.547 |                    0.604 |      0.000 |            6.586 |                       0.000 |        72 | True       | True            | False          |
| ('Regresión logística', '[suelo+hr+luz] C=0.1')                               |      0.587 |       0.163 |          0.547 |                    0.604 |      0.000 |            2.952 |                       0.000 |        72 | True       | True            | False          |
| ('Regresión logística', '[suelo+hr+luz] C=1.0')                               |      0.586 |       0.164 |          0.546 |                    0.604 |      0.000 |            2.877 |                       0.000 |        72 | True       | True            | False          |
| ('Regresión logística', '[suelo+hr+luz1h] C=0.01')                            |      0.589 |       0.158 |          0.545 |                    0.604 |      0.000 |            2.801 |                       0.000 |        72 | True       | True            | False          |
| ('Regresión logística', '[suelo+temp] C=1.0')                                 |      0.599 |       0.172 |          0.543 |                    0.604 |      0.000 |            2.195 |                       0.000 |        52 | True       | True            | False          |
| ('Regresión logística', '[suelo+hr+luz1h] C=1.0')                             |      0.584 |       0.162 |          0.542 |                    0.604 |      0.000 |            3.785 |                       0.000 |        72 | True       | True            | False          |
| ('Regresión logística', '[suelo+hr+luz1h] C=0.1')                             |      0.585 |       0.161 |          0.542 |                    0.604 |      0.000 |            3.634 |                       0.000 |        72 | True       | True            | False          |
| ('Regresión logística', '[suelo+hr] C=0.1')                                   |      0.586 |       0.172 |          0.542 |                    0.604 |      0.000 |            1.817 |                       0.000 |        52 | True       | True            | False          |
| ('Regresión logística', '[suelo+hr] C=1.0')                                   |      0.584 |       0.172 |          0.540 |                    0.604 |      0.000 |            1.817 |                       0.000 |        52 | True       | True            | False          |
| ('Regresión logística', '[suelo+temp+hr] C=0.01')                             |      0.593 |       0.154 |          0.539 |                    0.604 |      0.000 |            6.662 |                       0.000 |        72 | True       | True            | False          |
| ('Regresión logística', '[suelo+temp+vpd] C=0.01')                            |      0.606 |       0.170 |          0.538 |                    0.604 |      0.000 |            1.211 |                       0.000 |        72 | True       | True            | False          |
| ('Regresión logística', '[suelo+hr+vpd] C=1.0')                               |      0.581 |       0.169 |          0.533 |                    0.604 |      0.000 |            3.179 |                       0.000 |        72 | True       | True            | False          |
| ('Random Forest', '[suelo+hr+luz] max_depth=3, min_samples_leaf=100')         |      0.739 |       0.121 |          0.532 |                    1.000 |      1.000 |            0.000 |                       0.000 |      6750 | True       | False           | True           |
| ('Random Forest', '[suelo+luz1h] max_depth=3, min_samples_leaf=100')          |      0.738 |       0.105 |          0.531 |                    1.000 |      1.000 |            0.000 |                       0.000 |      6360 | True       | False           | True           |
| ('Random Forest', '[suelo+hr+luz1h] max_depth=3, min_samples_leaf=20')        |      0.726 |       0.116 |          0.531 |                    1.000 |      1.000 |            0.000 |                       0.000 |      6810 | True       | False           | True           |
| ('Regresión logística', '[suelo+hr+vpd] C=0.1')                               |      0.585 |       0.169 |          0.528 |                    0.604 |      0.000 |            3.255 |                       0.000 |        72 | True       | True            | False          |
| ('Regresión logística', '[suelo+luz+luz1h] C=0.1')                            |      0.592 |       0.174 |          0.528 |                    0.604 |      0.000 |            4.164 |                       0.000 |        72 | True       | True            | False          |
| ('Regresión logística', '[suelo+luz+luz1h] C=1.0')                            |      0.592 |       0.175 |          0.528 |                    0.604 |      0.000 |            4.012 |                       0.000 |        72 | True       | True            | False          |
| ('Regresión logística', '[suelo+hr+vpd] C=0.01')                              |      0.597 |       0.170 |          0.526 |                    0.604 |      0.000 |            3.179 |                       0.000 |        72 | True       | True            | False          |
| ('Regresión logística', '[suelo+luz] C=1.0')                                  |      0.593 |       0.176 |          0.525 |                    0.604 |      0.000 |            3.482 |                       0.000 |        52 | True       | True            | False          |
| ('Regresión logística', '[suelo+luz] C=0.1')                                  |      0.593 |       0.176 |          0.524 |                    0.604 |      0.000 |            3.558 |                       0.000 |        52 | True       | True            | False          |
| ('Regresión logística', '[suelo+luz1h] C=0.1')                                |      0.591 |       0.173 |          0.524 |                    0.604 |      0.000 |            4.012 |                       0.000 |        52 | True       | True            | False          |
| ('Regresión logística', '[suelo+luz1h] C=1.0')                                |      0.591 |       0.174 |          0.524 |                    0.604 |      0.000 |            3.936 |                       0.000 |        52 | True       | True            | False          |
| ('Árbol de decisión', '[suelo+vpd] max_depth=3, min_samples_leaf=100')        |      0.764 |       0.114 |          0.522 |                    1.000 |      1.000 |            0.000 |                       0.000 |       231 | True       | False           | True           |
| ('Árbol de decisión', '[suelo+hr+vpd] max_depth=3, min_samples_leaf=100')     |      0.764 |       0.114 |          0.522 |                    1.000 |      1.000 |            0.000 |                       0.000 |       231 | True       | False           | True           |
| ('Árbol de decisión', '[suelo+vpd+luz] max_depth=3, min_samples_leaf=100')    |      0.764 |       0.114 |          0.522 |                    1.000 |      1.000 |            0.000 |                       0.000 |       231 | True       | False           | True           |
| ('Árbol de decisión', '[suelo+vpd+luz1h] max_depth=3, min_samples_leaf=100')  |      0.764 |       0.114 |          0.522 |                    1.000 |      1.000 |            0.000 |                       0.000 |       231 | True       | False           | True           |
| ('Regresión logística', '[suelo+luz] C=0.01')                                 |      0.599 |       0.177 |          0.521 |                    0.604 |      0.000 |            2.574 |                       0.000 |        52 | True       | True            | False          |
| ('Regresión logística', '[suelo+luz+luz1h] C=0.01')                           |      0.593 |       0.167 |          0.521 |                    0.604 |      0.000 |            3.407 |                       0.000 |        72 | True       | True            | False          |
| ('Regresión logística', '[suelo+luz1h] C=0.01')                               |      0.594 |       0.168 |          0.520 |                    0.604 |      0.000 |            3.028 |                       0.000 |        52 | True       | True            | False          |
| ('Random Forest', '[suelo+luz+luz1h] max_depth=3, min_samples_leaf=20')       |      0.732 |       0.108 |          0.518 |                    1.000 |      1.000 |            0.000 |                       0.000 |      6690 | True       | False           | True           |
| ('Random Forest', '[suelo+luz+luz1h] max_depth=3, min_samples_leaf=100')      |      0.723 |       0.110 |          0.518 |                    1.000 |      1.000 |            0.000 |                       0.000 |      6600 | True       | False           | True           |
| ('Random Forest', '[suelo+hr+luz1h] max_depth=3, min_samples_leaf=100')       |      0.687 |       0.169 |          0.505 |                    0.691 |      0.221 |            0.000 |                       0.000 |      6750 | True       | False           | False          |
| ('Árbol de decisión', '[suelo+temp] max_depth=3, min_samples_leaf=100')       |      0.753 |       0.116 |          0.501 |                    0.396 |      1.000 |            0.000 |                       0.000 |       231 | True       | False           | False          |
| ('Árbol de decisión', '[suelo+temp+hr] max_depth=3, min_samples_leaf=100')    |      0.748 |       0.117 |          0.501 |                    0.396 |      1.000 |            0.000 |                       0.000 |       231 | True       | False           | False          |
| ('Árbol de decisión', '[suelo+temp+vpd] max_depth=3, min_samples_leaf=100')   |      0.751 |       0.116 |          0.501 |                    0.396 |      1.000 |            0.000 |                       0.000 |       231 | True       | False           | False          |
| ('Árbol de decisión', '[suelo+temp+luz] max_depth=3, min_samples_leaf=100')   |      0.750 |       0.117 |          0.501 |                    0.396 |      1.000 |            0.000 |                       0.000 |       231 | True       | False           | False          |
| ('Árbol de decisión', '[suelo+temp+luz] max_depth=4, min_samples_leaf=100')   |      0.701 |       0.096 |          0.501 |                    0.396 |      1.000 |            0.000 |                       0.000 |       411 | True       | False           | False          |
| ('Árbol de decisión', '[suelo+temp+luz1h] max_depth=3, min_samples_leaf=100') |      0.750 |       0.117 |          0.501 |                    0.396 |      1.000 |            0.000 |                       0.000 |       231 | True       | False           | False          |
| ('Árbol de decisión', '[suelo+temp] max_depth=4, min_samples_leaf=100')       |      0.698 |       0.093 |          0.499 |                    0.396 |      1.000 |            0.000 |                       0.000 |       411 | True       | False           | False          |
| ('Árbol de decisión', '[suelo+temp+vpd] max_depth=4, min_samples_leaf=100')   |      0.683 |       0.072 |          0.498 |                    0.396 |      1.000 |            0.000 |                       0.000 |       411 | True       | False           | False          |
| ('Árbol de decisión', '[suelo+temp+luz1h] max_depth=4, min_samples_leaf=100') |      0.701 |       0.096 |          0.498 |                    0.396 |      1.000 |            0.000 |                       0.000 |       411 | True       | False           | False          |
| ('Árbol de decisión', '[suelo+temp+hr] max_depth=4, min_samples_leaf=100')    |      0.680 |       0.089 |          0.495 |                    0.396 |      1.000 |            0.984 |                       0.000 |       411 | True       | False           | False          |

## Restricción de diseño — sólo suelo vs criterio original vs nuevo vs dos umbrales, reales — exactitud_bal

|                                                               |   todos |   sin dudosos |   sin el 13 |   sin dudosos ni el 13 |
|:--------------------------------------------------------------|--------:|--------------:|------------:|-----------------------:|
| ('criterio original (nb-f02-fa0df4)', 'reales fuera de fold') |   0.529 |         0.741 |       0.451 |                  0.555 |
| ('criterio original (nb-f02-fa0df4)', 'sim → real')           |   0.523 |         0.730 |       0.445 |                  0.531 |
| ('dos umbrales (baseline)', 'reales fuera de fold')           |   0.536 |         0.666 |       0.536 |                  0.666 |
| ('dos umbrales (baseline)', 'sim → real')                     |   0.536 |         0.666 |       0.536 |                  0.666 |
| ('nuevo (rf-f04-7734f6)', 'reales fuera de fold')             |   0.557 |         0.723 |       0.565 |                  0.809 |
| ('nuevo (rf-f04-7734f6)', 'sim → real')                       |   0.556 |         0.720 |       0.563 |                  0.802 |
| ('sólo suelo (rf-f0-c42286)', 'reales fuera de fold')         |   0.487 |         0.644 |       0.494 |                  0.724 |
| ('sólo suelo (rf-f0-c42286)', 'sim → real')                   |   0.557 |         0.717 |       0.563 |                  0.797 |

## Restricción de diseño — sólo suelo vs criterio original vs nuevo vs dos umbrales, reales — f1_macro

|                                                               |   todos |   sin dudosos |   sin el 13 |   sin dudosos ni el 13 |
|:--------------------------------------------------------------|--------:|--------------:|------------:|-----------------------:|
| ('criterio original (nb-f02-fa0df4)', 'reales fuera de fold') |   0.483 |         0.741 |       0.376 |                  0.556 |
| ('criterio original (nb-f02-fa0df4)', 'sim → real')           |   0.476 |         0.730 |       0.366 |                  0.530 |
| ('dos umbrales (baseline)', 'reales fuera de fold')           |   0.389 |         0.551 |       0.427 |                  0.608 |
| ('dos umbrales (baseline)', 'sim → real')                     |   0.389 |         0.551 |       0.427 |                  0.608 |
| ('nuevo (rf-f04-7734f6)', 'reales fuera de fold')             |   0.442 |         0.663 |       0.497 |                  0.827 |
| ('nuevo (rf-f04-7734f6)', 'sim → real')                       |   0.439 |         0.658 |       0.492 |                  0.819 |
| ('sólo suelo (rf-f0-c42286)', 'reales fuera de fold')         |   0.399 |         0.591 |       0.449 |                  0.698 |
| ('sólo suelo (rf-f0-c42286)', 'sim → real')                   |   0.439 |         0.655 |       0.492 |                  0.814 |

## Restricción de diseño — sólo suelo vs criterio original vs nuevo vs dos umbrales, reales — recall_marchita

|                                                               |   todos |   sin dudosos |   sin el 13 |   sin dudosos ni el 13 |
|:--------------------------------------------------------------|--------:|--------------:|------------:|-----------------------:|
| ('criterio original (nb-f02-fa0df4)', 'reales fuera de fold') |   0.407 |         0.604 |       0.407 |                  0.604 |
| ('criterio original (nb-f02-fa0df4)', 'sim → real')           |   0.407 |         0.604 |       0.407 |                  0.604 |
| ('dos umbrales (baseline)', 'reales fuera de fold')           |   0.674 |         1.000 |       0.674 |                  1.000 |
| ('dos umbrales (baseline)', 'sim → real')                     |   0.674 |         1.000 |       0.674 |                  1.000 |
| ('nuevo (rf-f04-7734f6)', 'reales fuera de fold')             |   0.674 |         1.000 |       0.674 |                  1.000 |
| ('nuevo (rf-f04-7734f6)', 'sim → real')                       |   0.674 |         1.000 |       0.674 |                  1.000 |
| ('sólo suelo (rf-f0-c42286)', 'reales fuera de fold')         |   0.677 |         1.000 |       0.677 |                  1.000 |
| ('sólo suelo (rf-f0-c42286)', 'sim → real')                   |   0.677 |         1.000 |       0.677 |                  1.000 |

## Restricción de diseño — resumen

|                                   | F1 macro serie (CV, config. fija)   |   puntaje real (config. fija) |   flash estimada (costo_esp32, float, B) |   flash del header exportado (B) |   recall marchita reales oof s/d |   ep. 12 oof | features          |
|:----------------------------------|:------------------------------------|------------------------------:|-----------------------------------------:|---------------------------------:|---------------------------------:|-------------:|:------------------|
| sólo suelo (rf-f0-c42286)         | 0.715 ± 0.112                       |                         0.623 |                                    24600 |                        24660.000 |                            1.000 |        1.000 | suelo_mv          |
| criterio original (nb-f02-fa0df4) | 0.589 ± 0.156                       |                         0.736 |                                       60 |                          122.000 |                            0.604 |        0.000 | suelo_mv, temp_c  |
| nuevo (rf-f04-7734f6)             | 0.720 ± 0.141                       |                         0.661 |                                    23730 |                        23790.000 |                            1.000 |        1.000 | suelo_mv, vpd_kpa |
| dos umbrales (baseline)           | 0.749 ± 0.123                       |                         0.551 |                                        8 |                          nan     |                            1.000 |        1.000 | suelo_mv          |

## Influencia ambiental — importancia por permutación (filas reales)

|                            |   caída exactitud bal. (media) |   desvío |   % predicciones que cambian (media) |
|:---------------------------|-------------------------------:|---------:|-------------------------------------:|
| ('final', 'suelo_mv')      |                          0.300 |    0.010 |                               51.289 |
| ('final', 'vpd_kpa')       |                          0.021 |    0.004 |                                5.307 |
| ('sim → real', 'suelo_mv') |                          0.241 |    0.010 |                               48.251 |
| ('sim → real', 'vpd_kpa')  |                          0.026 |    0.005 |                                8.183 |

## Influencia ambiental — ambiental en la mediana (filas reales)

|                                                  |   % filas reales que cambian |   filas |   episodios afectados |   % de los cambios de noche (22–8 h) |
|:-------------------------------------------------|-----------------------------:|--------:|----------------------:|-------------------------------------:|
| ('final', 'vpd_kpa', 'mediana de la serie')      |                        2.498 |  33.000 |                 2.000 |                                0.000 |
| ('final', 'vpd_kpa', 'mediana de lo real')       |                        2.498 |  33.000 |                 2.000 |                                0.000 |
| ('sim → real', 'vpd_kpa', 'mediana de la serie') |                        2.877 |  38.000 |                 1.000 |                                0.000 |
| ('sim → real', 'vpd_kpa', 'mediana de lo real')  |                        2.877 |  38.000 |                 1.000 |                                0.000 |

## Influencia ambiental — por episodio real

|   episodio_id | clase     | dudoso   |   filas |   % cambia |   acierto con ambiente |   acierto ambiental en mediana |
|--------------:|:----------|:---------|--------:|-----------:|-----------------------:|-------------------------------:|
|         1.000 | marchita  | False    |     131 |      0.000 |                  1.000 |                          1.000 |
|         3.000 | estresada | False    |      23 |      0.000 |                  0.000 |                          0.000 |
|         6.000 | estresada | False    |      69 |     24.638 |                  0.913 |                          0.754 |
|         8.000 | marchita  | True     |     105 |      0.000 |                  0.000 |                          0.000 |
|         9.000 | estresada | True     |      51 |      0.000 |                  0.000 |                          0.000 |
|        10.000 | saludable | False    |     137 |      0.000 |                  0.978 |                          0.978 |
|        11.000 | saludable | True     |      27 |      0.000 |                  0.000 |                          0.000 |
|        12.000 | marchita  | False    |      86 |      0.000 |                  1.000 |                          1.000 |
|        13.000 | estresada | False    |     136 |     11.765 |                  0.743 |                          0.860 |
|        14.000 | estresada | True     |     297 |      0.000 |                  0.000 |                          0.000 |
|        15.000 | saludable | False    |     259 |      0.000 |                  1.000 |                          1.000 |

## Influencia ambiental — barrido con suelo de octubre

|                                                     | rango real   | cambia la clase   | clases que recorre                                                                                                                                                                                                        |
|:----------------------------------------------------|:-------------|:------------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ('vpd_kpa', '1480 (saludable oct. (mediana real))') | 0.3996–4.153 | True              | 0.3996–0.5031: saludable | 0.5125–0.5784: estresada | 0.5878–4.153: saludable                                                                                                                                             |
| ('vpd_kpa', '1758 (marchita ep. 12 (mediana))')     | 0.3996–4.153 | True              | 0.3996–0.4655: marchita | 0.4749–0.6912: estresada | 0.7006–4.153: marchita                                                                                                                                               |
| ('vpd_kpa', '1930 (estresada ep. 13 (mediana))')    | 0.3996–4.153 | True              | 0.3996–1.049: estresada | 1.058–1.162: marchita | 1.171–1.359: estresada | 1.369–1.528: marchita | 1.538–1.557: estresada | 1.566–2.074: marchita | 2.083–2.601: estresada | 2.61–4.04: marchita | 4.049–4.153: estresada |
| ('vpd_kpa', '1619 (entre saludable y marchita)')    | 0.3996–4.153 | True              | 0.3996–0.4655: marchita | 0.4749–0.5784: estresada | 0.5878–4.153: saludable                                                                                                                                              |

## ¿Proxy de la hora? (V de Cramér con la franja, filas reales)

|                                                    |   V de Cramér con la franja de 3 h (filas reales) |
|:---------------------------------------------------|--------------------------------------------------:|
| clase real                                         |                                             0.466 |
| predicción sólo suelo (rf-f0-c42286)               |                                             0.388 |
| predicción criterio original (nb-f02-fa0df4)       |                                             0.150 |
| predicción nueva (rf-f04-7734f6)                   |                                             0.382 |
| predicción nueva con las ambientales en la mediana |                                             0.389 |
| vpd_kpa (en terciles)                              |                                             0.412 |

## Números clave

|                                                                                              | valor                                                                                                  |
|:---------------------------------------------------------------------------------------------|:-------------------------------------------------------------------------------------------------------|
| relleno (archivo, fecha)                                                                     | data/sintetico/payloads_relleno.jsonl (2026-10-21 23:58 UTC)                                           |
| filas / episodios (serie)                                                                    | 11,051 / 47                                                                                            |
| filas / episodios reales                                                                     | 1,321 / 11                                                                                             |
| episodios dudosos                                                                            | [8, 9, 11, 14]                                                                                         |
| fuga: RF 7 features, aleatoria vs por episodio (serie)                                       | 0.887 ± 0.009 vs 0.681 ± 0.133                                                                         |
| fuga: ídem sólo reales                                                                       | 0.947 ± 0.012 vs 0.291 ± 0.356                                                                         |
| criterio original en el espacio restringido (sin seguridad)                                  | Naive Bayes [suelo+temp]                                                                               |
| elegido con la condición de seguridad                                                        | Random Forest [suelo+vpd] max_depth=5, min_samples_leaf=20                                             |
| config final                                                                                 | Random Forest [suelo+vpd] max_depth=5, min_samples_leaf=20                                             |
| coincide con CONFIG_FINAL                                                                    | True                                                                                                   |
| versión                                                                                      | rf-f04-7734f6                                                                                          |
| header al día                                                                                | True                                                                                                   |
| F1 macro serie, elegido (búsqueda anidada)                                                   | 0.664 ± 0.150                                                                                          |
| F1 macro serie, dos umbrales                                                                 | 0.749 ± 0.123                                                                                          |
| puntaje real elegido / dos umbrales / umbral único / mayoritaria                             | 0.682 / 0.551 / 0.553 / 0.213                                                                          |
| desvío bootstrap del puntaje real                                                            | 0.154                                                                                                  |
| exactitud bal. reales fuera de fold (con / sin dudosos), elegido                             | 0.408 / 0.546                                                                                          |
| exactitud bal. sim → real (con / sin dudosos), elegido                                       | 0.436 / 0.544                                                                                          |
| exactitud bal. sólo reales (con / sin dudosos), elegido                                      | 0.089 / 0.143                                                                                          |
| exactitud bal. sim → real (todos / sin dud. / sin 13 / sin dud. ni 13), elegido              | 0.436 / 0.544 / 0.436 / 0.544                                                                          |
| exactitud bal. reales fuera de fold (todos / sin dud. / sin 13 / sin dud. ni 13), elegido    | 0.408 / 0.546 / 0.412 / 0.589                                                                          |
| costo elegido                                                                                | {'flash_B': 23730, 'ram_B': 28, 'ops': 390, 'exps': 0, 't_us_est': 16.25, 'exportable': 'sí (tablas)'} |
| restricción de diseño                                                                        | suelo_mv + al menos una ambiental en todos los candidatos con selección                                |
| features del modelo final                                                                    | suelo_mv, vpd_kpa                                                                                      |
| % filas reales que cambian con la ambiental en la mediana (final / sim → real)               | 2.498 / 2.877                                                                                          |
| configuraciones exploradas / que pasan costo + influencia + seguridad                        | 165 / 36                                                                                               |
| puntaje real config. fija: sólo suelo / criterio original / nuevo / dos umbrales             | 0.623 / 0.736 / 0.661 / 0.551                                                                          |
| exactitud bal. reales fuera de fold (todos / sin dud. / sin 13 / sin dud. ni 13), sólo suelo | 0.487 / 0.644 / 0.494 / 0.724                                                                          |
| exactitud bal. reales fuera de fold (todos / sin dud. / sin 13 / sin dud. ni 13), nuevo      | 0.557 / 0.723 / 0.565 / 0.809                                                                          |
| exactitud bal. sim → real (todos / sin dud. / sin 13 / sin dud. ni 13), sólo suelo           | 0.557 / 0.717 / 0.563 / 0.797                                                                          |
| exactitud bal. sim → real (todos / sin dud. / sin 13 / sin dud. ni 13), nuevo                | 0.556 / 0.720 / 0.563 / 0.802                                                                          |
| V de Cramér franja ~ predicción (sólo suelo / criterio original / nuevo)                     | 0.388 / 0.150 / 0.382                                                                                  |
