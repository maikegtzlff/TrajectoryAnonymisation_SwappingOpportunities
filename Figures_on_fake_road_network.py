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

#%% only want some edges to have traj points
# select those in Q
edges.to_file(r"D:\paper3\Figures\edges_for_RoadNetworkFigure.gpkg", driver="GPKG")

#%% EDGE SWAPPING: load the selected ones back in from Q
CollegeHill_e = gpd.read_file(r"d:\paper3\Figures\CollegeHill_edges.gpkg")
PonsonbyRoad_e = gpd.read_file(r"d:\paper3\Figures\PonsonbyRoad_edges.gpkg")

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


#%% plot for EDGE SWAPPING
#StMarys_e = gpd.read_file(r"d:\paper3\Figures\edgeswapping_edges1.gpkg")
#SelbySquare_e = gpd.read_file(r"d:\paper3\Figures\edgeswapping_edges2.gpkg")

StMarys_e_p = sample_points_weighted(StMarys_e, n_points=40)
SelbySquare_e_p = sample_points_weighted(SelbySquare_e, n_points=40)

# plot fake points
fig, ax = plt.subplots(figsize=(8, 8))

# base layers
edges.plot(ax=ax, linewidth=1, color='grey', zorder=1)
nodes.plot(ax=ax, color='grey', markersize=65, zorder=1)

# fake points
StMarys_e_p.plot(ax=ax, color='#0072B2', markersize=50, zorder=3, label="St Marys")
SelbySquare_e_p.plot(ax=ax, color='#E69F00', markersize=50, zorder=3, label="Selby Square")

ax.axis('off')

plt.tight_layout()
plt.show()

#%% split into head and tail in Q (and reduce sampling size)
StMarys_e_p.to_file(r"D:\paper3\Figures/StMarys_e_p_orig.gpkg")
SelbySquare_e_p.to_file(r"D:\paper3\Figures/SelbySquare_e_p_orig.gpkg")

#%% read head and tail back in (sampling rate reduced)
StMarys_e_p_red = gpd.read_file(r"D:\paper3\Figures/StMarys_e_p_final.gpkg")
SelbySquare_e_p_red = gpd.read_file(r"D:\paper3\Figures/SelbySquare_e_p_final.gpkg")

StMarys_e_p_red_head = gpd.read_file(r"d:\paper3\Figures\StMarys_e_p_head_final.gpkg")
SelbySquare_e_p_tail = gpd.read_file(r"d:\paper3\Figures\SelbySquare_e_p_tail_final.gpkg")

StMarys_e_p_tail = gpd.read_file(r"d:\paper3\Figures\StMarys_e_p_tail_final.gpkg")
SelbySquare_e_p_head = gpd.read_file(r"d:\paper3\Figures\SelbySquare_e_p_head_final.gpkg")

nodes_sharedEdge = gpd.read_file(r"d:\paper3\Figures\edgeswapping_NodesDefiningSharedEdge.gpkg")

sharedEdge = gpd.read_file(r"d:\paper3\Figures\shared_edge_final.gpkg")


#%% updated traj b for intersection swap
PonsonbyRoad_p2 = gpd.read_file(r"d:\paper3\Figures\edgeSwapOutcome_StMarys_2193.gpkg")
PonsonbyRoad_p2_head = gpd.read_file(r"d:\paper3\Figures\edgeSwapOutcome_StMarys_2193_head.gpkg")
PonsonbyRoad_p2_tail = gpd.read_file(r"d:\paper3\Figures\edgeSwapOutcome_StMarys_2193_tail.gpkg")


#%% 4 panel figure
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import matplotlib.patheffects as pe

# ===================
# transform all layers to NZTM (EPSG:2193)
# ===================
layers = [
    edges, nodes, nodes_sharedEdge, nodes_intersection, sharedEdge,
    StMarys_e_p_red, SelbySquare_e_p_red,
    StMarys_e_p_red_head, SelbySquare_e_p_tail,
    StMarys_e_p_tail, SelbySquare_e_p_head,
    CollegeHill_p2, PonsonbyRoad_p2,
    CollegeHill_p2_head, CollegeHill_p2_tail,
    PonsonbyRoad_p2_head, PonsonbyRoad_p2_tail
]

layers = [layer.to_crs(2193) for layer in layers]

(
    edges, nodes, nodes_sharedEdge, nodes_intersection, sharedEdge,
    StMarys_e_p_red, SelbySquare_e_p_red,
    StMarys_e_p_red_head, SelbySquare_e_p_tail,
    StMarys_e_p_tail, SelbySquare_e_p_head,
    CollegeHill_p2, PonsonbyRoad_p2,
    CollegeHill_p2_head, CollegeHill_p2_tail,
    PonsonbyRoad_p2_head, PonsonbyRoad_p2_tail
) = layers

