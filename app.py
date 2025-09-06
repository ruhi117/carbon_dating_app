# app.py
from flask import Flask, request, render_template, redirect, url_for
import pandas as pd
import numpy as np
import io, base64, os, re

# -----------------------------
# Matplotlib non-GUI backend
# -----------------------------
import matplotlib
matplotlib.use('Agg')   # avoids Tk runtime errors
import matplotlib.pyplot as plt

# -----------------------------
# Flask setup
# -----------------------------
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# -----------------------------
# Helpers
# -----------------------------
def normalize_df(df):
    df = df.copy()
    new_cols = [re.sub(r'[^0-9a-zA-Z]+', '_', str(c)).lower().strip('_') for c in df.columns]
    df.columns = new_cols

    mapping = {}
    sigma_assigned = False
    for c in df.columns:
        if 'cal' in c and 'bp' in c:
            mapping[c] = 'cal_bp'
        elif ('14c' in c and 'age' in c) or ('c14' in c and 'age' in c) or (c.startswith('14') and 'age' in c):
            mapping[c] = 'c14_age'
        elif 'delta' in c and '14' in c:
            mapping[c] = 'delta14c'
        elif 'sigma' in c:
            mapping[c] = 'sigma' if not sigma_assigned else 'sigma1'
            sigma_assigned = True
    return df.rename(columns=mapping)

def load_calibration_file(path):
    if not os.path.exists(path):
        print(f"[ERROR] Calibration file not found: {path}")
        return None
    try:
        df = pd.read_csv(path, skipinitialspace=True)
    except Exception as e:
        print(f"[ERROR] Could not read calibration file: {e}")
        return None

    df = normalize_df(df)
    if 'cal_bp' not in df.columns or 'c14_age' not in df.columns:
        print(f"[ERROR] Required columns missing in calibration file. Columns: {df.columns.tolist()}")
        return None

    keep_cols = ['cal_bp', 'c14_age']
    if 'sigma' in df.columns:
        keep_cols.append('sigma')
    df = df[keep_cols].dropna().reset_index(drop=True)
    df['cal_bp'] = pd.to_numeric(df['cal_bp'], errors='coerce')
    df['c14_age'] = pd.to_numeric(df['c14_age'], errors='coerce')
    if 'sigma' in df.columns:
        df['sigma'] = pd.to_numeric(df['sigma'], errors='coerce')
    df = df.dropna().reset_index(drop=True)
    print(f"[INFO] Calibration dataset loaded: {len(df)} rows")
    return df

CAL_FILE = "intcal20.14c"
cal_df = load_calibration_file(CAL_FILE)

def calibrate_c14(raw_age, df=cal_df):
    if df is None or len(df) == 0:
        return None
    ds = df.sort_values('c14_age')
    xp = ds['c14_age'].values
    fp = ds['cal_bp'].values
    if raw_age < xp.min() or raw_age > xp.max():
        return None
    return round(float(np.interp(raw_age, xp, fp)), 2)

def contamination_guidance(raw_age, cal_age):
    w = []
    if raw_age is None:
        w.append("Invalid input.")
        return w
    if cal_age is None:
        w.append("⚠️ Age outside calibration range. Consider alternative methods (U-series, K-Ar).")
        return w
    if raw_age > 50000:
        w.append("⚠️ Very old sample (>50k BP). C-14 may be unreliable.")
        w.append("Suggested: Uranium-series, K-Ar, or stratigraphic correlation.")
    elif raw_age < 1000:
        w.append("⚠️ Very young sample. Check for modern contamination.")
    w.append("📌 If uncertainty is large, request AMS or multiple replicate measurements.")
    w.append("📌 Record soil pH, depth, and pre-treatment protocol for lab notes.")
    return w

def plot_graph(raw_ages, cal_ages, df=cal_df):
    if df is None or len(df) == 0:
        return None
    ds = df.sort_values('c14_age')
    plt.figure(figsize=(9,4.5))
    plt.plot(ds['c14_age'], ds['cal_bp'], label='IntCal20 (cal BP vs 14C BP)')
    for raw, cal in zip(raw_ages, cal_ages):
        if cal is not None:
            plt.scatter(raw, cal, color='red', s=40)
            plt.text(raw, cal, f"{int(raw)} → {cal}", fontsize=8, va='bottom')
    plt.xlabel('Radiocarbon Age (14C BP)')
    plt.ylabel('Calendar Age (cal BP)')
    plt.title('Calibration curve with sample points')
    plt.gca().invert_xaxis()
    plt.grid(alpha=0.3)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode('ascii')
    plt.close()
    return img_b64

# -----------------------------
# Routes
# -----------------------------
@app.route('/')
def home():
    return render_template('index.html')  # shows scrollable slides

@app.route('/index')
def index():
    return render_template('index.html')  # optional alternative URL

@app.route('/input', methods=['GET', 'POST'])
def input_page():
    results = []
    img_str = None
    message = None

    if request.method == 'POST':
        raw_ages = []

        # single input
        c14_text = request.form.get('c14_age', '').strip()
        if c14_text:
            try:
                raw_ages.append(float(c14_text))
            except:
                message = "Could not parse the entered C-14 age. Use a number."

        # file upload
        upload = request.files.get('file')
        if upload and upload.filename:
            try:
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], upload.filename)
                upload.save(filepath)
                df_uploaded = pd.read_csv(filepath, skipinitialspace=True)
                df_uploaded = normalize_df(df_uploaded)
                if 'c14_age' in df_uploaded.columns:
                    arr = df_uploaded['c14_age'].astype(float).tolist()
                else:
                    num_cols = df_uploaded.select_dtypes(include=[np.number]).columns.tolist()
                    if not num_cols:
                        message = "Uploaded CSV had no numeric column. Expect 'C14_age'."
                        arr = []
                    else:
                        arr = df_uploaded[num_cols[0]].astype(float).tolist()
                raw_ages.extend(arr)
            except Exception as e:
                message = f"Failed to read uploaded CSV: {e}"

        if not raw_ages:
            if not message:
                message = "No input provided. Enter a C-14 age or upload CSV."
        else:
            raw_ages = [float(x) for x in raw_ages]
            cal_ages = [calibrate_c14(r) for r in raw_ages]
            for raw, cal in zip(raw_ages, cal_ages):
                warnings = contamination_guidance(raw, cal)
                results.append({'c14_age': raw, 'calibrated_age': cal, 'warnings': warnings})
            img_str = plot_graph(raw_ages, cal_ages)

        return render_template('results.html', results=results, img_str=img_str, message=message)

    return render_template('input.html', message=message)

# -----------------------------
if __name__ == '__main__':
    app.run(debug=True)
