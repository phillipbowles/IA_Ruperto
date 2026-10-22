<!-- GENERADO por notebooks/03_modelos.ipynb — no editar; se reescribe al re-ejecutar. -->
# Tablas del notebook 03_modelos

Relleno: data/sintetico/payloads_relleno.jsonl (2026-10-21 23:41 UTC). Modelo: `rf-f0-c42286`.

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
| Regresión logística     | 0.623 ± 0.147   | 0.615 ± 0.162 | 0.421 ± 0.265     | 0.836 ± 0.067 |
| Árbol de decisión       | 0.733 ± 0.133   | 0.712 ± 0.180 | 0.776 ± 0.171     | 0.818 ± 0.083 |
| Random Forest           | 0.744 ± 0.115   | 0.744 ± 0.119 | 0.799 ± 0.182     | 0.832 ± 0.081 |
| Naive Bayes             | 0.570 ± 0.099   | 0.549 ± 0.100 | 0.422 ± 0.284     | 0.789 ± 0.101 |
| k-NN                    | 0.712 ± 0.191   | 0.713 ± 0.190 | 0.711 ± 0.289     | 0.806 ± 0.156 |
| SVM RBF                 | 0.702 ± 0.143   | 0.706 ± 0.143 | 0.610 ± 0.294     | n/d           |
| MLP                     | 0.637 ± 0.188   | 0.639 ± 0.190 | 0.534 ± 0.275     | 0.813 ± 0.093 |

## Costo estimado en la ESP32

|                         | config                                             |   flash_B |   ram_B |   ops |   exps |   t_us_est | exportable                           |
|:------------------------|:---------------------------------------------------|----------:|--------:|------:|-------:|-----------:|:-------------------------------------|
| Clase mayoritaria       | [todas]                                            |         4 |       0 |     0 |      0 |      0.000 | sí (constante)                       |
| Umbral único (suelo_mv) | [suelo]                                            |        51 |      16 |     2 |      0 |      0.083 | sí (if/else o tablas)                |
| Dos umbrales (suelo_mv) | [suelo]                                            |         8 |       0 |     2 |      0 |      0.083 | sí (dos if)                          |
| Regresión logística     | [suelo+delta] C=0.01                               |        52 |      20 |    25 |      3 |      4.042 | sí (producto matriz-vector)          |
| Árbol de decisión       | [suelo] max_depth=4, min_samples_leaf=20           |       441 |      16 |     8 |      0 |      0.333 | sí (if/else o tablas)                |
| Random Forest           | [suelo] max_depth=5, min_samples_leaf=20           |     24600 |      28 |   390 |      0 |     16.250 | sí (tablas)                          |
| Naive Bayes             | [suelo]                                            |        36 |      12 |    15 |      3 |      3.625 | sí (fórmula cerrada)                 |
| k-NN                    | [suelo+delta] n_neighbors=25                       |     99475 |     216 | 88412 |      0 |   3683.833 | sí, pero guarda todo el train        |
| SVM RBF                 | [suelo+delta] C=0.1                                |    103260 |      28 | 64524 |   6452 |   9140.500 | sí, pero guarda los vectores soporte |
| MLP                     | [suelo+delta] alpha=0.001, hidden_layer_sizes=(8,) |       220 |      64 |   106 |      3 |      7.417 | sí (capas densas)                    |

## Selección (criterio §5.3 con puntaje real)

