#%% load libaries and data
import geopandas as gpd
import pandas as pd
import numpy as np

# baseline: cloaked and filled trajetcories (paper 2)
t_p2 = gpd.read_parquet(r'\\tsclient\R\paper3\filledtrajectories_gdfenriched2\traj_filled_baseline_ShiftedTimestamps_gapAware_CloakingGeomID_AllCloakingAreas_clean.parquet')

# swapped trajectories
# (1) edge swapped
gdf_edges_swppd = gpd.read_parquet(r"d:\paper3\Data\output\FinalSwappingForEvaluationFigures\final_points_edgeSwap_tidLength.parquet")
#  'container_id', 'orig_tid', 'orig_uid', 'container_segment_tid', 'traj_length_container_segment', 'container_length'

# (2) intersection swapped
gdf_nodess_swppd = gpd.read_parquet(r"d:\paper3\Data\output\FinalSwappingForEvaluationFigures\trajectories_swapped_nodes_NoKeySetReadable_length.parquet")
# container_id - tid after swapping
# print ((gdf_nodess_swppd['orig_tid'] == gdf_nodess_swppd['tid_subid']).any()) # TRUE
# tid_subid, orig_tid - orig tid, now segmented
# container_segment_tid? 
# container_length, traj_length_container_segment

# (3) cloaking geometry swapped
t_cswappingl_origsynf_headtailsynf = gpd.read_parquet(r"D:\paper3\Data\ClkSwpSynFilled_uid.parquet")
#t_cswappingl_origsynf_headtailsynf['final_uid'] = t_cswappingl_origsynf_headtailsynf['final_tid_origsynfilled'].str.split('_').str[1]
print(t_cswappingl_origsynf_headtailsynf['final_uid'].nunique()) # 97, same as before
print(t_cswappingl_origsynf_headtailsynf.final_tid_origsynfilled.nunique()) # same as before swapping, 19,189


#%% Distribution of number of points by user
counts_baseline = t_p2.groupby('uid').size()
#counts_edgeS = gdf_edges_swppd.groupby('orig_uid').size()
#counts_intersectionS = gdf_nodess_swppd.groupby('uid').size()
counts_cloakingS = t_cswappingl_origsynf_headtailsynf.groupby('final_uid').size()

summary_df = pd.DataFrame({
    'counts_baseline': counts_baseline.describe(),
    #'counts_edgeS': counts_edgeS.describe(),
    #'counts_intersectionS': counts_intersectionS.describe(),
    'counts_cloakingS': counts_cloakingS.describe()
})

print(summary_df)
#counts_baseline   counts_edgeS  counts_intersectionS  counts_cloakingS
#count        97.000000      97.000000             97.000000         97.000000
#mean      75617.948454   75617.948454          75617.948454      80109.278351
#std       63413.168718   63413.168718          63413.168718      53102.829887
#min        1995.000000    1995.000000           1995.000000       2518.000000
#25%       31696.000000   31696.000000          31696.000000      38580.000000
#50%       57225.000000   57225.000000          57225.000000      71446.000000
#75%       99526.000000   99526.000000          99526.000000     111535.000000
#max      370379.000000  370379.000000         370379.000000     217971.000000

# for edge and intersection swapping the number of points by user is the same as for the baseline
# that is because this must be the original user we are looking at, uid

# cant do this for edge and node based swapping as I did not create a new uid
# could assume that the first tid in a conatiner is the tid that dictates the uid

#%% edge and intersection based swapping outcomes also dont have a point id I could sort by
# points are in correct order witin their containers, and df is sorted by container
# i.e., dfs are currently in the corect order
# index is not mixed up
# use index to create a point id
gdf_edges_swppd = gdf_edges_swppd.reset_index().rename(columns={'index': 'point_id_global'})
gdf_nodess_swppd = gdf_nodess_swppd.reset_index().rename(columns={'index': 'point_id_global'})

#%% trajectory length
# what is the median, mean and std before swapping? max/min
# these lengths are not based on the road network

#%% must calculate trajectory lengths first
if t_p2.crs.to_epsg() != 2193:  
    print("ransforming to EPSG:2193")
    t_p2 = t_p2.to_crs(epsg=2193)

