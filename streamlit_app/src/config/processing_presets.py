"""
Processing Configuration Presets
Defines all available parameters and presets for MODIS data processing
"""

# Analysis Types and their available parameters
ANALYSIS_TYPES = {
    "melt_season": {
        "name": "Melt Season Analysis (MOD10A1/MYD10A1)",
        "description": "Daily snow albedo analysis following Williamson & Menounos (2021)",
        "workflow_module": "workflows.melt_season",
        "workflow_function": "run_melt_season_analysis_williamson",
        "output_files": [
            "athabasca_melt_season_data.csv",
            "athabasca_melt_season_results.csv",
            "athabasca_melt_season_focused_data.csv"
        ],
        "parameters": {
            "start_year": {"type": "int", "default": 2010, "min": 2000, "max": 2024},
            "end_year": {"type": "int", "default": 2024, "min": 2000, "max": 2024},
            "scale": {"type": "int", "default": 500, "options": [500]},
            "use_advanced_qa": {"type": "bool", "default": True},
            "qa_level": {"type": "select", "default": "standard", "options": ["strict", "standard", "relaxed", "basic", "custom"]}
        }
    },
    "mcd43a3": {
        "name": "MCD43A3 Broadband Albedo Analysis",
        "description": "16-day broadband albedo analysis with spectral decomposition",
        "workflow_module": "workflows.broadband_albedo",
        "workflow_function": "run_mcd43a3_analysis",
        "output_files": [
            "athabasca_mcd43a3_spectral_data.csv",
            "athabasca_mcd43a3_results.csv"
        ],
        "parameters": {
            "start_year": {"type": "int", "default": 2010, "min": 2000, "max": 2024},
            "end_year": {"type": "int", "default": 2024, "min": 2000, "max": 2024}
        }
    },
    "hypsometric": {
        "name": "Hypsometric Analysis",
        "description": "Elevation-based analysis with ±100m bands around glacier median",
        "workflow_module": "workflows.hypsometric",
        "workflow_function": "run_hypsometric_analysis_williamson",
        "output_files": [
            "athabasca_hypsometric_data.csv",
            "athabasca_hypsometric_results.csv"
        ],
        "parameters": {
            "start_year": {"type": "int", "default": 2010, "min": 2000, "max": 2024},
            "end_year": {"type": "int", "default": 2024, "min": 2000, "max": 2024},
            "scale": {"type": "int", "default": 500, "options": [500]}
        }
    }
}

# QA Level Configurations
QA_LEVELS = {
    "strict": {
        "name": "Advanced QA Strict",
        "description": "Highest quality data only (reduced coverage)",
        "use_advanced_qa": True,
        "basic_qa_threshold": 0,  # Only best quality
        "algorithm_flags": {
            "no_inland_water": True,
            "no_low_visible": True,
            "no_low_ndsi": True,
            "no_temp_issues": True,
            "no_clouds": True
        },
        "expected_coverage": "50-60%",
        "recommended_for": "Publications, climate trends"
    },
    "standard": {
        "name": "Advanced QA Standard",
        "description": "Research-grade filtering (recommended)",
        "use_advanced_qa": True,
        "basic_qa_threshold": 1,  # Best + good quality
        "algorithm_flags": {
            "no_inland_water": True,
            "no_low_visible": True,
            "no_low_ndsi": True,
            "no_temp_issues": False,  # Allow temp flagged (common on glaciers)
            "no_clouds": True
        },
        "expected_coverage": "70-80%",
        "recommended_for": "Most analyses"
    },
    "relaxed": {
        "name": "Advanced QA Relaxed",
        "description": "Maximum data coverage with good quality",
        "use_advanced_qa": True,
        "basic_qa_threshold": 2,  # Best + good + ok quality
        "algorithm_flags": {
            "no_inland_water": True,
            "no_low_visible": False,
            "no_low_ndsi": False,
            "no_temp_issues": False,
            "no_clouds": True
        },
        "expected_coverage": "85-95%",
        "recommended_for": "Exploratory analysis, sparse regions"
    },
    "basic": {
        "name": "Standard QA (Basic Only)",
        "description": "Basic QA filtering only - maximum data",
        "use_advanced_qa": False,
        "basic_qa_threshold": 1,
        "algorithm_flags": {},
        "expected_coverage": "90-95%",
        "recommended_for": "Initial exploration"
    },
    "custom": {
        "name": "Custom QA Configuration",
        "description": "User-defined QA settings from presets",
        "use_advanced_qa": True,
        "basic_qa_threshold": 1,
        "algorithm_flags": {
            "no_inland_water": True,
            "no_low_visible": True,
            "no_low_ndsi": True,
            "no_temp_issues": False,
            "no_clouds": True
        },
        "expected_coverage": "Variable",
        "recommended_for": "Advanced users",
        "presets": {}  # Will be populated with custom presets
    }
}

