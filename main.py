# import streamlit as st
# import fitz  # PyMuPDF
# import pytesseract
# from PIL import Image
# import io
# from reportlab.lib.pagesizes import letter
# from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
# from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
# from reportlab.lib.units import inch
# import xml.sax.saxutils as saxutils


# def extract_text_from_pdf(pdf_file):
#     pdf_bytes = pdf_file.read()
#     pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")

#     text = ""

#     for page_num in range(pdf_document.page_count):
#         page = pdf_document.load_page(page_num)
#         image_list = page.get_images(full=True)
#         if not image_list:
#             continue
#         for img_index, img in enumerate(image_list):
#             xref = img[0]
#             base_image = pdf_document.extract_image(xref)
#             image_bytes = base_image["image"]
#             image_ext = base_image["ext"]
#             image = Image.open(io.BytesIO(image_bytes))
#             page_text = pytesseract.image_to_string(image, lang='hin')
#             text += page_text 
#             # + "\n"

#     return text


# def create_pdf_with_text(text, output_pdf_path):
#     doc = SimpleDocTemplate(output_pdf_path, pagesize=letter)
#     styles = getSampleStyleSheet()
#     style = ParagraphStyle(
#         name='Justify',
#         parent=styles['Normal'],
#         alignment=4,
#         leading=12,
#         spaceAfter=6,
#         leftIndent=0,
#         rightIndent=0,
#         spaceBefore=0
#     )

#     sanitized_text = saxutils.escape(text)
#     paragraphs = sanitized_text.split('\n')
#     flowables = []
#     for para in paragraphs:
#         if para.strip():
#             p = Paragraph(para, style)
#             flowables.append(p)
#             flowables.append(Spacer(1, 0.1 * inch))
#     doc.build(flowables)


# st.title("PDF Text Extraction and Generation")

# uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

# if uploaded_file is not None:
#     extracted_text = extract_text_from_pdf(uploaded_file)
#     st.subheader("Extracted Text")
#     st.text(extracted_text)
#     if st.button("Generate PDF with Extracted Text"):
#         output_pdf_path = "extracted_text.pdf"
#         create_pdf_with_text(extracted_text, output_pdf_path)
#         with open(output_pdf_path, "rb") as file:
#             btn = st.download_button(
#                 label="Download PDF",
#                 data=file,
#                 file_name="extracted_text.pdf",
#                 mime="application/pdf"
#             )
import streamlit as st
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import multiprocessing
from functools import partial
import xml.sax.saxutils as saxutils
from time import sleep
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
import xml.sax.saxutils as saxutils
import time
import os

# Function to preprocess image for better OCR performance
def preprocess_image(image):
    # Convert image to grayscale
    return image.convert("L")

# Function to extract text from a single page of PDF and return it
def extract_text_from_page(page_num, pdf_bytes, progress_queue):
    pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = pdf_document.load_page(page_num)
    image_list = page.get_images(full=True)
    text = ""

    for img_index, img in enumerate(image_list):
        xref = img[0]
        base_image = pdf_document.extract_image(xref)
        image_bytes = base_image["image"]
        image = Image.open(io.BytesIO(image_bytes))
        
        # Preprocess image before OCR
        image = preprocess_image(image)
        
        page_text = pytesseract.image_to_string(image, lang='hin', config='--oem 3 --psm 6')
        text += page_text + "\n"

    progress_queue.put(page_num)  # Update the progress queue

    return text.strip()

# Function to extract text from PDF using multiprocessing
def extract_text_from_pdf_parallel(pdf_file, output_txt_path):
    pdf_bytes = pdf_file.read()
    num_pages = fitz.open(stream=pdf_bytes, filetype="pdf").page_count
    manager = multiprocessing.Manager()
    progress_queue = manager.Queue()

    # Use an optimal number of CPU cores for multiprocessing
    num_cores = min(4, multiprocessing.cpu_count())  # Adjust based on your system

    with multiprocessing.Pool(processes=num_cores) as pool:
        extract_partial = partial(extract_text_from_page, pdf_bytes=pdf_bytes, progress_queue=progress_queue)
        async_results = [pool.apply_async(extract_partial, args=(i,)) for i in range(num_pages)]

        progress_bar = st.progress(0)
        status_text = st.empty()

        start_time = time.time()
        extracted_texts = []

        for i in range(num_pages):
            page_num = progress_queue.get()
            progress_bar.progress((i + 1) / num_pages)
            status_text.text(f"Processing page {page_num + 1}/{num_pages}")
            extracted_texts.append(async_results[page_num].get())

        # Join all the text and write to the file once
        full_text = "\n".join(extracted_texts)
        with open(output_txt_path, "w", encoding="utf-8") as txt_file:
            txt_file.write(full_text)

        end_time = time.time()
        elapsed_time = end_time - start_time

    return elapsed_time

# Streamlit web application interface
def main():
    st.title("Text Extraction from PDF")

    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

    if uploaded_file is not None:
        # Generate a unique output file name based on the uploaded file name
        output_txt_path = f"{os.path.splitext(uploaded_file.name)[0]}_extracted.txt"

        # Start timer
        st.info("Extracting text from PDF and writing to TXT file. Please wait...")
        elapsed_time = extract_text_from_pdf_parallel(uploaded_file, output_txt_path)
        st.success("Text extraction and writing to TXT file complete!")

        st.write(f"Time taken for processing: {elapsed_time:.2f} seconds")

        # Provide download button for the TXT file
        with open(output_txt_path, "rb") as file:
            st.download_button(
                label="Download TXT",
                data=file,
                file_name=output_txt_path,
                mime="text/plain"
            )

if __name__ == '__main__':
    main()