|                         |   f1_macro |   f1_desvío |   exactitud_bal |   recall_marchita |   f1_reales_oof_sd |   f1_sim2real_sd |   puntaje_real |   flash_B |   ram_B |   t_us_est |   interpretabilidad | baseline   | restricciones_ok   | cv_ok   | real_ok   | cumple   |
|:------------------------|-----------:|------------:|----------------:|------------------:|-------------------:|-----------------:|---------------:|----------:|--------:|-----------:|--------------------:|:-----------|:-------------------|:--------|:----------|:---------|
| Clase mayoritaria       |      0.232 |       0.036 |           0.333 |             0.000 |              0.213 |            0.213 |          0.213 |         4 |       0 |      0.000 |                   1 | True       | True               | False   | False     | False    |
| Umbral único (suelo_mv) |      0.523 |       0.058 |           0.601 |             0.823 |              0.550 |            0.557 |          0.553 |        51 |      16 |      0.083 |                   1 | True       | True               | False   | True      | False    |
| Dos umbrales (suelo_mv) |      0.749 |       0.123 |           0.751 |             0.811 |              0.551 |            0.551 |          0.551 |         8 |       0 |      0.083 |                   1 | True       | True               | True    | True      | False    |
| Regresión logística     |      0.615 |       0.162 |           0.623 |             0.421 |              0.551 |            0.536 |          0.544 |        52 |      20 |      4.042 |                   2 | False      | True               | False   | True      | False    |
| Árbol de decisión       |      0.712 |       0.180 |           0.733 |             0.776 |              0.494 |            0.542 |          0.518 |       441 |      16 |      0.333 |                   1 | False      | True               | True    | False     | False    |
| Random Forest           |      0.744 |       0.119 |           0.744 |             0.799 |              0.591 |            0.588 |          0.589 |     24600 |      28 |     16.250 |                   3 | False      | True               | True    | True      | True     |
| Naive Bayes             |      0.549 |       0.100 |           0.570 |             0.422 |              0.738 |            0.599 |          0.669 |        36 |      12 |      3.625 |                   2 | False      | True               | False   | True      | False    |
| k-NN                    |      0.713 |       0.190 |           0.712 |             0.711 |              0.759 |            0.661 |          0.710 |     99475 |     216 |   3683.833 |                   4 | False      | False              | True    | True      | False    |
| SVM RBF                 |      0.706 |       0.143 |           0.702 |             0.610 |              0.918 |            0.672 |          0.795 |    103260 |      28 |   9140.500 |                   5 | False      | False              | True    | True      | False    |
| MLP                     |      0.639 |       0.190 |           0.637 |             0.534 |              0.526 |            0.529 |          0.527 |       220 |      64 |      7.417 |                   5 | False      | True               | True    | False     | False    |

## Elegido vs baselines

|                         |   f1_macro |   exactitud_bal |   recall_marchita |   f1_reales_oof_sd |   f1_sim2real_sd |   puntaje_real |   flash_B |
|:------------------------|-----------:|----------------:|------------------:|-------------------:|-----------------:|---------------:|----------:|
| Random Forest           |      0.744 |           0.744 |             0.799 |              0.591 |            0.588 |          0.589 | 24600.000 |
| Dos umbrales (suelo_mv) |      0.749 |           0.751 |             0.811 |              0.551 |            0.551 |          0.551 |     8.000 |
| Umbral único (suelo_mv) |      0.523 |           0.601 |             0.823 |              0.550 |            0.557 |          0.553 |    51.000 |
| Clase mayoritaria       |      0.232 |           0.333 |             0.000 |              0.213 |            0.213 |          0.213 |     4.000 |

## Configuraciones del tipo elegido

|                                                        |   F1 macro serie (CV) |   F1 macro reales fuera de fold, sin dudosos |   exactitud bal. reales fuera de fold |   % reales predichas marchita |   % marchita en la ventana post-arranque descartada |
|:-------------------------------------------------------|----------------------:|---------------------------------------------:|--------------------------------------:|------------------------------:|----------------------------------------------------:|
| CONFIG_FINAL: [suelo] max_depth=5, min_samples_leaf=20 |                 0.715 |                                        0.591 |                                 0.487 |                        22.937 |                                              41.912 |

## Control con reales — exactitud_bal

| modelo                  |   reales fuera de fold |   reales fuera de fold, sin dudosos |   sim → real |   sim → real, sin dudosos |   sólo reales (CV por episodio) |   sólo reales, sin dudosos |
|:------------------------|-----------------------:|------------------------------------:|-------------:|--------------------------:|--------------------------------:|---------------------------:|
| Clase mayoritaria       |                  0.333 |                               0.333 |        0.333 |                     0.333 |                           0.092 |                      0.232 |
| Umbral único (suelo_mv) |                  0.534 |                               0.664 |        0.442 |                     0.664 |                           0.144 |                      0.212 |
| Dos umbrales (suelo_mv) |                  0.536 |                               0.666 |        0.536 |                     0.666 |                           0.314 |                      0.495 |
| Regresión logística     |                  0.443 |                               0.562 |        0.418 |                     0.540 |                           0.412 |                      0.616 |
| Árbol de decisión       |                  0.412 |                               0.554 |        0.532 |                     0.654 |                           0.172 |                      0.325 |
| Random Forest           |                  0.494 |                               0.644 |        0.531 |                     0.657 |                           0.257 |                      0.402 |
| Naive Bayes             |                  0.535 |                               0.738 |        0.477 |                     0.613 |                           0.269 |                      0.402 |
| k-NN                    |                  0.552 |                               0.783 |        0.564 |                     0.721 |                           0.204 |                      0.370 |
| SVM RBF                 |                  0.641 |                               0.922 |        0.555 |                     0.724 |                           0.361 |                      0.519 |
| MLP                     |                  0.442 |                               0.549 |        0.465 |                     0.584 |                           0.082 |                      0.199 |

