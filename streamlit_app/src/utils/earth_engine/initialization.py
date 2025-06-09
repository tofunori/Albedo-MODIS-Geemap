"""
Earth Engine Initialization Module
Handles authentication and initialization with multiple fallback methods
"""

import streamlit as st


@st.cache_data(ttl=60)  # Cache for 1 minute only
def initialize_earth_engine():
    """
    Initialize Earth Engine - fast fail version
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Quick check - if we're clearly online and have no secrets, fail fast
    import os
    if not st.secrets and ('HOSTNAME' in os.environ or 'STREAMLIT_SHARING_MODE' in os.environ):
        return False
    
    try:
        import ee
        
        # METHOD 1: Try regular service account format
        if 'gee_service_account' in st.secrets:
            try:
                # Get the service account data from Streamlit secrets
                service_account_info = dict(st.secrets['gee_service_account'])
                
                # Debug info removed for cleaner interface
                
                # Ensure all required fields are present
                required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email', 'client_id']
                missing_fields = [field for field in required_fields if field not in service_account_info]
                
                if missing_fields:
                    st.sidebar.error(f"Missing required fields: {missing_fields}")
                    return False
                
                # Create credentials with the service account data
                credentials = ee.ServiceAccountCredentials(
                    service_account_info['client_email'],
                    key_data=service_account_info
                )
                ee.Initialize(credentials)
                return True
                
            except Exception as e:
                error_msg = str(e)
                st.sidebar.error(f"Auth failed: {error_msg[:80]}...")
                
                # Give specific help based on error type
                if "JSON object must be str" in error_msg:
                    st.sidebar.warning("⚠️ JSON format issue - try base64 method")
                elif "Invalid service account" in error_msg:
                    st.sidebar.warning("⚠️ Service account not registered")
                    st.sidebar.info("Register at: code.earthengine.google.com/register")
                elif "private_key" in error_msg:
                    st.sidebar.warning("⚠️ Private key format issue")
                    st.sidebar.info("Try using triple quotes: private_key = \"\"\"...\"\"\"")
                
        # METHOD 2: Try base64 encoded service account
        if 'gee_service_account_b64' in st.secrets:
            try:
                import base64
                import json
                
                # Decode base64 service account
                service_account_json = base64.b64decode(st.secrets['gee_service_account_b64']).decode()
                service_account_dict = json.loads(service_account_json)
                
                # Create credentials
                credentials = ee.ServiceAccountCredentials(
                    service_account_dict['client_email'],
                    key_data=service_account_dict
                )
                ee.Initialize(credentials)
                return True
                
            except Exception as e:
                st.sidebar.error(f"Base64 auth failed: {str(e)[:80]}...")
        
        # METHOD 3: Simple project auth (if available)
        if 'gee_project' in st.secrets:
            try:
                ee.Initialize(project=st.secrets['gee_project'])
                return True
            except Exception as e:
                st.sidebar.error(f"Project auth failed: {str(e)[:50]}...")
        
        # METHOD 4: LOCAL DEVELOPMENT - Simple authentication
        try:
            # This works if you've run 'earthengine authenticate' locally
            ee.Initialize()
            return True
        except Exception as e:
            # Check if we're running locally vs online
            import os
            if 'HOSTNAME' not in os.environ and 'STREAMLIT_SHARING_MODE' not in os.environ:
                # We're likely running locally
                st.sidebar.warning("🔐 Local authentication needed")
                st.sidebar.info("💡 Run in terminal: `earthengine authenticate`")
            
        return False
            
    except ImportError:
        return False
    except Exception:
        return False