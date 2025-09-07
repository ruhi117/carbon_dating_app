from flask import Flask, request, render_template, redirect, url_for
import pandas as pd
import numpy as np
import io, base64, os, re

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


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

def contamination_guidance(raw_age, cal_age, soil_pH=None, depth=None):
    recs = []
    if raw_age is None:
        recs.append("Invalid input for C-14 age.")
        return recs

    if cal_age is None:
        recs.append("Age is outside calibration range. Consider U-series or stratigraphic dating.")
    elif raw_age > 50000:
        recs.append("Very old sample (>50k BP). C-14 may be unreliable. Suggest alternative methods.")
    elif raw_age < 1000:
        recs.append("Very young sample. Modern contamination possible.")

    if soil_pH is not None:
        if soil_pH < 6.5:
            recs.append("Acidic soil detected. Consider liming to neutralize pH for better preservation.")
        elif soil_pH > 7.5:
            recs.append("Alkaline soil detected. Consider adding acidic amendments (e.g., elemental sulfur).")
        else:
            recs.append("Soil pH is within the optimal range for carbon dating (6.5–7.5).")

    if depth is not None:
        if depth < 30:
            recs.append("Shallow sample. Risk of modern contamination is higher.")
        elif depth > 200:
            recs.append("Deep sample. Ensure proper stratigraphic context is recorded.")
        else:
            recs.append("Sample depth is within typical excavation range.")

    recs.append("Document all pre-treatment protocols and replicate measurements for accuracy.")
    return recs

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


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/slides')
def slides():
    return render_template('slides.html')


@app.route('/results')
def results():
    return render_template('results.html')



@app.route('/input', methods=['GET', 'POST'])
def input_page():
    results = []
    summaries = []
    img_str = None
    message = None

    if request.method == 'POST':
        raw_ages = []

        
        c14_text = request.form.get('c14_age', '').strip()
        if c14_text:
            try:
                raw_ages.append(float(c14_text))
            except ValueError:
                message = "Could not parse the entered C-14 age. Use a numeric value."

       
        upload = request.files.get('file')
        if upload and upload.filename:
            if upload.filename.lower().endswith('.csv'):
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
                            message = "Uploaded CSV has no numeric column. Expect 'C14_age'."
                            arr = []
                        else:
                            arr = df_uploaded[num_cols[0]].astype(float).tolist()
                    raw_ages.extend(arr)
                except Exception as e:
                    message = f"Failed to read uploaded CSV: {e}"
            else:
                message = "Only CSV files are allowed for upload."

        
        soil_pH = request.form.get('soil_pH', '').strip()
        depth = request.form.get('depth', '').strip()
        location = request.form.get('location', '').strip()
        material = request.form.get('material', '').strip()

        try:
            soil_pH = float(soil_pH) if soil_pH else None
        except ValueError:
            message = "Soil pH must be a number."

        try:
            depth = float(depth) if depth else None
        except ValueError:
            message = "Depth must be a number."

       
        if not raw_ages:
            if not message:
                message = "No input provided. Enter a C-14 age or upload a CSV file."
        else:
            # Calibrate ages
            cal_ages = [calibrate_c14(r) for r in raw_ages]

            # Collect results
            for raw, cal in zip(raw_ages, cal_ages):
                warnings = contamination_guidance(raw, cal, soil_pH=soil_pH, depth=depth)
                results.append({
                    'c14_age': raw,
                    'calibrated_age': cal,
                    'warnings': warnings,
                    'soil_pH': soil_pH,
                    'depth': depth,
                    'location': location,
                    'material': material
                })

            # Generate calibration graph
            img_str = plot_graph(raw_ages, cal_ages)

            # Generate detailed summaries
            summaries = []
            for r in results:
                cal_age_str = f"{r['calibrated_age']} cal BP" if r['calibrated_age'] is not None else "Outside calibration range"
                summary = (
                    f"Sample details:\n"
                    f"- Radiocarbon Age: {r['c14_age']} 14C BP\n"
                    f"- Calibrated Age: {cal_age_str}\n"
                    f"- Location: {r.get('location','Not provided')}\n"
                    f"- Material: {r.get('material','Not provided')}\n"
                    f"- Soil pH: {r.get('soil_pH','Not provided')}\n"
                    f"- Depth: {r.get('depth','Not provided')} cm\n\n"
                    f"Recommendations:\n"
                )
                for w in r['warnings']:
                    summary += f"- {w}\n"
                summaries.append(summary)

                text = f"The sample has a radiocarbon age of {r['c14_age']} BP, calibrated to about {r['calibrated_age']} BP. "

                
                if r["soil_pH"]:
                    if float(r["soil_pH"]) < 5.5:
                        text += f"The soil is acidic (pH {r['soil_pH']}), which may reduce preservation quality. "
                    else:
                        text += f"The soil is neutral to alkaline (pH {r['soil_pH']}), favorable for preservation. "

                
                if r["depth"]:
                    depth_val = float(r["depth"])
                    if depth_val < 50:
                        text += f"The depth of {depth_val} cm indicates shallow burial, vulnerable to disturbance. "
                    elif depth_val < 200:
                        text += f"The depth of {depth_val} cm suggests stable medium burial conditions. "
                else:
                    text += f"At {depth_val} cm, the sample is deeply buried, offering better preservation. "

                
                if r["material"]:
                    text += f"The material type recorded is {r['material']}, which influences preservation accuracy. "
                else:
                    text += "Material type was not specified, which limits interpretation. "

                
                if r["location"]:
                    text += f"The location is noted as {r['location']}. "

                
                text += "Recommendation: Cross-check with nearby stratigraphic layers and apply soil conservation methods if required."
                summaries.append(text)
        return render_template('results.html', results=results, img_str=img_str, message=message, summaries=summaries)

    return render_template('input.html', message=message)


if __name__ == '__main__':
    app.run(debug=True)
