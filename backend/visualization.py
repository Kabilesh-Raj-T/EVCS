import folium
from folium.plugins import HeatMap

def add_station_heatmap(map_obj, coords):
    if len(coords) == 0:
        return

    n_points = len(coords)
    
    # Dynamic scaling based on density to prevent blue blob oversaturation
    # Increased radius/blur slightly to make it more sensitive
    if n_points > 20000:
        radius = 6
        blur = 5
        min_opacity = 0.15
    elif n_points > 5000:
        radius = 8
        blur = 10
        min_opacity = 0.2
    else:
        radius = 12
        blur = 18
        min_opacity = 0.3

    # Custom gradient shifted lower so hot colors appear faster (more sensitive)
    custom_gradient = {
        0.05: 'cyan',
        0.15: 'blue',
        0.3: 'purple',
        0.5: 'magenta',
        0.8: 'red'
    }

    HeatMap(
        coords.tolist(),
        name="Existing EV charging station density",
        radius=radius,
        blur=blur,
        min_opacity=min_opacity,
        gradient=custom_gradient
    ).add_to(map_obj)

def add_region_boundary(map_obj, region, india_boundary):
    pass
