#%% load libaries and data
import geopandas as gpd
import pandas as pd
import numpy as np

# baseline: cloaked and filled trajetcories (paper 2)
t_p2 = gpd.read_parquet(r'\\tsclient\R\paper3\filledtrajectories_gdfenriched2\traj_filled_baseline_ShiftedTimestamps_gapAware_CloakingGeomID_AllCloakingAreas_clean.parquet')


# swapped trajectories
# (1) edge swapped
gdf_edges_swppd = gpd.read_parquet(r"D:\paper3\Data\output/final_points_edgeSwap_FINAL.parquet")
#  'sub_container_id' because split


#%% (2) intersection swapped
gdf_nodess_swppd = gpd.read_parquet(r"d:\paper3\Data\filled_trajectories_list\trajectories_swapped_nodes_FINAL.parquet")
# sub_container_id is the split trajectory identifier with shorter lengths
# fix typo
#gdf_nodess_swppd.rename(columns={'conteiner_uid': 'container_uid'}, inplace=True)

# (3) cloaking geometry swapped
t_cswappingl_origsynf_headtailsynf = gpd.read_parquet(r"D:\paper3\Data\ClkSwpSynFilled_uid.parquet")
#t_cswappingl_origsynf_headtailsynf['container_uid'] = t_cswappingl_origsynf_headtailsynf['final_tid_origsynfilled'].str.split('_').str[1]
#print(t_cswappingl_origsynf_headtailsynf['container_uid'].nunique()) # 97, same as before
#print(t_cswappingl_origsynf_headtailsynf.final_tid_origsynfilled.nunique()) # same as before swapping, 19,189





#%% Distribution of number of points by user
counts_baseline = t_p2.groupby('uid').size()
counts_intersectionS = gdf_nodess_swppd.groupby('container_uid').size()
counts_edgeS = gdf_edges_swppd.groupby('container_uid').size()
counts_cloakingS = t_cswappingl_origsynf_headtailsynf.groupby('container_uid').size()

summary_df = pd.DataFrame({
    'counts_baseline': counts_baseline.describe().round(0),
    'counts_intersectionS': counts_intersectionS.describe().round(0),
    'counts_edgeS': counts_edgeS.describe().round(0),
    'counts_cloakingS': counts_cloakingS.describe().round(0)
})

print(summary_df)


#counts_baseline  counts_intersectionS  counts_edgeS  counts_cloakingS
#count             97.0                  97.0          97.0              97.0
#mean           75618.0               75618.0       75618.0           80109.0
#std            63413.0               43047.0       41888.0           53103.0
#min             1995.0                5000.0        5808.0            2518.0
#25%            31696.0               43503.0       49587.0           38580.0
#50%            57225.0               69076.0       70739.0           71446.0
#75%            99526.0              103364.0      101387.0          111535.0
#max           370379.0              213270.0      206163.0          217971.0

# average (mean) number of points by (new) is the same for intersection and edge based swapping as for baseline, but slightly higher for cloaking based swapping
# --> cloaking based swapping slightly increases the number per container. why? because we add synthetic points to connect heads and tails
# std: swapping leads to lower std values --> less variability in container length
# smallest vs larges container (i.e., extremes): swapping reduces max container length amd increases minimum (intersection and edge based more than cloaked)
# median number of points by container increases by swapping
# swapping maintains skew of baseline

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# Prepare the data
summary_data = pd.DataFrame({
    'Baseline': counts_baseline,
    'Intersection S': counts_intersectionS,
    'Edge S': counts_edgeS,
    'Cloaking S': counts_cloakingS
})

# Melt to long format for seaborn
melted = summary_data.melt(var_name='Dataset', value_name='Count')

# Plot
plt.figure(figsize=(10,6))
sns.boxplot(x='Dataset', y='Count', data=melted, palette=['#383a6b','#FDD45F','#F3B503','#C09003'], showfliers=True)
plt.yscale('log')  # optional, because you have large outliers
plt.ylabel("Trajectory points per container (log scale)")
plt.title("Comparison of container sizes by trajectory anonymisation method")
plt.show()



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
raw_nodess_swppd_length = gdf_nodess_swppd.groupby('container_id')['segment_length_m'].sum().reset_index()
raw_nodess_swppd_length.rename(columns={'segment_length_m':'total_length_m'}, inplace=True)