#%%
fig, axes = plt.subplots(2, 2, figsize=(16, 14))

# ===================
# shared trajectory style
# ===================
point_style = dict(
    alpha=1,
    edgecolor='white',
    linewidth=1,
    markersize=165,
    zorder=3
)

# ===================
# legend
# ===================
legend_elements = [
    Line2D([0], [0], marker='o', color='w', label='Trajectory A',
           markerfacecolor='#383a6b', markeredgecolor='white', markersize=12),
    Line2D([0], [0], marker='o', color='w', label='Trajectory B',
           markerfacecolor='#ea6d3d', markeredgecolor='white', markersize=12)
]

# ===================
# compute GLOBAL extent (AFTER CRS transform)
# ===================
all_layers = [
    edges, nodes, nodes_sharedEdge, nodes_intersection,
    StMarys_e_p_red, SelbySquare_e_p_red,
    StMarys_e_p_red_head, SelbySquare_e_p_tail,
    StMarys_e_p_tail, SelbySquare_e_p_head,
    CollegeHill_p2, PonsonbyRoad_p2,
    CollegeHill_p2_head, CollegeHill_p2_tail,
    PonsonbyRoad_p2_head, PonsonbyRoad_p2_tail
]

minx = min(layer.total_bounds[0] for layer in all_layers)
miny = min(layer.total_bounds[1] for layer in all_layers)
maxx = max(layer.total_bounds[2] for layer in all_layers)
maxy = max(layer.total_bounds[3] for layer in all_layers)

pad_x = (maxx - minx) * 0.05
pad_y = (maxy - miny) * 0.05

minx -= pad_x
maxx += pad_x
miny -= pad_y
maxy += pad_y

# ===================
# helpers
# ===================
def style_ax(ax):
    ax.axis('off')
    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(False)
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    ax.set_aspect('equal') 


def draw_base(ax):
    edges.plot(ax=ax, linewidth=1, color='grey', zorder=1)
    nodes.plot(ax=ax, color='grey', markersize=65, zorder=1)

# =========================
# (A.1)
# =========================
draw_base(axes[0, 0])
nodes_sharedEdge.plot(ax=axes[0, 0], color='grey', edgecolor='white', linewidth=2, markersize=65, zorder=4)
sharedEdge.plot(ax=axes[0, 0], linewidth=5, color='grey', zorder=1)

StMarys_e_p_red.plot(ax=axes[0, 0], color='#ea6d3d', **point_style)
SelbySquare_e_p_red.plot(ax=axes[0, 0], color='#383a6b', **point_style)

axes[0, 0].set_title("(A.1) Trajectories Sharing an Edge", loc='left', fontsize=20)

x1, y1 = nodes_sharedEdge.geometry.iloc[0].x, nodes_sharedEdge.geometry.iloc[0].y
x2, y2 = nodes_sharedEdge.geometry.iloc[1].x, nodes_sharedEdge.geometry.iloc[1].y

tx, ty = x1 + 50, y1 - 80  

axes[0, 0].annotate(
    "shared\nedge",
    xy=(x1, y1),
    xytext=(tx, ty),
    fontsize=16,
    arrowprops=dict(arrowstyle="-|>", linewidth=2.5, color='black')
)

axes[0, 0].annotate(
    "",
    xy=(x2, y2),
    xytext=(tx, ty),
    arrowprops=dict(arrowstyle="-|>", linewidth=2.5, color='black')
)

for text in axes[0, 0].texts:
    text.set_path_effects([pe.withStroke(linewidth=4, foreground="white")])

style_ax(axes[0, 0])

# =========================
# (A.2)
# =========================
draw_base(axes[0, 1])
nodes_sharedEdge.plot(ax=axes[0, 1], color='grey', edgecolor='white', linewidth=2, markersize=65, zorder=4)
sharedEdge.plot(ax=axes[0, 1], linewidth=5, color='grey', zorder=1)

StMarys_e_p_red_head.plot(ax=axes[0, 1], color='#ea6d3d', **point_style)
SelbySquare_e_p_tail.plot(ax=axes[0, 1], color='#ea6d3d', **point_style)

StMarys_e_p_tail.plot(ax=axes[0, 1], color='#383a6b', **point_style)
SelbySquare_e_p_head.plot(ax=axes[0, 1], color='#383a6b', **point_style)

