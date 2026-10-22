<!-- GENERADO por notebooks/03_modelos.ipynb — no editar; se reescribe al re-ejecutar. -->
# Tablas del notebook 03_modelos

Datos: `mediciones_raw_2026-10-21.csv` (sólo lo medido por la placa). Modelo: `arbol-p2-f012-58e644`.

## Conteo de filas y episodios

|           |   ('todos', 'filas') |   ('todos', 'episodios') |   ('sin dudosos', 'filas') |   ('sin dudosos', 'episodios') |
|:----------|---------------------:|-------------------------:|---------------------------:|-------------------------------:|
| saludable |              426.000 |                    3.000 |                    399.000 |                          2.000 |
| estresada |              598.000 |                    5.000 |                    244.000 |                          3.000 |
| marchita  |              333.000 |                    3.000 |                    222.000 |                          2.000 |
| total     |             1357.000 |                   11.000 |                    865.000 |                          7.000 |

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

## Fuga: partición aleatoria vs por episodio (exactitud balanceada)

|               |   aleatoria (filas mezcladas) |   por episodio |
|:--------------|------------------------------:|---------------:|
| RF 7 features |                         0.943 |          0.135 |

## Partición por episodio, fuera de fold (± desvío bootstrap por episodio)

|                         | ('todos', 'exactitud_bal')   | ('todos', 'f1_macro')   | ('todos', 'recall_marchita')   | ('sin dudosos', 'exactitud_bal')   | ('sin dudosos', 'f1_macro')   | ('sin dudosos', 'recall_marchita')   | ('todos', 'roc_auc_ovr')   | ('sin dudosos', 'roc_auc_ovr')   |
|:------------------------|:-----------------------------|:------------------------|:-------------------------------|:-----------------------------------|:------------------------------|:-------------------------------------|:---------------------------|:---------------------------------|
| Clase mayoritaria       | 0.095 ± 0.080                | 0.074 ± 0.050           | 0.000 ± 0.000                  | 0.232 ± 0.101                      | 0.110 ± 0.054                 | 0.000 ± 0.000                        | 0.304                      | 0.423                            |
| Umbral único (suelo_mv) | 0.300 ± 0.154                | 0.272 ± 0.132           | 0.396 ± 0.279                  | 0.412 ± 0.188                      | 0.388 ± 0.188                 | 0.595 ± 0.363                        | 0.295                      | 0.512                            |
| Dos umbrales (suelo_mv) | 0.295 ± 0.148                | 0.269 ± 0.131           | 0.396 ± 0.279                  | 0.416 ± 0.191                      | 0.393 ± 0.191                 | 0.595 ± 0.363                        | n/d                        | n/d                              |
| Regresión logística     | 0.094 ± 0.057                | 0.081 ± 0.045           | 0.000 ± 0.000                  | 0.128 ± 0.066                      | 0.142 ± 0.072                 | 0.000 ± 0.000                        | 0.220                      | 0.284                            |
| Árbol de decisión       | 0.207 ± 0.066                | 0.186 ± 0.074           | 0.000 ± 0.000                  | 0.326 ± 0.046                      | 0.316 ± 0.045                 | 0.000 ± 0.000                        | 0.288                      | 0.514                            |
| Random Forest           | 0.147 ± 0.046                | 0.127 ± 0.045           | 0.000 ± 0.000                  | 0.227 ± 0.059                      | 0.213 ± 0.026                 | 0.000 ± 0.000                        | 0.237                      | 0.346                            |
| Naive Bayes             | 0.184 ± 0.069                | 0.172 ± 0.074           | 0.000 ± 0.000                  | 0.304 ± 0.074                      | 0.297 ± 0.057                 | 0.000 ± 0.000                        | 0.303                      | 0.545                            |
| k-NN                    | 0.086 ± 0.073                | 0.081 ± 0.050           | 0.000 ± 0.000                  | 0.141 ± 0.101                      | 0.110 ± 0.053                 | 0.000 ± 0.000                        | 0.255                      | 0.363                            |
| SVM RBF                 | 0.057 ± 0.059                | 0.052 ± 0.037           | 0.000 ± 0.000                  | 0.119 ± 0.099                      | 0.069 ± 0.035                 | 0.000 ± 0.000                        | n/d                        | n/d                              |
| MLP                     | 0.203 ± 0.120                | 0.223 ± 0.114           | 0.270 ± 0.247                  | 0.395 ± 0.141                      | 0.306 ± 0.135                 | 0.405 ± 0.363                        | 0.413                      | 0.563                            |

## Costo estimado en la ESP32

|                         | config                                                                    |   flash_B |   ram_B |   ops |   exps |   t_us_est | exportable                           |
|:------------------------|:--------------------------------------------------------------------------|----------:|--------:|------:|-------:|-----------:|:-------------------------------------|
| Clase mayoritaria       | [suelo_mv+suelo_delta_1h+temp_c+hum_aire_pct+vpd_kpa+luz_mv+luz_media_1h] |         4 |       0 |     0 |      0 |      0.000 | sí (constante)                       |
| Umbral único (suelo_mv) | [suelo]                                                                   |        51 |      16 |     2 |      0 |      0.083 | sí (if/else o tablas)                |
| Dos umbrales (suelo_mv) | [suelo]                                                                   |         8 |       0 |     2 |      0 |      0.083 | sí (dos if)                          |
| Regresión logística     | [suelo+hr] C=1.0                                                          |        52 |      20 |    25 |      3 |      4.042 | sí (producto matriz-vector)          |
| Árbol de decisión       | [suelo+delta+temp] max_depth=2, min_samples_leaf=100                      |        81 |      16 |     4 |      0 |      0.167 | sí (if/else o tablas)                |
| Random Forest           | [suelo+hr] max_depth=5, min_samples_leaf=20                               |     11580 |      28 |   390 |      0 |     16.250 | sí (tablas)                          |
| Naive Bayes             | [suelo+hr+vpd]                                                            |        84 |      12 |    39 |      3 |      4.625 | sí (fórmula cerrada)                 |
| k-NN                    | [suelo+delta+hr] n_neighbors=25                                           |     17665 |     216 | 14933 |      0 |    622.208 | sí, pero guarda todo el train        |
| SVM RBF                 | [suelo+hr] C=0.1                                                          |     17468 |      28 | 10904 |   1090 |   1544.333 | sí, pero guarda los vectores soporte |
| MLP                     | [suelo+temp+vpd] alpha=0.001, hidden_layer_sizes=(8,)                     |       260 |      64 |   124 |      3 |      8.167 | sí (capas densas)                    |