t_p2 = t_p2.sort_values(['tid_subid', 'row_uid'])

t_p2['prev_geom'] = t_p2.groupby('tid_subid')['match_geometry'].shift(1)

t_p2['segment_length_m'] = t_p2.geometry.distance(t_p2['prev_geom'])
t_p2['segment_length_m'] = t_p2['segment_length_m'].fillna(0)
t_p2_length = t_p2.groupby('tid_subid')['segment_length_m'].sum().reset_index()
t_p2_length.rename(columns={'segment_length_m':'total_length_m'}, inplace=True)

t_p2_length.head()

#%% calc length for swapped dfs
# edges
if gdf_edges_swppd.crs.to_epsg() != 2193:  
    print("ransforming to EPSG:2193")
    gdf_edges_swppd = gdf_edges_swppd.to_crs(epsg=2193)

gdf_edges_swppd = gdf_edges_swppd.sort_values(['container_id', 'point_id_global'])

gdf_edges_swppd['prev_geom'] = gdf_edges_swppd.groupby('container_id')['geometry'].shift(1)

gdf_edges_swppd['segment_length_m'] = gdf_edges_swppd.geometry.distance(gdf_edges_swppd['prev_geom'])
gdf_edges_swppd['segment_length_m'] = gdf_edges_swppd['segment_length_m'].fillna(0)
gdf_edges_swppd_length = gdf_edges_swppd.groupby('container_id')['segment_length_m'].sum().reset_index()
gdf_edges_swppd_length.rename(columns={'segment_length_m':'total_length_m'}, inplace=True)


#%% intersection
if gdf_nodess_swppd.crs.to_epsg() != 2193:  
    print("ransforming to EPSG:2193")
    gdf_nodess_swppd = gdf_nodess_swppd.to_crs(epsg=2193)

gdf_nodess_swppd = gdf_nodess_swppd.sort_values(['container_id', 'point_id_global'])

gdf_nodess_swppd['prev_geom'] = gdf_nodess_swppd.groupby('container_id')['geometry'].shift(1)

gdf_nodess_swppd['segment_length_m'] = gdf_nodess_swppd.geometry.distance(gdf_nodess_swppd['prev_geom'])
gdf_nodess_swppd['segment_length_m'] = gdf_nodess_swppd['segment_length_m'].fillna(0)
gdf_nodess_swppd_length = gdf_nodess_swppd.groupby('container_id')['segment_length_m'].sum().reset_index()
gdf_nodess_swppd_length.rename(columns={'segment_length_m':'total_length_m'}, inplace=True)

gdf_nodess_swppd_length.head()

#%% same for swapped trajectories
if t_cswappingl_origsynf_headtailsynf.crs.to_epsg() != 2193:  
    print("ransforming to EPSG:2193")
    t_cswappingl_origsynf_headtailsynf = t_cswappingl_origsynf_headtailsynf.to_crs(epsg=2193)

t_cswappingl_origsynf_headtailsynf = t_cswappingl_origsynf_headtailsynf.sort_values(['final_tid_origsynfilled', 'point_id_global_synfilled'])

t_cswappingl_origsynf_headtailsynf['prev_geom'] = t_cswappingl_origsynf_headtailsynf.groupby('final_tid_origsynfilled')['match_geometry'].shift(1)

t_cswappingl_origsynf_headtailsynf['segment_length_m'] = t_cswappingl_origsynf_headtailsynf.geometry.distance(t_cswappingl_origsynf_headtailsynf['prev_geom'])
t_cswappingl_origsynf_headtailsynf['segment_length_m'] = t_cswappingl_origsynf_headtailsynf['segment_length_m'].fillna(0)
t_cswappingl_origsynf_headtailsynf_length = t_cswappingl_origsynf_headtailsynf.groupby('final_tid_origsynfilled')['segment_length_m'].sum().reset_index()
t_cswappingl_origsynf_headtailsynf_length.rename(columns={'segment_length_m':'total_length_m'}, inplace=True)

t_cswappingl_origsynf_headtailsynf_length.head()