## Control con reales — f1_macro

| modelo                  |   reales fuera de fold |   reales fuera de fold, sin dudosos |   sim → real |   sim → real, sin dudosos |   sólo reales (CV por episodio) |   sólo reales, sin dudosos |
|:------------------------|-----------------------:|------------------------------------:|-------------:|--------------------------:|--------------------------------:|---------------------------:|
| Clase mayoritaria       |                  0.162 |                               0.213 |        0.162 |                     0.213 |                           0.072 |                      0.106 |
| Umbral único (suelo_mv) |                  0.388 |                               0.550 |        0.351 |                     0.557 |                           0.130 |                      0.225 |
| Dos umbrales (suelo_mv) |                  0.389 |                               0.551 |        0.389 |                     0.551 |                           0.320 |                      0.479 |
| Regresión logística     |                  0.367 |                               0.551 |        0.362 |                     0.536 |                           0.390 |                      0.606 |
| Árbol de decisión       |                  0.332 |                               0.494 |        0.386 |                     0.542 |                           0.167 |                      0.265 |
| Random Forest           |                  0.402 |                               0.591 |        0.424 |                     0.588 |                           0.221 |                      0.338 |
| Naive Bayes             |                  0.486 |                               0.738 |        0.396 |                     0.599 |                           0.223 |                      0.365 |
| k-NN                    |                  0.501 |                               0.759 |        0.452 |                     0.661 |                           0.191 |                      0.305 |
| SVM RBF                 |                  0.601 |                               0.918 |        0.445 |                     0.672 |                           0.298 |                      0.469 |
| MLP                     |                  0.351 |                               0.526 |        0.377 |                     0.529 |                           0.065 |                      0.093 |

## Control con reales — recall_marchita

| modelo                  |   reales fuera de fold |   reales fuera de fold, sin dudosos |   sim → real |   sim → real, sin dudosos |   sólo reales (CV por episodio) |   sólo reales, sin dudosos |
|:------------------------|-----------------------:|------------------------------------:|-------------:|--------------------------:|--------------------------------:|---------------------------:|
| Clase mayoritaria       |                  0.000 |                               0.000 |        0.000 |                     0.000 |                           0.000 |                      0.000 |
| Umbral único (suelo_mv) |                  0.674 |                               1.000 |        0.000 |                     0.000 |                           0.000 |                      0.000 |
| Dos umbrales (suelo_mv) |                  0.674 |                               1.000 |        0.674 |                     1.000 |                           0.407 |                      0.604 |
| Regresión logística     |                  0.422 |                               0.604 |        0.422 |                     0.604 |                           0.220 |                      0.327 |
| Árbol de decisión       |                  0.665 |                               0.968 |        0.696 |                     1.000 |                           0.037 |                      0.055 |
| Random Forest           |                  0.696 |                               1.000 |        0.643 |                     0.931 |                           0.000 |                      0.000 |
| Naive Bayes             |                  0.432 |                               0.604 |        0.407 |                     0.604 |                           0.000 |                      0.000 |
| k-NN                    |                  0.677 |                               1.000 |        0.677 |                     1.000 |                           0.034 |                      0.051 |
| SVM RBF                 |                  0.693 |                               1.000 |        0.661 |                     0.982 |                           0.043 |                      0.065 |
| MLP                     |                  0.432 |                               0.618 |        0.624 |                     0.899 |                           0.000 |                      0.000 |

## Control con reales — roc_auc_ovr

