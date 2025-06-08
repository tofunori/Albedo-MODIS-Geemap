"""
Example usage of Advanced QA Filtering
Simple example showing how to use the new QA filtering options
"""

def example_usage():
    """
    Example showing how to use the new advanced QA filtering
    """
    print("🔬 ADVANCED QA FILTERING - USAGE EXAMPLES")
    print("=" * 70)
    
    print("""
📊 1. BASIC USAGE (replace your existing calls):

OLD way:
    df = extract_melt_season_data_yearly(2020, 2023)

NEW way with advanced QA:
    # Standard advanced filtering (recommended)
    df = extract_melt_season_data_yearly(
        2020, 2023, 
        use_advanced_qa=True, 
        qa_level='standard'
    )
    
    # Strict filtering (highest quality)
    df = extract_melt_season_data_yearly(
        2020, 2023, 
        use_advanced_qa=True, 
        qa_level='strict'
    )
""")

    print("""
🎯 2. WORKFLOW INTEGRATION:

For melt season analysis:
    results = run_melt_season_analysis_williamson(
        start_year=2020,
        end_year=2023,
        use_advanced_qa=True,    # Enable advanced filtering
        qa_level='standard'      # Quality level
    )
""")

    print("""
⚙️ 3. QUALITY LEVELS EXPLAINED:

'strict':
  - Basic QA = 0 (best quality only)
  - All Algorithm flags filtered
  - Highest quality, fewer observations
  - Use for: Final analyses, publications

'standard':
  - Basic QA ≤ 1 (best + good quality)
  - Critical flags filtered (water, clouds, low signal)
  - Balanced quality/quantity
  - Use for: Most analyses (RECOMMENDED)

'relaxed':
  - Basic QA ≤ 2 (best + good + ok quality)
  - Minimal Algorithm flag filtering
  - Maximum data coverage
  - Use for: Exploratory analysis
""")

    print("""
🔍 4. ALGORITHM FLAGS FILTERED:

Bit 0 - Inland Water:     Always excluded (critical)
Bit 1 - Low Visible:      Always excluded (detection issue)
Bit 2 - Low NDSI:         Always excluded (weak snow signal)
Bit 3 - Temperature/Height: Excluded in 'strict' only
Bit 5 - Probable Cloud:   Always excluded (contamination)
Bits 4,6,7:              Available for future customization
""")

    print("""
📈 5. EXPECTED BENEFITS:

Statistical Robustness:
  ✅ More reliable Mann-Kendall trend tests
  ✅ Better Sen's slope estimates
  ✅ Reduced false positive/negative trends

Scientific Validity:
  ✅ Follows Williamson & Menounos (2021) standards
  ✅ Improved peer review acceptance
  ✅ Better reproducibility

Data Quality:
  ✅ Excludes contaminated pixels (water, clouds)
  ✅ Removes low-confidence detections
  ✅ Maintains temporal coverage
""")

    print("""
🚀 6. QUICK START RECOMMENDATION:

1. Start with 'standard' advanced QA for most work
2. Compare with your existing results
3. Use 'strict' for final publication-quality analyses
4. Document your QA approach in methodology sections

Example command to test:
    df = extract_melt_season_data_yearly(
        2023, 2023,  # Single year for testing
        use_advanced_qa=True,
        qa_level='standard'
    )
""")

    print("""
📚 REFERENCES AND DOCUMENTATION:

- Complete flag reference: docs/mod10a1-qa-flags.md
- Implementation details: src/data/extraction.py
- Williamson & Menounos (2021) methodology
- MODIS Snow Products Collection 6.1 User Guide
""")

if __name__ == "__main__":
    example_usage()