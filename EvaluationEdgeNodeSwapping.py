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
container_counts = gdf_edges_swppd.groupby('container_id').agg(
    n_tid_subid=('tid_subid', 'nunique'),
    n_orig_tid_subid=('orig_tid_subid', 'nunique'),
    n_orig_tid=('orig_tid', 'nunique'),
    n_points=('uid', 'size')
).reset_index()

print(container_counts.head())

#%% longest sub-segment based on points
import pandas as pd


# 1️⃣ Count number of points per container & segment
container_segment_counts = (
    gdf_edges_swppd
    .groupby(['container_id', 'tid_subid'])
    .size()
    .reset_index(name='n_points_segment')
)

# 2️⃣ For each container, find the segment with the max points
idx_max = container_segment_counts.groupby('container_id')['n_points_segment'].idxmax()
longest_segments = container_segment_counts.loc[idx_max].copy()

# 3️⃣ Total points per container
total_points = gdf_edges_swppd.groupby('container_id').size().rename('n_points_container')

# Merge to get proportion
longest_segments = longest_segments.merge(total_points, left_on='container_id', right_index=True)
longest_segments['prop_longest_segment'] = longest_segments['n_points_segment'] / longest_segments['n_points_container']

# Optional: select relevant columns
longest_segments = longest_segments[['container_id', 'tid_subid', 'n_points_segment', 'n_points_container', 'prop_longest_segment']]

longest_segments.head()

#%%
#%%
import matplotlib.pyplot as plt

# Apply ggplot style
plt.style.use("ggplot")

# Create figure
fig, ax = plt.subplots(figsize=(8, 5))

# Histogram (in %)
ax.hist(
    longest_segments['prop_longest_segment']*100, 
    bins=30, 
    color="#fcc72d", 
    edgecolor="black"
)

# White background
ax.set_facecolor("white")

# Remove default grid
ax.grid(False)

# Add horizontal dotted grid lines at y-axis ticks
ax.yaxis.grid(True, linestyle=':', color='gray', alpha=0.7, zorder=0)

# Solid y-axis line
ax.spines['left'].set_visible(True)
ax.spines['left'].set_color('black')
ax.spines['left'].set_linewidth(0.8)

# Hide other spines
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['bottom'].set_visible(True)
ax.spines['bottom'].set_color('black')
ax.spines['bottom'].set_linewidth(0.8)

# Labels
ax.set_xlabel("Trajectory points of longest segment in relation to total number of points (%)")
ax.set_ylabel("Swapped trajectories")

# Add median line and rotated annotation
median_val = longest_segments['prop_longest_segment'].median()*100
ax.axvline(median_val, color="black", linestyle="--", linewidth=1.5, alpha=0.5)

ax.text(
    median_val + 2,
    ax.get_ylim()[1]*0.9,  # near top
    f"{median_val:.0f}%",
    color="black",
    fontsize=12,
    ha='center',
    va='bottom',
    rotation=90
)

plt.tight_layout()
plt.savefig(r"\\tsclient\R\paper3\Figures/hist_segmentLengthNrPoints_edge_based_swapping.svg", format="svg", bbox_inches="tight", dpi=300)
plt.show()

#%% and as a boxplot (to compare swapping methods)
import matplotlib.pyplot as plt

plt.style.use("ggplot")

# Convert to %
data_percent = longest_segments['prop_longest_segment'] * 100

fig, ax = plt.subplots(figsize=(8, 5))

# Boxplot
ax.boxplot(
    data_percent,
    patch_artist=True,
    boxprops=dict(facecolor="#fcc72d", edgecolor="black"),
    medianprops=dict(color="black", linewidth=2),
    whiskerprops=dict(color="black"),
    capprops=dict(color="black"),
    flierprops=dict(
        marker='o',
        markerfacecolor="#fcc72d",
        markeredgecolor="#fcc72d",
        markersize=4,
        alpha=0.01  # make outliers faint
    )
)