| modelo                  |   reales fuera de fold |   reales fuera de fold, sin dudosos |   sim → real |   sim → real, sin dudosos |   sólo reales (CV por episodio) |   sólo reales, sin dudosos |
|:------------------------|-----------------------:|------------------------------------:|-------------:|--------------------------:|--------------------------------:|---------------------------:|
| Clase mayoritaria       |                  0.500 |                               0.500 |        0.500 |                     0.500 |                           0.302 |                      0.424 |
| Umbral único (suelo_mv) |                  0.504 |                               0.802 |        0.651 |                     0.877 |                           0.241 |                      0.508 |
| Dos umbrales (suelo_mv) |                nan     |                             nan     |      nan     |                   nan     |                         nan     |                    nan     |
| Regresión logística     |                  0.585 |                               0.842 |        0.627 |                     0.817 |                           0.499 |                      0.794 |
| Árbol de decisión       |                  0.597 |                               0.749 |        0.652 |                     0.872 |                           0.284 |                      0.530 |
| Random Forest           |                  0.585 |                               0.718 |        0.654 |                     0.781 |                           0.378 |                      0.562 |
| Naive Bayes             |                  0.571 |                               0.858 |        0.638 |                     0.855 |                           0.319 |                      0.589 |
| k-NN                    |                  0.594 |                               0.858 |        0.665 |                     0.809 |                           0.337 |                      0.520 |
| SVM RBF                 |                nan     |                             nan     |      nan     |                   nan     |                         nan     |                    nan     |
| MLP                     |                  0.520 |                               0.844 |        0.611 |                     0.784 |                           0.231 |                      0.245 |

## Modelo final por episodio real

|   episodio | clase     | dudoso   |   filas |   suelo_mv_mediana |   final→salud |   final→estre |   final→march |   acierto final (train) |   acierto fuera de fold |   acierto sim→real |
|-----------:|:----------|:---------|--------:|-------------------:|--------------:|--------------:|--------------:|------------------------:|------------------------:|-------------------:|
|          1 | marchita  | False    |     131 |           2832.000 |         0.000 |         0.000 |         1.000 |                   1.000 |                   1.000 |              1.000 |
|          3 | estresada | False    |      23 |           2769.500 |         0.000 |         0.000 |         1.000 |                   0.000 |                   0.000 |              0.000 |
|          6 | estresada | False    |      69 |           2050.000 |         0.000 |         0.754 |         0.246 |                   0.754 |                   0.536 |              0.536 |
|          8 | marchita  | True     |     105 |           1512.000 |         0.990 |         0.000 |         0.010 |                   0.010 |                   0.010 |              0.010 |
|          9 | estresada | True     |      51 |           1454.000 |         1.000 |         0.000 |         0.000 |                   0.000 |                   0.000 |              0.000 |
|         10 | saludable | False    |     137 |           1504.000 |         0.971 |         0.022 |         0.007 |                   0.971 |                   0.912 |              0.971 |
|         11 | saludable | True     |      27 |           1785.500 |         0.000 |         0.074 |         0.926 |                   0.000 |                   0.000 |              0.000 |
|         12 | marchita  | False    |      86 |           1758.000 |         0.000 |         0.000 |         1.000 |                   1.000 |                   1.000 |              1.000 |
|         13 | estresada | False    |     136 |           1929.750 |         0.000 |         0.860 |         0.140 |                   0.860 |                   0.000 |              0.000 |
|         14 | estresada | True     |     297 |           1443.500 |         1.000 |         0.000 |         0.000 |                   0.000 |                   0.000 |              0.003 |
|         15 | saludable | False    |     259 |           1453.000 |         1.000 |         0.000 |         0.000 |                   1.000 |                   0.695 |              1.000 |

## Sensibilidad al ep. 13 — exactitud_bal reales fuera de fold

| modelo                  |   todos |   sin dudosos |   sin el 13 |   sin dudosos ni el 13 |
|:------------------------|--------:|--------------:|------------:|-----------------------:|
| Clase mayoritaria       |   0.333 |         0.333 |       0.333 |                  0.333 |
| Umbral único (suelo_mv) |   0.534 |         0.664 |       0.534 |                  0.664 |
| Dos umbrales (suelo_mv) |   0.536 |         0.666 |       0.536 |                  0.666 |
| Regresión logística     |   0.443 |         0.562 |       0.417 |                  0.497 |
| Árbol de decisión       |   0.412 |         0.554 |       0.420 |                  0.634 |
| Random Forest           |   0.494 |         0.644 |       0.500 |                  0.724 |
| Naive Bayes             |   0.535 |         0.738 |       0.460 |                  0.561 |
| k-NN                    |   0.552 |         0.783 |       0.520 |                  0.792 |
| SVM RBF                 |   0.641 |         0.922 |       0.581 |                  0.865 |
| MLP                     |   0.442 |         0.549 |       0.447 |                  0.614 |

## Sensibilidad al ep. 13 — F1 macro reales fuera de fold

