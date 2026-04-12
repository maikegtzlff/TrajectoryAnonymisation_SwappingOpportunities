#%% Re-identification figure

#%% load data
import geopandas as gpd
cloaking_geom_ri = gpd.read_parquet(r'\\tsclient\R\paper3\HomeDetection\Reidentified\cloaking_geom_ri.parquet')
StpPntsClstered_nodes_ri = gpd.read_parquet(r'\\tsclient\R\paper3\HomeDetection\Reidentified\StpPntsClstered_nodes_ri.parquet')
StpPntsClstered_edges_ri = gpd.read_parquet(r'\\tsclient\R\paper3\HomeDetection\Reidentified\StpPntsClstered_edges_ri.parquet')
StpPntsClstered_clkd_ri = gpd.read_parquet(r'\\tsclient\R\paper3\HomeDetection\Reidentified\StpPntsClstered_clkd_ri.parquet')



 






#%% interactive map of TRUE intersections
import folium

StpPntsClstered_edges_ri_4326 = StpPntsClstered_edges_ri.to_crs(epsg=4326)
StpPntsClstered_nodes_ri_4326 = StpPntsClstered_nodes_ri.to_crs(epsg=4326)
StpPntsClstered_clkd_ri_4326 = StpPntsClstered_clkd_ri.to_crs(epsg=4326)


cloaking_geom_ri_4326 = cloaking_geom_ri.to_crs(epsg=4326)

# get center of your data
center = [
    cloaking_geom_ri_4326.geometry.centroid.y.mean(),
    cloaking_geom_ri_4326.geometry.centroid.x.mean()
]

m = folium.Map(location=center, zoom_start=13)

# add sig loc layer of contributors
folium.GeoJson(
    cloaking_geom_ri_4326,
    name="sensitive location",
    style_function=lambda x: {"color": "black", "weight": 3}
).add_to(m)

for _, row in StpPntsClstered_edges_ri_4326.iterrows():
    folium.CircleMarker(
        location=[row.geometry.y, row.geometry.x],
        radius=5,
        color="blue",
        fill=True,
        fill_color="blue"
    ).add_to(m)

for _, row in StpPntsClstered_nodes_ri_4326.iterrows():
    folium.CircleMarker(
        location=[row.geometry.y, row.geometry.x],
        radius=5,
        color="red",
        fill=True,
        fill_color="red"
    ).add_to(m)

for _, row in StpPntsClstered_clkd_ri_4326.iterrows():
    folium.CircleMarker(
        location=[row.geometry.y, row.geometry.x],
        radius=5,
        color="green",
        fill=True,
        fill_color="green"
    ).add_to(m)


# layer control toggle
folium.LayerControl().add_to(m)

# save + open in browser
m.save("map.html")

import webbrowser
webbrowser.open("map.html")


#%%
print(cloaking_geom_ri.contributor_rank_uid.nunique())
print(len(cloaking_geom_ri)) #26 significant locations re-dentified when lookint at all 3 swapping ouputs combined - ie some are the same



#%% ADD NODE SWAPPING AND EDGE SWAPPING TO MAP, SELECT ONE CLOAKING GEOM TO REPRESENT AS FIGURE
# selected the ones I want for the figure in Qgis


#%% figure should be static
import matplotlib.pyplot as plt

fig, ax = plt.subplots()

cloaking_geom_ri.plot(ax=ax, color='black', label='sensitive location')

StpPntsClstered_nodes_ri.plot(ax=ax, color='red', alpha =0.3,  label='after node-swapping')
StpPntsClstered_edges_ri.plot(ax=ax, color='blue',  alpha =0.3, label='after edge-swapping')
StpPntsClstered_clkd_ri.plot(ax=ax, color='green',  alpha =0.3, label='after edge-swapping')

# looking for one cloaking area with all three swapping strategies for a little figure

ax.legend()
plt.show()








#%%#######################################
#%% data manipulated in QGIS
import geopandas as gpd

freq_loc = gpd.read_file(r"\\tsclient\R\paper3\HomeDetection\Reidentified\figure\freqloc_sample.gpkg")
poi = gpd.read_file(r"\\tsclient\R\paper3\HomeDetection\Reidentified\figure\POI_manipulated.gpkg")
buildings = gpd.read_file(r"\\tsclient\R/paper3/HomeDetection/Reidentified/figure/OneBuilding.gpkg")
roads = gpd.read_file(r"\\tsclient\R/paper3/HomeDetection/Reidentified/figure/roads_selected.gpkg")
cloaking_area = gpd.read_file(r"\\tsclient\R\paper3\HomeDetection\Reidentified\figure\cloaking_geom_selected.gpkg")

#%%
print(roads.crs)
print(cloaking_area.crs)
print(buildings.crs)
print(poi.crs)
print(freq_loc.crs)

#%%
poi.loc[6, "amenity"] = " "
poi[['amenity', 'name']]
#%%
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

minx, miny, maxx, maxy = cloaking_area.total_bounds
pad_x = (maxx - minx) * 0.3
pad_y = (maxy - miny) * 0.2

xmin = minx - pad_x
xmax = maxx + pad_x
ymin = miny - pad_y
ymax = maxy + pad_y

