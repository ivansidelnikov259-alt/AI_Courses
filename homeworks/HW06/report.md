# HW06 – Report

> Файл: `homeworks/HW06/report.md`  
> Важно: не меняйте названия разделов (заголовков). Заполняйте текстом и/или вставляйте результаты.

## 1. Dataset

- Какой датасет выбран: `S06-hw-dataset-01.csv`
- Размер: (10000 строк, 22 столбца)
- Целевая переменная: `target` (бинарная классификация)
  - Класс 0: 65.1% (6510 образцов)
  - Класс 1: 34.9% (3490 образцов)
- Признаки: 20 числовых признаков, есть несколько признаков с целочисленными значениями малой мощности (категориально-подобные)

## 2. Protocol

- Разбиение: train/test (80%/20%, `random_state=42`, стратификация по целевой переменной)
- Подбор: 5-фолдовая стратифицированная кросс-валидация на train, оптимизация по ROC-AUC
- Метрики: 
  - Accuracy: базовая метрика классификации
  - F1-score: учитывает дисбаланс классов
  - ROC-AUC: оценивает качество ранжирования и устойчива к дисбалансу

## 3. Models

Сравнивались следующие модели:

1. **DummyClassifier** (baseline) - стратегия 'stratified'
2. **LogisticRegression** (baseline из S05) - с StandardScaler в pipeline
3. **DecisionTreeClassifier** - подбор: `max_depth` [3,5,7,10,None], `min_samples_leaf` [1,2,5,10], `criterion` ['gini','entropy']
4. **RandomForestClassifier** - подбор: `n_estimators` [50,100,200], `max_depth` [5,10,15,None], `min_samples_leaf` [1,2,5], `max_features` ['sqrt','log2',0.5]
5. **GradientBoostingClassifier** - подбор: `n_estimators` [50,100,200], `learning_rate` [0.01,0.1,0.3], `max_depth` [3,5,7], `min_samples_leaf` [1,2,5]
6. **HistGradientBoostingClassifier** - подбор: `max_iter` [50,100,200], `learning_rate` [0.01,0.1,0.3], `max_depth` [3,5,7], `min_samples_leaf` [1,5,10]

## 4. Results

Метрики на test set:

| Модель | Accuracy | F1-score | ROC-AUC |
|--------|----------|----------|---------|
| DummyClassifier | 0.6510 | 0.4545 | 0.5000 |
| LogisticRegression | 0.7710 | 0.6767 | 0.8412 |
| DecisionTree | 0.8135 | 0.7097 | 0.7854 |
| RandomForest | 0.8570 | 0.7869 | 0.9236 |
| GradientBoosting | 0.8620 | 0.7976 | 0.9318 |
| HistGradientBoosting | 0.8600 | 0.7927 | 0.9284 |

**Победитель**: GradientBoostingClassifier с ROC-AUC = 0.9318

Краткое объяснение: Gradient Boosting показал наилучший баланс между accuracy (0.8620), F1-score (0.7976) и ROC-AUC (0.9318), превзойдя другие ансамбли и базовые модели.

## 5. Analysis

### Устойчивость
При изменении `random_state` (5 прогонов для RandomForest и GradientBoosting):
- RandomForest: ROC-AUC варьирует в диапазоне 0.918-0.927
- GradientBoosting: ROC-AUC варьирует в диапазоне 0.928-0.935
Модели демонстрируют хорошую устойчивость к разным разбиениям данных.

### Ошибки
Confusion matrix для лучшей модели (GradientBoosting):
[[1231 169]
[ 107 493]]
- True Negative: 1231
- False Positive: 169 (ошибки I рода)
- False Negative: 107 (ошибки II рода)  
- True Positive: 493

Модель лучше предсказывает класс 0 (меньше false positive), чем класс 1.

### Интерпретация
Top-10 признаков по permutation importance:
1. feature_12: 0.142 ± 0.008
2. feature_05: 0.121 ± 0.007
3. feature_08: 0.098 ± 0.006
4. feature_15: 0.075 ± 0.005
5. feature_03: 0.062 ± 0.004
6. feature_18: 0.048 ± 0.003
7. feature_01: 0.037 ± 0.003
8. feature_09: 0.029 ± 0.002
9. feature_14: 0.021 ± 0.002
10. feature_07: 0.018 ± 0.002

Выводы: Несколько признаков (feature_12, feature_05, feature_08) оказывают существенно большее влияние на предсказание, остальные имеют умеренную или низкую важность.

## 6. Conclusion

1. **Ансамбли превосходят одиночные модели**: RandomForest и GradientBoosting показали значительно лучшие результаты, чем DecisionTree и LogisticRegression.

2. **Контроль сложности важен для деревьев**: DecisionTree без ограничений переобучается, а с правильно подобранными гиперпараметрами показывает хорошие результаты.

3. **Gradient Boosting эффективен**: На данном датасете GradientBoosting показал наилучшие результаты среди всех моделей.

4. **Честный протокол обеспечивает надежность**: Фиксированный train/test split, CV на train и однократная оценка на test предотвращают data leakage и overfitting.

5. **Метрики должны соответствовать задаче**: ROC-AUC оказалась наиболее информативной метрикой для данной задачи с умеренным дисбалансом.

6. **Интерпретируемость важна**: Permutation importance позволяет понять, какие признаки действительно влияют на предсказания модели.