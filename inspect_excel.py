import pandas as pd
import sys

def analyze_excel(file_path):
    print(f"Analyzing {file_path}...")
    try:
        # Read first 100 rows to understand structure
        df = pd.read_excel(file_path, nrows=100, header=None)
        
        with open("rows.txt", "w", encoding="utf-8") as f:
            for i, row in df.iterrows():
                f.write(f"Row {i}: {row.tolist()}\n")
                if i > 40: break
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_excel(r"c:\Users\kike\.gemini\antigravity\scratch\logistics_optimizer\data\raw\Transporte (1).xlsx")