# White background
ax.set_facecolor("white")
ax.grid(False)

# Horizontal dotted grid lines at y-axis ticks
ax.yaxis.grid(True, linestyle=":", color="gray", alpha=0.7, zorder=0)

# Solid y-axis line
ax.spines['left'].set_visible(True)
ax.spines['left'].set_color('black')
ax.spines['left'].set_linewidth(0.8)

# Hide top and right spines
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Labels
ax.set_ylabel("Trajectory points of longest segment (%)")
ax.set_xticks([1])
ax.set_xticklabels([r"$t_{se}$"])  # your x-label

# Median annotation
median_val = data_percent.median()
ax.text(
    x=1,  # box x-position
    y=median_val,
    s=f"{median_val:.0f}%",  # show value
    color='black',
    fontsize=12,
    ha='center',
    va='bottom',
    alpha=0.7
)

plt.tight_layout()
plt.savefig(r"\\tsclient\R\paper3\Figures/boxplot_segmentLengthNrPoints_edge_based_swapping.svg", format="svg", bbox_inches="tight", dpi=300)
plt.show()



#%% get length of each segment in seconds
import pandas as pd

# Copy for safety
df = gdf_edges_swppd.copy()

# Group by container and segment (tid_subid) to get start and end timestamps
segment_durations = df.groupby(['container_id', 'tid_subid'])['unix_timestamp'].agg(['min', 'max']).reset_index()

# Compute duration in seconds
segment_durations['duration_sec'] = segment_durations['max'] - segment_durations['min']

# Find the longest segment duration per container
longest_segment = segment_durations.groupby('container_id')['duration_sec'].max().reset_index()
longest_segment.rename(columns={'duration_sec': 'longest_segment_sec'}, inplace=True)

# Convert to minutes if you want
longest_segment['longest_segment_min'] = longest_segment['longest_segment_sec'] / 60
longest_segment





#%% as a boxplot
# %%
import matplotlib.pyplot as plt

# Use ggplot style
plt.style.use("ggplot")

# Create figure
fig, ax = plt.subplots(figsize=(8, 5))

# Data: longest segment in hours
data_hours = longest_segment['longest_segment_min'] / 60  # minutes → hours

# Boxplot
ax.boxplot(
    data_hours,
    patch_artist=True,
    boxprops=dict(facecolor="#fcc72d", edgecolor="black"),
    medianprops=dict(color="black", linewidth=2),
    whiskerprops=dict(color="black"),
    capprops=dict(color="black"),
    flierprops=dict(
        marker='o',
        markerfacecolor="#fcc72d",
        markeredgecolor="#fcc72d",
        markersize=4,
        alpha=0.05
    )
)

# White background
ax.set_facecolor("white")

# Horizontal dotted grid
ax.grid(False)
ax.yaxis.grid(True, linestyle=":", color="gray", alpha=0.7, zorder=0)

# Solid y-axis line
ax.spines['left'].set_visible(True)
ax.spines['left'].set_color('black')
ax.spines['left'].set_linewidth(0.8)

# Hide top and right spines
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Labels
ax.set_ylabel("Longest segment duration (hours)")
ax.set_xticks([1])
ax.set_xticklabels([r"$t_{se}$"])

# Annotate median
median_val = data_hours.median()

median_hours_int = int(median_val)
median_minutes = int((median_val - median_hours_int) * 60)

ax.text(
    x=1,
    y=median_val,
    s=f"{median_hours_int}h {median_minutes}m",
    color='black',
    fontsize=12,
    ha='center',
    va='bottom',
    alpha=0.6
)

# Quartiles
#q1, q2, q3 = data_hours.quantile([0.25, 0.5, 0.75])
#quartiles = {
#    "Q1": q1,
#    "Median": q2,
#    "Q3": q3
#}
# Annotate each quartile
#for label, val in quartiles.items():
#    hours = int(val)
#    minutes = int((val - hours) * 60)
#    ax.text(
#        x=1.05,  # slightly to the right of the box
#        y=val,
#        s=f"{hours}h {minutes}m",
#        color='black',
#        fontsize=10,
#        ha='left',
#        va='center',
#        rotation=0
#    )