## Sensibilidad a dudosos y al ep. 13 — exactitud_bal

| modelo                  |   todos |   sin dudosos |   sin el 13 |   sin dudosos ni el 13 |
|:------------------------|--------:|--------------:|------------:|-----------------------:|
| Clase mayoritaria       |   0.095 |         0.232 |       0.018 |                  0.082 |
| Umbral único (suelo_mv) |   0.300 |         0.412 |       0.313 |                  0.563 |
| Dos umbrales (suelo_mv) |   0.295 |         0.416 |       0.309 |                  0.567 |
| Regresión logística     |   0.094 |         0.128 |       0.089 |                  0.150 |
| Árbol de decisión       |   0.207 |         0.326 |       0.162 |                  0.277 |
| Random Forest           |   0.147 |         0.227 |       0.143 |                  0.318 |
| Naive Bayes             |   0.184 |         0.304 |       0.120 |                  0.181 |
| k-NN                    |   0.086 |         0.141 |       0.101 |                  0.312 |
| SVM RBF                 |   0.057 |         0.119 |       0.072 |                  0.290 |
| MLP                     |   0.203 |         0.395 |       0.130 |                  0.285 |

## Sensibilidad a dudosos y al ep. 13 — f1_macro

| modelo                  |   todos |   sin dudosos |   sin el 13 |   sin dudosos ni el 13 |
|:------------------------|--------:|--------------:|------------:|-----------------------:|
| Clase mayoritaria       |   0.074 |         0.110 |       0.013 |                  0.022 |
| Umbral único (suelo_mv) |   0.272 |         0.388 |       0.313 |                  0.477 |
| Dos umbrales (suelo_mv) |   0.269 |         0.393 |       0.311 |                  0.481 |
| Regresión logística     |   0.081 |         0.142 |       0.074 |                  0.133 |
| Árbol de decisión       |   0.186 |         0.316 |       0.137 |                  0.250 |
| Random Forest           |   0.127 |         0.213 |       0.123 |                  0.226 |
| Naive Bayes             |   0.172 |         0.297 |       0.104 |                  0.197 |
| k-NN                    |   0.081 |         0.110 |       0.086 |                  0.123 |
| SVM RBF                 |   0.052 |         0.069 |       0.058 |                  0.080 |
| MLP                     |   0.223 |         0.306 |       0.160 |                  0.219 |

## Sensibilidad a dudosos y al ep. 13 — recall_marchita

| modelo                  |   todos |   sin dudosos |   sin el 13 |   sin dudosos ni el 13 |
|:------------------------|--------:|--------------:|------------:|-----------------------:|
| Clase mayoritaria       |   0.000 |         0.000 |       0.000 |                  0.000 |
| Umbral único (suelo_mv) |   0.396 |         0.595 |       0.396 |                  0.595 |
| Dos umbrales (suelo_mv) |   0.396 |         0.595 |       0.396 |                  0.595 |
| Regresión logística     |   0.000 |         0.000 |       0.000 |                  0.000 |
| Árbol de decisión       |   0.000 |         0.000 |       0.000 |                  0.000 |
| Random Forest           |   0.000 |         0.000 |       0.000 |                  0.000 |
| Naive Bayes             |   0.000 |         0.000 |       0.000 |                  0.000 |
| k-NN                    |   0.000 |         0.000 |       0.000 |                  0.000 |
| SVM RBF                 |   0.000 |         0.000 |       0.000 |                  0.000 |
| MLP                     |   0.270 |         0.405 |       0.270 |                  0.405 |

## Selección (criterio §5.3)

|                         |   puntaje |   puntaje_desvío |   f1_todos |   exactitud_bal_sd |   recall_marchita_sd |   flash_B |   ram_B |   t_us_est |   interpretabilidad | baseline   | restricciones_ok   | puntaje_ok   | cumple   |
|:------------------------|----------:|-----------------:|-----------:|-------------------:|---------------------:|----------:|--------:|-----------:|--------------------:|:-----------|:-------------------|:-------------|:---------|
| Clase mayoritaria       |     0.110 |            0.054 |      0.074 |              0.232 |                0.000 |         4 |       0 |      0.000 |                   1 | True       | True               | False        | False    |
| Umbral único (suelo_mv) |     0.388 |            0.188 |      0.272 |              0.412 |                0.595 |        51 |      16 |      0.083 |                   1 | True       | True               | True         | False    |
| Dos umbrales (suelo_mv) |     0.393 |            0.191 |      0.269 |              0.416 |                0.595 |         8 |       0 |      0.083 |                   1 | True       | True               | True         | False    |
| Regresión logística     |     0.142 |            0.072 |      0.081 |              0.128 |                0.000 |        52 |      20 |      4.042 |                   2 | False      | True               | False        | False    |
| Árbol de decisión       |     0.316 |            0.045 |      0.186 |              0.326 |                0.000 |        81 |      16 |      0.167 |                   1 | False      | True               | True         | True     |
| Random Forest           |     0.213 |            0.026 |      0.127 |              0.227 |                0.000 |     11580 |      28 |     16.250 |                   3 | False      | True               | False        | False    |
| Naive Bayes             |     0.297 |            0.057 |      0.172 |              0.304 |                0.000 |        84 |      12 |      4.625 |                   2 | False      | True               | True         | True     |
| k-NN                    |     0.110 |            0.053 |      0.081 |              0.141 |                0.000 |     17665 |     216 |    622.208 |                   4 | False      | True               | False        | False    |
| SVM RBF                 |     0.069 |            0.035 |      0.052 |              0.119 |                0.000 |     17468 |      28 |   1544.333 |                   5 | False      | False              | False        | False    |
| MLP                     |     0.306 |            0.135 |      0.223 |              0.395 |                0.405 |       260 |      64 |      8.167 |                   5 | False      | True               | True         | True     |