x1, y1 = StMarys_e_p_tail.geometry.iloc[3].x, StMarys_e_p_tail.geometry.iloc[3].y
x2, y2 = SelbySquare_e_p_tail.geometry.iloc[1].x, SelbySquare_e_p_tail.geometry.iloc[1].y

axes[0, 1].annotate(
    "first new\npoint of t$_B$",
    xy=(x1, y1),
    xytext=(x1 + 60, y1),
    fontsize=16,
    color='#383a6b',
    arrowprops=dict(arrowstyle="-|>", linewidth=2.5, color='#383a6b')
)

axes[0, 1].annotate(
    "first new\npoint of t$_A$",
    xy=(x2, y2),
    xytext=(x2 - 200, y2),
    fontsize=16,
    color='#ea6d3d',
    arrowprops=dict(arrowstyle="-|>", linewidth=2.5, color='#ea6d3d')
)

for text in axes[0, 1].texts:
    text.set_path_effects([pe.withStroke(linewidth=4, foreground="white")])

axes[0, 1].set_title("(A.2) Head and Tail Swapped at Shared Edge", loc='left', fontsize=20)
style_ax(axes[0, 1])

# =========================
# (B.1)
# =========================
draw_base(axes[1, 0])
nodes_intersection.plot(ax=axes[1, 0], color='grey', edgecolor='white', linewidth=2, markersize=65, zorder=4)

CollegeHill_p2.plot(ax=axes[1, 0], color='#383a6b', **point_style)
PonsonbyRoad_p2.plot(ax=axes[1, 0], color='#ea6d3d', **point_style)

x, y = nodes_intersection.geometry.iloc[0].x, nodes_intersection.geometry.iloc[0].y

axes[1, 0].annotate(
    "shared\nintersection",
    xy=(x, y),
    xytext=(x - 80, y + 100),
    fontsize=16,
    arrowprops=dict(arrowstyle="-|>", linewidth=2.5, color='black')
)

for text in axes[1, 0].texts:
    text.set_path_effects([pe.withStroke(linewidth=4, foreground="white")])

axes[1, 0].set_title("(B.1) Trajectories Meeting at an Intersection", loc='left', fontsize=20)
style_ax(axes[1, 0])

# =========================
# (B.2)
# =========================
draw_base(axes[1, 1])
nodes_intersection.plot(ax=axes[1, 1], color='grey', edgecolor='white', linewidth=2, markersize=65, zorder=4)

CollegeHill_p2_head.plot(ax=axes[1, 1], color='#383a6b', **point_style)
CollegeHill_p2_tail.plot(ax=axes[1, 1], color='#ea6d3d', **point_style)

PonsonbyRoad_p2_tail.plot(ax=axes[1, 1], color='#383a6b', **point_style)
PonsonbyRoad_p2_head.plot(ax=axes[1, 1], color='#ea6d3d', **point_style)

x1, y1 = CollegeHill_p2_tail.geometry.iloc[1].x, CollegeHill_p2_tail.geometry.iloc[1].y
x2, y2 = PonsonbyRoad_p2_tail.geometry.iloc[1].x, PonsonbyRoad_p2_tail.geometry.iloc[1].y

axes[1, 1].annotate(
    "first new\npoint of t$_B$",
    xy=(x1, y1),
    xytext=(x1, y1 + 60),
    fontsize=16,
    color="#ea6d3d",
    arrowprops=dict(arrowstyle="-|>", linewidth=2.5, color="#ea6d3d")
)

axes[1, 1].annotate(
    "first new\npoint of t$_A$",
    xy=(x2, y2),
    xytext=(x2, y2 - 80),
    fontsize=16,
    color="#383a6b",
    arrowprops=dict(arrowstyle="-|>", linewidth=2.5, color="#383a6b")
)

for text in axes[1, 1].texts:
    text.set_path_effects([pe.withStroke(linewidth=4, foreground="white")])

axes[1, 1].set_title("(B.2) Head and Tail Swapped at Intersection", loc='left', fontsize=20)
style_ax(axes[1, 1])

# =========================
# legend
# =========================
axes[0, 0].legend(handles=legend_elements, loc='upper left',
                  bbox_to_anchor=(-0.05, 1), frameon=False, fontsize=18)

axes[1, 0].legend(handles=legend_elements, loc='upper left',
                  bbox_to_anchor=(-0.05, 1), frameon=False, fontsize=18)

plt.tight_layout()
plt.savefig(r"\\tsclient\R\paper3\Figures/DirectSwapping.svg", format="svg", dpi=300, bbox_inches="tight")
plt.show()