#%%
t_p2_length_km = t_p2_length['total_length_m'] / 1000
gdf_nodess_swppd_length_km = gdf_nodess_swppd_length['total_length_m'] / 1000
gdf_edges_swppd_length_km = gdf_edges_swppd_length['total_length_m'] / 1000
t_cswappingl_origsynf_headtailsynf_length_km = t_cswappingl_origsynf_headtailsynf_length['total_length_m'] / 1000

#%% stats
from scipy.stats import ks_2samp

pairs = [(t_p2_length_km, gdf_nodess_swppd_length_km),
         (t_p2_length_km, gdf_edges_swppd_length_km),
         (t_p2_length_km, t_cswappingl_origsynf_headtailsynf_length_km),

         #(gdf_nodess_swppd_length_km, gdf_edges_swppd_length_km),                      # KS stat=0.783, p-value=0.000e+00
         #(gdf_nodess_swppd_length_km, t_cswappingl_origsynf_headtailsynf_length_km),   # KS stat=0.708, p-value=0.000e+00
         #(gdf_edges_swppd_length_km, t_cswappingl_origsynf_headtailsynf_length_km)     # KS stat=0.151, p-value=1.438e-192
         ]
for i,(a,b) in enumerate(pairs):
    stat,p = ks_2samp(a,b)
    print(f"Pair {i+1}: KS stat={stat:.3f}, p-value={p:.3e}")

# Kolmogorov–Smirnov refresher
# maximum difference between cumulative distributions
# 0 distributions similar
# 1 distributions different

#t_p2_length_km, gdf_nodess_swppd_length_km:                    KS stat=0.706, p-value=0.000e+00 --> very large KS = substantially different trajectory lengths
#t_p2_length_km, gdf_edges_swppd_length_km:                     KS stat=0.164, p-value=8.164e-226 --> moderte KS = some differences, less extreme as in nodes swapping
#t_p2_length_km, t_cswappingl_origsynf_headtailsynf_length_km:  KS stat=0.019, p-value=2.137e-03 --> distributions almost identical (expected, limited swapping opportunities - p small becasue of large sample size)
# differences can be xplained based on number of swapping opportunities 



#%%bopxlt
combined = pd.concat([
    t_p2_length_km.rename("Baseline"),
    gdf_nodess_swppd_length_km.rename("Intersection swapped"),
    gdf_edges_swppd_length_km.rename("Edge swapped"),
    t_cswappingl_origsynf_headtailsynf_length_km.rename("Cloaking area swapped")
], axis=1)

melted = combined.melt(var_name="Dataset", value_name="Length_km")
#%%
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Use ggplot style globally
plt.style.use("ggplot")

# Your palette
colors = ['#383a6b','#FDD45F','#F3B503','#C09003']

# Create figure and axis
fig, ax = plt.subplots(figsize=(10,6))

# Boxplot
sns.boxplot(
    x="Dataset",
    y="Length_km",
    data=melted,
    palette=colors,
    width=0.6,
    fliersize=0,
    showfliers=False,
    ax=ax
)

# White background
ax.set_facecolor('white')

# Hide default grid, add horizontal dotted grid lines
ax.grid(False)
ax.yaxis.grid(True, linestyle=':', color='gray', alpha=0.7, zorder=0)

# Solid y-axis line
ax.spines['left'].set_visible(True)
ax.spines['left'].set_color('black')
ax.spines['left'].set_linewidth(0.8)

# Hide top and right spines
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Annotate median values
datasets_unique = melted['Dataset'].unique()
for i, dataset_name in enumerate(datasets_unique):
    median_val = melted.loc[melted['Dataset']==dataset_name, 'Length_km'].median()
    ax.text(
        x=i,
        y=median_val,
        s=f"{median_val:.1f}",  
        color='black',
        fontsize=10,
        ha='center',
        va='bottom',
        alpha=0.7
    )

# Custom x-axis labels with LaTeX
ax.set_xticklabels([r"$t_f$", r"$t_{si}$", r"$t_{se}$", r"$t_{sc}$"])
ax.set_xlabel("Trajectory anonymisation approach", fontsize=14, color='#555555')

