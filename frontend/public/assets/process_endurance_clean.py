from PIL import Image
import math

src_path = r"C:\Users\Kabilesh\.gemini\antigravity\brain\216bf18c-0928-4443-901a-33b0bdd11f44\endurance_spaceship_1785518936728.jpg"
dst_path = r"D:\EVCS\frontend\public\assets\endurance_spaceship.png"

img = Image.open(src_path).convert("RGBA")
width, height = img.size
cx, cy = width / 2.0, height / 2.0
max_r = min(width, height) * 0.46 # Outer bound for the ring

pix = img.load()

for y in range(height):
    for x in range(width):
        r, g, b, a = pix[x, y]
        dist = math.hypot(x - cx, y - cy)
        brightness = (r + g + b) / 3.0

        # Remove isolated background stars/dots outside max radius or with low/medium background brightness
        if dist > max_r or brightness < 65:
            pix[x, y] = (0, 0, 0, 0)
        elif brightness < 85:
            # Smooth anti-aliased edge fade
            alpha = int((brightness - 65) / 20.0 * 255)
            pix[x, y] = (r, g, b, alpha)
        else:
            pix[x, y] = (r, g, b, 255)

img.save(dst_path, "PNG")
print("Clean transparent PNG saved successfully without stars!")
