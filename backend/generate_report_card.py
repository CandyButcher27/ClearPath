#!/usr/bin/env python3
"""
PDF Report Card Generator for ClearPath Products

This script reads the normalized shipment data from samples_normal.json
and generates a comprehensive PDF report card for a specified product,
including basic information and analysis of all abnormal flags.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor, black, white, red, green, orange
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.platypus.tableofcontents import TableOfContents
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
except ImportError:
    print("Error: reportlab is required. Install with: pip install reportlab")
    sys.exit(1)


@dataclass
class FlagAnalysis:
    """Stores analysis of a specific flag"""
    flag_name: str
    is_flagged: bool
    severity: str  # 'critical', 'warning', 'info'
    description: str
    root_cause: str
    recommendations: List[str]
    details: Dict[str, Any]


class ReportCardGenerator:
    def __init__(self, json_file_path: str):
        self.json_file_path = json_file_path
        self.data = self._load_data()
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
    def _load_data(self) -> List[Dict]:
        """Load normalized data from JSON file"""
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: File {self.json_file_path} not found")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in {self.json_file_path}: {e}")
            sys.exit(1)
    
    def _setup_custom_styles(self):
        """Setup custom styles for the PDF report"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=HexColor('#2E4053')
        ))
        
        # Heading style
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            textColor=HexColor('#34495E'),
            borderWidth=1,
            borderColor=HexColor('#BDC3C7'),
            borderPadding=5
        ))
        
        # Critical flag style
        self.styles.add(ParagraphStyle(
            name='CriticalFlag',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=red,
            backColor=HexColor('#FFE5E5'),
            borderPadding=3
        ))
        
        # Warning flag style
        self.styles.add(ParagraphStyle(
            name='WarningFlag',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=orange,
            backColor=HexColor('#FFF4E5'),
            borderPadding=3
        ))
        
        # Normal text style
        self.styles.add(ParagraphStyle(
            name='CustomNormal',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=6
        ))

    def find_product(self, product_id: str) -> Optional[Dict]:
        """Find product data by ID"""
        for product in self.data:
            if product.get('product_id') == product_id:
                return product
        return None

    def _analyze_flag(self, flag_name: str, flag_data: Dict, category: str) -> FlagAnalysis:
        """Analyze a specific flag and provide recommendations"""
        if not flag_data or flag_data.get('is_flagged') is None:
            return FlagAnalysis(
                flag_name=flag_name,
                is_flagged=False,
                severity='info',
                description="No issues detected",
                root_cause="",
                recommendations=[],
                details=flag_data or {}
            )
        
        is_flagged = flag_data.get('is_flagged', False)
        
        # Determine severity and provide analysis based on flag type
        if category == 'logistics_flags':
            return self._analyze_logistics_flag(flag_name, flag_data)
        elif category == 'quantity_weight_flags':
            return self._analyze_quantity_weight_flag(flag_name, flag_data)
        elif category == 'product_specific_flags':
            return self._analyze_product_specific_flag(flag_name, flag_data)
        elif category == 'financial_timing_flags':
            return self._analyze_financial_timing_flag(flag_name, flag_data)
        
        return FlagAnalysis(
            flag_name=flag_name,
            is_flagged=is_flagged,
            severity='warning' if is_flagged else 'info',
            description="Flag detected" if is_flagged else "No issues",
            root_cause="Unknown",
            recommendations=["Review this flag manually"],
            details=flag_data
        )

    def _analyze_logistics_flag(self, flag_name: str, flag_data: Dict) -> FlagAnalysis:
        """Analyze logistics-related flags"""
        if flag_name == 'destination_address_mismatch' and flag_data.get('is_flagged'):
            score = flag_data.get('score', 0)
            return FlagAnalysis(
                flag_name=flag_name,
                is_flagged=True,
                severity='critical' if score < 60 else 'warning',
                description=f"Destination address mismatch detected (similarity: {score}%)",
                root_cause="Bill of Lading and Packing List show different delivery addresses",
                recommendations=[
                    "Verify correct delivery address with customer",
                    "Update shipping documents to match",
                    "Confirm with warehouse which address is accurate"
                ],
                details=flag_data
            )
        
        elif flag_name == 'incoterm_conflict' and flag_data.get('is_flagged'):
            return FlagAnalysis(
                flag_name=flag_name,
                is_flagged=True,
                severity='warning',
                description="Incoterm conflict detected",
                root_cause=f"FOB point specified but freight terms are '{flag_data.get('terms', 'Unknown')}'",
                recommendations=[
                    "Review incoterm agreement with trading partner",
                    "Update Bill of Lading to reflect correct terms",
                    "Ensure financial responsibility is clearly defined"
                ],
                details=flag_data
            )
        
        elif flag_name == 'scac_missing' and flag_data.get('is_flagged'):
            return FlagAnalysis(
                flag_name=flag_name,
                is_flagged=True,
                severity='critical',
                description="Carrier SCAC code missing",
                root_cause="Standard Carrier Alpha Code not provided in carrier details",
                recommendations=[
                    "Obtain SCAC code from carrier",
                    "Update Bill of Lading with carrier information",
                    "Verify carrier is properly registered"
                ],
                details=flag_data
            )
        
        return FlagAnalysis(
            flag_name=flag_name,
            is_flagged=flag_data.get('is_flagged', False),
            severity='info',
            description="No logistics issues detected",
            root_cause="",
            recommendations=[],
            details=flag_data
        )

    def _analyze_quantity_weight_flag(self, flag_name: str, flag_data: Dict) -> FlagAnalysis:
        """Analyze quantity and weight related flags"""
        if flag_name == 'weight_mismatch' and flag_data.get('is_flagged'):
            variance = flag_data.get('variance_kg', 0)
            threshold = flag_data.get('threshold_kg', 0)
            return FlagAnalysis(
                flag_name=flag_name,
                is_flagged=True,
                severity='critical' if variance > threshold * 2 else 'warning',
                description=f"Weight mismatch: {variance}kg variance (threshold: {threshold}kg)",
                root_cause="Bill of Lading weight differs from Packing List weight",
                recommendations=[
                    "Re-weigh shipment if possible",
                    "Verify which document contains correct weight",
                    "Check for partial shipments or documentation errors"
                ],
                details=flag_data
            )
        
        elif flag_name == 'overcharge_risk' and flag_data.get('is_flagged'):
            inv_qty = flag_data.get('invoice_total_qty', 0)
            pl_qty = flag_data.get('pl_total_shipped', 0)
            return FlagAnalysis(
                flag_name=flag_name,
                is_flagged=True,
                severity='critical',
                description=f"Potential overcharge: Invoice qty ({inv_qty}) > Shipped qty ({pl_qty})",
                root_cause="Invoice shows higher quantity than what was shipped",
                recommendations=[
                    "Verify actual shipped quantity",
                    "Check for credit memos or adjustments",
                    "Review contract terms for billing practices"
                ],
                details=flag_data
            )
        
        elif flag_name == 'short_shipment' and flag_data.get('is_flagged'):
            short_items = flag_data.get('short_items', [])
            return FlagAnalysis(
                flag_name=flag_name,
                is_flagged=True,
                severity='warning',
                description=f"Short shipment detected: {len(short_items)} items affected",
                root_cause="Ordered quantity exceeds shipped quantity",
                recommendations=[
                    "Contact customer about shortage",
                    "Plan for supplemental shipment",
                    "Update inventory records"
                ],
                details=flag_data
            )
        
        return FlagAnalysis(
            flag_name=flag_name,
            is_flagged=flag_data.get('is_flagged', False),
            severity='info',
            description="No quantity/weight issues detected",
            root_cause="",
            recommendations=[],
            details=flag_data
        )

    def _analyze_product_specific_flag(self, flag_name: str, flag_data: Dict) -> FlagAnalysis:
        """Analyze product-specific flags"""
        if flag_name == 'hazmat_mismatch' and flag_data.get('is_flagged'):
            meta_haz = flag_data.get('meta_hazmat', False)
            bol_haz = flag_data.get('bol_hazmat', False)
            return FlagAnalysis(
                flag_name=flag_name,
                is_flagged=True,
                severity='critical',
                description=f"Hazardous material declaration mismatch: Metadata={meta_haz}, BoL={bol_haz}",
                root_cause="Inconsistent hazardous material classification across documents",
                recommendations=[
                    "Verify actual hazardous material status",
                    "Update Safety Data Sheet if needed",
                    "Ensure proper hazmat documentation and handling"
                ],
                details=flag_data
            )
        
        elif flag_name == 'density_anomaly' and flag_data.get('is_flagged'):
            density = flag_data.get('calculated_kg_m3', 0)
            expected = flag_data.get('expected_range', [])
            return FlagAnalysis(
                flag_name=flag_name,
                is_flagged=True,
                severity='warning',
                description=f"Density anomaly: {density}kg/m³ (expected: {expected})",
                root_cause="Calculated density falls outside expected range for material type",
                recommendations=[
                    "Verify weight and volume measurements",
                    "Check for material contamination or substitution",
                    "Review HS code classification"
                ],
                details=flag_data
            )
        
        return FlagAnalysis(
            flag_name=flag_name,
            is_flagged=flag_data.get('is_flagged', False),
            severity='info',
            description="No product-specific issues detected",
            root_cause="",
            recommendations=[],
            details=flag_data
        )

    def _analyze_financial_timing_flag(self, flag_name: str, flag_data: Dict) -> FlagAnalysis:
        """Analyze financial and timing flags"""
        if flag_name == 'tax_calculation_error' and flag_data.get('is_flagged'):
            errors = flag_data.get('tax_errors', [])
            return FlagAnalysis(
                flag_name=flag_name,
                is_flagged=True,
                severity='warning',
                description=f"Tax calculation errors detected: {len(errors)} items",
                root_cause="Tax amounts don't match calculated values based on percentages",
                recommendations=[
                    "Review tax calculations for all line items",
                    "Verify tax rates applied are correct",
                    "Check for tax exemptions or special rates"
                ],
                details=flag_data
            )
        
        return FlagAnalysis(
            flag_name=flag_name,
            is_flagged=flag_data.get('is_flagged', False),
            severity='info',
            description="No financial/timing issues detected",
            root_cause="",
            recommendations=[],
            details=flag_data
        )

    def _create_product_info_table(self, product: Dict) -> Table:
        """Create product information table"""
        data = [
            ['Product Information', ''],
            ['Product ID', product.get('product_id', 'N/A')],
            ['Category', product.get('category_metadata', {}).get('applied_category', 'N/A')],
            ['Total Weight', f"{product.get('normalized_aggregates', {}).get('total_weight_reported_kg', 0):.1f} kg"],
            ['Package Count', str(product.get('normalized_aggregates', {}).get('total_package_count', 0))],
            ['Total Value', f"{product.get('normalized_aggregates', {}).get('total_value', 0):.2f} {product.get('normalized_aggregates', {}).get('currency', 'USD')}"],
        ]
        
        # Handle long destination address by breaking it into multiple lines if needed
        destination = product.get('normalized_aggregates', {}).get('ship_to_address_standardized', 'N/A')
        if len(destination) > 50:
            # Split long addresses
            words = destination.split(', ')
            if len(words) > 2:
                destination = f"{words[0]},\n{', '.join(words[1:])}"
        
        data.append(['Destination', destination])
        
        table = Table(data, colWidths=[2.2*inch, 3.8*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#2E4053')),
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#E8F4FD')),
            ('GRID', (0, 0), (-1, -1), 1, HexColor('#BDC3C7')),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('WORDWRAP', (1, 0), (1, -1), True),  # Enable word wrap for second column
        ]))
        
        return table

    def _create_flag_analysis_section(self, flags: List[FlagAnalysis]) -> List:
        """Create flag analysis section as point-wise list instead of table"""
        elements = []
        
        flagged_flags = [flag for flag in flags if flag.is_flagged]
        
        if not flagged_flags:
            elements.append(Paragraph("✅ No flagged issues detected", self.styles['CustomNormal']))
            return elements
        
        # Group flags by severity
        critical_flags = [f for f in flagged_flags if f.severity == 'critical']
        warning_flags = [f for f in flagged_flags if f.severity == 'warning']
        info_flags = [f for f in flagged_flags if f.severity == 'info']
        
        # Critical Issues Section
        if critical_flags:
            elements.append(Paragraph("🔴 Critical Issues", self.styles['CustomHeading']))
            for flag in critical_flags:
                elements.append(Paragraph(f"<b>{flag.flag_name.replace('_', ' ').title()}</b>", self.styles['CriticalFlag']))
                elements.append(Paragraph(f"Description: {flag.description}", self.styles['CustomNormal']))
                elements.append(Paragraph(f"Root Cause: {flag.root_cause}", self.styles['CustomNormal']))
                elements.append(Paragraph("Recommendations:", self.styles['CustomNormal']))
                for i, rec in enumerate(flag.recommendations, 1):
                    elements.append(Paragraph(f"  {i}. {rec}", self.styles['CustomNormal']))
                elements.append(Spacer(1, 12))
        
        # Warning Issues Section  
        if warning_flags:
            elements.append(Paragraph("🟡 Warning Issues", self.styles['CustomHeading']))
            for flag in warning_flags:
                elements.append(Paragraph(f"<b>{flag.flag_name.replace('_', ' ').title()}</b>", self.styles['WarningFlag']))
                elements.append(Paragraph(f"Description: {flag.description}", self.styles['CustomNormal']))
                elements.append(Paragraph(f"Root Cause: {flag.root_cause}", self.styles['CustomNormal']))
                elements.append(Paragraph("Recommendations:", self.styles['CustomNormal']))
                for i, rec in enumerate(flag.recommendations, 1):
                    elements.append(Paragraph(f"  {i}. {rec}", self.styles['CustomNormal']))
                elements.append(Spacer(1, 12))
        
        # Info Issues Section
        if info_flags:
            elements.append(Paragraph("🟢 Information Items", self.styles['CustomHeading']))
            for flag in info_flags:
                elements.append(Paragraph(f"<b>{flag.flag_name.replace('_', ' ').title()}</b>", self.styles['CustomNormal']))
                elements.append(Paragraph(f"Description: {flag.description}", self.styles['CustomNormal']))
                if flag.recommendations:
                    elements.append(Paragraph("Recommendations:", self.styles['CustomNormal']))
                    for i, rec in enumerate(flag.recommendations, 1):
                        elements.append(Paragraph(f"  {i}. {rec}", self.styles['CustomNormal']))
                elements.append(Spacer(1, 12))
        
        return elements

    def _has_meaningful_value(self, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, bool):
            return value is True
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return value.strip() not in ("", "n/a", "na", "none", "null", "-")
        if isinstance(value, list):
            return any(self._has_meaningful_value(v) for v in value)
        if isinstance(value, dict):
            return any(self._has_meaningful_value(v) for v in value.values())
        return True

    def _append_metadata_value_lines(self, story: List, label: str, value: Any, depth: int = 0) -> None:
        indent = "  " * depth
        pretty_label = label.replace("_", " ").title()
        if isinstance(value, dict):
            story.append(Paragraph(f"{indent}<b>{pretty_label}:</b>", self.styles['CustomNormal']))
            for child_key, child_value in value.items():
                self._append_metadata_value_lines(story, child_key, child_value, depth + 1)
            return
        if isinstance(value, list):
            if not value:
                return
            story.append(Paragraph(f"{indent}<b>{pretty_label}:</b>", self.styles['CustomNormal']))
            for item in value:
                if isinstance(item, (dict, list)):
                    self._append_metadata_value_lines(story, "item", item, depth + 1)
                else:
                    item_str = str(item)
                    if len(item_str) > 120:
                        item_str = item_str[:117] + "..."
                    story.append(Paragraph(f"{indent}  - {item_str}", self.styles['CustomNormal']))
            return

        value_str = str(value)
        if len(value_str) > 150:
            value_str = value_str[:147] + "..."
        story.append(Paragraph(f"{indent}<b>{pretty_label}:</b> {value_str}", self.styles['CustomNormal']))

    def generate_report_card(self, product_id: str, output_path: str) -> bool:
        """Generate PDF report card for specified product"""
        product = self.find_product(product_id)
        if not product:
            print(f"Error: Product {product_id} not found in data")
            return False
        
        # Create PDF document
        doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        story = []
        
        # Title
        story.append(Paragraph(f"Product Report Card", self.styles['CustomTitle']))
        story.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", self.styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Product Information
        story.append(Paragraph("Product Information", self.styles['CustomHeading']))
        story.append(self._create_product_info_table(product))
        story.append(Spacer(1, 20))
        
        # Analyze all flags
        all_flags = []
        inconsistency_flags = product.get('inconsistency_flags', {})
        
        for category_name, category_data in inconsistency_flags.items():
            if isinstance(category_data, dict):
                for flag_name, flag_data in category_data.items():
                    if flag_data is not None:
                        analysis = self._analyze_flag(flag_name, flag_data, category_name)
                        all_flags.append(analysis)
        
        # Summary Statistics
        flagged_count = sum(1 for flag in all_flags if flag.is_flagged)
        critical_count = sum(1 for flag in all_flags if flag.severity == 'critical')
        warning_count = sum(1 for flag in all_flags if flag.severity == 'warning')
        
        story.append(Paragraph("Flag Summary", self.styles['CustomHeading']))
        summary_data = [
            ['Metric', 'Count'],
            ['Total Flags Checked', str(len(all_flags))],
            ['Flagged Issues', str(flagged_count)],
            ['Critical Issues', str(critical_count)],
            ['Warning Issues', str(warning_count)],
            ['Overall Health', 'GOOD' if critical_count == 0 else 'NEEDS ATTENTION']
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 1.5*inch])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#E8F4FD')),
            ('GRID', (0, 0), (-1, -1), 1, HexColor('#BDC3C7')),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('TEXTCOLOR', (1, 4), (1, 4), green if critical_count == 0 else red),
            ('FONTNAME', (1, 4), (1, 4), 'Helvetica-Bold'),
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 20))

        # Flag Analysis
        story.append(Paragraph("Flag Analysis & Recommendations", self.styles['CustomHeading']))
        flag_analysis_elements = self._create_flag_analysis_section(all_flags)
        story.extend(flag_analysis_elements)
        story.append(Spacer(1, 20))

        # Detailed Category Information
        category_metadata = product.get('category_metadata', {})
        if not isinstance(category_metadata, dict):
            category_metadata = {}
        fields = category_metadata.get('fields', {})
        if not isinstance(fields, dict):
            fields = {}

        story.append(Paragraph("Category-Specific Information", self.styles['CustomHeading']))
        if self._has_meaningful_value(fields):
            for key, value in fields.items():
                if not self._has_meaningful_value(value):
                    continue
                self._append_metadata_value_lines(story, key, value)
                story.append(Spacer(1, 4))
        else:
            story.append(
                Paragraph(
                    "No category-specific fields extracted after normalization.",
                    self.styles['CustomNormal'],
                )
            )

        # Build PDF
        try:
            doc.build(story)
            print(f"Report card generated successfully: {output_path}")
            return True
        except Exception as e:
            print(f"Error generating PDF: {e}")
            return False


