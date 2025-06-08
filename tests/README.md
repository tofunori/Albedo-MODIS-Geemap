# Tests Directory

Contains test files and validation scripts for the Athabasca Glacier Albedo Analysis project.

## Structure

### `development/`
Development and debugging test files:
- **`test_advanced_qa.py`** - Advanced quality assessment testing
- **`test_path_fix.py`** - Path resolution testing 
- **`test_qa_simple.py`** - Simple QA validation tests

### `qa_validation/`
Quality assessment validation scripts:
- **`qa_usage_example.py`** - Examples of QA filtering usage
- **`simple_qa_test.py`** - Basic QA functionality tests
- **`run_qa_comparison.py`** - QA level comparison tests

## Usage

### Running Tests
```bash
# Run specific test
python tests/development/test_advanced_qa.py

# Run QA validation
python tests/qa_validation/qa_usage_example.py
```

### Test Categories
- **Unit Tests**: Individual function testing
- **Integration Tests**: Workflow testing
- **Validation Tests**: Data quality verification
- **Development Tests**: Debugging and development aids

## Notes
- These files were moved from the root directory during codebase reorganization
- Some tests may need path updates after reorganization
- Consider converting to pytest format for better organization