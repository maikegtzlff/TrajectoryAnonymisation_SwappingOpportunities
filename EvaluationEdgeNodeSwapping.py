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


#%% node swapping outcomes
node_swp_lg = pd.read_parquet(r"d:\paper3\output\NodeSwapping\swap_log_node.parquet")
#gdf_nodess_swppd = gpd.read_parquet(r"D:\paper3\output\NodeSwapping/trajectories_swapped_nodes.parquet")


#%% load node swapping df without the one massive column
import pyarrow.parquet as pq
import pandas as pd
import geopandas as gpd
from shapely import wkb

pf = pq.ParquetFile(r"D:\paper3\output\NodeSwapping/trajectories_swapped_nodes.parquet")

dfs = []
for i in range(pf.num_row_groups):
    try:
        # Skip key_set
        table = pf.read_row_group(i, columns=[
            "container_id", "tid_subid", "swap_mode", "point_id", 
            "u","v","time_bin","geometry","timestamp",
            "uid","orig_tid","v_intersection_id_swap","is_node_arrival"
        ])
        df = table.to_pandas()
        dfs.append(df)
    except Exception as e:
        print(f"Failed row group {i}: {e}")

full_df = pd.concat(dfs, ignore_index=True)
# Convert WKB to Shapely
full_df["geometry"] = full_df["geometry"].apply(wkb.loads)
gdf_nodess_swppd = gpd.GeoDataFrame(full_df, geometry="geometry")
gdf_nodess_swppd.set_crs("EPSG:2193", inplace=True)


#%%
gdf_nodess_swppd.to_parquet(r"D:\paper3\output\NodeSwapping/trajectories_swapped_nodes_NoKeySetReadable.parquet")






#%% EVALUATION FIGURES
#(1) CDF
# %%
import numpy as np
import matplotlib.pyplot as plt

# -----------------------------
# First dataset: gdf_edges_swppd
# -----------------------------
data1 = gdf_edges_swppd.groupby('container_id')['uid'].nunique().values
data1_sorted = np.sort(data1)
cdf1 = np.arange(1, len(data1_sorted) + 1) / len(data1_sorted) * 100
color1 = "#fcc72d"

# -----------------------------
# Second dataset: gdf_nosed_swppd
# -----------------------------
data2 = gdf_nodess_swppd.groupby('container_id')['uid'].nunique().values
data2_sorted = np.sort(data2)
cdf2 = np.arange(1, len(data2_sorted) + 1) / len(data2_sorted) * 100
color2 = "#C09003"

# -----------------------------
# Plotting
# -----------------------------
fig, ax = plt.subplots(figsize=(8, 5))
ax.set_facecolor('white')

# Plot CDF lines with updated legend labels (remove 'swapping')
ax.plot(data1_sorted, cdf1, color=color1, linewidth=2, label="Edge")
ax.plot(data2_sorted, cdf2, color=color2, linewidth=2, label="Intersection")

# Limits and ticks
ax.set_xlim(left=0)
ax.set_ylim(0, 105)
ax.set_yticks([0, 25, 50, 75, 100])

# Axis labels
ax.set_xlabel("Number of pseudonyms per trajectory", fontsize=14, color='#555555')
ax.set_ylabel("CDF (%)", fontsize=14, color='#555555')

# Tick labels and tick lines (ggplot-style gray)
tick_color = '#555555'
for tick, label in zip(ax.yaxis.get_major_ticks(), ax.get_yticklabels()):
    if label.get_text() == "50":  # 50% special case
        tick.tick1line.set_color('red')
        tick.tick2line.set_color('red')
        label.set_color('red')
    else:
        tick.tick1line.set_color(tick_color)
        tick.tick2line.set_color(tick_color)
        label.set_color(tick_color)

for tick, label in zip(ax.xaxis.get_major_ticks(), ax.get_xticklabels()):
    tick.tick1line.set_color(tick_color)
    tick.tick2line.set_color(tick_color)
    label.set_color(tick_color)

ax.tick_params(axis='x', labelsize=12)
ax.tick_params(axis='y', labelsize=12)

# Solid axes
ax.spines['left'].set_visible(True)
ax.spines['left'].set_color(tick_color)
ax.spines['left'].set_linewidth(0.8)
ax.spines['bottom'].set_visible(True)
ax.spines['bottom'].set_color(tick_color)
ax.spines['bottom'].set_linewidth(0.8)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Horizontal lines at 25, 50, 75, 100 (skip 0)
for y in [25, 50, 75, 100]:
    if y == 50:
        ax.axhline(y, color='red', linestyle=':', linewidth=1.2, zorder=0)
    else:
        ax.axhline(y, color='#b0b0b0', linestyle=':', alpha=0.7, zorder=0)

ax.set_axisbelow(True)

# Legend with title and ggplot-style text color
leg = ax.legend(title="Swapping Opportunity", fontsize=12, loc='lower right', frameon=False)
leg.get_title().set_fontsize(12)
leg.get_title().set_color(tick_color)
for text in leg.get_texts():
    text.set_color(tick_color)

plt.savefig(r"\\tsclient\R\paper3\Figures/CDF_NumberOfPseudonymsByTrajectory_EdgeIntersection.svg", format="svg", bbox_inches="tight", dpi=300)
plt.show()



#%% look at containers with no swaps
import pandas as pd
import numpy as np