## Elegido vs baselines

|                         |   puntaje |   puntaje_desvío |   f1_todos |   exactitud_bal_sd |   recall_marchita_sd |   flash_B |
|:------------------------|----------:|-----------------:|-----------:|-------------------:|---------------------:|----------:|
| Árbol de decisión       |     0.316 |            0.045 |      0.186 |              0.326 |                0.000 |    81.000 |
| Dos umbrales (suelo_mv) |     0.393 |            0.191 |      0.269 |              0.416 |                0.595 |     8.000 |
| Umbral único (suelo_mv) |     0.388 |            0.188 |      0.272 |              0.412 |                0.595 |    51.000 |
| Clase mayoritaria       |     0.110 |            0.054 |      0.074 |              0.232 |                0.000 |     4.000 |

## Restricción de diseño — configuraciones probadas (compuerta de influencia ambiental)

|    | config                                               |   F1 interno |   desvío | dentro_1_desvío   |   flash_B |   % filas que cambian (ambiental → mediana) | cumple   |
|---:|:-----------------------------------------------------|-------------:|---------:|:------------------|----------:|--------------------------------------------:|:---------|
|  0 | [suelo+delta+temp] max_depth=2, min_samples_leaf=100 |        0.258 |    0.041 | True              |        81 |                                       9.727 | True     |

## Condición de seguridad — embudo por tipo

| tipo                |   configuraciones |   costo |   seguridad |   costo + influencia |   costo + influencia + seguridad |   max_recall_marchita |   max_ep12 |
|:--------------------|------------------:|--------:|------------:|---------------------:|---------------------------------:|----------------------:|-----------:|
| Naive Bayes         |             6.000 |   6.000 |       0.000 |                6.000 |                            0.000 |                 0.000 |      0.000 |
| Random Forest       |            24.000 |  24.000 |       0.000 |               24.000 |                            0.000 |                 0.000 |      0.000 |
| Regresión logística |            18.000 |  18.000 |       0.000 |               18.000 |                            0.000 |                 0.595 |      0.278 |
| Árbol de decisión   |            18.000 |  18.000 |       0.000 |               11.000 |                            0.000 |                 0.000 |      0.000 |

## Condición de seguridad — todas las configuraciones

