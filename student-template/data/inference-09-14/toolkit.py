"""第09课通用读表与自然频数工具；不含正式方案。"""
from pathlib import Path
import csv
HERE = Path(__file__).resolve().parent

def table(name):
    with (HERE/name).open(encoding='utf-8',newline='') as f:
        return list(csv.DictReader(f))

def natural_frequencies(n,base,sensitivity,specificity):
    if n<0 or any(not 0<=p<=1 for p in (base,sensitivity,specificity)):
        raise ValueError('invalid probability or size')
    tp=n*base*sensitivity; fp=n*(1-base)*(1-specificity)
    return {'true_positive':tp,'false_positive':fp,'positive':tp+fp,
            'missed':n*base-tp,'positive_predictive_value':tp/(tp+fp) if tp+fp else None}