fig, ax = plt.subplots(figsize=(8, 8))

# plotting
roads.plot(ax=ax, color='#404040', linewidth=0.5, zorder=1)
buildings.plot(ax=ax, color='#474747', edgecolor='#383838', linewidth=0.3, zorder=2)
poi.plot(ax=ax, color='#383a6b', markersize=5, edgecolor='#2C2E55', linewidth=0.3, zorder=4)


cloaking_area.plot(ax=ax, facecolor='#cb1f73', edgecolor='#cb1f73', alpha=0.3, linewidth=2, zorder=0)
cloaking_area.plot(ax=ax, facecolor='none', edgecolor='#cb1f73', alpha=1, linewidth=5, zorder=3)

#freq_loc.plot(ax=ax, color='#fcc72d', markersize=250, edgecolor='#FCC014', linewidth=1.5, zorder=5)
#freq_loc.plot(ax=ax, color='#fcc72d', markersize=250, edgecolor='#C09003', linewidth=1.5, zorder=5)
freq_loc.plot(ax=ax, color='#fcc72d', marker='*', markersize=250, edgecolor='#C09003', linewidth=1.5, zorder=5)

#print(poi[['amenity', 'name']])

offsets = {
    0: (40, -15),   # right parking
    1: (-10, 20),    # restaurant right
    2: (-30, 50),   # supermarket
    3: (-20, 80),     # fast food left
    4: (-10, -25),  # parking left
    5: (15, -30),   # fuel
    6: (-75, 65)     # fast food right
}

# annotate POIs
for idx, row in poi.iterrows():
    geom = row.geometry
    pt = geom.representative_point()  
    
    x, y = pt.x, pt.y
    label = str(row["amenity"])

    dx, dy = offsets.get(idx, (3, 3))  
    
    text = ax.annotate(
        label,
        xy=(x, y),
        xytext=(dx, dy),
        textcoords="offset points",
        fontsize=12,
        color='#383a6b',
        arrowprops=dict(
            arrowstyle="-|>",
            color="#383a6b",
            lw=0.8
        ),
        zorder=6
    )

    text.set_path_effects([
        pe.withStroke(linewidth=3, foreground="white")
    ])

    if text.arrow_patch is not None:
        text.arrow_patch.set_path_effects([
            pe.withStroke(linewidth=4, foreground="white")
        ])

# annotate cloaking area
import numpy as np

geom = cloaking_area.geometry.iloc[0]
boundary = geom.boundary

label = "CLOAKING AREA"

# anchor 
#center_fraction = (0.5 + 0.5) % 1.0
offset = -0.01  
center_fraction = (center_fraction + offset) % 1.0
boundary_length = boundary.length

# Anchor distance along boundary
center_distance = boundary_length * center_fraction

# Define a local segment around the anchor
segment_length = boundary_length * 0.25  

start_distance = center_distance - segment_length / 2
end_distance = center_distance + segment_length / 2

# Evenly space characters within this local segment
distances = np.linspace(start_distance, end_distance, len(label))

# Offset distance away from buffer
offset_dist = boundary_length * 0.02

for char, d in zip(label, distances):
    # Wrap distances around boundary length
    d = d % boundary_length
    
    point = boundary.interpolate(d)
    next_point = boundary.interpolate((d + 1) % boundary_length)
    
    x, y = point.x, point.y
    
    # Direction along boundary (tangent)
    dx = next_point.x - x
    dy = next_point.y - y
    
    # Normalize tangent
    length = np.hypot(dx, dy)
    if length == 0:
        continue
    dx /= length
    dy /= length
    
    # Perpendicular (normal)
    nx = -dy
    ny = dx
    
    # Apply outward offset
    x = x + nx * offset_dist
    y = y + ny * offset_dist
    
    # Rotation follows tangent
    angle = np.degrees(np.arctan2(dy, dx))
    
    txt = ax.text(
        x, y,
        char,
        fontsize=22,
        rotation=angle,
        rotation_mode='anchor',
        ha='center',
        va='center',
        color='#cb1f73'
    )

    # Add halo
    txt.set_path_effects([
        pe.withStroke(linewidth=3, foreground="white")
    ])


# legend
legend_elements = [
    Line2D([0], [0], 
           marker='*', #'o', 
           color='w',
           label='Frequent location',
           markerfacecolor='#fcc72d',
           markeredgecolor='#C09003',
           markersize=10),

    #Patch(facecolor='#cb1f73', edgecolor='#cb1f73', alpha=0.3, label='Cloaking area'),

    Patch(facecolor='#383a6b', edgecolor='#2C2E55', label='POI'),
    Patch(facecolor='#474747', edgecolor='#383838', label='Residential buildings')
]
legend = ax.legend(handles=legend_elements, loc='lower right', frameon=False,  prop={'size': 10})
for text in legend.get_texts():
    if text.get_text() == 'Frequent location':
        text.set_fontweight('bold')

ax.set_xlim(xmin, xmax)
ax.set_ylim(ymin, ymax)
ax.set_axis_off()

plt.savefig(r"\\tsclient\R\paper3\Figures/SigLocReidentifiedAsFreqLoc.svg", format="svg", bbox_inches="tight", dpi=300)
plt.show()