# Labels and title
ax.set_ylabel("Trajectory length (km)", fontsize=14, color='#555555')

# add legend
import matplotlib.patches as mpatches

labels = [r"Baseline ($t_f$)", r"Intersection-swapping ($t_{si}$)", r"Edge-swapping ($t_{se}$)", r"Cloaking Area-swapping ($t_{sc}$)"]
colors = ['#383a6b','#FDD45F','#F3B503','#C09003']
patches = [mpatches.Patch(color=colors[i], label=labels[i]) for i in range(len(labels))]
ax.legend(handles=patches, fontsize=12, loc='upper right', frameon=False)

plt.savefig(r"\\tsclient\R\paper3\Figures/TrajLengthSwapped.svg", format="svg", bbox_inches="tight", dpi=300)

plt.show()


#%% split the tid of the swapped df by artificially adding tids
# Compute describe for each
desc_t_p2 = t_p2_length_km.describe()
desc_gdf_nodes = gdf_nodess_swppd_length_km.describe()
desc_gdf_edges = gdf_edges_swppd_length_km.describe()
desc_cswapping = t_cswappingl_origsynf_headtailsynf_length_km.describe()

# Combine into single DataFrame
summary_df = pd.DataFrame({
    'Cloaked & filled': desc_t_p2,
    'Nodes Swapped': desc_gdf_nodes,
    'Edges Swapped': desc_gdf_edges,
    'Swapped within cloaking geometry': desc_cswapping
})

print(summary_df)
# Census and household surveys for Auckland: average 30km daily,
# individual trip lengths is shorter (~10km when travelling by car)
# outer districts have longer trip lengths
# this mathces our 25% to 50%, with the mean being a little high, of the baseline. remember, baseline is the 100 most active users in the sample

#%% make sure that both segments of the split tid have reasonable lengths
# split intersection based swapping first
min_len = 10000   # 10 km
max_len = 45000   # 45 km

gdf_nodess_swppd = gdf_nodess_swppd.sort_values(['container_id','point_id_global']).copy()

# cumulative distance for each container
gdf_nodess_swppd['traj_length_container_segment'] = gdf_nodess_swppd.groupby('container_id')['segment_length_m'].cumsum()

container_total = gdf_nodess_swppd.groupby('container_id')['segment_length_m'].sum()

gdf_nodess_swppd['sub_container_id'] = gdf_nodess_swppd['container_id']

for cid, total_len in container_total.items():

    if total_len <= max_len:
        continue  # no splitting needed

    mask = gdf_nodess_swppd['container_id'] == cid
    cum = gdf_nodess_swppd.loc[mask,'traj_length_container_segment'].values

    splits = []
    current = 0

    # dynamically handle leftover distances after splitting
    while True:
        remaining = total_len - current

        # If remaining distance fits within [min_len, max_len], make it the last segment
        if min_len <= remaining <= max_len:
            splits.append(total_len)
            break

        # If remaining is smaller than min_len, extend previous segment
        if remaining < min_len:
            if splits:
                splits[-1] = total_len
            else:
                splits.append(total_len)
            break

        # Otherwise, create a random segment within min–max
        step = np.random.uniform(min_len, max_len)
        current += step

        # If step overshoots remaining distance, cap it
        if current > total_len:
            current = total_len

        splits.append(current)

    # Assign sub_container IDs
    segment_ids = np.searchsorted(splits, cum)
    gdf_nodess_swppd.loc[mask,'sub_container_id'] = [
        f"{cid}_{i+1}" for i in segment_ids
    ]

# sub_conatiner_id have _ after main container id, if main container was split
# otherwise sub_container_id == main_container, i.e. not split --> this explains lengths under 10km
# must treat all as string
gdf_nodess_swppd['sub_container_id'] = gdf_nodess_swppd['sub_container_id'].astype(str) 

gdf_nodess_swppd


#%%
print(gdf_nodess_swppd.groupby('sub_container_id')['container_id'].nunique().max()) # 1, didn't mix across containers (good)

segment_lengths = (
    gdf_nodess_swppd
    .groupby('sub_container_id')['segment_length_m']
    .sum()
)
segment_lengths.describe()

