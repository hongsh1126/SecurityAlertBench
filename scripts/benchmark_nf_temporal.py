"""Run a leakage-safe temporal benchmark on a public NF flow CSV.

The raw dataset is intentionally not committed.  The adapter infers the label and
timestamp columns, keeps numeric flow features, and writes a reproducible report.
"""
from __future__ import annotations

import argparse, json, re, sys, time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (average_precision_score, f1_score, precision_score,
                             recall_score, roc_auc_score)
from sklearn.pipeline import make_pipeline

try:
    from xgboost import XGBClassifier
except ImportError:  # pragma: no cover
    XGBClassifier = None

LABEL_CANDIDATES = ("Label", "label", "Attack", "attack", "target", "Target", "Class", "class")
TIME_CANDIDATES = ("Timestamp", "timestamp", "event_time", "Time", "time", "ts")

def choose_column(columns, candidates, explicit=None):
    if explicit:
        if explicit not in columns: raise ValueError(f"Column not found: {explicit}")
        return explicit
    lower = {str(c).lower(): c for c in columns}
    for c in candidates:
        if c.lower() in lower: return lower[c.lower()]
    return None

def binary_label(series: pd.Series) -> pd.Series:
    text = series.astype(str).str.strip().str.lower()
    benign = text.isin({"0", "false", "benign", "normal", "normal traffic"})
    malicious = text.isin({"1", "true", "attack", "anomaly", "malicious", "dos", "ddos"})
    if (benign | malicious).all(): return malicious.astype(int)
    # Numeric labels: the most common class is treated as benign only when labels are 0/1.
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().all() and set(numeric.unique()).issubset({0, 1}): return numeric.astype(int)
    raise ValueError("Could not map labels to benign/malicious. Use --label-column and inspect values.")

def load_nf(path: Path, label_column=None, time_column=None, max_rows=None):
    frame = pd.read_csv(path, nrows=max_rows)
    label = choose_column(frame.columns, LABEL_CANDIDATES, label_column)
    if label is None: raise ValueError(f"No label column found. Columns include: {list(frame.columns[:20])}")
    ts_col = choose_column(frame.columns, TIME_CANDIDATES, time_column)
    if ts_col is None:
        # NF files sometimes have no timestamp; preserve a documented row-order proxy.
        frame["__row_time"] = np.arange(len(frame)); ts_col = "__row_time"
    y = binary_label(frame[label])
    ts = pd.to_datetime(frame[ts_col], errors="coerce", utc=True)
    if ts.notna().sum() < len(frame) * .8 and ts_col != "__row_time":
        raise ValueError(f"Timestamp column {ts_col!r} is not parseable for temporal ordering.")
    numeric = frame.select_dtypes(include=[np.number]).drop(columns=[label], errors="ignore")
    numeric = numeric.replace([np.inf, -np.inf], np.nan)
    numeric = numeric.loc[:, numeric.notna().any()]
    if numeric.shape[1] < 2: raise ValueError("At least two numeric flow features are required.")
    out = numeric.copy(); out["__timestamp"] = ts.fillna(pd.Timestamp("1970-01-01", tz="UTC")); out["__y"] = y.values
    return out, {"label_column": label, "timestamp_column": ts_col, "rows": len(out), "features": numeric.columns.tolist()}

def metrics(y, p, s):
    return {"precision": precision_score(y,p,zero_division=0), "recall": recall_score(y,p,zero_division=0),
            "f1": f1_score(y,p,zero_division=0), "roc_auc": roc_auc_score(y,s), "pr_auc": average_precision_score(y,s)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True); ap.add_argument("--output", type=Path, default=Path("reports/nf_temporal_benchmark.json"))
    ap.add_argument("--label-column"); ap.add_argument("--time-column"); ap.add_argument("--max-rows", type=int)
    ap.add_argument("--train-fraction", type=float, default=.7); ap.add_argument("--validation-fraction", type=float, default=.15); ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    if XGBClassifier is None: raise SystemExit("xgboost is required: pip install xgboost")
    df, meta = load_nf(args.data, args.label_column, args.time_column, args.max_rows)
    df = df.sort_values("__timestamp").reset_index(drop=True); n=len(df); cut1=int(n*args.train_fraction); cut2=int(n*(args.train_fraction+args.validation_fraction))
    train, test = df.iloc[:cut1], df.iloc[cut2:]
    Xtr=train.drop(columns=["__timestamp","__y"]); Xte=test.drop(columns=["__timestamp","__y"]); ytr=train.__y; yte=test.__y
    models={"random_forest": RandomForestClassifier(n_estimators=300,class_weight="balanced",random_state=args.seed,n_jobs=-1), "xgboost": XGBClassifier(n_estimators=300,max_depth=8,learning_rate=.08,subsample=.8,colsample_bytree=.8,eval_metric="logloss",tree_method="hist",random_state=args.seed,n_jobs=-1)}
    result={"dataset":meta,"split":{"method":"chronological","train_rows":len(train),"validation_rows":cut2-cut1,"test_rows":len(test),"train_end":str(train.__timestamp.max()),"test_start":str(test.__timestamp.min())},"models":{}}
    for name, model in models.items():
        t=time.perf_counter(); pipe=make_pipeline(SimpleImputer(strategy="median"),model); pipe.fit(Xtr,ytr); score=pipe.predict_proba(Xte)[:,1]; pred=(score>=.5).astype(int)
        result["models"][name]={"metrics":metrics(yte,pred,score),"fit_seconds":round(time.perf_counter()-t,3)}
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(result,indent=2,default=str),encoding="utf-8"); print(json.dumps(result,indent=2,default=str))
if __name__ == "__main__": main()
