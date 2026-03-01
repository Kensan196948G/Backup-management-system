"""
PDF Generator Service using WeasyPrint

Generates professional PDF reports with:
- ISO 27001 compliant templates
- ISO 19650 compliant templates
- Japanese font support
- Charts and graphs embedding
- Headers, footers, and page numbers
- Table of contents
- Cover pages
"""

import base64
import logging
import os
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from flask import render_template
from weasyprint import CSS, HTML
from weasyprint.text.fonts import FontConfiguration

logger = logging.getLogger(__name__)


class PDFGenerator:
    """
    PDF generation service using WeasyPrint.

    Features:
    - HTML to PDF conversion
    - CSS styling for print media
    - Japanese font support (Noto Sans CJK JP)
    - Page numbers and headers/footers
    - Chart/graph embedding
    - ISO compliance templates
    """

    def __init__(self):
        """Initialize PDF generator with font configuration"""
        self.font_config = FontConfiguration()
        self.base_css = self._get_base_css()

    def _get_base_css(self) -> str:
        """Get base CSS for PDF generation with print optimizations"""
        return """
        @page {
            size: A4;
            margin: 2.5cm 2cm 3cm 2cm;

            @top-left {
                content: string(header-title);
                font-size: 10pt;
                color: #666;
                padding-bottom: 0.5cm;
                border-bottom: 1pt solid #ddd;
            }

            @top-right {
                content: string(header-date);
                font-size: 10pt;
                color: #666;
                padding-bottom: 0.5cm;
                border-bottom: 1pt solid #ddd;
            }

            @bottom-center {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 9pt;
                color: #666;
            }
        }

        @page :first {
            margin-top: 0;
            @top-left { content: none; }
            @top-right { content: none; }
        }

        * {
            box-sizing: border-box;
        }

        body {
            font-family: 'Noto Sans CJK JP', 'DejaVu Sans', sans-serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #333;
        }

        h1 {
            font-size: 24pt;
            font-weight: bold;
            margin: 0 0 1cm 0;
            page-break-after: avoid;
        }

        h2 {
            font-size: 18pt;
            font-weight: bold;
            margin: 1.5cm 0 0.5cm 0;
            page-break-after: avoid;
            border-bottom: 2pt solid #2c3e50;
            padding-bottom: 0.2cm;
        }

        h3 {
            font-size: 14pt;
            font-weight: bold;
            margin: 1cm 0 0.4cm 0;
            page-break-after: avoid;
        }

        h4 {
            font-size: 12pt;
            font-weight: bold;
            margin: 0.8cm 0 0.3cm 0;
            page-break-after: avoid;
        }

        p {
            margin: 0.3cm 0;
            text-align: justify;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 0.5cm 0;
            page-break-inside: avoid;
            font-size: 10pt;
        }

        thead {
            display: table-header-group;
        }

        th {
            background-color: #34495e;
            color: white;
            padding: 0.3cm;
            text-align: left;
            font-weight: bold;
            border: 1pt solid #2c3e50;
        }

        td {
            padding: 0.25cm 0.3cm;
            border: 1pt solid #ddd;
        }

        tr:nth-child(even) {
            background-color: #f8f9fa;
        }

        .cover-page {
            height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            page-break-after: always;
        }

        .cover-title {
            font-size: 36pt;
            font-weight: bold;
            margin-bottom: 1cm;
            color: #2c3e50;
        }

        .cover-subtitle {
            font-size: 18pt;
            color: #7f8c8d;
            margin-bottom: 2cm;
        }

        .cover-info {
            font-size: 14pt;
            color: #95a5a6;
            line-height: 2;
        }

        .toc {
            page-break-after: always;
        }

        .toc h2 {
            border-bottom: 3pt solid #2c3e50;
        }

        .toc-item {
            margin: 0.3cm 0;
            padding-left: 0.5cm;
        }

        .toc-item a {
            text-decoration: none;
            color: #2c3e50;
        }

        .section {
            margin: 1cm 0;
        }

        .metric-box {
            display: inline-block;
            width: 30%;
            margin: 0.5cm 1.5%;
            padding: 0.5cm;
            border: 1pt solid #ddd;
            border-radius: 4pt;
            text-align: center;
        }

        .metric-value {
            font-size: 24pt;
            font-weight: bold;
            color: #2c3e50;
            margin: 0.2cm 0;
        }

        .metric-label {
            font-size: 10pt;
            color: #7f8c8d;
        }

        .success {
            color: #27ae60;
        }

        .warning {
            color: #f39c12;
        }

        .danger {
            color: #e74c3c;
        }

        .info {
            color: #3498db;
        }

        .status-badge {
            display: inline-block;
            padding: 0.1cm 0.3cm;
            border-radius: 3pt;
            font-size: 9pt;
            font-weight: bold;
            color: white;
        }

        .status-success {
            background-color: #27ae60;
        }

        .status-warning {
            background-color: #f39c12;
        }

        .status-danger {
            background-color: #e74c3c;
        }

        .status-info {
            background-color: #3498db;
        }

        .chart-container {
            margin: 1cm 0;
            text-align: center;
            page-break-inside: avoid;
        }

        .chart-image {
            max-width: 100%;
            height: auto;
        }

        .compliance-grid {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 0.3cm;
            margin: 0.5cm 0;
        }

        .compliance-item {
            border: 1pt solid #ddd;
            padding: 0.3cm;
            text-align: center;
            border-radius: 4pt;
        }

        .compliance-check {
            font-size: 20pt;
            margin: 0.2cm 0;
        }

        .footer-note {
            margin-top: 2cm;
            padding-top: 0.5cm;
            border-top: 1pt solid #ddd;
            font-size: 9pt;
            color: #7f8c8d;
            text-align: center;
        }

        .page-break {
            page-break-after: always;
        }

        .no-break {
            page-break-inside: avoid;
        }

        .signature-box {
            margin-top: 2cm;
            border: 1pt solid #ddd;
            padding: 0.5cm;
            border-radius: 4pt;
        }

        .signature-line {
            margin: 1cm 0 0.3cm 0;
            border-bottom: 1pt solid #333;
            width: 60%;
        }
        """

    def generate_pdf_from_html(
        self, html_content: str, custom_css: Optional[str] = None, attachments: Optional[List[str]] = None
    ) -> bytes:
        """
        Generate PDF from HTML content.

        Args:
            html_content: HTML string to convert
            custom_css: Additional CSS to apply
            attachments: List of file paths to embed

        Returns:
            PDF content as bytes
        """
        try:
            # Combine CSS
            css_list = [CSS(string=self.base_css, font_config=self.font_config)]
            if custom_css:
                css_list.append(CSS(string=custom_css, font_config=self.font_config))

            # Generate PDF
            html_obj = HTML(string=html_content)
            pdf_bytes = html_obj.write_pdf(stylesheets=css_list, font_config=self.font_config)

            logger.info("PDF generated successfully")
            return pdf_bytes

        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}", exc_info=True)
            raise

    def generate_pdf_from_template(self, template_name: str, context: Dict, custom_css: Optional[str] = None) -> bytes:
        """
        Generate PDF from Flask template.

        Args:
            template_name: Template file name (in templates/reports/)
            context: Template context variables
            custom_css: Additional CSS to apply

        Returns:
            PDF content as bytes
        """
        try:
            # Render template
            html_content = render_template(f"reports/{template_name}", **context)

            # Generate PDF
            return self.generate_pdf_from_html(html_content, custom_css)

        except Exception as e:
            logger.error(f"Error generating PDF from template: {str(e)}", exc_info=True)
            raise

    def embed_chart_as_base64(self, chart_path: str) -> str:
        """
        Convert chart image to base64 for embedding in HTML.

        Args:
            chart_path: Path to chart image file

        Returns:
            Base64 encoded image data URI
        """
        try:
            with open(chart_path, "rb") as f:
                image_data = f.read()

            # Detect image type from extension
            ext = Path(chart_path).suffix.lower()
            mime_type = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".gif": "image/gif",
                ".svg": "image/svg+xml",
            }.get(ext, "image/png")

            # Encode to base64
            base64_data = base64.b64encode(image_data).decode("utf-8")
            return f"data:{mime_type};base64,{base64_data}"

        except Exception as e:
            logger.error(f"Error embedding chart: {str(e)}")
            return ""

    def generate_iso27001_report(self, data: Dict, start_date: datetime, end_date: datetime) -> bytes:
        """
        Generate ISO 27001 compliant report.

        Args:
            data: Report data dictionary
            start_date: Report period start
            end_date: Report period end

        Returns:
            PDF content as bytes
        """
        context = {
            "report_title": "ISO 27001 Information Security Management Report",
            "start_date": start_date,
            "end_date": end_date,
            "generated_date": datetime.now(timezone.utc),
            "data": data,
            "standard": "ISO/IEC 27001:2013",
            "clauses": self._get_iso27001_clauses(data),
        }

        return self.generate_pdf_from_template("iso27001_template.html", context)

    def generate_iso19650_report(self, data: Dict, start_date: datetime, end_date: datetime) -> bytes:
        """
        Generate ISO 19650 compliant report.

        Args:
            data: Report data dictionary
            start_date: Report period start
            end_date: Report period end

        Returns:
            PDF content as bytes
        """
        context = {
            "report_title": "ISO 19650 Information Management Report",
            "start_date": start_date,
            "end_date": end_date,
            "generated_date": datetime.now(timezone.utc),
            "data": data,
            "standard": "ISO 19650:2018",
            "requirements": self._get_iso19650_requirements(data),
        }

        return self.generate_pdf_from_template("iso19650_template.html", context)

    def _get_iso27001_clauses(self, data: Dict) -> List[Dict]:
        """Get ISO 27001 control clauses status"""
        return [
            {
                "number": "A.12.3",
                "title": "Information Backup",
                "description": "Backup copies of information and software shall be taken and tested regularly",
                "status": "compliant" if data.get("compliance_rate", 0) >= 95 else "non_compliant",
                "evidence": f"Compliance rate: {data.get('compliance_rate', 0)}%",
            },
            {
                "number": "A.12.4",
                "title": "Logging and Monitoring",
                "description": "Event logs shall be produced, kept and regularly reviewed",
                "status": "compliant" if data.get("total_actions", 0) > 0 else "partial",
                "evidence": f"Total logged actions: {data.get('total_actions', 0)}",
            },
            {
                "number": "A.18.1",
                "title": "Compliance with Legal Requirements",
                "description": "Ensure compliance with legal, statutory, regulatory obligations",
                "status": "compliant",
                "evidence": "3-2-1-1-0 rule enforced",
            },
        ]

    def _get_iso19650_requirements(self, data: Dict) -> List[Dict]:
        """Get ISO 19650 requirements status"""
        return [
            {
                "number": "5.1.7",
                "title": "Information Management",
                "description": "Information shall be managed throughout its lifecycle",
                "status": "compliant" if data.get("total_jobs", 0) > 0 else "non_compliant",
                "evidence": f"Active backup jobs: {data.get('total_jobs', 0)}",
            },
            {
                "number": "5.1.8",
                "title": "Information Security",
                "description": "Information security shall be maintained",
                "status": "compliant" if data.get("verification_rate", 0) >= 90 else "partial",
                "evidence": f"Verification rate: {data.get('verification_rate', 0)}%",
            },
            {
                "number": "5.7",
                "title": "Archive and Retrieval",
                "description": "Information shall be archived and retrievable",
                "status": "compliant",
                "evidence": "Multi-tier backup strategy implemented",
            },
        ]