plt.tight_layout()
plt.savefig(r"\\tsclient\R\paper3\Figures/boxplot_segmentLengthDuration_edge_based_swapping.svg", format="svg", bbox_inches="tight", dpi=300)

plt.show()


#%% look at segment durations
# Copy data for safety
df = gdf_edges_swppd.copy()

# Compute duration of each segment (tid_subid) per container
segments = df.groupby(['container_id', 'tid_subid'])['unix_timestamp'].agg(['min', 'max']).reset_index()
segments['duration_sec'] = segments['max'] - segments['min']  # duration in seconds
segments['duration_min'] = segments['duration_sec'] / 60
segments['duration_hr'] = segments['duration_sec'] / 3600

thresholds_min = [15, 60, 240]  # in minutes
thresholds_label = ["<15 min", "<1 h", "<4 h"]

#%% all segments in container
# Function to compute % of segments under thresholds per container
def pct_segments_under(df_seg, thresholds):
    result = []
    for cid, group in df_seg.groupby('container_id'):
        total_segs = len(group)
        pct_dict = {'container_id': cid, 'n_segments': total_segs}
        for th in thresholds:
            pct_dict[f'under_{th}min'] = (group['duration_min'] < th).sum() / total_segs * 100
        result.append(pct_dict)
    return pd.DataFrame(result)

pct_all = pct_segments_under(segments, thresholds_min)

#%% longest segment in container
# Get longest segment duration per container
longest_seg = segments.groupby('container_id')['duration_min'].max().reset_index()

# Compare to thresholds
for th in thresholds_min:
    longest_seg[f'under_{th}min'] = (longest_seg['duration_min'] < th) * 100  # 0 or 100%

#%%
# %%
# %%
import matplotlib.pyplot as plt
import numpy as np

plt.style.use("ggplot")
fig, ax = plt.subplots(figsize=(8,5), facecolor="white")
ax.set_facecolor("white")

# Prepare data for boxplot (all segments)
data_all = [pct_all[f'under_{th}min'] for th in thresholds_min]

# Boxplot
bp = ax.boxplot(
    data_all,
    patch_artist=True,
    boxprops=dict(facecolor="#fcc72d", edgecolor="black"),
    medianprops=dict(color="black", linewidth=2),
    whiskerprops=dict(color="black"),
    capprops=dict(color="black"),
    flierprops=dict(
        marker='o',
        markerfacecolor="#fcc72d",
        markeredgecolor="#fcc72d",
        markersize=4,
        alpha=0.05
    )
)

# Labels
ax.set_xticks([1,2,3])
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

# Add median values on top of each box
for i, y in enumerate([np.median(d) for d in data_all], start=1):
    ax.text(i, y + 1, f"{y:.1f}%", ha='center', va='bottom', fontweight='bold', alpha=0.7)

plt.tight_layout()
plt.savefig(r"\\tsclient\R\paper3\Figures/boxplot_segmentDuration_edge_based_swapping.svg", format="svg", bbox_inches="tight", dpi=300)
plt.show()



#%% combine both boxplots to one?






























#%% longest segment in terms of meters
gdf_edges_swppd.crs

#%% calculate trajectory length - new trajectory
# update timestamp in container
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


#%%
import movingpandas as mpd
import pandas as pd

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

#%%
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

# Prepare data in km
segment_data_km = gdf_edges_segmentLength['traj_length_container_segment'].dropna() / 1000
container_lengths_unique = gdf_edges_segmentLength.drop_duplicates(subset=['container_id'])
container_data_km = container_lengths_unique['container_length'].dropna() / 1000

# Create figure with 2 subplots side by side
fig, (axA, axB) = plt.subplots(1, 2, figsize=(14,6))