def main():
    """Main function to run the report card generator"""
    if len(sys.argv) != 3:
        print("Usage: python generate_report_card.py <product_id> <output_pdf_path>")
        print("Example: python generate_report_card.py PRD-001 report_card_PRD001.pdf")
        sys.exit(1)
    
    product_id = sys.argv[1]
    output_path = sys.argv[2]
    
    # Determine JSON file path (same directory as this script)
    script_dir = Path(__file__).parent
    json_file = script_dir / "samples_normal.json"
    
    if not json_file.exists():
        print(f"Error: samples_normal.json not found in {script_dir}")
        sys.exit(1)
    
    # Generate report card
    generator = ReportCardGenerator(str(json_file))
    success = generator.generate_report_card(product_id, output_path)
    
    if success:
        print(f"\nReport card for {product_id} generated successfully!")
        print(f"Output file: {output_path}")
        
        # Show summary
        product = generator.find_product(product_id)
        if product:
            inconsistency_flags = product.get('inconsistency_flags', {})
            flagged_count = 0
            for category_data in inconsistency_flags.values():
                if isinstance(category_data, dict):
                    for flag_data in category_data.values():
                        if flag_data and flag_data.get('is_flagged'):
                            flagged_count += 1
            
            print(f"Summary: {flagged_count} flagged issues detected")
    else:
        print("Failed to generate report card")
        sys.exit(1)


if __name__ == "__main__":
    main()

