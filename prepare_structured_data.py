import os
import json
import re
import fitz  # PyMuPDF
import pytesseract
from pytesseract import Output
from PIL import Image

FIELD_MAP = {
    "product name": "Product Name",
    "application": "Application",
    "nominal thickness": "Nominal Thickness",
    "thickness": "Nominal Thickness",
    "grammage": "Grammage",
    "gsm": "Grammage",
    "printability": "Surface Printability option",
    "surface printability": "Surface Printability option",
    "cof": "COF(dy)",
    "sit": "SIT",
    "seal init": "SIT",
    "seal initiation": "SIT",
    "wvtr": "WVTR",
    "shrinkage": "Shrinkage",
    "optical density": "Optical Density",
    "seal strength": "Seal strength",
    "otr": "OTR"
}


def pdf_page_to_image(page, dpi=300):
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)


def extract_fields_from_image(img, filename):
    data = pytesseract.image_to_data(img, output_type=Output.DICT)
    n_boxes = len(data['text'])

    results = {
        "Product Name": os.path.splitext(filename)[0],
        "Application": [],
        "Nominal Thickness": [],
        "Grammage": "",
        "Surface Printability option": "",
        "COF(dy)": "",
        "SIT": "",
        "WVTR": "",
        "Shrinkage": "",
        "Optical Density": "",
        "Seal strength": "",
        "OTR": []
    }

    for i in range(n_boxes):
        text = data['text'][i].strip().lower()
        if not text or len(text) < 2:
            continue

        for key, field in FIELD_MAP.items():
            if key in text:
                for j in range(i+1, min(i+6, n_boxes)):
                    val = re.findall(r"\d+\.?\d*", data['text'][j])
                    if val:
                        if isinstance(results[field], list):
                            results[field].extend(val)
                        else:
                            results[field] = val[0]
                        break

    for key in ["Application", "Nominal Thickness", "OTR"]:
        results[key] = sorted(set(results[key]))

    return results


def main():
    pdf_folder = "pdfs"
    output_file = "extracted_data.json"
    all_results = []

    for pdf_filename in os.listdir(pdf_folder):
        if pdf_filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(pdf_folder, pdf_filename)
            doc = fitz.open(pdf_path)
            for i, page in enumerate(doc):
                print(f"🔍 Processing {pdf_filename} page {i+1}")
                image = pdf_page_to_image(page)
                data = extract_fields_from_image(image, pdf_filename)
                all_results.append({"pdf": pdf_filename, "page": i + 1, "data": data})

    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"✅ Done. Extracted data saved to {output_file}")

if __name__ == "__main__":
    main()
