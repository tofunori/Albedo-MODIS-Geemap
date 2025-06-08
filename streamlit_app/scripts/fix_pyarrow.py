"""
PyArrow Fix Script for Windows Streamlit Dashboard
Provides automated solutions for PyArrow DLL loading issues
"""

import subprocess
import sys
import os

def check_pyarrow():
    """Check if PyArrow is properly installed"""
    try:
        import pyarrow as pa
        print(f"✅ PyArrow {pa.__version__} is working correctly")
        return True
    except ImportError as e:
        print(f"❌ PyArrow import failed: {e}")
        return False

def fix_pyarrow_conda():
    """Fix PyArrow using conda"""
    print("🔧 Attempting to fix PyArrow with conda...")
    try:
        # Remove existing pyarrow
        subprocess.run([sys.executable, "-m", "conda", "remove", "pyarrow", "-y"], 
                      capture_output=True, check=False)
        
        # Reinstall with conda-forge
        result = subprocess.run([sys.executable, "-m", "conda", "install", 
                               "-c", "conda-forge", "pyarrow", "-y"], 
                              capture_output=True, check=True)
        
        print("✅ PyArrow reinstalled with conda-forge")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Conda fix failed: {e}")
        return False

def fix_pyarrow_pip():
    """Fix PyArrow using pip"""
    print("🔧 Attempting to fix PyArrow with pip...")
    try:
        # Force reinstall with pip
        result = subprocess.run([sys.executable, "-m", "pip", "install", 
                               "--force-reinstall", "--no-deps", "pyarrow"], 
                              capture_output=True, check=True)
        
        print("✅ PyArrow force-reinstalled with pip")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Pip fix failed: {e}")
        return False

def main():
    """Main fix routine"""
    print("🏔️ Athabasca Glacier Dashboard - PyArrow Fix Script")
    print("=" * 60)
    
    # Check current status
    if check_pyarrow():
        print("🎉 No fix needed! PyArrow is working correctly.")
        return
    
    print("\n🔍 PyArrow issue detected. Attempting fixes...")
    
    # Try conda fix first (better for conda environments)
    if os.environ.get('CONDA_DEFAULT_ENV'):
        print(f"\n📦 Detected conda environment: {os.environ.get('CONDA_DEFAULT_ENV')}")
        if fix_pyarrow_conda():
            if check_pyarrow():
                print("🎉 Fixed with conda! You can now run the dashboard.")
                return
    
    # Try pip fix
    print("\n🐍 Trying pip fix...")
    if fix_pyarrow_pip():
        if check_pyarrow():
            print("🎉 Fixed with pip! You can now run the dashboard.")
            return
    
    # Manual instructions if automated fixes fail
    print("\n❌ Automated fixes failed. Manual solutions:")
    print("=" * 50)
    print("1️⃣ **Conda Environment:**")
    print("   conda remove pyarrow")
    print("   conda install -c conda-forge pyarrow")
    print("")
    print("2️⃣ **Pip Alternative:**")
    print("   pip uninstall pyarrow")
    print("   pip install --no-binary pyarrow pyarrow")
    print("")
    print("3️⃣ **Complete Environment Rebuild:**")
    print("   conda create -n gee_new python=3.10")
    print("   conda activate gee_new")
    print("   pip install -r requirements.txt")
    print("")
    print("4️⃣ **Windows Specific:**")
    print("   - Install Microsoft Visual C++ Redistributable")
    print("   - Update conda: conda update conda")
    print("")
    print("💡 After fixing, run: streamlit run streamlit_dashboard_modular.py")

if __name__ == "__main__":
    main()