|                                                                             |   puntaje |   f1_todos |   recall_marchita_sd |   ep12 |   exactitud_bal_sd |   pct_influencia |   pct_marchita_sonda_mojada |   flash_B | costo_ok   | influencia_ok   | seguridad_ok   |
|:----------------------------------------------------------------------------|----------:|-----------:|---------------------:|-------:|-------------------:|-----------------:|----------------------------:|----------:|:-----------|:----------------|:---------------|
| ('Regresión logística', '[suelo+hr] C=0.01')                                |     0.529 |      0.349 |                0.595 |  0.000 |              0.530 |           23.434 |                       0.000 |        52 | True       | True            | False          |
| ('Regresión logística', '[suelo+hr] C=1.0')                                 |     0.514 |      0.339 |                0.595 |  0.000 |              0.512 |           24.024 |                       0.000 |        52 | True       | True            | False          |
| ('Regresión logística', '[suelo+hr] C=0.1')                                 |     0.508 |      0.335 |                0.595 |  0.000 |              0.506 |           23.508 |                       0.000 |        52 | True       | True            | False          |
| ('Regresión logística', '[suelo+vpd] C=0.01')                               |     0.473 |      0.312 |                0.595 |  0.000 |              0.469 |            5.527 |                       0.000 |        52 | True       | True            | False          |
| ('Regresión logística', '[suelo+hr+vpd] C=0.01')                            |     0.404 |      0.265 |                0.514 |  0.000 |              0.393 |           22.771 |                       0.000 |        72 | True       | True            | False          |
| ('Regresión logística', '[suelo+vpd] C=0.1')                                |     0.400 |      0.266 |                0.595 |  0.000 |              0.393 |            9.801 |                       0.000 |        52 | True       | True            | False          |
| ('Regresión logística', '[suelo+hr+vpd] C=0.1')                             |     0.394 |      0.261 |                0.595 |  0.000 |              0.388 |           23.729 |                       0.000 |        72 | True       | True            | False          |
| ('Regresión logística', '[suelo+hr+vpd] C=1.0')                             |     0.388 |      0.259 |                0.595 |  0.000 |              0.383 |           23.729 |                       0.000 |        72 | True       | True            | False          |
| ('Random Forest', '[suelo+hr] max_depth=5, min_samples_leaf=20')            |     0.383 |      0.238 |                0.000 |  0.000 |              0.429 |           11.349 |                       0.000 |     11580 | True       | True            | False          |
| ('Regresión logística', '[suelo+temp] C=0.01')                              |     0.382 |      0.224 |                0.000 |  0.000 |              0.369 |            6.116 |                       0.000 |        52 | True       | True            | False          |
| ('Regresión logística', '[suelo+vpd] C=1.0')                                |     0.378 |      0.253 |                0.595 |  0.000 |              0.371 |           11.643 |                       0.000 |        52 | True       | True            | False          |
| ('Regresión logística', '[suelo+temp] C=0.1')                               |     0.368 |      0.218 |                0.000 |  0.000 |              0.379 |            8.180 |                       0.000 |        52 | True       | True            | False          |
| ('Random Forest', '[suelo+vpd] max_depth=3, min_samples_leaf=20')           |     0.348 |      0.207 |                0.000 |  0.000 |              0.379 |            4.348 |                       0.000 |      5790 | True       | True            | False          |
| ('Regresión logística', '[suelo+temp] C=1.0')                               |     0.331 |      0.199 |                0.000 |  0.000 |              0.355 |            8.990 |                       0.000 |        52 | True       | True            | False          |
| ('Regresión logística', '[suelo+temp+hr] C=1.0')                            |     0.329 |      0.207 |                0.000 |  0.000 |              0.390 |           32.867 |                       0.000 |        72 | True       | True            | False          |
| ('Árbol de decisión', '[suelo+hr] max_depth=4, min_samples_leaf=100')       |     0.327 |      0.202 |                0.000 |  0.000 |              0.383 |            0.000 |                       0.000 |       201 | True       | False           | False          |
| ('Naive Bayes', '[suelo+temp]')                                             |     0.324 |      0.188 |                0.000 |  0.000 |              0.324 |            4.422 |                       0.000 |        60 | True       | True            | False          |
| ('Random Forest', '[suelo+hr] max_depth=3, min_samples_leaf=20')            |     0.324 |      0.191 |                0.000 |  0.000 |              0.351 |            3.390 |                       0.000 |      5730 | True       | True            | False          |
| ('Random Forest', '[suelo+vpd] max_depth=5, min_samples_leaf=20')           |     0.322 |      0.192 |                0.000 |  0.000 |              0.357 |           12.601 |                       0.000 |     12990 | True       | True            | False          |
| ('Naive Bayes', '[suelo+hr]')                                               |     0.316 |      0.188 |                0.000 |  0.000 |              0.358 |            3.906 |                       0.000 |        60 | True       | True            | False          |
| ('Regresión logística', '[suelo+temp+hr] C=0.01')                           |     0.313 |      0.194 |                0.000 |  0.000 |              0.366 |           25.792 |                       0.000 |        72 | True       | True            | False          |
| ('Regresión logística', '[suelo+temp+hr] C=0.1')                            |     0.307 |      0.190 |                0.000 |  0.000 |              0.358 |           32.351 |                       0.000 |        72 | True       | True            | False          |
| ('Naive Bayes', '[suelo+hr+vpd]')                                           |     0.306 |      0.176 |                0.000 |  0.000 |              0.298 |            5.748 |                       0.000 |        84 | True       | True            | False          |
| ('Naive Bayes', '[suelo+temp+hr]')                                          |     0.302 |      0.177 |                0.000 |  0.000 |              0.323 |            3.316 |                       0.000 |        84 | True       | True            | False          |
| ('Naive Bayes', '[suelo+temp+vpd]')                                         |     0.295 |      0.168 |                0.000 |  0.000 |              0.282 |            8.696 |                       0.000 |        84 | True       | True            | False          |
| ('Naive Bayes', '[suelo+vpd]')                                              |     0.293 |      0.166 |                0.000 |  0.000 |              0.268 |            4.937 |                       0.000 |        60 | True       | True            | False          |
| ('Random Forest', '[suelo+hr+vpd] max_depth=3, min_samples_leaf=20')        |     0.281 |      0.168 |                0.000 |  0.000 |              0.327 |            6.853 |                       0.000 |      5670 | True       | True            | False          |
| ('Random Forest', '[suelo+temp+hr] max_depth=3, min_samples_leaf=20')       |     0.278 |      0.167 |                0.000 |  0.000 |              0.310 |           17.760 |                       0.000 |      5070 | True       | True            | False          |
| ('Regresión logística', '[suelo+temp+vpd] C=0.01')                          |     0.277 |      0.167 |                0.000 |  0.000 |              0.276 |            6.043 |                       0.000 |        72 | True       | True            | False          |
| ('Random Forest', '[suelo+temp+vpd] max_depth=3, min_samples_leaf=20')      |     0.271 |      0.161 |                0.000 |  0.000 |              0.313 |           23.581 |                       0.000 |      5160 | True       | True            | False          |
| ('Random Forest', '[suelo+temp] max_depth=5, min_samples_leaf=20')          |     0.265 |      0.165 |                0.000 |  0.000 |              0.315 |           34.635 |                       0.000 |     11370 | True       | True            | False          |
| ('Random Forest', '[suelo+temp] max_depth=3, min_samples_leaf=20')          |     0.265 |      0.159 |                0.000 |  0.000 |              0.304 |           29.035 |                       0.000 |      5040 | True       | True            | False          |
| ('Regresión logística', '[suelo+temp+vpd] C=1.0')                           |     0.264 |      0.169 |                0.113 |  0.278 |              0.289 |           25.792 |                       0.000 |        72 | True       | True            | False          |
| ('Random Forest', '[suelo+temp+hr] max_depth=5, min_samples_leaf=20')       |     0.263 |      0.161 |                0.000 |  0.000 |              0.298 |           23.803 |                       0.000 |     10920 | True       | True            | False          |
| ('Random Forest', '[suelo+vpd] max_depth=3, min_samples_leaf=100')          |     0.245 |      0.145 |                0.000 |  0.000 |              0.237 |           13.780 |                       0.000 |      4110 | True       | True            | False          |
| ('Random Forest', '[suelo+vpd] max_depth=5, min_samples_leaf=100')          |     0.244 |      0.145 |                0.000 |  0.000 |              0.237 |           22.034 |                       0.000 |      5670 | True       | True            | False          |
| ('Random Forest', '[suelo+hr+vpd] max_depth=5, min_samples_leaf=20')        |     0.229 |      0.136 |                0.000 |  0.000 |              0.236 |           28.077 |                       0.000 |     11820 | True       | True            | False          |
| ('Árbol de decisión', '[suelo+temp+hr] max_depth=2, min_samples_leaf=100')  |     0.221 |      0.138 |                0.000 |  0.000 |              0.237 |            9.727 |                       0.000 |        81 | True       | True            | False          |
| ('Árbol de decisión', '[suelo+vpd] max_depth=2, min_samples_leaf=100')      |     0.220 |      0.130 |                0.000 |  0.000 |              0.206 |            0.000 |                       0.000 |        81 | True       | False           | False          |
| ('Árbol de decisión', '[suelo+vpd] max_depth=3, min_samples_leaf=100')      |     0.220 |      0.130 |                0.000 |  0.000 |              0.206 |            0.000 |                       0.000 |       141 | True       | False           | False          |
| ('Random Forest', '[suelo+temp+vpd] max_depth=5, min_samples_leaf=20')      |     0.218 |      0.132 |                0.000 |  0.000 |              0.232 |           31.098 |                       0.000 |     11880 | True       | True            | False          |
| ('Regresión logística', '[suelo+temp+vpd] C=0.1')                           |     0.213 |      0.128 |                0.000 |  0.000 |              0.222 |           19.455 |                       0.000 |        72 | True       | True            | False          |
| ('Árbol de decisión', '[suelo+temp] max_depth=2, min_samples_leaf=100')     |     0.211 |      0.132 |                0.000 |  0.000 |              0.226 |            9.727 |                       0.000 |        81 | True       | True            | False          |
| ('Árbol de decisión', '[suelo+temp+vpd] max_depth=2, min_samples_leaf=100') |     0.211 |      0.132 |                0.000 |  0.000 |              0.226 |            9.727 |                       0.000 |        81 | True       | True            | False          |
| ('Árbol de decisión', '[suelo+hr] max_depth=2, min_samples_leaf=100')       |     0.210 |      0.123 |                0.000 |  0.000 |              0.196 |            0.000 |                       0.000 |        81 | True       | False           | False          |
| ('Árbol de decisión', '[suelo+hr] max_depth=3, min_samples_leaf=100')       |     0.210 |      0.123 |                0.000 |  0.000 |              0.196 |            0.000 |                       0.000 |       141 | True       | False           | False          |
| ('Árbol de decisión', '[suelo+hr+vpd] max_depth=2, min_samples_leaf=100')   |     0.210 |      0.123 |                0.000 |  0.000 |              0.196 |            0.000 |                       0.000 |        81 | True       | False           | False          |
| ('Árbol de decisión', '[suelo+hr+vpd] max_depth=3, min_samples_leaf=100')   |     0.210 |      0.123 |                0.000 |  0.000 |              0.196 |            0.000 |                       0.000 |       141 | True       | False           | False          |
| ('Random Forest', '[suelo+temp+hr] max_depth=3, min_samples_leaf=100')      |     0.203 |      0.125 |                0.000 |  0.000 |              0.215 |           15.033 |                       0.000 |      4110 | True       | True            | False          |
| ('Random Forest', '[suelo+hr+vpd] max_depth=3, min_samples_leaf=100')       |     0.202 |      0.117 |                0.000 |  0.000 |              0.190 |           18.939 |                       0.000 |      4110 | True       | True            | False          |
| ('Random Forest', '[suelo+hr] max_depth=3, min_samples_leaf=100')           |     0.196 |      0.114 |                0.000 |  0.000 |              0.185 |            4.716 |                       0.000 |      4140 | True       | True            | False          |
| ('Random Forest', '[suelo+hr] max_depth=5, min_samples_leaf=100')           |     0.196 |      0.114 |                0.000 |  0.000 |              0.185 |           12.380 |                       0.000 |      5430 | True       | True            | False          |
| ('Árbol de decisión', '[suelo+vpd] max_depth=4, min_samples_leaf=100')      |     0.196 |      0.116 |                0.000 |  0.000 |              0.182 |            9.654 |                       0.000 |       201 | True       | True            | False          |
| ('Random Forest', '[suelo+hr+vpd] max_depth=5, min_samples_leaf=100')       |     0.196 |      0.113 |                0.000 |  0.000 |              0.185 |           23.876 |                       0.000 |      5460 | True       | True            | False          |
| ('Random Forest', '[suelo+temp+hr] max_depth=5, min_samples_leaf=100')      |     0.196 |      0.121 |                0.000 |  0.000 |              0.208 |           23.066 |                       0.000 |      5550 | True       | True            | False          |
| ('Árbol de decisión', '[suelo+hr+vpd] max_depth=4, min_samples_leaf=100')   |     0.191 |      0.115 |                0.000 |  0.000 |              0.189 |            9.654 |                       0.000 |       201 | True       | True            | False          |
| ('Random Forest', '[suelo+temp+vpd] max_depth=3, min_samples_leaf=100')     |     0.170 |      0.103 |                0.000 |  0.000 |              0.175 |           19.823 |                       0.000 |      4170 | True       | True            | False          |
| ('Árbol de decisión', '[suelo+temp+hr] max_depth=3, min_samples_leaf=100')  |     0.158 |      0.097 |                0.000 |  0.000 |              0.167 |            9.727 |                       0.000 |       141 | True       | True            | False          |
| ('Árbol de decisión', '[suelo+temp+hr] max_depth=4, min_samples_leaf=100')  |     0.158 |      0.097 |                0.000 |  0.000 |              0.167 |           22.329 |                       0.000 |       201 | True       | True            | False          |
| ('Random Forest', '[suelo+temp+vpd] max_depth=5, min_samples_leaf=100')     |     0.157 |      0.095 |                0.000 |  0.000 |              0.163 |           33.014 |                       0.000 |      5580 | True       | True            | False          |
| ('Random Forest', '[suelo+temp] max_depth=3, min_samples_leaf=100')         |     0.153 |      0.094 |                0.000 |  0.000 |              0.161 |           15.844 |                       0.000 |      4440 | True       | True            | False          |
| ('Random Forest', '[suelo+temp] max_depth=5, min_samples_leaf=100')         |     0.153 |      0.094 |                0.000 |  0.000 |              0.161 |           21.444 |                       0.000 |      5670 | True       | True            | False          |
| ('Árbol de decisión', '[suelo+temp] max_depth=3, min_samples_leaf=100')     |     0.150 |      0.092 |                0.000 |  0.000 |              0.157 |            9.727 |                       0.000 |       141 | True       | True            | False          |
| ('Árbol de decisión', '[suelo+temp] max_depth=4, min_samples_leaf=100')     |     0.150 |      0.092 |                0.000 |  0.000 |              0.157 |           22.329 |                       0.000 |       201 | True       | True            | False          |
| ('Árbol de decisión', '[suelo+temp+vpd] max_depth=3, min_samples_leaf=100') |     0.150 |      0.092 |                0.000 |  0.000 |              0.157 |            9.727 |                       0.000 |       141 | True       | True            | False          |
| ('Árbol de decisión', '[suelo+temp+vpd] max_depth=4, min_samples_leaf=100') |     0.150 |      0.092 |                0.000 |  0.000 |              0.157 |           22.329 |                       0.000 |       201 | True       | True            | False          |