# -----------------------------
# data1: Edge-swapping
# -----------------------------
data1 = gdf_edges_swppd.groupby('container_id')['uid'].nunique().values
n_single_e = np.sum(data1 == 1)
n_total_e = len(data1)
perc_single_e = n_single_e / n_total_e * 100

# Points per container for single-uid containers
uid_counts_e = gdf_edges_swppd.groupby('container_id')['uid'].nunique()
single_uid_containers_e = uid_counts_e[uid_counts_e == 1].index
point_counts_e = gdf_edges_swppd.groupby('container_id').size()
single_uid_point_counts_e = point_counts_e.loc[single_uid_containers_e]

median_points_e = single_uid_point_counts_e.median()
max_points_e = single_uid_point_counts_e.max()

# -----------------------------
# data2: Intersection-swapping
# -----------------------------
data2 = gdf_nodess_swppd.groupby('container_id')['uid'].nunique().values
n_single_i = np.sum(data2 == 1)
n_total_i = len(data2)
perc_single_i = n_single_i / n_total_i * 100

# Points per container for single-uid containers
uid_counts_i = gdf_nodess_swppd.groupby('container_id')['uid'].nunique()
single_uid_containers_i = uid_counts_i[uid_counts_i == 1].index
point_counts_i = gdf_nodess_swppd.groupby('container_id').size()
single_uid_point_counts_i = point_counts_i.loc[single_uid_containers_i]

median_points_i = single_uid_point_counts_i.median()
max_points_i = single_uid_point_counts_i.max()

#%%-----------------------------
# summary table
# -----------------------------
summary_table = pd.DataFrame({
    "Dataset": ["Edge-swapping", "Intersection-swapping"],
    #"Percentage (%)": [round(perc_single_e,2), round(perc_single_i,2)],
    #"Trajectories with no swaps": [n_single_e, n_single_i],
    #"Total trajectories": [n_total_e, n_total_i],
    "Trajectories with no swaps": [f"{perc_single_e:.2f}% ({n_single_e})",
                                    f"{perc_single_i:.2f}% ({n_single_i})"],
    "Median points": [f"{median_points_e:.0f}", f"{median_points_i:.0f}"],
    #"Max points": [max_points_e, max_points_i]
})

from IPython.display import display, HTML
display(HTML(summary_table.to_html(index=False)))




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
container_counts = gdf_edges_swppd.groupby('container_id').agg(
    n_tid_subid=('tid_subid', 'nunique'),
    n_orig_tid_subid=('orig_tid_subid', 'nunique'),
    n_orig_tid=('orig_tid', 'nunique'),
    n_points=('uid', 'size')
).reset_index()

print(container_counts.head())

#%% longest sub-segment based on points
import pandas as pd

# number of points per container & segment
container_segment_counts = (
    gdf_edges_swppd
    .groupby(['container_id', 'tid_subid'])
    .size()
    .reset_index(name='n_points_segment')
)

# find the segment with the max points by container
idx_max = container_segment_counts.groupby('container_id')['n_points_segment'].idxmax()
longest_segments = container_segment_counts.loc[idx_max].copy()

# points per container
total_points = gdf_edges_swppd.groupby('container_id').size().rename('n_points_container')

# Merge to get proportion
longest_segments = longest_segments.merge(total_points, left_on='container_id', right_index=True)
longest_segments['prop_longest_segment'] = longest_segments['n_points_segment'] / longest_segments['n_points_container']

# Optional: select relevant columns
longest_segments = longest_segments[['container_id', 'tid_subid', 'n_points_segment', 'n_points_container', 'prop_longest_segment']]

longest_segments.head()

#%%
# Step 1: Count points per container & segment (using orig_tid)
container_segment_counts_i = (
    gdf_nodess_swppd
    .groupby(['container_id', 'orig_tid'])
    .size()
    .reset_index(name='n_points_segment')
)

# Step 2: segment with max points for each container
idx_max_i = container_segment_counts_i.groupby('container_id')['n_points_segment'].idxmax()
longest_segments_i = container_segment_counts_i.loc[idx_max_i].copy()

# Step 3: points per container
total_points_i = gdf_nodess_swppd.groupby('container_id').size().rename('n_points_container')

# Step 4: merge and compute proportion
longest_segments_i = longest_segments_i.merge(total_points_i, left_on='container_id', right_index=True)
longest_segments_i['prop_longest_segment'] = longest_segments_i['n_points_segment'] / longest_segments_i['n_points_container']

print(longest_segments_i.head())
print(longest_segments_i['prop_longest_segment'].describe())
#%%
data_percent_edge = longest_segments['prop_longest_segment'] * 100
data_percent_intersection = longest_segments_i['prop_longest_segment'] * 100

#%%
import matplotlib.pyplot as plt
import numpy as np

# as percentages
data_list = [data_percent_edge, data_percent_intersection]
colors = ["#fcc72d", "#C09003"]  # match boxplot colors
custom_labels = ["Edge-swapping (t$_{se}$)", "Intersection-swapping (t$_{si}$)"]

fig, ax = plt.subplots(figsize=(8,5))

bins = 30

# Plot histograms
for data, color in zip(data_list, colors):
    ax.hist(
        data, 
        bins=bins, 
        color=color, 
        edgecolor='black', 
        alpha=0.6  # semi-transparent for overlap
    )

# annotate medians
for i, (data, color) in enumerate(zip(data_list, colors)):
    median_val = np.median(data)
    ax.axvline(median_val, color=color, linestyle="--", linewidth=1.5, alpha=0.9)
    ax.text(
        median_val-1.15, 
        ax.get_ylim()[1]*0.9,  # near top
        f"{median_val:.0f}%", 
        color=color, 
        fontsize=12, 
        ha='center', 
        va='bottom',
        rotation=90
    )