# Remove grey background
fig.patch.set_facecolor('white')
axA.set_facecolor('white')
axB.set_facecolor('white')

# -------------------
# Plot A: Container lengths
# -------------------
bpA = axA.boxplot(container_data_km, showfliers=False,
                  patch_artist=True,
                  boxprops=dict(facecolor='#fcc72d', color='black'),
                  medianprops={'color': 'black', 'linewidth': 2})
axA.set_ylabel("Length (km)", fontsize=16)
axA.set_title("A Container Lengths", fontsize=22)
axA.set_xticks([1])
axA.set_xticklabels([r'$t_{se}$'], fontsize=16)
axA.tick_params(axis='y', labelsize=12)
axA.spines['left'].set_linewidth(1.5)
axA.spines['left'].set_color('black')
axA.yaxis.grid(True, linestyle=':', color='grey', alpha=0.7)

# Annotate median
medianA = np.median(container_data_km)
axA.text(0.95, medianA+18.5, f"{medianA:.0f}km", va='center', ha='left', fontsize=12, fontweight='bold', color='black')

# -------------------
# Plot B: Segment lengths
# -------------------
bpB = axB.boxplot(segment_data_km, showfliers=False,
                  patch_artist=True,
                  boxprops=dict(facecolor='#C09003', color='black'),
                  medianprops={'color': 'black', 'linewidth': 2})
axB.set_ylabel("Length (km)", fontsize=16)
axB.set_title("B Segment Lengths", fontsize=22)
axB.set_xticks([1])
axB.set_xticklabels([r'$t_{se}$'], fontsize=16)
axB.yaxis.tick_right()
axB.yaxis.set_label_position("right")
axB.tick_params(axis='y', labelsize=12)
axB.spines['right'].set_linewidth(1.5)
axB.spines['right'].set_color('black')
axB.yaxis.grid(True, linestyle=':', color='grey', alpha=0.7)

# Annotate median
medianB = np.median(segment_data_km)
axB.text(0.975, medianB+0.5, f"{medianB:.0f}km", va='center', ha='left', fontsize=12, fontweight='bold', color='black')

plt.tight_layout()
plt.savefig(r"\\tsclient\R\paper3\Figures/boxplot_segmentLengths_edge_based_swapping.svg", format="svg", bbox_inches="tight", dpi=300)
plt.show()

#%% and as historgams
# %%
import matplotlib.pyplot as plt
import numpy as np

# Prepare data in km
segment_data_km = gdf_edges_segmentLength['traj_length_container_segment'].dropna() / 1000
container_lengths_unique = gdf_edges_segmentLength.drop_duplicates(subset=['container_id'])
container_data_km = container_lengths_unique['container_length'].dropna() / 1000

# Remove outliers using 1.5*IQR rule
def remove_outliers(data):
    q1, q3 = np.percentile(data, [25, 75])
    iqr = q3 - q1
    lower = q1 - 1.5*iqr
    upper = q3 + 1.5*iqr
    return data[(data >= lower) & (data <= upper)]

container_no_outliers = remove_outliers(container_data_km)
segment_no_outliers = remove_outliers(segment_data_km)

# Create figure
fig, (axA, axB) = plt.subplots(1, 2, figsize=(14,6))
fig.patch.set_facecolor('white')
axA.set_facecolor('white')
axB.set_facecolor('white')

n_bins = 20

# Function to select a few ticks
def select_ticks(bins, n_ticks=5):
    idx = np.linspace(0, len(bins)-1, n_ticks, dtype=int)
    return bins[idx]

# -------------------
# Histogram A
# -------------------
countsA, binsA, _ = axA.hist(container_no_outliers, bins=n_bins, 
                             weights=np.ones_like(container_no_outliers)/len(container_no_outliers)*100,
                             color='#fcc72d', edgecolor='black')


