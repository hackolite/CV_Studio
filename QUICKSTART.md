# Quick Start: Secure WebSocket API Key Setup

## For New Users

### Step 1: Copy the Template
```bash
cp .env.example .env
```

### Step 2: Add Your API Key
Edit the `.env` file and replace `your_api_key_here` with your actual API key:
```bash
AIS_STREAM_API_KEY=your_actual_key_from_aisstream_io
```

### Step 3: Run the Example
```bash
python examples/example_ais_stream.py
```

That's it! Your API key is now secure and hidden from version control.

## Get Your API Key

1. Visit: https://aisstream.io/
2. Sign up for a free account
3. Copy your API key from the dashboard
4. Paste it into your `.env` file

## Three Ways to Provide API Key

### 🏆 Method 1: .env File (Recommended)
```bash
# One-time setup
cp .env.example .env
echo "AIS_STREAM_API_KEY=your_key" >> .env

# Run anytime
python examples/example_ais_stream.py
```

**Pros:**
- ✅ Most secure
- ✅ Easy to manage
- ✅ Git-ignored by default
- ✅ Best for development

### ⚙️ Method 2: Environment Variable
```bash
# Set once per session
export AIS_STREAM_API_KEY='your_key'

# Run anytime
python examples/example_ais_stream.py
```

**Pros:**
- ✅ Good for CI/CD
- ✅ Production-ready
- ✅ No files needed

### ⚠️ Method 3: Command Line (Not Recommended)
```bash
python examples/example_ais_stream.py YOUR_KEY
```

**Cons:**
- ❌ Visible in shell history
- ❌ Not secure
- ❌ Only for quick testing

## Security Notes

✅ **DO:**
- Use `.env` file for development
- Use environment variables for production
- Keep `.env` file private (never commit it)
- Use `.env.example` for documentation

❌ **DON'T:**
- Hardcode API keys in source code
- Commit `.env` files to git
- Share API keys in chat or email
- Use command line for production

## Troubleshooting

### "No API key provided" Error
```bash
# Check if API key is set
echo $AIS_STREAM_API_KEY

# If empty, set it:
export AIS_STREAM_API_KEY='your_key'

# Or use .env file:
cp .env.example .env
# Edit .env and add your key
```

### "python-dotenv not installed" Warning
```bash
pip install python-dotenv
```

### API Key Not Loading from .env
```bash
# Make sure .env is in the project root
ls -la .env

# Check file permissions
chmod 600 .env

# Verify content
cat .env
```

## Documentation

For more details, see:
- `SECURE_API_KEY_GUIDE.md` - Comprehensive security guide
- `node/InputNode/README_Websocket_AIS.md` - WebSocket node documentation

## Questions?

- Check the documentation files above
- Run the tests: `python tests/test_env_config.py`
- Look at the example: `examples/example_ais_stream.py`