# white background
ax.set_facecolor("white")
ax.grid(False)

# horizontal dotted grid lines at y-axis ticks
ax.yaxis.grid(True, linestyle=":", color="#d3d3d3", alpha=0.7, zorder=0)

# Solid x and y axes
ax.spines['left'].set_visible(True)
ax.spines['left'].set_color('black')
ax.spines['left'].set_linewidth(0.8)
ax.spines['bottom'].set_visible(True)
ax.spines['bottom'].set_color('black')
ax.spines['bottom'].set_linewidth(0.8)

# hide top and right spines
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# axis labels
ax.set_xlabel("Trajectory points of longest segment (%)", fontsize=14, color="#555555")
ax.set_ylabel("Swapped trajectories", fontsize=14, color="#555555")

# tick labels
tick_color = "#555555"
ax.tick_params(axis='x', colors=tick_color, labelsize=12)
ax.tick_params(axis='y', colors=tick_color, labelsize=12)

# legend below with custom labels
handles = [plt.Line2D([0], [0], color=c, lw=8) for c in colors]
ax.legend(handles, custom_labels, loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=2, frameon=False, fontsize=12)

plt.tight_layout()
plt.savefig(r"\\tsclient\R\paper3\Figures/hist_segmentLengthNrPoints_medianAnnotated.svg",
            format="svg", bbox_inches="tight", dpi=300)
plt.show()



#%% and as a boxplot (to compare swapping methods)

import matplotlib.pyplot as plt
import numpy as np

# as percentages
data_list = [data_percent_edge, data_percent_intersection]
labels = [r"t$_{se}$", r"t$_{si}$"]  # subscripts
colors = ["#fcc72d", "#C09003"]

fig, ax = plt.subplots(figsize=(6,5))

# Boxplot
bp = ax.boxplot(
    data_list,
    patch_artist=True,
    medianprops=dict(color="black", linewidth=2),
    whiskerprops=dict(color="black"),
    capprops=dict(color="black"),
    flierprops=dict(marker='o', markersize=4, alpha=0.7),  # base alpha
    labels=labels
)

# apply colors to boxes and fliers
for patch, flier, color in zip(bp['boxes'], bp['fliers'], colors):
    patch.set_facecolor(color)
    patch.set_edgecolor('black')
    # Set fliers color and transparency
    flier.set_markerfacecolor(color)
    flier.set_markeredgecolor(color)
    flier.set_alpha(0.01)  # more transparent

# white background
ax.set_facecolor("white")
ax.grid(False)

# horizontal dotted grid lines at y-axis ticks
ax.yaxis.grid(True, linestyle=":", color="gray", alpha=0.7, zorder=0)

# solid y-axis line
ax.spines['left'].set_visible(True)
ax.spines['left'].set_color('black')
ax.spines['left'].set_linewidth(0.8)

# hide top and right spines
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# labels
ax.set_ylabel("Trajectory points of longest segment (%)")

# annotate medians
for i, data in enumerate(data_list, start=1):
    median_val = np.median(data)
    ax.text(i, median_val, f"{median_val:.0f}%", ha='center', va='bottom', fontsize=10)

# legend below without title
handles = [plt.Line2D([0], [0], color=c, lw=8) for c in colors]
custom_labels = ["Edge-swapping (t$_{se}$)", "Intersection-swapping (t$_{si}$)"]  
ax.legend(handles, custom_labels, loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=2, frameon=False)

plt.tight_layout()
plt.savefig(r"\\tsclient\R\paper3\Figures/boxplot_longestSegment_NrPoits_edgeAndNode.svg", format="svg", bbox_inches="tight", dpi=300)
plt.show()




#%% get length of each segment in seconds
import pandas as pd

df = gdf_edges_swppd.copy()

# group by container and segment (tid_subid) to get start and end timestamps
segment_durations = df.groupby(['container_id', 'tid_subid'])['unix_timestamp'].agg(['min', 'max']).reset_index()

# duration in seconds
segment_durations['duration_sec'] = segment_durations['max'] - segment_durations['min']

# longest segment duration per container
longest_segment = segment_durations.groupby('container_id')['duration_sec'].max().reset_index()
longest_segment.rename(columns={'duration_sec': 'longest_segment_sec'}, inplace=True)

# convert to minutes if you want
longest_segment['longest_segment_min'] = longest_segment['longest_segment_sec'] / 60
longest_segment

#%%
gdf_nodess_swppd = gdf_nodess_swppd.rename(columns={'timestamp': 'unix_timestamp'})


#%% as a boxplot
import matplotlib.pyplot as plt
import numpy as np

plt.style.use("ggplot")
fig, ax = plt.subplots(figsize=(6,5))

data_list = [data_hours_edge, data_hours_intersection]
labels = [r"t$_{se}$", r"t$_{si}$"]
colors = ["#fcc72d", "#C09003"]

# Boxplot with wider boxes
bp = ax.boxplot(
    data_list,
    patch_artist=True,
    medianprops=dict(color="black", linewidth=2),
    whiskerprops=dict(color="black"),
    capprops=dict(color="black"),
    flierprops=dict(marker='o', markersize=4, alpha=0.2),
    labels=labels,
    widths=0.7  # <-- make boxes wider
)

