import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.stattools import durbin_watson
from pathlib import Path
import json
import os

def run_hedonic_analysis(input_path, output_json):
    print(f"Loading data from {input_path}...")
    # Skip header rows based on previous inspection
    df = pd.read_excel(input_path, skiprows=7)
    
    # Rename columns based on inspection
    cols = [
        'Planta', 'Destino', 'Transportista', 'Fecha', 'TipoEnvio',
        'Trips', 'Drops', 'Days', 'Distance', 'Pallets', 'Cost'
    ]
    df.columns = cols[:len(df.columns)]
    
    # Basic Cleaning
    df = df.dropna(subset=['Cost', 'Distance', 'Pallets'])
    df = df[df['Cost'] > 0]
    df = df[df['Distance'] > 0]
    df = df[df['Pallets'] > 0]
    df = df[df['Trips'] > 0]
    
    # Feature Engineering
    df['CostPerTrial'] = df['Cost'] / df['Trips']
    df['DistancePerTrial'] = df['Distance'] / df['Trips']
    df['PalletsPerTrial'] = df['Pallets'] / df['Trips']
    
    # Log transformations (Hedonic standard)
    df['log_Cost'] = np.log(df['CostPerTrial'])
    df['log_Distance'] = np.log(df['DistancePerTrial'])
    df['log_Pallets'] = np.log(df['PalletsPerTrial'])
    
    # Categorical variables encoding (Top 5 carriers to avoid sparsity)
    top_carriers = df['Transportista'].value_counts().nlargest(5).index
    df['Carrier_Grouped'] = df['Transportista'].apply(lambda x: x if x in top_carriers else 'Other')
    
    # Base predictors
    X_base = df[['log_Distance', 'log_Pallets']]
    type_dummies = pd.get_dummies(df['TipoEnvio'], prefix='Type', drop_first=True)
    carrier_dummies = pd.get_dummies(df['Carrier_Grouped'], prefix='Carr', drop_first=True)
    
    # Model 1: Full Model (with Carrier and Pallets)
    X1 = pd.concat([X_base, carrier_dummies, type_dummies], axis=1)
    X1 = sm.add_constant(X1)
    model1 = sm.OLS(df['log_Cost'], X1.astype(float)).fit()
    
    # Model 2: Base Model (without Carrier, with Pallets)
    X2 = pd.concat([X_base, type_dummies], axis=1)
    X2 = sm.add_constant(X2)
    model2 = sm.OLS(df['log_Cost'], X2.astype(float)).fit()

    # Model 3: No Pallets Model (with Carrier, without Pallets)
    X3 = pd.concat([df[['log_Distance']], type_dummies], axis=1)
    X3 = sm.add_constant(X3)
    model3 = sm.OLS(df['log_Cost'], X3.astype(float)).fit()
    
    def get_model_stats(model, X):
        dw = durbin_watson(model.resid)
        _, bp_pvalue, _, _ = het_breuschpagan(model.resid, X)
        return {
            "summary": {
                "rsquared": model.rsquared,
                "rsquared_adj": model.rsquared_adj,
                "fvalue": model.fvalue,
                "f_pvalue": model.f_pvalue,
                "n_obs": int(model.nobs),
                "durbin_watson": dw,
                "breusch_pagan_p": bp_pvalue
            },
            "coefficients": model.params.to_dict(),
            "pvalues": model.pvalues.to_dict(),
            "std_errors": model.bse.to_dict(),
            "variables": list(X.columns)
        }

    # Prepare results for JSON
    results = {
        "model_full": get_model_stats(model1, X1),
        "model_base": get_model_stats(model2, X2),
        "model_no_pallets": get_model_stats(model3, X3)
    }
    
    # Save to JSON
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    
    print(f"Analysis complete. Results saved to {output_json}")
    print("\n--- MODEL 1 (FULL) ---")
    print(model1.summary())
    print("\n--- MODEL 2 (BASE) ---")
    print(model2.summary())
    print("\n--- MODEL 3 (NO PALLETS) ---")
    print(model3.summary())

if __name__ == "__main__":
    input_file = r"c:\Users\kike\.gemini\antigravity\scratch\logistics_optimizer\data\raw\Transporte (1).xlsx"
    output_file = r"c:\Users\kike\.gemini\antigravity\scratch\logistics_optimizer\outputs\results\hedonic_results.json"
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    run_hedonic_analysis(input_file, output_file)
