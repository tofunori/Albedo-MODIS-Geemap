"""
Statistical Analysis Module for MODIS Albedo Data
Implements Mann-Kendall test and Sen's slope estimation
Following Williamson & Menounos (2021) methodology
"""

import numpy as np
from scipy.stats import kendalltau

def mann_kendall_test(data):
    """
    Perform Mann-Kendall trend test
    
    Args:
        data: Time series data (array-like)
    
    Returns:
        dict: Results with trend direction, p-value, and tau
    """
    n = len(data)
    if n < 4:
        return {'trend': 'no_trend', 'p_value': 1.0, 'tau': 0.0}
    
    # Create sequence
    x = np.arange(n)
    
    # Calculate Kendall's tau and p-value
    tau, p_value = kendalltau(x, data)
    
    # Determine trend
    if p_value < 0.05:
        if tau > 0:
            trend = 'increasing'
        else:
            trend = 'decreasing'
    else:
        trend = 'no_trend'
    
    return {
        'trend': trend,
        'p_value': p_value,
        'tau': tau
    }

def sens_slope_estimate(data):
    """
    Calculate Sen's slope estimate (robust trend estimator)
    
    Args:
        data: Time series data (array-like)
    
    Returns:
        dict: Slope per year and intercept
    """
    n = len(data)
    if n < 4:
        return {'slope_per_year': 0.0, 'intercept': np.mean(data)}
    
    slopes = []
    for i in range(n):
        for j in range(i+1, n):
            if j != i:
                slope = (data[j] - data[i]) / (j - i)
                slopes.append(slope)
    
    if slopes:
        slope_per_year = np.median(slopes)
        intercept = np.median(data) - slope_per_year * np.median(np.arange(n))
    else:
        slope_per_year = 0.0
        intercept = np.mean(data)
    
    return {
        'slope_per_year': slope_per_year,
        'intercept': intercept
    }

def calculate_trend_statistics(values, years):
    """
    Calculate comprehensive trend statistics for a time series
    
    Args:
        values: Array of values
        years: Array of corresponding years
    
    Returns:
        dict: Comprehensive statistics including change rates
    """
    # Mann-Kendall test
    mk_result = mann_kendall_test(values)
    
    # Sen's slope
    sens_result = sens_slope_estimate(values)
    
    # Calculate change statistics
    first_year_value = values[0]
    last_year_value = values[-1]
    total_change = last_year_value - first_year_value
    total_percent_change = (total_change / first_year_value) * 100
    change_per_year = sens_result['slope_per_year']
    change_percent_per_year = (change_per_year / first_year_value) * 100
    
    # Statistical significance
    significance = "significant" if mk_result['p_value'] < 0.05 else "not significant"
    
    return {
        'mann_kendall': mk_result,
        'sens_slope': sens_result,
        'n_years': len(years),
        'change_per_year': change_per_year,
        'change_percent_per_year': change_percent_per_year,
        'total_change': total_change,
        'total_percent_change': total_percent_change,
        'significance': significance,
        'period': f"{years.min()}-{years.max()}"
    } 