## Configuraciones del tipo elegido

|                                                                                                          |   F1 macro fuera de fold, sin dudosos |   F1 macro fuera de fold, todos |   exactitud bal. fuera de fold, todos |   % filas predichas marchita (modelo con todo) |   % marchita en la ventana post-arranque descartada |
|:---------------------------------------------------------------------------------------------------------|--------------------------------------:|--------------------------------:|--------------------------------------:|-----------------------------------------------:|----------------------------------------------------:|
| CONFIG_FINAL: Árbol de decisión [suelo+delta+temp] max_depth=2, min_samples_leaf=100                     |                                 0.282 |                           0.181 |                                 0.200 |                                          9.727 |                                               8.276 |
| criterio de §5.5 (sin seguridad): Árbol de decisión [suelo+delta+temp] max_depth=2, min_samples_leaf=100 |                                 0.282 |                           0.181 |                                 0.200 |                                          9.727 |                                               8.276 |

## Restricción de diseño — sólo suelo vs criterio §5.5 vs final vs dos umbrales — exactitud_bal

| modelo                               |   todos |   sin dudosos |   sin el 13 |   sin dudosos ni el 13 |
|:-------------------------------------|--------:|--------------:|------------:|-----------------------:|
| criterio §5.5 (arbol-p2-f012-58e644) |   0.200 |         0.279 |       0.207 |                  0.361 |
| dos umbrales (baseline)              |   0.295 |         0.416 |       0.309 |                  0.567 |
| final (arbol-p2-f012-58e644)         |   0.200 |         0.279 |       0.207 |                  0.361 |
| sólo suelo (rf-f0-395a04)            |   0.263 |         0.411 |       0.224 |                  0.432 |

