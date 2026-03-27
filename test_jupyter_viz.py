#!/usr/bin/env python3
"""
Quick test to check if Jupyter + matplotlib visualization is working
Run this to diagnose visualization issues
"""

import matplotlib.pyplot as plt
import numpy as np
import sys

print("🔍 Jupyter Matplotlib Diagnostic Test")
print("=" * 50)

print(f"🐍 Python version: {sys.version}")
print(f"📊 Matplotlib version: {plt.matplotlib.__version__}")
print(f"🖥️ Matplotlib backend: {plt.get_backend()}")

# Test basic plotting
print("\n📈 Creating test plot...")
fig, ax = plt.subplots(figsize=(10, 6))

# Sample data
x = np.linspace(0, 10, 100)
y1 = np.sin(x)
y2 = np.cos(x)
y3 = 0.5 * x

ax.plot(x, y1, 'b-', linewidth=2, label='Fine-tuned Model (100%)')
ax.plot(x, y2, 'r--', linewidth=2, label='Pre-trained Model (20%)')
ax.plot(x, y3, 'g:', linewidth=2, label='Linear Growth')

ax.set_xlabel('Building Complexity (Zones)', fontsize=12)
ax.set_ylabel('Success Rate (%)', fontsize=12)
ax.set_title('Test Visualization - Model Performance Comparison', fontsize=14, fontweight='bold')
ax.legend()
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.show()

print("✅ Test plot created!")
print("\n💡 If you see a plot above in your Jupyter notebook:")
print("   - Your matplotlib setup is working correctly")
print("   - The model comparison visualizations should work")
print("\n❌ If you DON'T see a plot:")
print("   - Try running: %matplotlib inline")
print("   - Check if you're using Jupyter notebook (not lab)")
print("   - Your matplotlib backend might need configuration")
print("\n🔧 Quick fixes to try:")
print("   1. Restart Jupyter kernel: Kernel → Restart & Clear Output")
print("   2. Run: %matplotlib inline")
print("   3. Check browser console for errors")
print("   4. Try: pip install --upgrade matplotlib")