# apply colors to boxes and fliers
for patch, flier, color in zip(bp['boxes'], bp['fliers'], colors):
    patch.set_facecolor(color)
    patch.set_edgecolor('black')
    flier.set_markerfacecolor(color)
    flier.set_markeredgecolor(color)

# axis formatting
ax.set_ylabel("Longest segment duration (hours)")
ax.set_facecolor("white")
ax.grid(False)
ax.yaxis.grid(True, linestyle=":", color="gray", alpha=0.7, zorder=0)
ax.spines['left'].set_visible(True)
ax.spines['left'].set_color('black')
ax.spines['left'].set_linewidth(0.8)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# annotate medians
for i, data in enumerate(data_list, start=1):
    median_val = np.median(data)
    median_hours_int = int(median_val)
    median_minutes = int((median_val - median_hours_int) * 60)
    ax.text(
        x=i,
        y=median_val,
        s=f"{median_hours_int}h {median_minutes}m",
        color='black',
        fontsize=10,
        ha='center',
        va='bottom',
        alpha=0.7
    )

# legend below without title
handles = [plt.Line2D([0], [0], color=c, lw=8) for c in colors]
custom_labels = ["Edge-swapping (t$_{se}$)", "Intersection-swapping (t$_{si}$)"]  
ax.legend(handles, custom_labels, loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=2, frameon=False)


plt.tight_layout()
plt.savefig(r"\\tsclient\R\paper3\Figures/boxplot_longestSegment_duration_edgeAndNode.svg", format="svg", bbox_inches="tight", dpi=300)
plt.show()


#%% look at segment durations
# %%
#%%
import matplotlib.pyplot as plt
import numpy as np

plt.style.use("ggplot")

# Thresholds
thresholds_min = [15, 60, 240]  # in minutes
thresholds_label = ["<15 min", "<1 h", "<4 h"]

# -----------------------------
# Function to compute % segments under thresholds
# -----------------------------
def pct_segments_under(df_seg, thresholds):
    result = []
    for cid, group in df_seg.groupby('container_id'):
        total_segs = len(group)
        pct_dict = {'container_id': cid, 'n_segments': total_segs}
        for th in thresholds:
            pct_dict[f'under_{th}min'] = (group['duration_min'] < th).sum() / total_segs * 100
        result.append(pct_dict)
    return pd.DataFrame(result)

# -----------------------------
# Compute segment durations for edges
# -----------------------------
df_edges = gdf_edges_swppd.copy()
df_edges_segments = df_edges.groupby(['container_id', 'tid_subid'])['unix_timestamp'].agg(['min','max']).reset_index()
df_edges_segments['duration_sec'] = df_edges_segments['max'] - df_edges_segments['min']
df_edges_segments['duration_min'] = df_edges_segments['duration_sec'] / 60

pct_edges = pct_segments_under(df_edges_segments, thresholds_min)

# -----------------------------
# Compute segment durations for intersections
# -----------------------------
df_nodes = gdf_nodess_swppd.copy()
df_nodes_segments = df_nodes.groupby(['container_id', 'orig_tid'])['unix_timestamp'].agg(['min','max']).reset_index()
df_nodes_segments['duration_sec'] = df_nodes_segments['max'] - df_nodes_segments['min']
df_nodes_segments['duration_min'] = df_nodes_segments['duration_sec'] / 60

pct_nodes = pct_segments_under(df_nodes_segments, thresholds_min)

# -----------------------------
# Prepare data for boxplot (all segments)
# Each element is a list of values for a threshold
data_all_edges = [pct_edges[f'under_{th}min'] for th in thresholds_min]
data_all_nodes = [pct_nodes[f'under_{th}min'] for th in thresholds_min]

# Combine for grouped boxplot: [edges_thresh1, nodes_thresh1, edges_thresh2, nodes_thresh2, ...]
data_grouped = []
for e, n in zip(data_all_edges, data_all_nodes):
    data_grouped.extend([e, n])

# Colors: alternate edges and nodes
colors = ["#fcc72d", "#C09003"] * len(thresholds_min)

# X-axis positions
positions = []
for i in range(len(thresholds_min)):
    positions.extend([i*3+1, i*3+2])  # space between threshold groups

# -----------------------------
# Plot
# -----------------------------
fig, ax = plt.subplots(figsize=(10,5), facecolor="white")
ax.set_facecolor("white")

bp = ax.boxplot(
    data_grouped,
    patch_artist=True,
    positions=positions,
    widths=0.8,
    medianprops=dict(color="black", linewidth=2),
    whiskerprops=dict(color="black"),
    capprops=dict(color="black"),
    flierprops=dict(marker='o', markersize=4, alpha=0.05),
)

# Color boxes and fliers
for patch, flier, color in zip(bp['boxes'], bp['fliers'], colors):
    patch.set_facecolor(color)
    patch.set_edgecolor("black")
    flier.set_markerfacecolor(color)
    flier.set_markeredgecolor(color)

# X-axis
ax.set_xticks([1.5, 4.5, 7.5])
ax.set_xticklabels(thresholds_label)
ax.set_ylabel("% of segments under threshold")
ax.set_ylim(0, 100)

# Horizontal dotted grid
ax.grid(False)
ax.yaxis.grid(True, linestyle=":", color="gray", alpha=0.7, zorder=0)

# Solid y-axis line
ax.spines['left'].set_visible(True)
ax.spines['left'].set_color('black')
ax.spines['left'].set_linewidth(0.8)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Add median annotations for both boxes
for i, d in zip(positions, data_grouped):
    median_val = np.median(d)
    ax.text(i, median_val + 1, f"{median_val:.1f}%", ha='center', va='bottom', fontweight='bold', alpha=0.7)

