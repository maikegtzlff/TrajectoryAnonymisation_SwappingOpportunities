#%% 
import pandas as pd
import numpy as np
import geopandas as gpd

#%%
edge_swp_lg = pd.read_parquet(r"d:\paper3\output\EdgeSwapping\swap_log__edgeSwap.parquet")
edge_csum = pd.read_parquet(r"d:\paper3\output\EdgeSwapping\container_summary_edgeSwap.parquet")
gdf_edges_swppd = gpd.read_parquet(r"d:\paper3\output\EdgeSwapping\final_points_edgeSwap.parquet")

#%% swap log: records every swap between two containers --> trakcs individual swaps between conatiners
edge_swp_lg.head()
# one row = one swap at a specifc edge and time bin
# tail_points: number of points that were swapped from each container


#%% container summary: final state of each container after all swaps are complete --> aggreagted per container stats
edge_csum.head()
# each row is one container
# number of original trajectories contruting at least one point to this container
# number of unique users
# average number of swaps per point in this container --> as a boxplot?
# maximum number of swaps a point in this container experienced
# tutal number of points in container 
# in current state: no trajectory id

#%%
gdf_edges_swppd.head()
#%%
gdf_edges_swppd.columns

# swap tracking
# 'container_id' - final container
# 'swap_count' - how many times this point was swapped
# 'visited_containers' - list of container IDs sthi point has been in over the swap process




#%% evaluation figures
#(1) CDF
# %%
import numpy as np
import matplotlib.pyplot as plt

# Data
data = gdf_edges_swppd.groupby('container_id')['uid'].nunique().values
data_sorted = np.sort(data)
cdf = np.arange(1, len(data_sorted) + 1) / len(data_sorted) * 100  # percent

percentiles = [50]
perc_values = np.percentile(data_sorted, percentiles)

line_color = "#fcc72d"  # new color

fig, ax = plt.subplots(figsize=(8, 5))

# White background
ax.set_facecolor('white')

# Plot CDF line
ax.plot(data_sorted, cdf, color=line_color, linewidth=2)

# Add percentile points and annotation
for p, val in zip(percentiles, perc_values):
    y_val = p
    x_val = val
    ax.plot(x_val, y_val, marker='o', color=line_color, markersize=6)
    ax.text(
        x_val - 1,
        y_val + 2,
        f'{int(x_val)}',
        color=line_color,
        fontsize=14,
        ha='center',
        va='bottom',
        fontweight='bold'
    )

# -----------------------------
# Annotation at CDF 100%
# -----------------------------
x_last = data_sorted[-1]
y_last = cdf[-1]  # 100
ax.text(
    x_last + 1,  # slightly to the right of last point
    y_last,      # same height as CDF 100
    "Edge-based swapping",
    color=line_color,
    fontsize=14,
    ha='left',
    va='center',  # vertically centered on the line
    fontweight='bold'
)

# Set limits and ticks
ax.set_xlim(left=0)
ax.set_ylim(0, 105)
ax.set_yticks([0, 25, 50, 75, 100])

# Axis labels (titles for x and y)
ax.set_xlabel("Number of trajectories per container", fontsize=14)  # x-axis label font size
ax.set_ylabel("CDF (%)", fontsize=14)  # y-axis label font size

# Tick labels (numbers along the axes)
ax.tick_params(axis='x', labelsize=12)  # x-axis ticks font size
ax.tick_params(axis='y', labelsize=12)  # y-axis ticks font size

# Solid axes
ax.spines['left'].set_visible(True)
ax.spines['left'].set_color('black')
ax.spines['left'].set_linewidth(0.8)

ax.spines['bottom'].set_visible(True)
ax.spines['bottom'].set_color('black')
ax.spines['bottom'].set_linewidth(0.8)

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Dotted grid
ax.grid(True, which='both', linestyle=':', color='gray', alpha=0.7, zorder=0)
ax.set_axisbelow(True)

# Labels
ax.set_xlabel("Number of pseudonyms per trajectory")
ax.set_ylabel("CDF (%)")

# export to svg
plt.savefig(r"\\tsclient\R\paper3\Figures/cdf_edge_based_swapping.svg", format="svg", bbox_inches="tight", dpi=300)

plt.show()

#%% look at containers with no swaps
data = gdf_edges_swppd.groupby('container_id')['uid'].nunique().values
n_single = np.sum(data == 1)
n_total = len(data)

print(f"Containers with exactly 1 pseudonym: {n_single}")
print(f"Total containers: {n_total}")
print(f"Percentage: {n_single / n_total * 100:.2f}%")

#%%
# Number of unique uids per container
uid_counts = gdf_edges_swppd.groupby('container_id')['uid'].nunique()

# Containers that have exactly one pseudonym
single_uid_containers = uid_counts[uid_counts == 1].index

# Count total rows (points) per container
point_counts = gdf_edges_swppd.groupby('container_id').size()

# Keep only the single-uid containers
single_uid_point_counts = point_counts.loc[single_uid_containers]

median_points = single_uid_point_counts.median()
max_points = single_uid_point_counts.max()

print(f"Median number of points: {median_points}")
print(f"Maximum number of points: {max_points}")





################################################
#%% (2) pseudonym changes by point
import matplotlib.pyplot as plt

plt.tight_layout()
plt.show()
plt.style.use("ggplot")

fig, ax = plt.subplots(figsize=(6, 4))

changes = gdf_edges_swppd['swap_count']

ax.boxplot(
    changes,
    patch_artist=True,
    boxprops=dict(facecolor="#fcc72d", edgecolor="black"),
    medianprops=dict(color="black", linewidth=2),
    whiskerprops=dict(color="black"),
    capprops=dict(color="black"),
    flierprops=dict(
        marker='o',
        markerfacecolor='#fcc72d',
        markeredgecolor='#fcc72d',
        markersize=4,
        alpha=0.01  
    )
)

# White background
ax.set_facecolor('white')

# Hide the default grid
ax.grid(False)
# Add horizontal dotted grid lines at y-axis ticks
ax.yaxis.grid(True, linestyle=':', color='gray', alpha=0.7, zorder=0)

# Solid y-axis line
ax.spines['left'].set_visible(True)
ax.spines['left'].set_color('black')
ax.spines['left'].set_linewidth(0.8)

# Hide top and right spines
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

ax.set_ylabel("Pseudonym changes")

# Custom x-axis label
ax.set_xticks([1])
ax.set_xticklabels([r"$t_{se}$"])

# Get the median from the data
median_val = changes.median()

# Annotate the median on top of the existing median line
ax.text(
    x=1,  # x-position aligned with the box
    y=median_val,  # y-position exactly at the median
    s=f"{int(median_val)}",  # text to display
    color='black',  # same as median line
    fontsize=10,
    ha='center',  # horizontally centered over the box
    va='bottom',   # place text just above the line
    alpha=0.5
)

plt.tight_layout()
plt.savefig(r"\\tsclient\R\paper3\Figures/PointsSwapped_edge_based_swapping.svg", format="svg", bbox_inches="tight", dpi=300)
plt.show()




#################################################
#%% Figrues on longest sub-segment