| modelo                  |   todos |   sin dudosos |   sin el 13 |   sin dudosos ni el 13 |
|:------------------------|--------:|--------------:|------------:|-----------------------:|
| Clase mayoritaria       |   0.162 |         0.213 |       0.175 |                  0.240 |
| Umbral único (suelo_mv) |   0.388 |         0.550 |       0.425 |                  0.606 |
| Dos umbrales (suelo_mv) |   0.389 |         0.551 |       0.427 |                  0.608 |
| Regresión logística     |   0.367 |         0.551 |       0.347 |                  0.510 |
| Árbol de decisión       |   0.332 |         0.494 |       0.371 |                  0.596 |
| Random Forest           |   0.402 |         0.591 |       0.452 |                  0.698 |
| Naive Bayes             |   0.486 |         0.738 |       0.382 |                  0.562 |
| k-NN                    |   0.501 |         0.759 |       0.479 |                  0.762 |
| SVM RBF                 |   0.601 |         0.918 |       0.526 |                  0.881 |
| MLP                     |   0.351 |         0.526 |       0.386 |                  0.610 |

## Sensibilidad al ep. 13 — exactitud_bal sim → real

| modelo                  |   todos |   sin dudosos |   sin el 13 |   sin dudosos ni el 13 |
|:------------------------|--------:|--------------:|------------:|-----------------------:|
| Clase mayoritaria       |   0.333 |         0.333 |       0.333 |                  0.333 |
| Umbral único (suelo_mv) |   0.442 |         0.664 |       0.379 |                  0.664 |
| Dos umbrales (suelo_mv) |   0.536 |         0.666 |       0.536 |                  0.666 |
| Regresión logística     |   0.418 |         0.540 |       0.393 |                  0.484 |
| Árbol de decisión       |   0.532 |         0.654 |       0.532 |                  0.654 |
| Random Forest           |   0.531 |         0.657 |       0.528 |                  0.655 |
| Naive Bayes             |   0.477 |         0.613 |       0.445 |                  0.531 |
| k-NN                    |   0.564 |         0.721 |       0.573 |                  0.805 |
| SVM RBF                 |   0.555 |         0.724 |       0.563 |                  0.823 |
| MLP                     |   0.465 |         0.584 |       0.470 |                  0.623 |

## Sensibilidad al ep. 13 — F1 macro sim → real

| modelo                  |   todos |   sin dudosos |   sin el 13 |   sin dudosos ni el 13 |
|:------------------------|--------:|--------------:|------------:|-----------------------:|
| Clase mayoritaria       |   0.162 |         0.213 |       0.175 |                  0.240 |
| Umbral único (suelo_mv) |   0.351 |         0.557 |       0.285 |                  0.484 |
| Dos umbrales (suelo_mv) |   0.389 |         0.551 |       0.427 |                  0.608 |
| Regresión logística     |   0.362 |         0.536 |       0.348 |                  0.506 |
| Árbol de decisión       |   0.386 |         0.542 |       0.422 |                  0.596 |
| Random Forest           |   0.424 |         0.588 |       0.453 |                  0.630 |
| Naive Bayes             |   0.396 |         0.599 |       0.366 |                  0.530 |
| k-NN                    |   0.452 |         0.661 |       0.505 |                  0.824 |
| SVM RBF                 |   0.445 |         0.672 |       0.501 |                  0.838 |
| MLP                     |   0.377 |         0.529 |       0.418 |                  0.607 |

## Sensibilidad al ep. 13 — recall marchita sim → real

| modelo                  |   todos |   sin dudosos |   sin el 13 |   sin dudosos ni el 13 |
|:------------------------|--------:|--------------:|------------:|-----------------------:|
| Clase mayoritaria       |   0.000 |         0.000 |       0.000 |                  0.000 |
| Umbral único (suelo_mv) |   0.000 |         0.000 |       0.000 |                  0.000 |
| Dos umbrales (suelo_mv) |   0.674 |         1.000 |       0.674 |                  1.000 |
| Regresión logística     |   0.422 |         0.604 |       0.422 |                  0.604 |
| Árbol de decisión       |   0.696 |         1.000 |       0.696 |                  1.000 |
| Random Forest           |   0.643 |         0.931 |       0.643 |                  0.931 |
| Naive Bayes             |   0.407 |         0.604 |       0.407 |                  0.604 |
| k-NN                    |   0.677 |         1.000 |       0.677 |                  1.000 |
| SVM RBF                 |   0.661 |         0.982 |       0.661 |                  0.982 |
| MLP                     |   0.624 |         0.899 |       0.624 |                  0.899 |

