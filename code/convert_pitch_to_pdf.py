#!/usr/bin/env python3
"""
Convert MASTER_PITCH_OPTIMIZED.txt to professional PDF using built-in libraries
"""
import sys
from pathlib import Path

# Try different approaches
try:
    from fpdf import FPDF
    use_fpdf = True
except ImportError:
    use_fpdf = False

def create_pdf_with_fpdf(text_file, output_pdf):
    """Create PDF using fpdf2 (simpler than reportlab)"""
    from fpdf import FPDF
    
    pdf = FPDF(format='A4', margin=15)
    pdf.add_page()
    pdf.set_font('Courier', '', 9)
    
    with open(text_file, 'r', encoding='utf-8') as f:
        for line in f:
            # Handle long lines
            line = line.rstrip('\n')
            if len(line) > 95:
                # Split long lines
                while len(line) > 95:
                    pdf.cell(0, 4, line[:95], ln=1)
                    line = line[95:]
            pdf.cell(0, 4, line, ln=1)
    
    pdf.output(output_pdf)
    return output_pdf

def create_pdf_html_conversion(text_file, html_file, pdf_file):
    """Create HTML first, then offer to convert to PDF"""
    html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LumenCore Master Pitch</title>
    <style>
        body {
            font-family: 'Courier New', monospace;
            line-height: 1.5;
            color: #1a1a1a;
            background: white;
            padding: 40px;
            max-width: 900px;
            margin: 0 auto;
        }
        h1, h2, h3 {
            font-family: 'Segoe UI', Tahoma, sans-serif;
            color: #003366;
        }
        .header {
            text-align: center;
            border-bottom: 3px solid #003366;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        .section {
            margin: 30px 0;
            page-break-inside: avoid;
        }
        .divider {
            text-align: center;
            color: #666;
            margin: 20px 0;
            font-weight: bold;
        }
        pre {
            white-space: pre-wrap;
            word-wrap: break-word;
            background: #f5f5f5;
            padding: 15px;
            border-left: 4px solid #003366;
            overflow-x: auto;
        }
        .highlight {
            background: #fffacd;
            padding: 2px 5px;
        }
        ul, ol {
            margin-left: 20px;
        }
        li {
            margin: 8px 0;
        }
        @media print {
            body { padding: 20px; }
            .section { page-break-inside: avoid; }
        }
        .footer {
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #ccc;
            font-size: 0.9em;
            color: #666;
        }
    </style>
</head>
<body>
"""
    
    with open(text_file, 'r', encoding='utf-8') as f:
        content = f.read()
        # Basic HTML escaping and formatting
        content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        content = content.replace('\n\n', '</p><p>')
        html_content += f'<pre>{content}</pre>'
    
    html_content += """
    <div class="footer">
        <p>© 2026 LumenCore™ | Proprietary & Confidential</p>
        <p>For qualified investors and strategic partners only</p>
    </div>
</body>
</html>
"""
    
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return html_file

# Main execution
if __name__ == '__main__':
    text_file = Path(r'c:\Users\Novac\iCloudDrive\Lumen_nova-core master-dos\MASTER_PITCH_OPTIMIZED.txt')
    pdf_file = Path(r'c:\Users\Novac\iCloudDrive\Lumen_nova-core master-dos\MASTER_PITCH_OPTIMIZED.pdf')
    html_file = Path(r'c:\Users\Novac\iCloudDrive\Lumen_nova-core master-dos\MASTER_PITCH_OPTIMIZED.html')
    
    if not text_file.exists():
        print(f"Error: {text_file} not found")
        sys.exit(1)
    
    try:
        # Try fpdf2 first
        if use_fpdf:
            print(f"Creating PDF with fpdf2...")
            create_pdf_with_fpdf(str(text_file), str(pdf_file))
            print(f"✓ PDF created: {pdf_file}")
        else:
            print(f"fpdf2 not available. Creating HTML version (printable to PDF)...")
            html_out = create_pdf_html_conversion(str(text_file), str(html_file), str(pdf_file))
            print(f"✓ HTML created: {html_out}")
            print(f"  → Open in browser and print to PDF (Ctrl+P → Save as PDF)")
    except Exception as e:
        print(f"Error: {e}")
        print(f"Fallback: Creating HTML version...")
        html_out = create_pdf_html_conversion(str(text_file), str(html_file), str(pdf_file))
        print(f"✓ HTML created: {html_out}")
        sys.exit(0)
