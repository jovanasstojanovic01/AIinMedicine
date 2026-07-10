import os
import pandas as pd
import config


def flatten_multirow_columns(df):
    
    new_cols = []
    for top, bottom in df.columns:
        top = str(top).strip()
        bottom = str(bottom).strip()
        if top == "VF":
            new_cols.append(f"VF_{bottom}")
        elif bottom.startswith("Unnamed") or bottom in ("", "nan"):
            new_cols.append(top)
        else:
            new_cols.append(f"{top}_{bottom}")
    df.columns = new_cols
    return df


def main():
    grape_excel_path = os.path.join(config.DATA_DIR, "VF and clinical information.xlsx")
    unet_features_path = os.path.join(config.OUTPUT_DIR, "grape_extracted_features.xlsx")

    output_baseline_path = os.path.join(config.OUTPUT_DIR, "grape_baseline_merged.xlsx")
    output_followup_path = os.path.join(config.OUTPUT_DIR, "grape_followup_merged.xlsx")

    if not os.path.exists(grape_excel_path):
        print(f"[GREŠKA] Nije pronađen GRAPE Excel fajl na putanji: {grape_excel_path}")
        return
    if not os.path.exists(unet_features_path):
        print(f"[GREŠKA] Nije pronađen EXCEL sa UNet osobinama na putanji: {unet_features_path}")
        return

    print("-> Učitavanje podataka...")
    unet_df = pd.read_excel(unet_features_path)

    df_baseline = pd.read_excel(grape_excel_path, sheet_name=0, header=[0, 1])
    df_followup = pd.read_excel(grape_excel_path, sheet_name=1, header=[0, 1])

    print(f"-> Broj zapisa pre spajanja - Baseline: {len(df_baseline)}, Follow-up: {len(df_followup)}")

    df_baseline = flatten_multirow_columns(df_baseline)
    df_followup = flatten_multirow_columns(df_followup)

    print("-> Spajanje UNet parametara sa Sheet 1 (Baseline)...")
    baseline_merged = pd.merge(df_baseline, unet_df, on="Corresponding CFP", how="left")

    print("-> Spajanje UNet parametara sa Sheet 2 (Follow-up)...")
    followup_merged = pd.merge(df_followup, unet_df, on="Corresponding CFP", how="left")

    unet_cols = ["vCDR", "hCDR", "aCDR", "Rim_Area_Pixels"]
    NO_CFP_MARKER = "/"

    for name, df_merged, df_original in [
        ("Baseline", baseline_merged, df_baseline),
        ("Follow-up", followup_merged, df_followup),
    ]:
        no_cfp_mask = df_original["Corresponding CFP"].astype(str).str.strip() == NO_CFP_MARKER
        missing_unet = df_merged["vCDR"].isna()

        n_no_cfp = no_cfp_mask.sum()
        n_real_mismatch = (missing_unet & ~no_cfp_mask.values).sum()

        print(f"-> {name}: {n_no_cfp} poseta bez CFP slike (marker '/', očekivano), {n_real_mismatch} pravih promašaja u merge-u (neočekivano).")
        if n_real_mismatch > 0:
            print(f"   [UPOZORENJE] {n_real_mismatch} redova u {name} ima naziv CFP slike koji NE postoji u UNet feature fajlu — vredi proveriti zašto (npr. slika nije obrađena ekstrakcijom).")

        df_merged["has_cfp"] = (~missing_unet).astype(float)

    baseline_merged[unet_cols] = baseline_merged[unet_cols].fillna(0.0)
    followup_merged[unet_cols] = followup_merged[unet_cols].fillna(0.0)

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    baseline_merged.to_excel(output_baseline_path, index=False)
    followup_merged.to_excel(output_followup_path, index=False)

    print("\n================ SPAJANJE PODATAKA USPEŠNO ================")
    print(f"1. Baseline tabela sačuvana na:  {output_baseline_path}")
    print(f"2. Follow-up tabela sačuvana na: {output_followup_path}")
    print(f"Dodata obeležja: {unet_cols + ['has_cfp']}")
    print("==========================================================")


if __name__ == "__main__":
    main()