# Custom legend
handles = [plt.Line2D([0],[0], color="#fcc72d", lw=8),
           plt.Line2D([0],[0], color="#C09003", lw=8)]
labels = ["Edge-swapping (t$_{se}$)", "Intersection-swapping (t$_{si}$)"]  

ax.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=2, frameon=False)

plt.tight_layout()
plt.savefig(r"\\tsclient\R\paper3\Figures/boxplot_segmentDuration_edges_and_nodes.svg",
            format="svg", bbox_inches="tight", dpi=300)
plt.show()





#%% combine both boxplots to one?




#%% longest segment in terms of meters
import movingpandas as mpd
import pandas as pd

gdf_edges_swppd.crs

#%% calculate trajectory length - new trajectory
# timestamp doesnn't matter for length calculaion
# Create TrajectoryCollection
traj_collection2 = mpd.TrajectoryCollection(gdf_edges_swppd, traj_id_col='container_id', t='unix_timestamp')
# Extract trajectory lengths as a DataFrame
lengths_df2 = pd.DataFrame([
    {'container_id': traj.id, 'container_length': traj.get_length()}
    for traj in traj_collection2.trajectories
])
# Merge back into your original GeoDataFrame
gdf_edges_swppd = gdf_edges_swppd.merge(lengths_df2, on='container_id', how='left')
print(gdf_edges_swppd.head())

#%% calculate trajectory length: trajectory segments
# add new identifier
gdf_edges_swppd['container_segment_tid'] = gdf_edges_swppd['container_id'].astype('str') + '_' + gdf_edges_swppd['tid_subid']
gdf_edges_swppd[['container_segment_tid', 'container_id', 'tid_subid']]
# Create TrajectoryCollection
traj_collection = mpd.TrajectoryCollection(gdf_edges_swppd, traj_id_col='container_segment_tid', t='unix_timestamp')

# Extract trajectory lengths as a DataFrame
lengths_df = pd.DataFrame([
    {'container_segment_tid': traj.id, 'traj_length_container_segment': traj.get_length()}
    for traj in traj_collection.trajectories
])

# Merge back into your original GeoDataFrame
gdf_edges_swppd = gdf_edges_swppd.merge(lengths_df, on='container_segment_tid', how='left')
print(gdf_edges_swppd.head())

#%% 
gdf_edges_swppd.to_parquet(r"d:\paper3\output\EdgeSwapping\final_points_edgeSwap_tidLength.parquet")


#%% get length of node swapped trajectories
import geopandas as gpd
gdf_nodess_swppd = gpd.read_parquet(r"D:\paper3\output\NodeSwapping/trajectories_swapped_nodes_NoKeySetReadable.parquet")
gdf_nodess_swppd.set_crs(2193, inplace=True)
gdf_nodess_swppd.crs

#%% get trajectory length
import movingpandas as mpd
import pandas as pd

gdf_nodess_swppd_tc_t = mpd.TrajectoryCollection(gdf_nodess_swppd, traj_id_col='container_id', t='timestamp')

# Extract trajectory lengths as a DataFrame
gdf_nodess_swppd_tc_t_length = pd.DataFrame([
    {'container_id': traj.id, 'container_length': traj.get_length()}
    for traj in gdf_nodess_swppd_tc_t.trajectories
])
# Merge back into your original GeoDataFrame
gdf_nodess_swppd = gdf_nodess_swppd.merge(gdf_nodess_swppd_tc_t_length, on='container_id', how='left')
print(gdf_nodess_swppd.head())




#%% get segment length
# add new identifier
gdf_nodess_swppd['container_segment_tid'] = gdf_nodess_swppd['container_id'].astype('str') + '_' + gdf_nodess_swppd['orig_tid']

# Create TrajectoryCollection
gdf_nodess_swppd_tc_cs = mpd.TrajectoryCollection(gdf_nodess_swppd, traj_id_col='container_segment_tid', t='timestamp')

# Extract trajectory lengths as a DataFrame
gdf_nodess_swppd_tc_cs_length = pd.DataFrame([
    {'container_segment_tid': traj.id, 'traj_length_container_segment': traj.get_length()}
    for traj in gdf_nodess_swppd_tc_cs.trajectories
])

# Merge back into your original GeoDataFrame
gdf_nodess_swppd = gdf_nodess_swppd.merge(gdf_nodess_swppd_tc_cs_length, on='container_segment_tid', how='left')
gdf_nodess_swppd.to_parquet(r"D:\paper3\output\NodeSwapping/trajectories_swapped_nodes_NoKeySetReadable_length.parquet")



#%% prep node swap data 
# Remove duplicate segments within containers
gdf_nodes_segmentLength = gdf_nodess_swppd.drop_duplicates(subset=['container_id', 'orig_tid'])

# Longest segment per container
longest_segment_nodes = (
    gdf_nodes_segmentLength
    .groupby('container_id')['traj_length_container_segment']
    .max()
    .reset_index(name='longest_segment')
)

# Container lengths
container_lengths_nodes = (
    gdf_nodes_segmentLength
    .drop_duplicates(subset=['container_id'])
    [['container_id', 'container_length']]
)

# Merge to get fraction
longest_fraction_nodes = longest_segment_nodes.merge(container_lengths_nodes, on='container_id')
longest_fraction_nodes['longest_fraction'] = (
    longest_fraction_nodes['longest_segment'] / longest_fraction_nodes['container_length']
)