## Restricción de diseño — sólo suelo vs criterio §5.5 vs final vs dos umbrales — f1_macro

| modelo                               |   todos |   sin dudosos |   sin el 13 |   sin dudosos ni el 13 |
|:-------------------------------------|--------:|--------------:|------------:|-----------------------:|
| criterio §5.5 (arbol-p2-f012-58e644) |   0.181 |         0.282 |       0.206 |                  0.328 |
| dos umbrales (baseline)              |   0.269 |         0.393 |       0.311 |                  0.481 |
| final (arbol-p2-f012-58e644)         |   0.181 |         0.282 |       0.206 |                  0.328 |
| sólo suelo (rf-f0-395a04)            |   0.225 |         0.373 |       0.183 |                  0.320 |

## Restricción de diseño — sólo suelo vs criterio §5.5 vs final vs dos umbrales — recall_marchita

| modelo                               |   todos |   sin dudosos |   sin el 13 |   sin dudosos ni el 13 |
|:-------------------------------------|--------:|--------------:|------------:|-----------------------:|
| criterio §5.5 (arbol-p2-f012-58e644) |   0.240 |         0.360 |       0.240 |                  0.360 |
| dos umbrales (baseline)              |   0.396 |         0.595 |       0.396 |                  0.595 |
| final (arbol-p2-f012-58e644)         |   0.240 |         0.360 |       0.240 |                  0.360 |
| sólo suelo (rf-f0-395a04)            |   0.000 |         0.000 |       0.000 |                  0.000 |

## Restricción de diseño — resumen

|                                      |   puntaje (F1 sin dudosos) |   desvío bootstrap |   flash estimada (costo_esp32, float, B) |   flash del header exportado (B) |   recall marchita sin dudosos |   ep. 12 | features                         |
|:-------------------------------------|---------------------------:|-------------------:|-----------------------------------------:|---------------------------------:|------------------------------:|---------:|:---------------------------------|
| sólo suelo (rf-f0-395a04)            |                      0.373 |              0.061 |                                    12900 |                        12960.000 |                         0.000 |    0.000 | suelo_mv                         |
| criterio §5.5 (arbol-p2-f012-58e644) |                      0.282 |              0.136 |                                       81 |                           81.000 |                         0.360 |    0.000 | suelo_mv, suelo_delta_1h, temp_c |
| final (arbol-p2-f012-58e644)         |                      0.282 |              0.136 |                                       81 |                           81.000 |                         0.360 |    0.000 | suelo_mv, suelo_delta_1h, temp_c |
| dos umbrales (baseline)              |                      0.393 |              0.191 |                                        8 |                          nan     |                         0.595 |    0.000 | suelo_mv                         |