split_nodess_swppd_length = gdf_nodess_swppd.groupby('sub_container_id')['segment_length_m'].sum().reset_index()
split_nodess_swppd_length.rename(columns={'segment_length_m':'total_length_m'}, inplace=True)

raw_edges_swppd_length = gdf_edges_swppd.groupby('container_id')['segment_length_m'].sum().reset_index()
raw_edges_swppd_length.rename(columns={'segment_length_m':'total_length_m'}, inplace=True)

split_edges_swppd_length = gdf_edges_swppd.groupby('sub_container_id')['segment_length_m'].sum().reset_index()
split_edges_swppd_length.rename(columns={'segment_length_m':'total_length_m'}, inplace=True)



t_p2_length_km = t_p2_length['total_length_m'] / 1000

raw_nodess_swppd_length_km = raw_nodess_swppd_length['total_length_m'] / 1000
split_nodess_swppd_length_km = split_nodess_swppd_length['total_length_m'] / 1000

raw_edges_swppd_length_km = raw_edges_swppd_length['total_length_m'] / 1000
split_edges_swppd_length_km = split_edges_swppd_length['total_length_m'] / 1000

t_cswappingl_origsynf_headtailsynf_length_km = t_cswappingl_origsynf_headtailsynf_length['total_length_m'] / 1000

#%% stats
from scipy.stats import ks_2samp

pairs = [(t_p2_length_km, raw_nodess_swppd_length_km),
         (t_p2_length_km, split_nodess_swppd_length_km),
         
         (t_p2_length_km, raw_edges_swppd_length_km),
         (t_p2_length_km, split_edges_swppd_length_km),


         (t_p2_length_km, t_cswappingl_origsynf_headtailsynf_length_km)
         ]
for i,(a,b) in enumerate(pairs):
    stat,p = ks_2samp(a,b)
    print(f"Pair {i+1}: KS stat={stat:.3f}, p-value={p:.3e}")

# Kolmogorov–Smirnov refresher
# maximum difference between cumulative distributions
# 0 distributions similar
# 1 distributions different

#t_p2_length_km, raw_nodess_swppd_length_km:    KS stat=0.706, p-value=0.000e+00 --> very large KS = substantially different trajectory lengths
#t_p2_length_km, split_nodess_swppd_length_km:  KS stat=0.423, p-value=0.000e+00 --> KS decreases, still moderately different (p significant)

#t_p2_length_km, raw_edges_swppd_length_km:     KS stat=0.164, p-value=8.164e-226 --> moderte KS = some differences, less extreme as in nodes swapping - p exterelemy small
#t_p2_length_km, split_edges_swppd_length_km:   KS stat=0.423, p-value=0.000e+00   -- KS acctually increases but p value 

#t_p2_length_km, t_cswappingl_origsynf_headtailsynf_length_km:  KS stat=0.019, p-value=2.137e-03 --> distributions almost identical (expected, limited swapping opportunities - p small becasue of large sample size)
# differences can be xplained based on number of swapping opportunities 



#%%bopxlt
combined = pd.concat([
    t_p2_length_km.rename("Baseline"),

    raw_nodess_swppd_length_km.rename("Intersection swapped"),
    split_nodess_swppd_length_km.rename("Split intersection swapped"),

    raw_edges_swppd_length_km.rename("Edge swapped"),
    split_edges_swppd_length_km.rename("Split edge swapped"),

    t_cswappingl_origsynf_headtailsynf_length_km.rename("Cloaking area swapped")
], axis=1)

melted = combined.melt(var_name="Dataset", value_name="Length_km")



# %%
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as path_effects


plt.style.use("ggplot")

#prep df
melted_clean = melted.dropna(subset=['Length_km'])
datasets = melted_clean['Dataset'].unique()
box_data = [melted_clean.loc[melted_clean['Dataset']==ds, 'Length_km'].values for ds in datasets]

positions = np.arange(len(datasets))

colors = ['#383a6b','#FDD45F','#FDD45F','#F3B503', '#F3B503','#C09003']

# boxplot
fig, ax = plt.subplots(figsize=(10,6))

