import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def generate_pdf():
    os.makedirs("sample_docs", exist_ok=True)
    pdf_path = "sample_docs/trap_document_test.pdf"
    
    c = canvas.Canvas(pdf_path, pagesize=letter)
    
    # Title
    c.setFont("Helvetica-Bold", 24)
    c.setFillColorRGB(0.09, 0.12, 0.23) # Dark Navy
    c.drawString(50, 720, "AcmeTech Enterprise Workflow Suite")
    
    # Subtitle
    c.setFont("Helvetica-Oblique", 12)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawString(50, 700, "Official Factual Briefing & Product Summary - Fiscal Year 2026")
    
    # Divider
    c.setStrokeColorRGB(0.7, 0.7, 0.7)
    c.setLineWidth(1)
    c.line(50, 685, 550, 685)
    
    # Body Paragraph 1
    c.setFont("Helvetica", 11)
    c.setFillColorRGB(0.1, 0.1, 0.1)
    c.drawString(50, 660, "AcmeTech is the world's leading AI-assisted automation engine. Originally founded on")
    c.drawString(50, 642, "October 12, 2010, the company has scaled rapidly to power modern digital enterprises.")
    
    # Section Header: Stats & Growth
    c.setFont("Helvetica-Bold", 14)
    c.setFillColorRGB(0.2, 0.3, 0.6)
    c.drawString(50, 600, "Key Market Milestones")
    
    # Stats Items
    c.setFont("Helvetica", 11)
    c.setFillColorRGB(0.1, 0.1, 0.1)
    # Claim 1: Outdated/Incorrect pricing (normally enterprise is much higher or different, but let's make a checkable price)
    c.drawString(70, 575, "- Pricing: Enterprise subscription starts at a flat rate of $49 per user per month.")
    
    # Claim 2: Fabricated Scale (500M enterprise organizations is impossible since there are only about 330M businesses globally)
    c.drawString(70, 555, "- Global Scaling: As of 2025, AcmeTech has over 500 million active enterprise clients globally.")
    
    # Claim 3: False Capital of Australia (Sydney is false, Canberra is correct)
    c.drawString(70, 535, "- Headquarters: Operating out of Sydney, the capital city of Australia.")
    
    # Claim 4: Technical figures (uptime)
    c.drawString(70, 515, "- Uptime: We maintain a proven 99.999% uptime service level agreement (SLA).")
    
    # Claim 5: Fabricated Acquisition (Apple acquiring Microsoft/AcmeTech for 150B in 2025)
    c.drawString(70, 495, "- Historical Acquisition: In June 2025, AcmeTech was acquired by Apple Inc. for $150 billion.")
    
    # Footer
    c.setFont("Helvetica", 9)
    c.setFillColorRGB(0.6, 0.6, 0.6)
    c.drawString(50, 50, "Copyright 2026 AcmeTech Group. Information extracted for validation purposes.")
    
    c.save()
    print(f"Successfully generated {pdf_path}")

if __name__ == "__main__":
    generate_pdf()