print(longest_fraction_nodes.head())

#%%
gdf_edges_swppd = gpd.read_parquet(r"d:\paper3\output\EdgeSwapping\final_points_edgeSwap_tidLength.parquet")



#%% plot trajectory length in me
# Remove duplicate segments within containers
gdf_edges_segmentLength = gdf_edges_swppd.drop_duplicates(subset=['container_id', 'tid_subid'])

# Get longest segment per container
longest_segment = (
    gdf_edges_segmentLength
    .groupby('container_id')['traj_length_container_segment']
    .max()
    .reset_index(name='longest_segment')
)

# Get one container length per container
container_lengths = (
    gdf_edges_segmentLength
    .drop_duplicates(subset=['container_id'])
    [['container_id', 'container_length']]
)

# Merge
longest_fraction = longest_segment.merge(container_lengths, on='container_id')

# Calculate fraction
longest_fraction['longest_fraction'] = (
    longest_fraction['longest_segment'] /
    longest_fraction['container_length']
)

print(longest_fraction.head())





#%% boxplot all segment length
import matplotlib.pyplot as plt
import numpy as np

# -------------------
# Prepare data in km
# -------------------
container_data_edge = gdf_edges_swppd.drop_duplicates(subset=['container_id'])['container_length'].dropna() / 1000
container_data_nodes = gdf_nodess_swppd.drop_duplicates(subset=['container_id'])['container_length'].dropna() / 1000
segment_data_edge = gdf_edges_swppd['traj_length_container_segment'].dropna() / 1000
segment_data_nodes = gdf_nodess_swppd['traj_length_container_segment'].dropna() / 1000

colors = ['#fcc72d', '#C09003']
labels = ['t$_{se}$', 't$_{si}$']

# -------------------
# Create figure with 2 subplots
# -------------------
fig, (axA, axB) = plt.subplots(1, 2, figsize=(14,6))
fig.patch.set_facecolor('white')
for ax in (axA, axB):
    ax.set_facecolor('white')
    ax.yaxis.grid(True, linestyle=':', color='grey', alpha=0.7)

# -------------------
# Plot boxplots
# -------------------
datasets = [[container_data_edge, container_data_nodes],
            [segment_data_edge, segment_data_nodes]]

axes = [axA, axB]
titles = ["A Container Lengths", "B Segment Lengths"]

