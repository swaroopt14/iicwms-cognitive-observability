#!/usr/bin/env python3
"""Minimal backend startup without problematic imports"""

import warnings
warnings.filterwarnings('ignore')

# Set environment variables
import os
os.environ['ENABLE_CREWAI'] = 'false'

print('🔧 CrewAI disabled via environment variable')
print('🚀 Starting minimal backend...')

# Create minimal FastAPI app
from fastapi import FastAPI
import uvicorn

# Create minimal app
app = FastAPI()

@app.get("/")
def root():
    return {"status": "running", "message": "Minimal backend is working!"}

if __name__ == "__main__":
    print("🚀 Starting uvicorn server...")
    uvicorn.run(app, host='0.0.0.0', port=8000, reload=False)
    print("✅ Minimal backend started successfully!")