# Custom QA Presets
CUSTOM_QA_PRESETS = {
    "glacier_focused": {
        "name": "Glacier-Focused QA",
        "description": "Optimized for glacier surfaces - allows temperature flagged pixels",
        "basic_qa_threshold": 1,
        "algorithm_flags": {
            "no_inland_water": True,
            "no_low_visible": True,
            "no_low_ndsi": False,  # Allow low NDSI (common on ice)
            "no_temp_issues": False,  # Allow temp flagged (common on glaciers)
            "no_high_swir": False,  # Allow high SWIR (common on ice)
            "no_clouds": True,
            "no_shadows": False  # Allow shadows (common in mountainous terrain)
        },
        "expected_coverage": "75-85%"
    },
    "cloud_strict": {
        "name": "Cloud-Strict QA",
        "description": "Aggressive cloud filtering for clear pixels only",
        "basic_qa_threshold": 0,
        "algorithm_flags": {
            "no_inland_water": True,
            "no_low_visible": True,
            "no_low_ndsi": True,
            "no_temp_issues": True,
            "no_high_swir": True,
            "no_clouds": True,
            "no_shadows": True
        },
        "expected_coverage": "40-60%"
    },
    "shadow_sensitive": {
        "name": "Shadow-Sensitive QA",
        "description": "Enhanced shadow detection for complex terrain",
        "basic_qa_threshold": 1,
        "algorithm_flags": {
            "no_inland_water": True,
            "no_low_visible": True,  # Helps detect shadows
            "no_low_ndsi": True,
            "no_temp_issues": False,
            "no_high_swir": False,  # Allow high SWIR
            "no_clouds": True,
            "no_shadows": True  # Extra shadow filtering
        },
        "expected_coverage": "65-75%"
    },
    "maximum_coverage": {
        "name": "Maximum Coverage QA",
        "description": "Minimal filtering for maximum data retention",
        "basic_qa_threshold": 2,
        "algorithm_flags": {
            "no_inland_water": True,
            "no_low_visible": False,
            "no_low_ndsi": False,
            "no_temp_issues": False,
            "no_high_swir": False,
            "no_clouds": True,  # Only remove clouds
            "no_shadows": False
        },
        "expected_coverage": "90-98%"
    },
    "publication_quality": {
        "name": "Publication Quality QA",
        "description": "Strictest settings for scientific publications",
        "basic_qa_threshold": 0,
        "algorithm_flags": {
            "no_inland_water": True,
            "no_low_visible": True,
            "no_low_ndsi": True,
            "no_temp_issues": True,
            "no_high_swir": True,
            "no_clouds": True,
            "no_shadows": True
        },
        "expected_coverage": "30-50%"
    }
}

