import PyPDF2
import os

pdf_path = r"C:\Users\mdk72\Documents\project\주도주매매\주도주 퀀트 자동매매 로직 생성.pdf"
output_path = r"C:\Users\mdk72\Documents\project\주도주매매\strategy_extracted.txt"

def extract_text(path):
    with open(path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text

if os.path.exists(pdf_path):
    extracted_text = extract_text(pdf_path)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(extracted_text)
    print(f"Extracted text saved to {output_path}")
else:
    print(f"PDF not found at {pdf_path}")
