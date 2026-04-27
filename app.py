import streamlit as st
import pandas as pd
import io
import math

from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.graphics.barcode import code128
from reportlab.graphics import renderPDF


# -------------------------------
# PAGE CONFIG
# -------------------------------
st.set_page_config(
    page_title="Aditya Sticker Generator",
    page_icon="🏷️",
    layout="centered"
)

# -------------------------------
# CUSTOM STYLE
# -------------------------------
st.markdown("""
<style>
.main {
background-color:#f8f9fa;
}

.stButton>button {
width:100%;
height:3em;
border-radius:8px;
background:#007bff;
color:white;
font-weight:600;
}

.stDownloadButton>button{
width:100%;
height:3em;
border-radius:8px;
background:#28a745;
color:white;
font-weight:600;
}

.upload-text{
font-size:1.2rem;
font-weight:bold;
}

.small-note{
font-size:0.9rem;
color:gray;
}
</style>
""", unsafe_allow_html=True)


# -------------------------------
# HELPERS
# -------------------------------

REQUIRED_COLUMNS = [
    "product name",
    "mrp",
    "copies",
    "unit"
]


def normalize_columns(df):
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace("_", " ", regex=False)
    )
    return df


def fit_centered_text(c, text, font="Times-Bold",
                      start_size=10,
                      min_size=6,
                      available_width=4.4*cm):
    """
    Reduce font until text fits.
    """
    size = start_size

    while size >= min_size:
        if c.stringWidth(text, font, size) <= available_width:
            return size
        size -= 0.5

    return min_size


def clean_mrp(val):
    try:
        num = float(val)
        if num.is_integer():
            return str(int(num))
        return str(num)
    except:
        return str(val)


def make_template():
    sample = pd.DataFrame({
        "Product name": [
            "Steel Pipe",
            "Wall Tile",
            "PVC Fitting"
        ],
        "MRP": [
            450,
            1200,
            80
        ],
        "Copies": [
            10,
            5,
            20
        ],
        "Unit": [
            "pcs",
            "box",
            "pcs"
        ]
    })

    output = io.BytesIO()
    sample.to_csv(output, index=False)
    output.seek(0)
    return output


# -------------------------------
# PDF GENERATOR
# -------------------------------

def generate_pdf(
    df,
    show_barcode=False
):

    buffer = io.BytesIO()

    label_width = 5 * cm
    label_height = 2.5 * cm

    c = canvas.Canvas(
        buffer,
        pagesize=(label_width, label_height)
    )

    skipped_rows = []

    for idx, row in df.iterrows():

        try:
            product = str(row["product name"]).strip()

            if product.lower() in ["nan", ""]:
                skipped_rows.append(idx+2)
                continue

            mrp = clean_mrp(row["mrp"])
            unit = str(row["unit"]).strip()

            copies = int(float(row["copies"]))

            if copies <= 0:
                skipped_rows.append(idx+2)
                continue

        except:
            skipped_rows.append(idx+2)
            continue

        price_line = f"MRP: Rs {mrp}/{unit}"

        for i in range(copies):

            # Header
            c.setFont("Times-Bold",8)
            c.drawCentredString(
                label_width/2,
                label_height-0.45*cm,
                "Aditya Enterprises"
            )

            c.setFont("Times-Bold",7)
            c.drawCentredString(
                label_width/2,
                label_height-0.80*cm,
                "PAN No: 604867492"
            )

            c.setFont("Times-Bold",8)
            c.drawCentredString(
                label_width/2,
                label_height-1.18*cm,
                "OLD STOCK"
            )

            # Auto-fit product text
            size = fit_centered_text(
                c,
                product,
                start_size=10,
                available_width=4.3*cm
            )

            c.setFont("Times-Bold",size)
            c.drawCentredString(
                label_width/2,
                label_height-1.65*cm,
                product
            )

            c.setFont("Times-Bold",10)
            c.drawCentredString(
                label_width/2,
                label_height-2.05*cm,
                price_line
            )

            # Optional barcode
            if show_barcode:
                barcode = code128.Code128(
                    product[:20],
                    barHeight=0.25*cm,
                    barWidth=0.012*cm
                )
                barcode.drawOn(
                    c,
                    0.55*cm,
                    0.15*cm
                )

            c.showPage()

    c.save()

    buffer.seek(0)

    return buffer, skipped_rows


# -------------------------------
# UI
# -------------------------------

st.title("RH Sticker Generator")
st.write(
    "Generate precision thermal labels for "
    "**Aditya Enterprises**"
)

st.download_button(
    "Download Sample CSV Template",
    data=make_template(),
    file_name="RH_template.csv",
    mime="text/csv"
)

st.divider()

st.markdown(
'<p class="upload-text">Step 1: Upload Data</p>',
unsafe_allow_html=True
)

uploaded_file = st.file_uploader(
    "Upload CSV or Excel",
    type=["csv","xlsx"]
)

barcode_option = st.checkbox(
    "Include Barcode"
)

if uploaded_file:

    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        df = normalize_columns(df)

        missing = [
            c for c in REQUIRED_COLUMNS
            if c not in df.columns
        ]

        if missing:
            st.error(
                "Missing columns: "
                + ", ".join(missing)
            )
            st.stop()

        st.success("File verified successfully")

        with st.expander("Preview Data"):
            st.dataframe(df.head(20))

        # Total labels count
        total_labels = pd.to_numeric(
            df["copies"],
            errors="coerce"
        ).fillna(0).clip(lower=0).sum()

        st.info(
            f"Total Labels To Generate: {int(total_labels)}"
        )

        st.markdown(
        '<p class="upload-text">Step 2: Generate PDF</p>',
        unsafe_allow_html=True
        )

        if st.button("Create Labels PDF"):

            with st.spinner("Generating labels..."):

                pdf_data, skipped = generate_pdf(
                    df,
                    barcode_option
                )

                st.session_state["pdf_data"] = pdf_data

                if skipped:
                    st.warning(
                        "Skipped invalid rows "
                        f"(Excel rows): {skipped}"
                    )

                st.success("PDF Ready")

        if "pdf_data" in st.session_state:

            st.download_button(
                "Download Labels PDF",
                data=st.session_state["pdf_data"],
                file_name="Aditya_Labels.pdf",
                mime="application/pdf"
            )

    except Exception as e:
        st.error(
            f"Error: {str(e)}"
        )


st.divider()

st.caption(
"Label: 5cm x 2.5cm | "
"Auto-fit text | "
"Thermal Print Ready"
)
