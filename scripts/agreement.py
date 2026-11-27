"""
Inter-rater agreement for the clinical prompt-issue taxonomy.

Usage:
    python scripts/agreement.py annotation/results/annotator1.xlsx annotation/results/annotator2.xlsx \
        --key annotation/results/design_key.csv --out-dir annotation/results
    Add --sheet Calibration to check the calibration round.

Reports, per category (binary labels):
  - Cohen's kappa between the two annotators
  - percent agreement
  - positive agreement  (2*both_yes / (yes_A + yes_B)); stable when a label is rare
  - each annotator's agreement with the design (intended) labels
Plus Cohen's kappa over the single primary label, and a list of disagreements to adjudicate.
Writes agreement_results.csv (the table for Slide C) and disagreements.csv.
Needs only pandas + openpyxl.
"""
import argparse, os, sys
import pandas as pd

CATS = ["A1", "A2", "B1", "B2", "B3", "B4", "B5"]
FLAG_BELOW = 0.60


def cohen_kappa(a, b):
    a, b = list(a), list(b)
    n = len(a)
    if n == 0:
        return float("nan")
    labels = sorted(set(a) | set(b))
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(l) / n) * (b.count(l) / n) for l in labels)
    if pe == 1:            # both annotators used one label for every item
        return 1.0 if po == 1 else float("nan")
    return (po - pe) / (1 - pe)


def load(path, sheet):
    df = pd.read_excel(path, sheet_name=sheet, dtype={"item_id": str})
    df = df[df["item_id"].notna()].set_index("item_id")
    for c in CATS + ["Clean"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    missing = df[CATS].isna().any(axis=1)
    if missing.any():
        sys.exit(f"{path}: unlabeled cells in items {', '.join(df.index[missing])}. Fill every 0/1 cell first.")
    df["primary_label"] = df["primary_label"].fillna("").astype(str).str.strip()
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("annotator1"); ap.add_argument("annotator2")
    ap.add_argument("--sheet", default="Main")
    ap.add_argument("--key", default="design_key.csv")
    ap.add_argument("--out-dir", default=".", help="folder for agreement_results.csv and disagreements.csv")
    args = ap.parse_args()

    a, b = load(args.annotator1, args.sheet), load(args.annotator2, args.sheet)
    common = a.index.intersection(b.index)
    a, b = a.loc[common], b.loc[common]
    try:
        key = pd.read_csv(args.key, dtype={"item_id": str}).set_index("item_id").loc[common]
    except (FileNotFoundError, KeyError):
        key = None

    rows = []
    for c in CATS:
        x, y = a[c].astype(int), b[c].astype(int)
        both, ya, yb = int(((x == 1) & (y == 1)).sum()), int(x.sum()), int(y.sum())
        k = cohen_kappa(x, y)
        row = {
            "Category": c, "n_items": len(x),
            "kappa": round(k, 2), "pct_agreement": round((x == y).mean() * 100, 1),
            "positive_agreement": round(2 * both / (ya + yb), 2) if ya + yb else float("nan"),
            "yes_annotator1": ya, "yes_annotator2": yb,
        }
        if key is not None:
            row["ann1_vs_design_pct"] = round((x == key[c]).mean() * 100, 1)
            row["ann2_vs_design_pct"] = round((y == key[c]).mean() * 100, 1)
        row["status"] = "revise" if k < FLAG_BELOW else "ok"
        rows.append(row)

    pk = cohen_kappa(a["primary_label"], b["primary_label"])
    prim = {"Category": "Primary label", "n_items": len(a), "kappa": round(pk, 2),
            "pct_agreement": round((a["primary_label"] == b["primary_label"]).mean() * 100, 1),
            "status": "revise" if pk < FLAG_BELOW else "ok"}
    if key is not None:
        prim["ann1_vs_design_pct"] = round((a["primary_label"] == key["primary_label"]).mean() * 100, 1)
        prim["ann2_vs_design_pct"] = round((b["primary_label"] == key["primary_label"]).mean() * 100, 1)
    rows.append(prim)

    res = pd.DataFrame(rows)
    os.makedirs(args.out_dir, exist_ok=True)
    res.to_csv(os.path.join(args.out_dir, "agreement_results.csv"), index=False)
    print(f"Sheet: {args.sheet} | items compared: {len(common)}\n")
    print(res.to_string(index=False))
    print(f"\nMean kappa across categories: {res['kappa'][:-1].mean():.2f}")

    dis = []
    for iid in common:
        diff = [c for c in CATS if a.at[iid, c] != b.at[iid, c]]
        if diff or a.at[iid, "primary_label"] != b.at[iid, "primary_label"]:
            dis.append({"item_id": iid, "categories_disagree": ",".join(diff),
                        "primary_1": a.at[iid, "primary_label"], "primary_2": b.at[iid, "primary_label"],
                        "notes_1": a.at[iid, "notes"] if "notes" in a else "",
                        "notes_2": b.at[iid, "notes"] if "notes" in b else ""})
    pd.DataFrame(dis).to_csv(os.path.join(args.out_dir, "disagreements.csv"), index=False)
    print(f"\n{len(dis)} items to adjudicate -> {os.path.join(args.out_dir, 'disagreements.csv')}")
    print(f"Agreement table -> {os.path.join(args.out_dir, 'agreement_results.csv')}")


if __name__ == "__main__":
    main()
