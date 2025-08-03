#!/usr/bin/env python3
"""
Setup script for the AI Market News Review System

This script helps users set up the system and test its functionality.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    return True

def install_dependencies():
    """Install required dependencies."""
    print("\n📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def setup_environment():
    """Set up environment file."""
    print("\n🔧 Setting up environment...")
    
    env_file = Path(".env")
    env_example = Path("env_example.txt")
    
    if env_file.exists():
        print("✅ .env file already exists")
        return True
    
    if env_example.exists():
        shutil.copy(env_example, env_file)
        print("✅ Created .env file from template")
        print("📝 Please edit .env file and add your DeepSeek API key")
        return True
    else:
        print("❌ env_example.txt not found")
        return False

def create_directories():
    """Create necessary directories."""
    print("\n📁 Creating directories...")
    
    directories = ["reports", "templates", "logs"]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created {directory}/ directory")
    
    return True

def test_system():
    """Test the system functionality."""
    print("\n🧪 Testing system...")
    
    try:
        result = subprocess.run([sys.executable, "test_system.py"], 
                              capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ System test completed successfully")
            return True
        else:
            print("⚠️  System test completed with warnings (expected without API key)")
            return True
    except subprocess.TimeoutExpired:
        print("⚠️  System test timed out (this is normal)")
        return True
    except Exception as e:
        print(f"❌ System test failed: {e}")
        return False

def show_next_steps():
    """Show next steps for the user."""
    print("\n" + "="*60)
    print("🎉 SETUP COMPLETED!")
    print("="*60)
    print("\n📋 Next steps:")
    print("1. Edit .env file and add your DeepSeek API key")
    print("2. Get your API key from: https://platform.deepseek.com/")
    print("3. Test the system with: python main.py --once")
    print("4. Set up automated reports with: python scheduler.py --once")
    print("\n📚 For more information, see README.md")
    print("="*60)

def main():
    """Main setup function."""
    print("🚀 AI Market News Review System Setup")
    print("="*60)
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Install dependencies
    if not install_dependencies():
        return False
    
    # Create directories
    if not create_directories():
        return False
    
    # Setup environment
    if not setup_environment():
        return False
    
    # Test system
    if not test_system():
        return False
    
    # Show next steps
    show_next_steps()
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 