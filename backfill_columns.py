import pandas as pd
import json

def load_mapping():
    try:
        with open("category_mapping.json", "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading mapping: {e}")
        return {}

def categorize_transaction(particulars, mapping):
    if pd.isna(particulars): return "Other / Uncategorized"
    particulars_str = str(particulars).upper()
    for category, keywords in mapping.items():
        for keyword in keywords:
            if str(keyword).upper() in particulars_str:
                return category
    return "Other / Uncategorized"

def backfill():
    file_path = "NEW_Consolodated10YearsStatementsICICI_1454_2016To25.xlsx"
    print(f"Loading {file_path}...")
    df = pd.read_excel(file_path)
    
    mapping = load_mapping()
    
    print("Normalizing dates...")
    # The user's new file seems to have multiple date formats (e.g. 07/03/2016). Let's use robust parsing.
    # We will prioritize 'Date' column if multiple exist.
    date_col = 'Date' if 'Date' in df.columns else 'Transaction Date'
    
    # Handle possible empty rows
    df = df.dropna(subset=[date_col, 'Particulars'], how='all')
    
    # Try parsing date with dayfirst=True since ICICI is typically DD-MM-YYYY or DD/MM/YYYY
    parsed_dates = pd.to_datetime(df[date_col], dayfirst=True, errors='coerce')
    
    print("Backfilling YEAR, Month, Year_Month...")
    df['YEAR'] = parsed_dates.dt.year
    df['Month'] = parsed_dates.dt.month
    df['Year_Month'] = parsed_dates.dt.to_period('M').astype(str)
    
    print("Backfilling Categories...")
    df['Category'] = df['Particulars'].apply(lambda x: categorize_transaction(x, mapping))
    
    print("Saving back to excel...")
    df.to_excel(file_path, index=False)
    print("Done! Backfill complete.")

if __name__ == "__main__":
    backfill()
