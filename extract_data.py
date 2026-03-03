import pdfplumber
import pandas as pd
import os
import glob
import re
import json

PDF_DIR = "pdfData"
files = glob.glob(os.path.join(PDF_DIR, "*.pdf"))

all_transactions = []

# To track balances across the file (optional, just for diff computation)
def parse_amt(val):
    return float(val.replace(',', ''))

def load_mapping():
    try:
        with open("category_mapping.json", "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading category mapping: {e}")
        return {}

def categorize_transaction(particulars, mapping):
    particulars_upper = particulars.upper()
    for category, keywords in mapping.items():
        for keyword in keywords:
            if keyword.upper() in particulars_upper:
                return category
    return "Other / Uncategorized"

mapping = load_mapping()

for file in files:
    filename = os.path.basename(file)
    try:
        year = filename.split('_')[1][3:]
    except IndexError:
        continue
        
    print(f"Processing {filename} for Year {year}...")
    try:
        with pdfplumber.open(file) as pdf:
            current_tx = None
            for page in pdf.pages:
                text = page.extract_text(y_tolerance=5)
                if not text: continue
                
                for line in text.split('\n'):
                    line = line.strip()
                    if not line: continue
                    
                    # Ignore known headers/footers
                    if "Statement of Transactions" in line or "ACCOUNT DETAILS" in line or "Page " in line or "MHW1" in line or "MR.VIKRAM" in line:
                        continue
                    if "DATE MODE" in line or "FIXED DEPOSITS" in line or "TOTAL " in line:
                        continue
                        
                    # Match full transaction: Date, Particulars, Amount, Balance
                    match_full = re.match(r"^(\d{2}-\d{2}-\d{4})\s+(.*?)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})$", line)
                    # Match brought forward (no amount): Date, Particulars, Balance
                    match_bf = re.match(r"^(\d{2}-\d{2}-\d{4})\s+(.*?)\s+([\d,]+\.\d{2})$", line)
                    
                    if match_full:
                        if current_tx:
                            all_transactions.append(current_tx)
                            
                        date, part, amt, bal = match_full.groups()
                        current_tx = {
                            "Year": year,
                            "Date": date,
                            "Particulars": part.strip(),
                            "Category": categorize_transaction(part.strip(), mapping),
                            "Amount": parse_amt(amt),
                            "Balance": parse_amt(bal),
                            "Deposits": 0.0,
                            "Withdrawals": 0.0
                        }
                    elif match_bf:
                        if current_tx:
                            all_transactions.append(current_tx)
                            
                        date, part, bal = match_bf.groups()
                        current_tx = {
                            "Year": year,
                            "Date": date,
                            "Particulars": part.strip(),
                            "Category": categorize_transaction(part.strip(), mapping),
                            "Amount": 0.0,
                            "Balance": parse_amt(bal),
                            "Deposits": 0.0,
                            "Withdrawals": 0.0
                        }
                    else:
                        # Continuation line for particulars
                        if current_tx:
                            # Avoid appending junk
                            if not re.match(r"^\d{2}-\d{2}-\d{4}", line):
                                current_tx["Particulars"] += " " + line
            
            if current_tx:
                all_transactions.append(current_tx)
                
    except Exception as e:
        print(f"Error processing {filename}: {e}")

if all_transactions:
    # Compute Deposits and Withdrawals mathematically to be perfectly accurate
    df = pd.DataFrame(all_transactions)
    
    # Sort by standard Date logic just in case, though they are sequential in PDF
    # df['Date_Obj'] = pd.to_datetime(df['Date'], format="%d-%m-%Y")
    # df = df.sort_values('Date_Obj')
    
    prev_balance = 0.0
    for i, row in df.iterrows():
        # If it's a B/F (Brought Forward) or first transaction, just set prev_balance
        if row['Amount'] == 0.0 or i == 0:
            pass
        else:
            diff = row['Balance'] - prev_balance
            # Handle float precision
            diff = round(diff, 2)
            if diff > 0:
                df.at[i, 'Deposits'] = row['Amount']
            elif diff < 0:
                df.at[i, 'Withdrawals'] = row['Amount']
            else:
                # Fallback if diff is 0 but amount isn't, though rare
                pass
        prev_balance = row['Balance']
        
    df = df[['Year', 'Date', 'Particulars', 'Category', 'Deposits', 'Withdrawals', 'Balance']]
    
    output_path = "Vikram_Consolidated_Statements_10Years.xlsx"
    df.to_excel(output_path, index=False)
    print(f"\nExcel file created successfully at {output_path} with {len(df)} rows!")
else:
    print("\nNo data was extracted from the PDFs.")