for ax, data, title in zip(axes, datasets, titles):
    bp = ax.boxplot(data,
                    patch_artist=True,
                    showfliers=False,
                    widths=0.8,
                    medianprops={'color': 'black', 'linewidth': 2})
    
    # Apply colors
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_edgecolor('black')
    
    # Annotate medians
    for i, d in enumerate(data, start=1):
        median_val = np.median(d)
        ax.text(i, median_val + 0.5, f"{median_val:.0f} km",
                ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    # Labels and title
    ax.set_title(title, fontsize=22)
    ax.set_xticks([1,2])
    ax.set_xticklabels(labels, fontsize=16)
    ax.tick_params(axis='y', labelsize=12)

# -------------------
# Adjust spines
# -------------------
# Left y-axis for axA, right y-axis for axB, no x-axis lines
axA.spines['left'].set_visible(True)
axA.spines['left'].set_linewidth(1.5)
axA.spines['left'].set_color('black')
axA.spines['bottom'].set_visible(False)
axA.spines['top'].set_visible(False)
axA.spines['right'].set_visible(False)

axB.spines['right'].set_visible(True)
axB.spines['right'].set_linewidth(1.5)
axB.spines['right'].set_color('black')
axB.spines['bottom'].set_visible(False)
axB.spines['top'].set_visible(False)
axB.spines['left'].set_visible(False)
axB.yaxis.tick_right()
axB.yaxis.set_label_position("right")

# -------------------
# Add single legend below plots
# -------------------
custom_labels = ["Edge-swapping (t$_{se}$)", "Intersection-swapping (t$_{si}$)"]
handles = [plt.Line2D([0], [0], color=c, lw=8) for c in colors]
fig.legend(handles, custom_labels,
           loc='upper center',
           bbox_to_anchor=(0.5, -0.05),
           ncol=2,
           frameon=False,
           labelspacing=0.3,
           fontsize=16)

plt.tight_layout()
plt.savefig(r"\\tsclient\R\paper3\Figures/boxplot_segmentLengths_both_swapping.svg",
            format="svg", bbox_inches="tight", dpi=300)
plt.show()

#%% and as historgams
import matplotlib.pyplot as plt
import numpy as np

# -------------------
# Set ggplot style globally
# -------------------
plt.style.use('ggplot')
plt.rcParams.update({
    'font.family': 'sans-serif',  # ggplot-like font
    'font.sans-serif': 'DejaVu Sans',  # default matplotlib ggplot font
    'axes.titleweight': 'bold',
    'axes.titlesize': 22,
    'axes.labelsize': 16,
    'xtick.labelsize': 16,
    'ytick.labelsize': 12
})

# -------------------
# Prepare data in km
# -------------------
container_data_edge = gdf_edges_swppd.drop_duplicates(subset=['container_id'])['container_length'].dropna() / 1000
container_data_nodes = gdf_nodess_swppd.drop_duplicates(subset=['container_id'])['container_length'].dropna() / 1000
segment_data_edge = gdf_edges_swppd['traj_length_container_segment'].dropna() / 1000
segment_data_nodes = gdf_nodess_swppd['traj_length_container_segment'].dropna() / 1000

colors = ['#fcc72d', '#C09003']
labels = ['t$_{se}$', 't$_{si}$']

# -------------------
# Create figure with 2 subplots
# -------------------
fig, (axA, axB) = plt.subplots(1, 2, figsize=(14,6))
fig.patch.set_facecolor('white')
for ax in (axA, axB):
    ax.set_facecolor('white')
    ax.yaxis.grid(True, linestyle=':', color='grey', alpha=0.7)

# -------------------
# Plot boxplots
# -------------------
datasets = [[container_data_edge, container_data_nodes],
            [segment_data_edge, segment_data_nodes]]
axes = [axA, axB]
titles = ["A Trajectory Lengths (km)", "B Segment Lengths (km)"]

for ax, data, title in zip(axes, datasets, titles):
    bp = ax.boxplot(data,
                    patch_artist=True,
                    showfliers=False,
                    widths=0.8,
                    medianprops={'color': 'black', 'linewidth': 2})
    
    # Apply colors to boxes
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_edgecolor('black')
    
    # Annotate medians
    for i, d in enumerate(data, start=1):
        median_val = np.median(d)
        ax.text(i, median_val + 0.5, f"{median_val:.0f} km",
                ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    # Labels and title
    ax.set_title(title)
    ax.set_xticks([1,2])
    ax.set_xticklabels(labels)

# -------------------
# Adjust spines
# -------------------
# Left y-axis for axA, right y-axis for axB, no x-axis lines
axA.spines['left'].set_visible(True)
axA.spines['left'].set_linewidth(1.5)
axA.spines['left'].set_color('black')
axA.spines['bottom'].set_visible(False)
axA.spines['top'].set_visible(False)
axA.spines['right'].set_visible(False)

axB.spines['right'].set_visible(True)
axB.spines['right'].set_linewidth(1.5)
axB.spines['right'].set_color('black')
axB.spines['bottom'].set_visible(False)
axB.spines['top'].set_visible(False)
axB.spines['left'].set_visible(False)
axB.yaxis.tick_right()
axB.yaxis.set_label_position("right")

# -------------------
# Add single legend below plots
# -------------------
custom_labels = ["Edge-swapping (t$_{se}$)", "Intersection-swapping (t$_{si}$)"]
handles = [plt.Line2D([0], [0], color=c, lw=8) for c in colors]
fig.legend(handles, custom_labels,
           loc='upper center',
           bbox_to_anchor=(0.5, -0.05),
           ncol=2,
           frameon=False,
           labelspacing=0.3,
           fontsize=16)

plt.tight_layout()
plt.savefig(r"\\tsclient\R\paper3\Figures/boxplot_segmentLengths_both_swapping.svg",
            format="svg", bbox_inches="tight", dpi=300)
plt.show()








#%% categorizing container length
# %%
import pandas as pd

def make_summary_table_with_median(labels, counts1, percent1, counts2, percent2,
                                   col1_name, col2_name,
                                   median1_km, median2_km):
    """
    Create a summary table with percentages and counts in parentheses,
    and append median lengths at the bottom.
    """
    # Ensure all labels are included, fill missing with 0
    counts1_full = counts1.reindex(labels, fill_value=0)
    percent1_full = percent1.reindex(labels, fill_value=0)
    
    counts2_full = counts2.reindex(labels, fill_value=0)
    percent2_full = percent2.reindex(labels, fill_value=0)
    
    # Format as "percent% (count)"
    formatted1 = [f"{p:.1f}% ({c})" for p, c in zip(percent1_full, counts1_full)]
    formatted2 = [f"{p:.1f}% ({c})" for p, c in zip(percent2_full, counts2_full)]
    
    # Build DataFrame
    table = pd.DataFrame({
        "Length category": labels,
        col1_name: formatted1,
        col2_name: formatted2
    })
    
    # Append median row
    table = pd.concat([
        table,
        pd.DataFrame({
            "Length category": ["Median length (km)"],
            col1_name: [f"{median1_km:.2f}"],
            col2_name: [f"{median2_km:.2f}"]
        })
    ], ignore_index=True)
    
    return table

# -------------------
# Create summary table for container lengths
# -------------------
labels_order = [
    "<10km", "10–15km", "15–20km", "20–30km", 
    "30–50km", "50–100km", ">100km"
]

summary_table_containers = make_summary_table_with_median(
    labels_order,
    counts_edges, percent_edges,
    counts_nodes, percent_nodes,
    "Edge-swapping", "Intersection-swapping",
    median_edges_km, median_nodes_km
)

print("Container Lengths Summary:")
from IPython.display import display, HTML
display(HTML(summary_table_containers.to_html(index=False)))

# -------------------
# For segment/trajectory lengths
# -------------------
# Categorize segments similarly
def categorize_segments(df, name="dataset", bins=None, labels=None):
    """
    Categorize segment lengths into bins, compute counts, percentages, median.
    """
    df_unique = df.drop_duplicates(subset=['container_id']).copy()
    df_unique['segment_km'] = df_unique['traj_length_container_segment'] / 1000
    df_unique['length_category'] = pd.cut(df_unique['segment_km'], bins=bins, labels=labels)
    
    counts = df_unique['length_category'].value_counts().sort_index()
    percent = (counts / counts.sum() * 100).round(2)
    
    median_km = df_unique['segment_km'].median()
    
    return df_unique, counts, percent, median_km

# Use same bins/labels as containers
gdf_edges_seg_unique, counts_edges_seg, percent_edges_seg, median_edges_seg_km = categorize_segments(
    gdf_edges_swppd, name="Edge-swapping", bins=[0,10,15,20,30,50,100,float('inf')], labels=labels_order
)
gdf_nodes_seg_unique, counts_nodes_seg, percent_nodes_seg, median_nodes_seg_km = categorize_segments(
    gdf_nodess_swppd, name="Intersection-swapping", bins=[0,10,15,20,30,50,100,float('inf')], labels=labels_order
)

summary_table_segments = make_summary_table_with_median(
    labels_order,
    counts_edges_seg, percent_edges_seg,
    counts_nodes_seg, percent_nodes_seg,
    "Edge-swapping", "Intersection-swapping",
    median_edges_seg_km, median_nodes_seg_km
)

print("\nSegment Lengths Summary:")
from IPython.display import display, HTML
display(HTML(summary_table_segments.to_html(index=False)))




#%% histogram
import matplotlib.pyplot as plt
import numpy as np

# -------------------
# Prepare data in km
# -------------------
container_edge = gdf_edges_swppd.drop_duplicates(subset=['container_id'])['container_length'].dropna() / 1000
container_nodes = gdf_nodess_swppd.drop_duplicates(subset=['container_id'])['container_length'].dropna() / 1000

segment_edge = gdf_edges_swppd['traj_length_container_segment'].dropna() / 1000
segment_nodes = gdf_nodess_swppd['traj_length_container_segment'].dropna() / 1000

colors = ['#fcc72d', '#C09003']
labels = ["Edge-swapping (t$_{se}$)", "Intersection-swapping (t$_{si}$)"]

# -------------------
# Function to remove outliers using 1.5*IQR
# -------------------
def remove_outliers(data):
    q1, q3 = np.percentile(data, [25, 75])
    iqr = q3 - q1
    lower, upper = q1 - 1.5*iqr, q3 + 1.5*iqr
    return data[(data >= lower) & (data <= upper)]

container_edge_no = remove_outliers(container_edge)
container_nodes_no = remove_outliers(container_nodes)
segment_edge_no = remove_outliers(segment_edge)
segment_nodes_no = remove_outliers(segment_nodes)

# -------------------
# Compute consistent bins
# -------------------
n_bins = 20

# Container bins
container_min = min(container_edge_no.min(), container_nodes_no.min())
container_max = max(container_edge_no.max(), container_nodes_no.max())
container_bins = np.linspace(container_min, container_max, n_bins + 1)

# Segment bins
segment_min = min(segment_edge_no.min(), segment_nodes_no.min())
segment_max = max(segment_edge_no.max(), segment_nodes_no.max())
segment_bins = np.linspace(segment_min, segment_max, n_bins + 1)

# -------------------
# Create figure with 2 rows
# -------------------
fig, (axC, axS) = plt.subplots(2, 1, figsize=(12, 10))
fig.patch.set_facecolor('white')
axC.set_facecolor('white')
axS.set_facecolor('white')

# -------------------
# Container lengths histogram
# -------------------
for data, color, label in zip([container_edge_no, container_nodes_no], colors, labels):
    axC.hist(data, bins=container_bins, weights=np.ones_like(data)/len(data)*100,
             color=color, edgecolor='black', alpha=0.7, label=label)

axC.set_title("A Container Lengths", fontsize=20)
axC.set_xlabel("Length (km)", fontsize=14)
axC.set_ylabel("Percentage (%)", fontsize=14)
axC.tick_params(axis='both', labelsize=12)
axC.yaxis.grid(True, linestyle=':', color='grey', alpha=0.7)  # only horizontal
axC.xaxis.grid(False)  # remove vertical grid lines
axC.legend(frameon=False, fontsize=14)

# Align x-ticks with bin edges and round up
xticks_c = container_bins[::max(1, n_bins//8)]
axC.set_xticks(xticks_c)
axC.set_xticklabels([f"{int(np.ceil(x))}" for x in xticks_c])

# -------------------
# Segment lengths histogram
# -------------------
for data, color, label in zip([segment_edge_no, segment_nodes_no], colors, labels):
    axS.hist(data, bins=segment_bins, weights=np.ones_like(data)/len(data)*100,
             color=color, edgecolor='black', alpha=0.7, label=label)

axS.set_title("B Segment Lengths", fontsize=20)
axS.set_xlabel("Length (km)", fontsize=14)
axS.set_ylabel("Percentage (%)", fontsize=14)
axS.tick_params(axis='both', labelsize=12)
axS.yaxis.grid(True, linestyle=':', color='grey', alpha=0.7)  # horizontal only
axS.xaxis.grid(False)  # remove vertical lines
axS.legend(frameon=False, fontsize=14)

# Align x-ticks with bin edges and round up
xticks_s = segment_bins[::max(1, n_bins//8)]
axS.set_xticks(xticks_s)
axS.set_xticklabels([f"{int(np.ceil(x))}" for x in xticks_s])

plt.tight_layout()
plt.subplots_adjust(hspace=0.35) 
plt.savefig(r"\\tsclient\R\paper3\Figures/histograms_container_segment_both_swapping.svg",
            format="svg", bbox_inches="tight", dpi=300)
plt.show()


#%% road network coverage
gdf_edges_swppd.osmid_edge
# container id is new final tid
# trajectory sub-segments are tid_subid
# would compare number of points by osmid_edge to raw. by time bin? total?