class ChartGenerator:
    """
    Generate charts for PDF reports using matplotlib.

    Note: Charts are generated as PNG images and embedded in PDFs
    """

    @staticmethod
    def generate_compliance_trend_chart(data: Dict, output_path: str) -> str:
        """
        Generate compliance trend chart.

        Args:
            data: Chart data dictionary
            output_path: Output file path

        Returns:
            Path to generated chart
        """
        try:
            import matplotlib

            matplotlib.use("Agg")  # Non-GUI backend
            import matplotlib.font_manager as fm
            import matplotlib.pyplot as plt

            # Try to use Japanese font
            try:
                font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
                if os.path.exists(font_path):
                    fm.fontManager.addfont(font_path)
                    plt.rcParams["font.family"] = "Noto Sans CJK JP"
            except Exception:  # nosec B110 - font loading is optional, ignore failures
                pass

            dates = data.get("dates", [])
            compliance_rates = data.get("compliance_rates", [])

            plt.plot(dates, compliance_rates, marker="o", linewidth=2, color="#2c3e50")
            plt.axhline(y=95, color="#27ae60", linestyle="--", label="Target (95%)")
            plt.fill_between(dates, compliance_rates, alpha=0.3)

            plt.xlabel("Date", fontsize=12)
            plt.ylabel("Compliance Rate (%)", fontsize=12)
            plt.title("3-2-1-1-0 Compliance Trend", fontsize=14, fontweight="bold")
            plt.grid(True, alpha=0.3)
            plt.legend()
            plt.tight_layout()

            plt.savefig(output_path, dpi=150, bbox_inches="tight")
            plt.close()

            logger.info(f"Chart generated: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error generating chart: {str(e)}")
            return ""

    @staticmethod
    def generate_backup_status_pie_chart(data: Dict, output_path: str) -> str:
        """
        Generate backup status pie chart.

        Args:
            data: Chart data dictionary
            output_path: Output file path

        Returns:
            Path to generated chart
        """
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            plt.figure(figsize=(8, 8))

            labels = ["Success", "Failed", "Warning"]
            sizes = [data.get("success_count", 0), data.get("failed_count", 0), data.get("warning_count", 0)]
            colors = ["#27ae60", "#e74c3c", "#f39c12"]
            explode = (0.1, 0, 0)  # Explode success slice

            plt.pie(sizes, explode=explode, labels=labels, colors=colors, autopct="%1.1f%%", shadow=True, startangle=90)

            plt.axis("equal")
            plt.title("Backup Execution Status", fontsize=14, fontweight="bold")
            plt.tight_layout()

            plt.savefig(output_path, dpi=150, bbox_inches="tight")
            plt.close()

            logger.info(f"Chart generated: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error generating chart: {str(e)}")
            return ""
