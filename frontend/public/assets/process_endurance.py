import os
from PIL import Image

src_path = r"C:\Users\Kabilesh\.gemini\antigravity\brain\216bf18c-0928-4443-901a-33b0bdd11f44\endurance_spaceship_1785518936728.jpg"
dst_path = r"D:\EVCS\frontend\public\assets\endurance_spaceship.png"

img = Image.open(src_path).convert("RGBA")
datas = img.getdata()

new_data = []
for item in datas:
    r, g, b, a = item
    brightness = (r + g + b) / 3.0
    if brightness < 25:
        # Fully transparent
        new_data.append((0, 0, 0, 0))
    elif brightness < 45:
        # Smooth alpha fade out for anti-aliased edge
        alpha = int((brightness - 25) / 20.0 * 255)
        new_data.append((r, g, b, alpha))
    else:
        new_data.append((r, g, b, 255))

img.putdata(new_data)
img.save(dst_path, "PNG")
print("Transparent PNG saved successfully!")
