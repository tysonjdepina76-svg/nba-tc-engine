# TC ML Classifier — Classification Report

## Performance Summary

| Class | Precision | Recall | F1 | Support |
|-------|-----------|--------|-----|---------|
| Class 0 (Lays) | 0.88 | 0.98 | 0.93 | 73,718 |
| Class 1 (Backs) | 0.85 | 0.41 | 0.56 | 16,271 |
| **Accuracy** | 0.88 | | | 89,989 |

## Macro Averages

- **Precision (macro)**: 0.865
- **Recall (macro)**: 0.695
- **F1 (macro)**: 0.745

## Weighted Averages

- **Precision (weighted)**: 0.879
- **Recall (weighted)**: 0.880
- **F1 (weighted)**: 0.866

## Interpretation

**Lays (Class 0)** are the model's strength:
- 98% recall = catches almost every lay opportunity
- 93% F1 = production-grade precision/recall balance

**Backs (Class 1)** need work:
- 41% recall = missing 59% of back opportunities
- 0.56 F1 = below 0.65 production threshold
- The class imbalance (73.7k vs 16.3k = 4.5:1) is the root cause

## Recommended Fixes

1. **SMOTE oversample** Class 1 to balance at 2:1 or 1:1
2. **Class weights** in XGBoost: `scale_pos_weight=4.5`
3. **Threshold tuning** — lower decision threshold from 0.5 to 0.35
4. **Cost-sensitive learning** — penalize missing a Back 3x more than a Lay

## Expected Impact After Fixes

- Class 1 Recall: 0.41 → 0.70+
- Class 1 F1: 0.56 → 0.70+
- Overall Accuracy: 0.88 → 0.85 (acceptable trade — fewer missed Backs)