axA.set_title("A Container Lengths", fontsize=22)
axA.set_xlabel("Length (km)", fontsize=16)
axA.set_ylabel("Percentage (%)", fontsize=16)
axA.tick_params(axis='both', labelsize=12)
axA.yaxis.grid(True, linestyle=':', color='grey', alpha=0.7)
axA.spines['left'].set_linewidth(1.5)
axA.spines['left'].set_color('black')

# Select 5 x-axis ticks evenly across bins
x_ticks_A = select_ticks(binsA, n_ticks=5)
axA.set_xticks(x_ticks_A)
axA.set_xticklabels([f"{tick:.0f}" for tick in x_ticks_A])  # round to 0 decimals

# -------------------
# Histogram B
# -------------------
countsB, binsB, _ = axB.hist(segment_no_outliers, bins=n_bins,
                             weights=np.ones_like(segment_no_outliers)/len(segment_no_outliers)*100,
                             color='#C09003', edgecolor='black')

axB.set_title("B Segment Lengths", fontsize=22)
axB.set_xlabel("Length (km)", fontsize=16)
axB.set_ylabel("Percentage (%)", fontsize=16)
axB.tick_params(axis='both', labelsize=12)
axB.yaxis.tick_right()
axB.yaxis.set_label_position("right")
axB.yaxis.grid(True, linestyle=':', color='grey', alpha=0.7)
axB.spines['right'].set_linewidth(1.5)
axB.spines['right'].set_color('black')

# Select 5 x-axis ticks evenly across bins
x_ticks_B = select_ticks(binsB, n_ticks=5)
axB.set_xticks(x_ticks_B)
axB.set_xticklabels([f"{tick:.0f}" for tick in x_ticks_B])  # round to 0 decimals

# After plotting both histograms, get the maximum y value
ymax = max(axA.get_ylim()[1], axB.get_ylim()[1])

# Set the same y-limit for both axes
axA.set_ylim(0, ymax)
axB.set_ylim(0, ymax)


plt.tight_layout()
plt.savefig(r"\\tsclient\R\paper3\Figures/histogram_segmentLengths_edge_based_swapping.svg", format="svg", bbox_inches="tight", dpi=300)

plt.show()
#%%
print("Bin width for B:", binsB[1] - binsB[0])
print("Bin width for A:", binsA[1] - binsA[0])

#%% categorizing container length
# Convert to km
container_lengths_unique['container_km'] = (
    container_lengths_unique['container_length'] / 1000
)

# Categorize
bins = [0, 10, 15, 20, 30, 50, 100, float('inf')]
labels = [
    "<10km",
    "10–15km",
    "15–20km",
    "20–30km",
    "30–50km",
    "50–100km",
    ">100km"
]

container_lengths_unique['length_category'] = pd.cut(
    container_lengths_unique['container_km'],
    bins=bins,
    labels=labels
)

# Count per category
category_counts = container_lengths_unique['length_category'].value_counts().sort_index()

print(category_counts)
#%% and in %
# Convert to km
container_lengths_unique['container_km'] = (
    container_lengths_unique['container_length'] / 1000
)

# Categorize
bins = [0, 10, 15, 20, 30, 50, 100, float('inf')]
labels = [
    "<10km",
    "10–15km",
    "15–20km",
    "20–30km",
    "30–50km",
    "50–100km",
    ">100km"
]

container_lengths_unique['length_category'] = pd.cut(
    container_lengths_unique['container_km'],
    bins=bins,
    labels=labels
)

# Count per category
category_counts = container_lengths_unique['length_category'].value_counts().sort_index()

# Convert to percentage
category_percent = (category_counts / category_counts.sum()) * 100

# Optional: round for readability
category_percent = category_percent.round(2)

print(category_percent)

#%%
median_length = container_lengths_unique['container_length'].median()
print("Median container length (meters):", median_length)
print("Median container length (km):", median_length / 1000)


#%% road network coverage
gdf_edges_swppd.osmid_edge
# container id is new final tid
# trajectory sub-segments are tid_subid
# would compare number of points by osmid_edge to raw. by time bin? total?