#%% add split length back to df
segment_lengths_df = segment_lengths.reset_index()
segment_lengths_df.rename(
    columns={'segment_length_m':'sub_container_total_length_m'},
    inplace=True
)

gdf_nodess_swppd = gdf_nodess_swppd.merge(
    segment_lengths_df,
    on='sub_container_id',
    how='left'
)
gdf_nodess_swppd['sub_container_total_length_km'] = round(gdf_nodess_swppd['sub_container_total_length_m']/1000,2)
gdf_nodess_swppd.head()

#%%
gdf_nodess_swppd.to_parquet(r"d:\paper3\Data\output\FinalSwappingForEvaluationFigures\trajectories_swapped_nodes_NoKeySetReadable_IntersectionSwappedTrajSplitForLength.parquet")
#%%
gdf_nodess_swppd = gpd.read_parquet(r"d:\paper3\Data\output\FinalSwappingForEvaluationFigures\trajectories_swapped_nodes_NoKeySetReadable_IntersectionSwappedTrajSplitForLength.parquet")
gdf_nodess_swppd.head()

#%% edge-based
gdf_edges_swppd = gdf_edges_swppd.sort_values(['container_id','point_id_global']).copy()

# cumulative distance for each container
gdf_edges_swppd['traj_length_container_segment'] = gdf_edges_swppd.groupby('container_id')['segment_length_m'].cumsum()

container_total = gdf_edges_swppd.groupby('container_id')['segment_length_m'].sum()

gdf_edges_swppd['sub_container_id'] = gdf_edges_swppd['container_id']

for cid, total_len in container_total.items():

    if total_len <= max_len:
        continue  # no splitting needed

    mask = gdf_edges_swppd['container_id'] == cid
    cum = gdf_edges_swppd.loc[mask,'traj_length_container_segment'].values

    splits = []
    current = 0

    # dynamically handle leftover distances after splitting
    while True:
        remaining = total_len - current

        # If remaining distance fits within [min_len, max_len], make it the last segment
        if min_len <= remaining <= max_len:
            splits.append(total_len)
            break

        # If remaining is smaller than min_len, extend previous segment
        if remaining < min_len:
            if splits:
                splits[-1] = total_len
            else:
                splits.append(total_len)
            break

        # Otherwise, create a random segment within min–max
        step = np.random.uniform(min_len, max_len)
        current += step

        # If step overshoots remaining distance, cap it
        if current > total_len:
            current = total_len

        splits.append(current)

    # Assign sub_container IDs
    segment_ids = np.searchsorted(splits, cum)
    gdf_edges_swppd.loc[mask,'sub_container_id'] = [
        f"{cid}_{i+1}" for i in segment_ids
    ]

# sub_conatiner_id have _ after main container id, if main container was split
# otherwise sub_container_id == main_container, i.e. not split --> this explains lengths under 10km
# must treat all as string
gdf_edges_swppd['sub_container_id'] = gdf_edges_swppd['sub_container_id'].astype(str) 

gdf_edges_swppd

#%%
print(gdf_edges_swppd.groupby('sub_container_id')['container_id'].nunique().max()) # 1, didn't mix across containers (good)

segment_lengths = (
    gdf_edges_swppd
    .groupby('sub_container_id')['segment_length_m']
    .sum()
)
segment_lengths.describe()

#%%
segment_lengths_df = segment_lengths.reset_index()
segment_lengths_df.rename(
    columns={'segment_length_m':'sub_container_total_length_m'},
    inplace=True
)

gdf_edges_swppd = gdf_edges_swppd.merge(
    segment_lengths_df,
    on='sub_container_id',
    how='left'
)
gdf_edges_swppd['sub_container_total_length_km'] = round(gdf_edges_swppd['sub_container_total_length_m']/1000,2)
gdf_edges_swppd.head()

#%% export 
gdf_edges_swppd.to_parquet(r"d:\paper3\Data\output\FinalSwappingForEvaluationFigures\final_points_edgeSwap_tidLength_EdgeSwappedTrajSplitForLength.parquet")

#%% recalculate df length stats based on new split container_id

#%% timestamps: fix after splitting trajectories