## Influencia ambiental — importancia por permutación

| feature        |   caída exactitud bal. (media) |   desvío |   % predicciones que cambian (media) |
|:---------------|-------------------------------:|---------:|-------------------------------------:|
| suelo_mv       |                          0.123 |    0.009 |                               32.385 |
| suelo_delta_1h |                          0.000 |    0.000 |                                0.000 |
| temp_c         |                          0.146 |    0.007 |                               17.701 |

## Influencia ambiental — ambiental en la mediana

| ambiental → mediana   |   % filas que cambian |   filas |   episodios afectados |   % de los cambios de noche (22–8 h) |
|:----------------------|----------------------:|--------:|----------------------:|-------------------------------------:|
| temp_c                |                 9.727 | 132.000 |                 1.000 |                               90.909 |

## Influencia ambiental — por episodio

|   episodio_id | clase     | dudoso   |   filas |   % cambia |   acierto con ambiente |   acierto ambiental en mediana |
|--------------:|:----------|:---------|--------:|-----------:|-----------------------:|-------------------------------:|
|         1.000 | marchita  | False    |     132 |    100.000 |                  1.000 |                          0.000 |
|         3.000 | estresada | False    |      24 |      0.000 |                  1.000 |                          1.000 |
|         6.000 | estresada | False    |      74 |      0.000 |                  1.000 |                          1.000 |
|         8.000 | marchita  | True     |     111 |      0.000 |                  0.000 |                          0.000 |
|         9.000 | estresada | True     |      52 |      0.000 |                  0.000 |                          0.000 |
|        10.000 | saludable | False    |     140 |      0.000 |                  1.000 |                          1.000 |
|        11.000 | saludable | True     |      27 |      0.000 |                  0.815 |                          0.815 |
|        12.000 | marchita  | False    |      90 |      0.000 |                  0.000 |                          0.000 |
|        13.000 | estresada | False    |     146 |      0.000 |                  0.904 |                          0.904 |
|        14.000 | estresada | True     |     302 |      0.000 |                  0.000 |                          0.000 |
|        15.000 | saludable | False    |     259 |      0.000 |                  1.000 |                          1.000 |

## Influencia ambiental — barrido con suelo de octubre

|                                                 | rango medido   | cambia la clase   | clases que recorre                        |
|:------------------------------------------------|:---------------|:------------------|:------------------------------------------|
| ('temp_c', '1480 (saludable oct. (mediana))')   | 8.1–34         | True              | 8.1–10.24: marchita | 10.31–34: saludable |
| ('temp_c', '1758 (marchita ep. 12 (mediana))')  | 8.1–34         | True              | 8.1–10.24: marchita | 10.31–34: saludable |
| ('temp_c', '1927 (estresada ep. 13 (mediana))') | 8.1–34         | True              | 8.1–10.24: marchita | 10.31–34: estresada |
| ('temp_c', '1619 (entre saludable y marchita)') | 8.1–34         | True              | 8.1–10.24: marchita | 10.31–34: saludable |

## ¿Proxy de la hora? (V de Cramér con la franja)

|                                                    |   V de Cramér con la franja de 3 h |
|:---------------------------------------------------|-----------------------------------:|
| clase                                              |                              0.471 |
| predicción sólo suelo (rf-f0-395a04)               |                              0.394 |
| predicción criterio §5.5 (arbol-p2-f012-58e644)    |                              0.373 |
| predicción final (arbol-p2-f012-58e644)            |                              0.373 |
| predicción final con las ambientales en la mediana |                              0.211 |
| temp_c (en terciles)                               |                              0.363 |

## Luz como proxy de la hora — regresiones logísticas con luz

|                                       |   F1 sin dudosos |   recall marchita sin dudosos |   ep. 12 |   % marchita en saludables de noche (train) |   % marchita, datos nuevos de noche |   % marchita, datos nuevos de día |
|:--------------------------------------|-----------------:|------------------------------:|---------:|--------------------------------------------:|------------------------------------:|----------------------------------:|
| [suelo_mv+luz_media_1h] C=0.01        |            0.607 |                         0.914 |    0.967 |                                      21.154 |                              75.833 |                             0.000 |
| [suelo_mv+luz_media_1h] C=0.1         |            0.594 |                         0.905 |    0.956 |                                      20.513 |                              75.833 |                             0.000 |
| [suelo_mv+luz_media_1h] C=1.0         |            0.589 |                         0.901 |    0.956 |                                      20.513 |                              75.833 |                             0.000 |
| [suelo_mv+luz_mv+luz_media_1h] C=0.01 |            0.587 |                         0.883 |    0.933 |                                      78.846 |                              75.833 |                             0.000 |
| [suelo_mv+luz_mv+luz_media_1h] C=0.1  |            0.606 |                         0.901 |    0.956 |                                      19.872 |                              78.333 |                             1.562 |
| [suelo_mv+luz_mv+luz_media_1h] C=1.0  |            0.621 |                         0.937 |    1.000 |                                      23.077 |                              82.500 |                             7.812 |
| [suelo_mv+luz_mv] C=0.01              |            0.604 |                         0.856 |    0.889 |                                      23.077 |                               0.000 |                             0.000 |
| [suelo_mv+luz_mv] C=0.1               |            0.609 |                         0.851 |    0.889 |                                      23.077 |                               9.167 |                             0.000 |
| [suelo_mv+luz_mv] C=1.0               |            0.603 |                         0.847 |    0.889 |                                      23.077 |                               9.167 |                             0.000 |

## Modelo final por episodio

