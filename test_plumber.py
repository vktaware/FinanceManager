import pdfplumber

file = "pdfData/Statement_DEC2016_806271531.pdf"

with open("output.txt", "w", encoding="utf-8") as out:
    with pdfplumber.open(file) as pdf:
        for i in range(1): # Just first page
            out.write(f"--- Page {i+1} ---\n")
            page = pdf.pages[i]
            
            # y_tolerance=5 to group multi-line stuff that's slightly misaligned
            text = page.extract_text(y_tolerance=5)
            out.write(text)