# Processing Presets for common use cases
PROCESSING_PRESETS = {
    "recent_analysis": {
        "name": "Recent Analysis (2020-2024)",
        "description": "Focus on recent 5 years with standard quality",
        "analysis_type": "melt_season",
        "parameters": {
            "start_year": 2020,
            "end_year": 2024,
            "scale": 500,
            "use_advanced_qa": True,
            "qa_level": "standard"
        }
    },
    "full_timeseries": {
        "name": "Full Time Series (2010-2024)",
        "description": "Complete MODIS record with balanced quality",
        "analysis_type": "melt_season",
        "parameters": {
            "start_year": 2010,
            "end_year": 2024,
            "scale": 500,
            "use_advanced_qa": True,
            "qa_level": "standard"
        }
    },
    "high_quality": {
        "name": "High Quality Analysis",
        "description": "Maximum quality for scientific publications",
        "analysis_type": "melt_season",
        "parameters": {
            "start_year": 2010,
            "end_year": 2024,
            "scale": 500,
            "use_advanced_qa": True,
            "qa_level": "strict"
        }
    },
    "fast_test": {
        "name": "Fast Test (5 years, coarse resolution)",
        "description": "Quick processing for testing parameters",
        "analysis_type": "melt_season",
        "parameters": {
            "start_year": 2020,
            "end_year": 2024,
            "scale": 500,
            "use_advanced_qa": False,
            "qa_level": "basic"
        }
    },
    "spectral_analysis": {
        "name": "Spectral Analysis (MCD43A3)",
        "description": "Broadband albedo with spectral decomposition",
        "analysis_type": "mcd43a3",
        "parameters": {
            "start_year": 2010,
            "end_year": 2024
        }
    },
    "elevation_analysis": {
        "name": "Elevation Analysis (Hypsometric)",
        "description": "Albedo trends by elevation bands",
        "analysis_type": "hypsometric",
        "parameters": {
            "start_year": 2010,
            "end_year": 2024,
            "scale": 500
        }
    }
}

# Fixed spatial resolution (500m standard)
SPATIAL_RESOLUTIONS = {
    500: {
        "name": "Standard (500m)",
        "description": "Standard MODIS resolution",
        "processing_time": "Standard",
        "data_size": "Standard"
    }
}

# Temporal ranges
TEMPORAL_RANGES = {
    "recent": {
        "name": "Recent (2020-2024)",
        "start_year": 2020,
        "end_year": 2024,
        "description": "Focus on recent 5 years"
    },
    "fire_context": {
        "name": "Fire Years Context (2017-2021)",
        "start_year": 2017,
        "end_year": 2021,
        "description": "Forest fire years with context"
    },
    "decade": {
        "name": "Last Decade (2015-2024)",
        "start_year": 2015,
        "end_year": 2024,
        "description": "10-year analysis period"
    },
    "full_modis": {
        "name": "Full MODIS Record (2010-2024)",
        "start_year": 2010,
        "end_year": 2024,
        "description": "Complete MODIS albedo record"
    },
    "custom": {
        "name": "Custom Range",
        "start_year": None,
        "end_year": None,
        "description": "User-defined date range"
    }
}

def get_analysis_config(analysis_type):
    """Get configuration for a specific analysis type"""
    return ANALYSIS_TYPES.get(analysis_type, {})

def get_qa_config(qa_level):
    """Get QA configuration for a specific level"""
    return QA_LEVELS.get(qa_level, {})

def get_preset_config(preset_name):
    """Get preset configuration"""
    return PROCESSING_PRESETS.get(preset_name, {})

def validate_parameters(analysis_type, parameters):
    """Validate parameters for a specific analysis type"""
    config = get_analysis_config(analysis_type)
    if not config:
        return False, f"Unknown analysis type: {analysis_type}"
    
    param_config = config.get("parameters", {})
    errors = []
    
    for param_name, param_value in parameters.items():
        if param_name not in param_config:
            continue
        
        param_def = param_config[param_name]
        param_type = param_def["type"]
        
        # Type validation
        if param_type == "int" and not isinstance(param_value, int):
            errors.append(f"{param_name} must be an integer")
        elif param_type == "bool" and not isinstance(param_value, bool):
            errors.append(f"{param_name} must be a boolean")
        elif param_type == "select" and param_value not in param_def["options"]:
            errors.append(f"{param_name} must be one of {param_def['options']}")
        
        # Range validation
        if param_type == "int":
            if "min" in param_def and param_value < param_def["min"]:
                errors.append(f"{param_name} must be >= {param_def['min']}")
            if "max" in param_def and param_value > param_def["max"]:
                errors.append(f"{param_name} must be <= {param_def['max']}")
    
    # Logical validation
    if "start_year" in parameters and "end_year" in parameters:
        if parameters["start_year"] > parameters["end_year"]:
            errors.append("start_year must be <= end_year")
    
    return len(errors) == 0, errors

def get_default_parameters(analysis_type):
    """Get default parameters for an analysis type"""
    config = get_analysis_config(analysis_type)
    if not config:
        return {}
    
    defaults = {}
    for param_name, param_def in config.get("parameters", {}).items():
        defaults[param_name] = param_def["default"]
    
    return defaults