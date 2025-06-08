# 🌍 Earth Engine Setup for MODIS Pixel Visualization

To enable real MODIS pixel visualization in the Interactive Albedo Map, you need to authenticate with Google Earth Engine.

## 🚀 For Streamlit Cloud Deployment

### Step 1: Create a Google Earth Engine Service Account

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Earth Engine API:
   - Go to "APIs & Services" > "Library"
   - Search for "Earth Engine API"
   - Click "Enable"

### Step 2: Create Service Account Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "Service Account"
3. Fill in:
   - Service account name: `ee-streamlit-app`
   - Service account ID: (auto-generated)
   - Description: "Earth Engine access for Streamlit app"
4. Click "Create and Continue"
5. Skip the optional steps and click "Done"

### Step 3: Create JSON Key

1. Click on your new service account
2. Go to "Keys" tab
3. Click "Add Key" > "Create new key"
4. Choose "JSON" format
5. Save the downloaded JSON file

### Step 4: Register Service Account with Earth Engine

1. Go to [Google Earth Engine service accounts page](https://code.earthengine.google.com/register)
2. Click "Register a service account"
3. Enter the service account email from your JSON file (looks like `ee-streamlit-app@your-project.iam.gserviceaccount.com`)
4. Click "Register"

### Step 5: Add to Streamlit Secrets

1. In your Streamlit Cloud app settings, go to "Secrets"
2. Add the entire content of your JSON file under the key `gee_service_account`:

```toml
[gee_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "ee-streamlit-app@your-project.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
```

## 💻 For Local Development

### Option 1: Command Line Authentication (Easiest)

```bash
# Install Earth Engine CLI
pip install earthengine-api

# Authenticate
earthengine authenticate

# Follow the browser prompts to authenticate
```

### Option 2: Service Account File

1. Follow steps 1-4 from the Streamlit Cloud section above
2. Save the JSON file as `ee-service-account.json` in your `streamlit_app/` directory
3. Add `ee-service-account.json` to your `.gitignore` (don't commit credentials!)

## ✅ Verification

Once configured, the Interactive Albedo Map will:
- Show real MODIS 500m pixel boundaries
- Display actual albedo values from the selected date
- Color pixels based on albedo measurements
- Clip pixels to the exact glacier boundary

## 🔧 Troubleshooting

**"Earth Engine Authentication Required" error:**
- Ensure you've completed all steps above
- Check that the service account email is registered with Earth Engine
- Verify the JSON credentials are correctly added to Streamlit secrets

**"No valid MODIS pixels found" error:**
- This means authentication worked but no data exists for that date
- Try selecting a different date with known observations

**Map shows but no pixels appear:**
- Check the Earth Engine quota limits
- Ensure the service account has access to MODIS collections