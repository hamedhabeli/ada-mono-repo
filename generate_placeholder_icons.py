import os
import sys
import subprocess

def install_and_import(package):
    try:
        __import__(package)
    except ImportError:
        print(f"Installing {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Make sure Pillow is installed
install_and_import("Pillow")

from PIL import Image, ImageDraw

def generate_icons():
    icons_dir = os.path.join("frontend", "src-tauri", "icons")
    os.makedirs(icons_dir, exist_ok=True)
    
    # Create a nice 512x512 canvas with a dark blue background
    size = (512, 512)
    # Slate-900 is (15, 23, 42)
    image = Image.new("RGBA", size, color=(15, 23, 42, 255))
    draw = ImageDraw.Draw(image)
    
    # Draw a beautiful cyan circle
    # cyan is (6, 182, 212)
    margin = 40
    draw.ellipse(
        [margin, margin, size[0] - margin, size[1] - margin],
        outline=(6, 182, 212, 255),
        width=20
    )
    
    # Draw a smaller filled circle in the center
    inner_margin = 150
    draw.ellipse(
        [inner_margin, inner_margin, size[0] - inner_margin, size[1] - inner_margin],
        fill=(6, 182, 212, 180)
    )
    
    # Save standard PNGs
    image.save(os.path.join(icons_dir, "icon.png"), "PNG")
    image.resize((32, 32), Image.Resampling.LANCZOS).save(os.path.join(icons_dir, "32x32.png"), "PNG")
    image.resize((128, 128), Image.Resampling.LANCZOS).save(os.path.join(icons_dir, "128x128.png"), "PNG")
    image.resize((256, 256), Image.Resampling.LANCZOS).save(os.path.join(icons_dir, "128x128@2x.png"), "PNG")
    
    # Save standard Multi-size ICO
    ico_image = image.resize((256, 256), Image.Resampling.LANCZOS)
    ico_image.save(
        os.path.join(icons_dir, "icon.ico"),
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    )
    
    # Save ICNS (Apple standard)
    try:
        icns_image = image.resize((512, 512), Image.Resampling.LANCZOS)
        icns_image.save(os.path.join(icons_dir, "icon.icns"), format="ICNS")
        print("Generated Apple .icns file successfully.")
    except Exception as e:
        print(f"Warning: Could not save .icns format directly ({e}). Creating a fallback placeholder.")
        with open(os.path.join(icons_dir, "icon.icns"), "wb") as f:
            f.write(b"")

    print("All icons successfully generated in frontend/src-tauri/icons!")

if __name__ == "__main__":
    generate_icons()
