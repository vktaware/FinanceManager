import pdfplumber

file = "pdfData/Statement_DEC2016_806271531.pdf"

with open("output.txt", "w", encoding="utf-8") as out:
    with pdfplumber.open(file) as pdf:
        for i in range(min(5, len(pdf.pages))):
            out.write(f"--- Page {i+1} ---\n")
            tables = pdf.pages[i].extract_tables()
            for j, table in enumerate(tables):
                out.write(f"Table {j+1}:\n")
                if not table: continue
                out.write(f"  Header: {table[0]}\n")
                if len(table) > 1:
                    out.write(f"  Row 1: {table[1]}\n")
                out.write("\n")