## Binario requiere cuidado

|                         | exactitud_bal   | f1_cuidado    | recall_cuidado   | roc_auc       |   exactitud_bal reales fuera de fold (sin dudosos) |   recall_cuidado reales fuera de fold (sin dudosos) |   exactitud_bal sim → real (sin dudosos) |   recall_cuidado sim → real (sin dudosos) |
|:------------------------|:----------------|:--------------|:-----------------|:--------------|---------------------------------------------------:|----------------------------------------------------:|-----------------------------------------:|------------------------------------------:|
| Clase mayoritaria       | 0.500 ± 0.000   | 0.061 ± 0.122 | 0.200 ± 0.400    | 0.500 ± 0.000 |                                              0.097 |                                               0.193 |                                    0.500 |                                     0.000 |
| Umbral único (suelo_mv) | 0.879 ± 0.073   | 0.859 ± 0.093 | 0.779 ± 0.139    | 0.879 ± 0.073 |                                              0.996 |                                               1.000 |                                    0.996 |                                     1.000 |
| Árbol de decisión       | 0.848 ± 0.069   | 0.790 ± 0.163 | 0.826 ± 0.133    | 0.884 ± 0.083 |                                              0.784 |                                               1.000 |                                    0.981 |                                     1.000 |
| Regresión logística     | 0.875 ± 0.055   | 0.848 ± 0.091 | 0.831 ± 0.125    | 0.900 ± 0.066 |                                              0.962 |                                               1.000 |                                    0.956 |                                     1.000 |
| Naive Bayes             | 0.824 ± 0.118   | 0.810 ± 0.112 | 0.731 ± 0.098    | 0.855 ± 0.124 |                                              1.000 |                                               1.000 |                                    1.000 |                                     1.000 |

## Números clave

|                                                                                           | valor                                                                                                  |
|:------------------------------------------------------------------------------------------|:-------------------------------------------------------------------------------------------------------|
| relleno (archivo, fecha)                                                                  | data/sintetico/payloads_relleno.jsonl (2026-10-21 23:41 UTC)                                           |
| filas / episodios (serie)                                                                 | 11,051 / 47                                                                                            |
| filas / episodios reales                                                                  | 1,321 / 11                                                                                             |
| episodios dudosos                                                                         | [8, 9, 11, 14]                                                                                         |
| fuga: RF 7 features, aleatoria vs por episodio (serie)                                    | 0.887 ± 0.009 vs 0.681 ± 0.133                                                                         |
| fuga: ídem sólo reales                                                                    | 0.947 ± 0.012 vs 0.291 ± 0.356                                                                         |
| elegido                                                                                   | Random Forest                                                                                          |
| config final                                                                              | Random Forest [suelo] max_depth=5, min_samples_leaf=20                                                 |
| coincide con CONFIG_FINAL                                                                 | True                                                                                                   |
| versión                                                                                   | rf-f0-c42286                                                                                           |
| header al día                                                                             | True                                                                                                   |
| F1 macro serie, elegido (búsqueda anidada)                                                | 0.744 ± 0.119                                                                                          |
| F1 macro serie, dos umbrales                                                              | 0.749 ± 0.123                                                                                          |
| puntaje real elegido / dos umbrales / umbral único / mayoritaria                          | 0.589 / 0.551 / 0.553 / 0.213                                                                          |
| desvío bootstrap del puntaje real                                                         | 0.051                                                                                                  |
| exactitud bal. reales fuera de fold (con / sin dudosos), elegido                          | 0.494 / 0.644                                                                                          |
| exactitud bal. sim → real (con / sin dudosos), elegido                                    | 0.531 / 0.657                                                                                          |
| exactitud bal. sólo reales (con / sin dudosos), elegido                                   | 0.257 / 0.402                                                                                          |
| exactitud bal. sim → real (todos / sin dud. / sin 13 / sin dud. ni 13), elegido           | 0.531 / 0.657 / 0.528 / 0.655                                                                          |
| exactitud bal. reales fuera de fold (todos / sin dud. / sin 13 / sin dud. ni 13), elegido | 0.494 / 0.644 / 0.500 / 0.724                                                                          |
| costo elegido                                                                             | {'flash_B': 24600, 'ram_B': 28, 'ops': 390, 'exps': 0, 't_us_est': 16.25, 'exportable': 'sí (tablas)'} |
