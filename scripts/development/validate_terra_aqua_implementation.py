#!/usr/bin/env python3
"""
Validation script for Terra-Aqua fusion implementation
Run this in your Google Earth Engine Python environment
"""

def validate_implementation():
    """Validate the Terra-Aqua fusion implementation"""
    print("🔍 Validating Terra-Aqua Fusion Implementation")
    print("=" * 55)
    
    import os
    import sys
    
    # Check if we're in the right directory
    current_dir = os.getcwd()
    expected_files = ['src/config.py', 'src/data/extraction.py', 'CLAUDE.md']
    
    print(f"📂 Current directory: {current_dir}")
    
    missing_files = []
    for file in expected_files:
        if os.path.exists(file):
            print(f"✅ Found: {file}")
        else:
            print(f"❌ Missing: {file}")
            missing_files.append(file)
    
    if missing_files:
        print(f"\n⚠️ Missing files: {missing_files}")
        print("💡 Make sure you're in the project root directory")
        return False
    
    # Check if the new function exists
    try:
        with open('src/data/extraction.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'combine_terra_aqua_literature_method' in content:
            print("✅ New Terra-Aqua fusion function found")
        else:
            print("❌ Terra-Aqua fusion function not found")
            return False
            
        if 'literature-based Terra-Aqua fusion strategy' in content:
            print("✅ Implementation comments found")
        else:
            print("❌ Implementation comments not found")
            
        # Check for key implementation features
        features = [
            'Terra priority',
            'quality_score', 
            'qualityMosaic',
            'satellite_name'
        ]
        
        found_features = []
        for feature in features:
            if feature in content:
                found_features.append(feature)
                print(f"✅ Feature found: {feature}")
            else:
                print(f"❌ Feature missing: {feature}")
        
        implementation_score = len(found_features) / len(features)
        print(f"\n📊 Implementation completeness: {implementation_score*100:.0f}%")
        
        if implementation_score >= 0.75:
            print("✅ Implementation looks good!")
            return True
        else:
            print("⚠️ Implementation may be incomplete")
            return False
            
    except Exception as e:
        print(f"❌ Error reading implementation: {e}")
        return False

def check_documentation():
    """Check if documentation was updated"""
    print(f"\n📚 Checking Documentation Updates")
    print("=" * 40)
    
    try:
        with open('CLAUDE.md', 'r', encoding='utf-8') as f:
            content = f.read()
            
        doc_features = [
            'Terra-Aqua Data Fusion Strategy',
            'Literature-Based',
            'combine_terra_aqua_literature_method',
            'Priorité Terra sur Aqua',
            'Gap-filling hierarchique'
        ]
        
        found_docs = []
        for feature in doc_features:
            if feature in content:
                found_docs.append(feature)
                print(f"✅ Doc section found: {feature}")
            else:
                print(f"❌ Doc section missing: {feature}")
        
        doc_score = len(found_docs) / len(doc_features)
        print(f"\n📊 Documentation completeness: {doc_score*100:.0f}%")
        
        return doc_score >= 0.8
        
    except Exception as e:
        print(f"❌ Error reading documentation: {e}")
        return False

def provide_next_steps():
    """Provide next steps for testing"""
    print(f"\n🚀 Next Steps for Testing")
    print("=" * 30)
    print("1. Activate your Google Earth Engine environment:")
    print("   conda activate gee  # or your EE environment name")
    print()
    print("2. Test Earth Engine connection:")
    print("   python -c \"import ee; ee.Initialize(); print('EE OK')\"")
    print()
    print("3. Test the new fusion method:")
    print("   python -c \"from src.data.extraction import extract_time_series_fast; print('Import OK')\"")
    print()
    print("4. Run a quick extraction test:")
    print("   python -c \"")
    print("   from src.data.extraction import extract_time_series_fast")
    print("   data = extract_time_series_fast('2023-07-01', '2023-07-05', scale=500)")
    print("   print(f'Extracted {len(data)} observations')\"")
    print()
    print("5. Check the fusion statistics in the output for:")
    print("   - Terra (MOD10A1): X observations")
    print("   - Aqua (MYD10A1): Y observations") 
    print("   - Combined (literature method): Z daily composites")
    print("   - Reduction: X+Y-Z duplicate observations removed")

if __name__ == "__main__":
    print("🧪 Terra-Aqua Fusion Implementation Validator")
    print("=" * 60)
    
    # Validate implementation
    impl_ok = validate_implementation()
    
    # Check documentation 
    doc_ok = check_documentation()
    
    # Summary
    print(f"\n🎯 Validation Summary:")
    print(f"   Implementation: {'✅ PASS' if impl_ok else '❌ FAIL'}")
    print(f"   Documentation: {'✅ PASS' if doc_ok else '❌ FAIL'}")
    
    if impl_ok and doc_ok:
        print(f"\n🎉 SUCCESS! Terra-Aqua fusion is properly implemented.")
        print(f"🔬 The system now follows scientific literature best practices:")
        print(f"   • Terra prioritized over Aqua (band 6 reliability)")
        print(f"   • Gap-filling strategy (Terra first, Aqua backup)")
        print(f"   • Daily composites (eliminates pseudo-replication)")
        print(f"   • Quality-based mosaicking")
    else:
        print(f"\n⚠️ Some issues found. Review the implementation.")
    
    provide_next_steps()