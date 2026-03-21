#%% import libraries
import geopandas as gpd

import osmnx as ox
import random
import numpy as np

import matplotlib.pyplot as plt


#%% fake traj points on akl road network
#lat, lon = -36.85347373440171, 174.76862289905253 #UoA Science
lat, lon = -36.84723597318564, 174.7444934641292 # Hotel Ponsonby

# download and extract road network (plus radius)
G = ox.graph_from_point((lat, lon), dist=250, network_type="drive")
nodes, edges = ox.graph_to_gdfs(G)


#%% add fake points to roads - weighted by length
def sample_points_weighted(edges, n_points=100):
    lengths = edges.geometry.length
    probs = lengths / lengths.sum()
    
    points = []
    
    for _ in range(n_points):
        edge = edges.sample(1, weights=probs).iloc[0]
        line = edge.geometry
        
        pt = line.interpolate(random.random(), normalized=True)
        points.append(pt)
    
    points_gdf =  gpd.GeoDataFrame(geometry=points, crs=edges.crs)
    
    return points_gdf

CollegeHill_p2 = sample_points_weighted(CollegeHill_e, n_points=8)
PonsonbyRoad_p2 = sample_points_weighted(PonsonbyRoad_e, n_points=14)

#%% only want some edges to have traj points
# select those in Q
edges.to_file(r"D:\paper3\Figures\edges_for_RoadNetworkFigure.gpkg", driver="GPKG")

#%% load the selected ones back in from Q
CollegeHill_e = gpd.read_file(r"d:\paper3\Figures\CollegeHill_edges.gpkg")
PonsonbyRoad_e = gpd.read_file(r"d:\paper3\Figures\PonsonbyRoad_edges.gpkg")


#%% split points into head and tail in QGIS
CollegeHill_p2.to_file(r"D:\paper3\Figures\CollegeHill_edgee_points.gpkg", driver="GPKG")
PonsonbyRoad_p2.to_file(r"D:\paper3\Figures\PonsonbyRoad_edges_points.gpkg", driver="GPKG")
nodes.to_file(r"D:\paper3\Figures\nodes.gpkg", driver="GPKG")

#%% load data back in
CollegeHill_p2_head = gpd.read_file(r"d:\paper3\Figures\CollegeHill_edgee_points_head.gpkg")
CollegeHill_p2_tail = gpd.read_file(r"d:\paper3\Figures\CollegeHill_edgee_points_tail.gpkg")

PonsonbyRoad_p2_head = gpd.read_file(r"d:\paper3\Figures\PonsonbyRoad_edges_points_head.gpkg")
PonsonbyRoad_p2_tail = gpd.read_file(r"d:\paper3\Figures\PonsonbyRoad_edges_points_tail.gpkg")

nodes_intersection = gpd.read_file(r"d:\paper3\Figures\nodes_intersection.gpkg")

#%% line annotations for head and tail
CollegeHill_tail_annotation = gpd.read_file(r"d:\paper3\Figures\collegeHill_tail_line.gpkg")
CollegeHill_head_annotation = gpd.read_file(r"d:\paper3\Figures\collegeHill_head_line.gpkg")
PonsonbyRoad_tail_annotation = gpd.read_file(r"d:\paper3\Figures\PonsnobyRoad_tail.gpkg")
PonsonbyRoad_head_annotation = gpd.read_file(r"d:\paper3\Figures\PonsonbyRoad_head.gpkg")






#%% plots before and after swapping
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import matplotlib.patheffects as pe

fig, axes = plt.subplots(1, 2, figsize=(16, 8))

# ===================
# Custom legend (left only)
# ===================
legend_elements = [
    Line2D([0], [0], marker='o', color='w', label='Trajectory A',
           markerfacecolor='#0072B2', markeredgecolor='white', markersize=12),
    Line2D([0], [0], marker='o', color='w', label='Trajectory B',
           markerfacecolor='#E69F00', markeredgecolor='white', markersize=12)
]

# ===================
# Plot 1 (left)
# ===================
edges.plot(ax=axes[0], linewidth=1, color='grey', zorder=1)
nodes.plot(ax=axes[0], color='grey', markersize=65, zorder=1)
nodes_intersection.plot(ax=axes[0], color='black', markersize=65, zorder=2)

CollegeHill_p2.plot(
    ax=axes[0],
    color='#0072B2',
    alpha=0.9,
    edgecolor='white',
    linewidth=1,
    markersize=165,
    zorder=3
)

PonsonbyRoad_p2.plot(
    ax=axes[0],
    color='#E69F00',
    alpha=0.9,
    edgecolor='white',
    linewidth=1,
    markersize=165,
    zorder=3
)

# ---- Annotation with halo + styled arrow ----
x = nodes_intersection.geometry.iloc[0].x
y = nodes_intersection.geometry.iloc[0].y

axes[0].annotate(
    "shared\nintersection",
    xy=(x, y),
    xytext= (x-0.001, y + 0.00125),
    fontsize=18,
    arrowprops=dict(
        arrowstyle="-|>",  
        linewidth=2.5,
        color='black',
        shrinkA=5,
        shrinkB=5
    )
)

# Add halo to annotation text
for text in axes[0].texts:
    text.set_path_effects([
        pe.withStroke(linewidth=4, foreground="white")
    ])

axes[0].set_title("(B.1) two trajectories meeting at an intersection", fontsize=24)
axes[0].axis('off')

# Legend styling (no frame, bigger font, upper left)
axes[0].legend(
    handles=legend_elements,
    loc='upper left',
    frameon=False,
    fontsize=18
)




# ===================
# Plot 2 (right) unchanged
# ===================
edges.plot(ax=axes[1], linewidth=1, color='grey', zorder=1)
nodes.plot(ax=axes[1], color='grey', markersize=65, zorder=1)
nodes_intersection.plot(ax=axes[1], color='black', markersize=65, zorder=2)

CollegeHill_p2_head.plot(
    ax=axes[1],
    color='#0072B2',
    alpha=0.9,
    edgecolor='white',
    linewidth=1,
    markersize=165,
    zorder=3
)

CollegeHill_p2_tail.plot(
    ax=axes[1],
    color='#E69F00',
    alpha=0.9,
    edgecolor='white',
    linewidth=1,
    markersize=165,
    zorder=3
)

PonsonbyRoad_p2_tail.plot(
    ax=axes[1],
    color='#0072B2',
    alpha=0.9,
    edgecolor='white',
    linewidth=1,
    markersize=165,
    zorder=3
)

PonsonbyRoad_p2_head.plot(
    ax=axes[1],
    color='#E69F00',
    alpha=0.9,
    edgecolor='white',
    linewidth=1,
    markersize=165,
    zorder=3
)

axes[1].set_title("(B.2) head and tail swapped at intersection", fontsize=24)
axes[1].axis('off')

plt.tight_layout()
plt.savefig(r"\\tsclient\R\paper3\Figures/DirectSwapping.svg", format="svg", dpi=300, bbox_inches="tight")
plt.show()



 
 

