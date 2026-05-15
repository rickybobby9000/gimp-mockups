#!/usr/bin/env python3
"""
T-Shirt Mockup Creator - Standalone Version
A simplified version that works without GTK/PyGObject dependencies.
Uses only Pillow for image processing with a simple terminal interface.
"""

import os
import sys
from PIL import Image, ImageTk
import math

def get_float_input(prompt, default, min_val=None, max_val=None):
    """Get float input from user with validation"""
    while True:
        try:
            value = input(f"{prompt} [{default}]: ").strip()
            if not value:
                return default
            value = float(value)
            if min_val is not None and value < min_val:
                print(f"Value must be at least {min_val}")
                continue
            if max_val is not None and value > max_val:
                print(f"Value must be at most {max_val}")
                continue
            return value
        except ValueError:
            print("Please enter a valid number")

def get_int_input(prompt, default, min_val=None, max_val=None):
    """Get integer input from user with validation"""
    while True:
        try:
            value = input(f"{prompt} [{default}]: ").strip()
            if not value:
                return default
            value = int(value)
            if min_val is not None and value < min_val:
                print(f"Value must be at least {min_val}")
                continue
            if max_val is not None and value > max_val:
                print(f"Value must be at most {max_val}")
                continue
            return value
        except ValueError:
            print("Please enter a valid integer")

def main():
    print("=" * 60)
    print("T-SHIRT MOCKUP CREATOR")
    print("=" * 60)
    print()
    
    # Get t-shirt image path
    while True:
        tshirt_path = input("Enter path to t-shirt mockup image: ").strip()
        if os.path.exists(tshirt_path):
            break
        print("File not found. Please try again.")
    
    # Get graphic image path
    while True:
        graphic_path = input("Enter path to graphic image: ").strip()
        if os.path.exists(graphic_path):
            break
        print("File not found. Please try again.")
    
    print("\nLoading images...")
    
    try:
        # Load images
        tshirt_img = Image.open(tshirt_path).convert("RGBA")
        graphic_img = Image.open(graphic_path).convert("RGBA")
        
        print(f"T-shirt size: {tshirt_img.width}x{tshirt_img.height}")
        print(f"Graphic size: {graphic_img.width}x{graphic_img.height}")
        print()
        
        # Get transformation parameters
        print("Enter transformation parameters (press Enter for defaults):")
        print()
        
        scale = get_float_input("Scale factor", 1.0, 0.1, 5.0)
        rotation = get_float_input("Rotation (degrees)", 0.0, -180.0, 180.0)
        
        # Calculate initial center position
        scaled_width = int(graphic_img.width * scale)
        scaled_height = int(graphic_img.height * scale)
        default_x = (tshirt_img.width - scaled_width) // 2
        default_y = (tshirt_img.height - scaled_height) // 2
        
        print(f"\nDefault position (centered): X={default_x}, Y={default_y}")
        offset_x = get_int_input("X offset", default_x, -tshirt_img.width, tshirt_img.width * 2)
        offset_y = get_int_input("Y offset", default_y, -tshirt_img.height, tshirt_img.height * 2)
        
        print("\nProcessing mockup...")
        
        # Apply transformations
        # Scale graphic
        graphic_img = graphic_img.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
        
        # Rotate graphic (negative because PIL rotates counter-clockwise)
        if rotation != 0:
            graphic_img = graphic_img.rotate(-rotation, expand=False, resample=Image.Resampling.BICUBIC)
        
        # Create result image
        result = tshirt_img.copy()
        
        # Paste graphic with transparency mask
        result.paste(graphic_img, (offset_x, offset_y), graphic_img)
        
        # Get output path
        base_name = os.path.splitext(os.path.basename(tshirt_path))[0]
        default_output = f"{base_name}_mockup.png"
        output_path = input(f"\nOutput filename [{default_output}]: ").strip()
        if not output_path:
            output_path = default_output
        
        # Save result
        result.save(output_path, "PNG")
        
        print(f"\n✓ Mockup saved successfully to: {os.path.abspath(output_path)}")
        print(f"  Final size: {result.width}x{result.height}")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