boxes = ax.boxplot(box_data, patch_artist=True, positions=positions, widths=0.6, showfliers=False)
# 2nd and 4th box hatched
for i, b in enumerate(boxes['boxes']):
    b.set_facecolor(colors[i % len(colors)])
    b.set_edgecolor('black')
    b.set_linewidth(1.2)
    #if i == 1:  # hatch only the second box
    if i in [1,3]:
        b.set_hatch('//')
# annotate medians
for median in boxes['medians']:
    median.set_color('black')
    median.set_linewidth(1.2)
for i, medline in enumerate(boxes['medians']):
    median_val = medline.get_ydata()[0]
    txt = ax.text(
        x=positions[i],
        y=median_val,
        s=f"{median_val:.1f}",
        ha='center',
        va='bottom',
        fontsize=12,
        color='black',
        #fontweight='bold',
        alpha=0.7
    )
    txt.set_path_effects([
        path_effects.Stroke(linewidth=3.5, foreground='white'), 
        path_effects.Normal() 
    ])

ax.set_xticks(positions)
ax.set_xticklabels([r"$t_f$", r"$t_{si}$", r"$t_{si}$ split", r"$t_{se}$", r"$t_{se}$ split", r"$t_{sc}$"], fontsize=14)
ax.set_xlabel("Trajectory swapping approach", fontsize=16, color='#555555')
ax.set_ylabel("Trajectory length (km)", fontsize=16, color='#555555')

ax.set_facecolor('white')
ax.grid(False)
ax.yaxis.grid(True, linestyle=':', color='gray', alpha=0.7, zorder=0)
ax.spines['left'].set_visible(True)
ax.spines['left'].set_color('black')
ax.spines['left'].set_linewidth(0.8)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

labels = [
    r"Baseline ($t_f$)",
    r"Intersection-swapping ($t_{si}$ and $t_{si} split$)",
    r"Edge-swapping ($t_{se}$ and $t_{se}$ split)",
    r"Cloaking Area-swapping ($t_{sc}$)"
]
patches = [mpatches.Patch(color=colors[i], label=labels[i]) for i in range(len(labels))]
hatch_patch = mpatches.Patch(facecolor='none', edgecolor='black', hatch='//', label='require splitting')
patches.append(hatch_patch)

ax.legend(handles=patches, fontsize=14, loc='upper right', frameon=False)

plt.savefig(r"\\tsclient\R\paper3\Figures/TrajLengthSwapped_split.svg", format="svg", bbox_inches="tight", dpi=300)

plt.tight_layout()
plt.show()







########################################################################

#%%
t_cswappingl_origsynf_headtailsynf.columns
# no time_bin or timesstamp column, must add from t_froSwapping based on point_id_unique
#%% now look at timestamps after swapping: cloaking areas
df = t_cswappingl_origsynf_headtailsynf.copy()
# Previous time_bin within container
df['prev_time_bin'] = df.groupby('final_tid_origsynfilled')['time_bin'].shift()
# Difference
df['time_bin_diff'] = df['time_bin'] - df['prev_time_bin']
# Flag decreases
df['flag_problem'] = df['time_bin_diff'] < 0
# Remove valid wrap-around (3 -> 0)
#df.loc[(df['prev_time_bin'] == 3) & (df['time_bin'] == 0), 'flag_problem'] = False
df.loc[df['time_bin'] == 0, 'flag_problem'] = False

df[df['flag_problem']] # NO JUMPS IN TIME BINS, when taking gaps in sparse trajectories into account 
# (i.e., a sparse trajectory can record a point in time bin  2, skips 3, goes directly to 0. 0 is the night time time bin (to early morning))
# hence any 'decrease' to 0 is acceptable

#%% now calculate time diff in seconds to previous point as replacement for timestamp
# block identifier for orig_tid, incase orig_tid is repeated (shouldn't be repeated, thiss is a safety measure only)
# how do I handle segment shifts? none for now
t_cswappingl_origsynf_headtailsynf['orig_tid_block'] = t_cswappingl_origsynf_headtailsynf.groupby('final_tid_origsynfilled')['original_tid'].transform(lambda x: (x != x.shift()).cumsum())
t_cswappingl_origsynf_headtailsynf['sec_fromPrevPoint'] = t_cswappingl_origsynf_headtailsynf.groupby(['final_tid_origsynfilled','orig_tid_block'])['unix_timestamp_afterCloaking'].diff()
t_cswappingl_origsynf_headtailsynf