|   episodio | clase     | dudoso   |   filas |   suelo_mv_mediana |   final→salud |   final→estre |   final→march |   acierto final (train) |   acierto fuera de fold |
|-----------:|:----------|:---------|--------:|-------------------:|--------------:|--------------:|--------------:|------------------------:|------------------------:|
|          1 | marchita  | False    |     132 |           2832.000 |         0.000 |         0.000 |         1.000 |                   1.000 |                   0.606 |
|          3 | estresada | False    |      24 |           2766.500 |         0.000 |         1.000 |         0.000 |                   1.000 |                   0.000 |
|          6 | estresada | False    |      74 |           2048.000 |         0.000 |         1.000 |         0.000 |                   1.000 |                   0.541 |
|          8 | marchita  | True     |     111 |           1518.000 |         1.000 |         0.000 |         0.000 |                   0.000 |                   0.000 |
|          9 | estresada | True     |      52 |           1454.000 |         1.000 |         0.000 |         0.000 |                   0.000 |                   0.000 |
|         10 | saludable | False    |     140 |           1504.000 |         1.000 |         0.000 |         0.000 |                   1.000 |                   0.893 |
|         11 | saludable | True     |      27 |           1785.500 |         0.815 |         0.185 |         0.000 |                   0.815 |                   0.000 |
|         12 | marchita  | False    |      90 |           1758.000 |         1.000 |         0.000 |         0.000 |                   0.000 |                   0.000 |
|         13 | estresada | False    |     146 |           1927.000 |         0.096 |         0.904 |         0.000 |                   0.904 |                   0.000 |
|         14 | estresada | True     |     302 |           1445.000 |         1.000 |         0.000 |         0.000 |                   0.000 |                   0.000 |
|         15 | saludable | False    |     259 |           1453.000 |         1.000 |         0.000 |         0.000 |                   1.000 |                   0.000 |

## Binario requiere cuidado

|                         |   exactitud_bal (todos) |   recall_cuidado (todos) |   roc_auc (todos) |   exactitud_bal (sin dudosos) |   recall_cuidado (sin dudosos) |   roc_auc (sin dudosos) |
|:------------------------|------------------------:|-------------------------:|------------------:|------------------------------:|-------------------------------:|------------------------:|
| Clase mayoritaria       |                   0.500 |                    1.000 |             0.500 |                         0.500 |                          1.000 |                   0.500 |
| Umbral único (suelo_mv) |                   0.396 |                    0.202 |             0.349 |                         0.516 |                          0.403 |                   0.696 |
| Árbol de decisión       |                   0.327 |                    0.539 |             0.331 |                         0.502 |                          0.882 |                   0.505 |
| Regresión logística     |                   0.377 |                    0.359 |             0.316 |                         0.569 |                          0.717 |                   0.611 |
| Naive Bayes             |                   0.481 |                    0.506 |             0.505 |                         0.743 |                          1.000 |                   0.964 |

## Números clave

|                                                                                 | valor                                                                                                                      |
|:--------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------------------------------------|
| snapshot                                                                        | mediciones_raw_2026-10-21.csv                                                                                              |
| filas / episodios                                                               | 1,357 / 11                                                                                                                 |
| filas / episodios sin dudosos                                                   | 865 / 7                                                                                                                    |
| episodios dudosos                                                               | [8, 9, 11, 14]                                                                                                             |
| fuga: RF 7 features, aleatoria vs por episodio                                  | 0.943 vs 0.135                                                                                                             |
| criterio §5.3 en el espacio restringido (sin seguridad)                         | Árbol de decisión [suelo+delta+temp] max_depth=2, min_samples_leaf=100                                                     |
| elegido tras la condición de seguridad                                          | Árbol de decisión [suelo+delta+temp] max_depth=2, min_samples_leaf=100 (ninguna configuración la cumple: queda la de §5.5) |
| config final                                                                    | Árbol de decisión [suelo+delta+temp] max_depth=2, min_samples_leaf=100                                                     |
| coincide con CONFIG_FINAL                                                       | True                                                                                                                       |
| versión                                                                         | arbol-p2-f012-58e644                                                                                                       |
| header al día                                                                   | True                                                                                                                       |
| F1 macro sin dudosos, búsqueda anidada del tipo final                           | 0.316 ± 0.045                                                                                                              |
| F1 macro sin dudosos, dos umbrales                                              | 0.393 ± 0.191                                                                                                              |
| config. final fija: F1 macro (todos / sin dudosos)                              | 0.181 / 0.282                                                                                                              |
| config. final fija: exactitud bal. (todos / sin dudosos)                        | 0.200 / 0.279                                                                                                              |
| config. final fija: recall marchita (todos / sin dudosos)                       | 0.240 / 0.360                                                                                                              |
| config. final fija: exactitud bal. (todos / sin dud. / sin 13 / sin dud. ni 13) | 0.200 / 0.279 / 0.207 / 0.361                                                                                              |
| costo elegido                                                                   | {'flash_B': 81, 'ram_B': 16, 'ops': 4, 'exps': 0, 't_us_est': 0.16666666666666666, 'exportable': 'sí (if/else o tablas)'}  |
| restricción de diseño                                                           | suelo_mv + al menos una ambiental en todos los candidatos con selección                                                    |
| features del modelo final                                                       | suelo_mv, suelo_delta_1h, temp_c                                                                                           |
| % filas que cambian con la ambiental en la mediana                              | 9.727                                                                                                                      |
| configuraciones exploradas / que pasan costo + influencia + seguridad           | 66 / 0                                                                                                                     |
| puntaje config. fija: sólo suelo / criterio §5.5 / final / dos umbrales         | 0.373 / 0.282 / 0.282 / 0.393                                                                                              |
| V de Cramér franja ~ clase / predicción final / sólo suelo                      | 0.471 / 0.373 / 0.394                                                                                                      |
| datos nuevos 22/10: filas / predicción                                          | 184 / {'saludable': 184}                                                                                                   |
