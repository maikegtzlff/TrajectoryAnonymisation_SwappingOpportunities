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
#t_cswappingl_origsynf_headtailsynf = gpd.read_parquet(r"D:\paper3\Data\ClkSwpSynFilled_uid.parquet")
#t_cswappingl_origsynf_headtailsynf['container_uid'] = t_cswappingl_origsynf_headtailsynf['final_tid_origsynfilled'].str.split('_').str[1]
#print(t_cswappingl_origsynf_headtailsynf['container_uid'].nunique()) # 97, same as before
#print(t_cswappingl_origsynf_headtailsynf.final_tid_origsynfilled.nunique()) # same as before swapping, 19,189

#final with alll attributes is 
t_cswappingl_origsynf_headtailsynf = gpd.read_parquet(r"D:\paper3\Data\ClkSwpSynFilled_uid_length_timestamps_FINAL.parquet")



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

# t_cswappingl_origsynf_headtailsynf = t_cswappingl_origsynf_headtailsynf.sort_values(['final_tid_origsynfilled', 'point_id_global_synfilled'])
t_cswappingl_origsynf_headtailsynf = t_cswappingl_origsynf_headtailsynf.sort_values(['final_tid_origsynfilled', 'point_id_global'])

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



#%% boxplot for traj length of all 6 df
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as path_effects

plt.style.use("ggplot")

#prep df
melted_clean = melted.dropna(subset=['Length_km'])
#datasets = melted_clean['Dataset'].unique()
datasets = ['Baseline', 
            'Edge swapped', 'Split edge swapped', 
            'Intersection swapped', 'Split intersection swapped',
            'Cloaking area swapped']

box_data = [melted_clean.loc[melted_clean['Dataset']==ds, 'Length_km'].values for ds in datasets]

positions = np.arange(len(datasets))

colors = ['#383a6b', '#FDD45F','#FDD45F','#F3B503', '#F3B503','#C09003']

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
ax.set_xticklabels([r"$t_f$", r"$t_{se}$", r"$t_{se}$ split", r"$t_{si}$", r"$t_{si}$ split", r"$t_{sc}$"], fontsize=14)
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
    r"Edge-swapping ($t_{se}$ and $t_{se}$ split)",
    r"Intersection-swapping ($t_{si}$ and $t_{si} split$)",
    r"Cloaking Area-swapping ($t_{sc}$)"
]
patches = [mpatches.Patch(color=colors[i], label=labels[i]) for i in range(len(labels))]
hatch_patch = mpatches.Patch(facecolor='none', edgecolor='black', hatch='//', label='require splitting')
patches.append(hatch_patch)

ax.legend(handles=patches, fontsize=14, loc='upper left', frameon=False)

plt.savefig(r"\\tsclient\R\paper3\Figures/TrajLengthSwapped_all.svg", format="svg", bbox_inches="tight", dpi=300)

plt.tight_layout()
plt.show()

#%% only show split ones on boxplot 
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as path_effects
import numpy as np


#datasets_to_keep = ['Baseline',  'Split edge swapped', 'Split intersection swapped', 'Cloaking area swapped']

#melted_split = melted[melted['Dataset'].isin(datasets_to_keep)].dropna(subset=['Length_km'])
#datasets = melted_split['Dataset'].unique()
datasets = ['Baseline',  'Split edge swapped', 'Split intersection swapped', 'Cloaking area swapped']


box_data = [
    melted_split.loc[melted_split['Dataset']==ds, 'Length_km'].values
    for ds in datasets
]

positions = np.arange(len(datasets))

# Colors for the boxes
colors = ['#383a6b','#FDD45F','#F3B503','#C09003']

# -------------------------
# CREATE BOXPLOT
# -------------------------
fig, ax = plt.subplots(figsize=(10,6))

boxes = ax.boxplot(
    box_data,
    patch_artist=True,
    positions=positions,
    widths=0.6,
    showfliers=False
)

# Set box colors
for i, b in enumerate(boxes['boxes']):
    b.set_facecolor(colors[i])
    b.set_edgecolor('black')
    b.set_linewidth(1.2)

# Median styling
for median in boxes['medians']:
    median.set_color('black')
    median.set_linewidth(1.2)

# Annotate medians
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
        alpha=0.7
    )
    txt.set_path_effects([
        path_effects.Stroke(linewidth=3.5, foreground='white'), 
        path_effects.Normal() 
    ])

# X-axis labels
ax.set_xticks(positions)
ax.set_xticklabels(
    [r"$t_f$", r"$t_{se}$ split", r"$t_{si}$ split", r"$t_{sc}$"],
    fontsize=14
)
ax.set_xlabel("Trajectory swapping approach", fontsize=16, color='#555555')
ax.set_ylabel("Trajectory length (km)", fontsize=16, color='#555555')

# Grid and spines
ax.set_facecolor('white')
ax.grid(False)
ax.yaxis.grid(True, linestyle=':', color='gray', alpha=0.7, zorder=0)
ax.spines['left'].set_visible(True)
ax.spines['left'].set_color('black')
ax.spines['left'].set_linewidth(0.8)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Legend
labels = [
    r"Baseline ($t_f$)",
    r"Edge-swapping ($t_{se}$ split)",
    r"Intersection-swapping ($t_{si} split$)",
    r"Cloaking Area-swapping ($t_{sc}$)"
]
patches = [mpatches.Patch(color=colors[i], label=labels[i]) for i in range(len(labels))]
#ax.legend(handles=patches, fontsize=14, loc='upper right', frameon=False)
ax.legend(
    handles=patches,
    fontsize=14,
    loc='upper center',            # center horizontally
    bbox_to_anchor=(0.5, -0.15),  # position below axes
    ncol=2,                        # two columns → two rows
    frameon=False
)

plt.tight_layout()

plt.savefig(r"\\tsclient\R\paper3\Figures/TrajLengthSwapped_split.svg", format="svg", bbox_inches="tight", dpi=300)

plt.show()


########################################################################

#%%
t_cswappingl_origsynf_headtailsynf.columns
# no time_bin or timesstamp column, must add from t_froSwapping based on point_id_unique

#%% clean up df
pd.set_option('display.max_colwidth', None)
print(t_cswappingl_origsynf_headtailsynf['final_tid'].equals(t_cswappingl_origsynf_headtailsynf['original_tid'])) # false
#t_cswappingl_origsynf_headtailsynf[t_cswappingl_origsynf_headtailsynf['final_tid'] != t_cswappingl_origsynf_headtailsynf['original_tid']][['final_tid', 'original_tid']]
# some final_tid has none, oriinal_tid is also different to final. 
# final is after swapping and not filled with tid ofr syn points yet?
print(t_cswappingl_origsynf_headtailsynf[t_cswappingl_origsynf_headtailsynf['final_tid'] != t_cswappingl_origsynf_headtailsynf['original_tid']]['point_type'].unique())
# ['orig_synthetic' 'swapping_synthetic' None]
t_cswappingl_origsynf_headtailsynf[t_cswappingl_origsynf_headtailsynf['final_tid'] != t_cswappingl_origsynf_headtailsynf['original_tid']][['point_type', 'final_tid', 'original_tid', 'final_tid_origsynfilled']]
# final_tid_origsynfilled is final_tid but with values for the synthetic points

#pd.reset_option('display.max_colwidth')
#%% update column names 
t_cswappingl_origsynf_headtailsynf['container_tid'] = t_cswappingl_origsynf_headtailsynf['final_tid_origsynfilled']


#%% look at uid
t_cswappingl_origsynf_headtailsynf[['point_id_global_synfilled', 'point_id_global', 'point_id_unique']]
# point_id_global_synfilled is the container point id
# point_id_global is shorter
# point_id_global is NOT in t_forSwapping, so this is the point_id after swapping before filling
#%% rename columns
t_cswappingl_origsynf_headtailsynf.rename(columns={'point_id_global': 'point_id_global_beforeFilling'}, inplace=True)
t_cswappingl_origsynf_headtailsynf.rename(columns={'point_id_global_synfilled': 'point_id_global'}, inplace=True)




#%%
t_forSwapping = gpd.read_parquet(r"d:\paper3\Data\t_forSwapping_26723gaps_labelled.parquet")
t_forSwapping.columns
# point_id_unique
# unix_timestamp_final
# hour
# time_bin
# 
#%% 
t_forSwapping = t_forSwapping[['point_id_unique', 'unix_timestamp_final', 'hour', 'time_bin_label', 'time_bin']].copy()
t_forSwapping.head()

#%% merge time bin info to df
# won't have time info for synthetic points
t_cswappingl_origsynf_headtailsynf_temporal = t_cswappingl_origsynf_headtailsynf.merge(t_forSwapping, on='point_id_unique', how='left')
t_cswappingl_origsynf_headtailsynf_temporal

#%%
print(t_cswappingl_origsynf_headtailsynf_temporal.unix_timestamp_final.isna().any())
# True
print(t_cswappingl_origsynf_headtailsynf_temporal.hour.isna().any())
# True
print(t_cswappingl_origsynf_headtailsynf_temporal.time_bin.isna().any())
# True


cols = ['unix_timestamp_final', 'hour', 'time_bin']
na_summary = pd.DataFrame({
    'NA_count': t_cswappingl_origsynf_headtailsynf_temporal[cols].isna().sum(),
    'NA_percent': t_cswappingl_origsynf_headtailsynf_temporal[cols].isna().mean() * 100
})
print(na_summary)

#                      NA_count  NA_percent
#unix_timestamp_final    443867    5.712133
#hour                    443867    5.712133
#time_bin                443867    5.712133

#%% look at the temporal information for the synthetic trajectories connecting heads and tails
t_cswappingl_origsynf_headtailsynf_temporal['time_sec_sinceOrigin'].isna().mean() * 100
#94.31137878670887
#94.31137878670887 + 5.712133 = 100



#%% now look at timestamps after swapping: cloaking areas
df = t_cswappingl_origsynf_headtailsynf_temporal.copy()
# Previous time_bin within container
df['prev_time_bin'] = df.groupby('container_tid')['time_bin'].shift()
# Difference
df['time_bin_diff'] = df['time_bin'] - df['prev_time_bin']
# Flag decreases
df['flag_problem'] = df['time_bin_diff'] < 0
# Remove valid wrap-around (3 -> 0)
#df.loc[(df['prev_time_bin'] == 3) & (df['time_bin'] == 0), 'flag_problem'] = False
df.loc[df['time_bin'] == 0, 'flag_problem'] = False

df[df['flag_problem']] # 4 rows, 4 different container_tids
# all flat_peak (2), prev time bin 3




#%% fix these timebins
print(df[df['flag_problem']].container_tid.unique())

# look at one of them
df_cont = df[df['container_tid'] == '20200422_465b146da7c31336a60ae621318be651e9da3571_5603'].copy()

mask = pd.Series(False, index=df_cont.index)

for shift in range(-5, 6):
    mask |= df_cont['flag_problem'].shift(shift, fill_value=False)

df_context = df_cont[mask]

df_context[['point_type', 'point_id_global', 'point_id_unique', 'active_swap', 'true_pair_id', 'original_tid', 'hour', 'time_bin', 'unix_timestamp_final']]
# going from 16 to 15 o'clock

# NOT AN ACTIVE SWAP, same original tid! hour also goes back to 16
# --> overwrite the hour, timebin columns and remove timesmatp


#%% look at the timestamp!
import pandas as pd

# Example timestamps
unix_ts = [
    1.58830565e+09, 1.58830565e+09, 1.58830565e+09, 1.58830568e+09,
    1.58830568e+09, 1.58830569e+09, 1.58830570e+09, 1.58830571e+09,
    1.58830572e+09, 1.58830572e+09
]

# Convert to pandas datetime in UTC, then convert to Auckland timezone
auckland_ts = pd.to_datetime(unix_ts, unit='s', utc=True).tz_convert('Pacific/Auckland')

print(auckland_ts)

# they are ALL 16, not 15
# DatetimeIndex([   '2020-05-01 16:00:50+12:00', 
#                   '2020-05-01 16:00:50+12:00',
#                   '2020-05-01 16:00:50+12:00', 
#                   '2020-05-01 16:01:20+12:00',
#                   '2020-05-01 16:01:20+12:00', 
#                   '2020-05-01 16:01:30+12:00',
#                   '2020-05-01 16:01:40+12:00', 
#                   '2020-05-01 16:01:50+12:00',
#                   '2020-05-01 16:02:00+12:00', 
#                   '2020-05-01 16:02:00+12:00'],
#              dtype='datetime64[ns, Pacific/Auckland]', freq=None)

#%% look at the timestamp
print(df['unix_timestamp_final'].isna().any()) # true
df['datetime_debug'] = pd.to_datetime(df['unix_timestamp_final'], unit='s', utc=True)
df['datetime_debug'] = df['datetime_debug'].dt.tz_convert('Pacific/Auckland')
print(df['datetime_debug'].isna().any()) # true

#%%
df['hour_debug'] = df['datetime_debug'].dt.hour
print(df['hour_debug'].isna().any()) # true
#%% only get time_bin if hour exists
import numpy as np

def assign_time_bin(hour):
    if pd.isna(hour):
        return np.nan
    elif 7 <= hour < 9:
        return "morning peak"
    elif 9 <= hour < 16:
        return "flat peak"
    elif 16 <= hour < 20:
        return "evening peak"
    else:
        return "night time"

df['time_bin_label_debug'] = df['hour_debug'].apply(assign_time_bin)

mapping = {
    'night time': 0,
    'morning peak': 1,
    'flat peak': 2,
    'evening peak': 3,
}

df['time_bin_debug'] = df['time_bin_label_debug'].map(mapping)


print(df['time_bin_debug'].isna().any()) # True
print(df['time_bin_label_debug'].isna().any())# False
print("Label NaNs:", df['time_bin_label_debug'].isna().sum())
print("Numeric NaNs:", df['time_bin_debug'].isna().sum())


df[['datetime_debug', 'hour_debug', 'time_bin_debug']].head()

#%%
# Previous time_bin within container
df['prev_time_bin_debug'] = df.groupby('container_tid')['time_bin_debug'].shift()
# Difference
df['time_bin_diff_debug'] = df['time_bin_debug'] - df['prev_time_bin_debug']
# Flag decreases
df['flag_problem_debug'] = df['time_bin_diff_debug'] < 0
# Remove valid wrap-around (3 -> 0)
#df.loc[(df['prev_time_bin'] == 3) & (df['time_bin'] == 0), 'flag_problem'] = False
df.loc[df['time_bin_debug'] == 0, 'flag_problem_debug'] = False

df[df['flag_problem_debug']] # 0 rows!

#%% those timestamps to 
df.rename(columns={'unix_timestamp_final': 'unix_timestamp_final_debug'}, inplace=True)
t_cswappingl_origsynf_headtailsynf_temporal = t_cswappingl_origsynf_headtailsynf_temporal.merge(df[['point_id_global', 'hour_debug', 'time_bin_debug', 'time_bin_label_debug', 'unix_timestamp_final_debug']], on ='point_id_global', how='left')
print(t_cswappingl_origsynf_headtailsynf_temporal['unix_timestamp_final'].equals(t_cswappingl_origsynf_headtailsynf_temporal['unix_timestamp_final_debug']))    
t_cswappingl_origsynf_headtailsynf_temporal.head()

#%%
t_cswappingl_origsynf_headtailsynf_temporal[t_cswappingl_origsynf_headtailsynf_temporal['time_sec_sinceOrigin'].notna()][['point_type', 'point_id_global', 'point_id_global_beforeFilling', 
                                                                                                                            'unix_timestamp_final', 'unix_timestamp_final_debug',
                                                                                                                            'hour', 'hour_debug',
                                                                                                                            'time_bin', 'time_bin_debug',
                                                                                                                            'time_bin_label', 'time_bin_label_debug'
                                                                                                                          ]]



#%%
cols_to_check = [
    'unix_timestamp_final', 'unix_timestamp_final_debug',
    'hour', 'hour_debug',
    'time_bin', 'time_bin_debug',
    'time_bin_label', 'time_bin_label_debug'
]

# Subset of the DataFrame where time_sec_sinceOrigin is not NA
df_subset = t_cswappingl_origsynf_headtailsynf_temporal[
    t_cswappingl_origsynf_headtailsynf_temporal['time_sec_sinceOrigin'].notna()
][cols_to_check]

# Check if all values in each column are NaN
all_na = df_subset.isna().all()
print(all_na)

#%%
print(t_cswappingl_origsynf_headtailsynf_temporal['unix_timestamp_final'].equals(t_cswappingl_origsynf_headtailsynf_temporal['unix_timestamp_final_debug'])) 
# TRUE

#%% create one 'timestamp like' column
t_cswappingl_origsynf_headtailsynf_temporal['seconds_to_unixOROrigin'] = np.where(
    t_cswappingl_origsynf_headtailsynf_temporal['unix_timestamp_final'].isna(),
    t_cswappingl_origsynf_headtailsynf_temporal['time_sec_sinceOrigin'],  # use this if unix_timestamp_final is NaN
    t_cswappingl_origsynf_headtailsynf_temporal['unix_timestamp_final']     # else use original unix_timestamp_final
)

t_cswappingl_origsynf_headtailsynf_temporal[['unix_timestamp_final', 'time_sec_sinceOrigin', 'seconds_to_unixOROrigin']]
#%%
cols_to_check2 = [
    'unix_timestamp_final', 'time_sec_sinceOrigin', 'seconds_to_unixOROrigin'
]

# Subset of the DataFrame where time_sec_sinceOrigin is not NA
df_subset2 = t_cswappingl_origsynf_headtailsynf_temporal[
    t_cswappingl_origsynf_headtailsynf_temporal['time_sec_sinceOrigin'].notna()
][cols_to_check2]
df_subset2


#%% now calculate time diff in seconds to previous point as replacement for timestamp
# block identifier for orig_tid, incase orig_tid is repeated (shouldn't be repeated, thiss is a safety measure only)
# how do I handle segment shifts? none for now
t_cswappingl_origsynf_headtailsynf_temporal['orig_tid_block'] = t_cswappingl_origsynf_headtailsynf_temporal.groupby('container_tid')['original_tid'].transform(lambda x: (x != x.shift()).cumsum())
# synthetic points alread have sec from PrevPoints (or is it seconds to next?)
# these will have their own orig_tid (the odid)

t_cswappingl_origsynf_headtailsynf_temporal['sec_fromPrevPoint'] = t_cswappingl_origsynf_headtailsynf_temporal.groupby(['container_tid','orig_tid_block'])['seconds_to_unixOROrigin'].diff()
print(t_cswappingl_origsynf_headtailsynf_temporal.sec_fromPrevPoint.isna().any()) # True, but other dfs have this too (firs/last in container)
t_cswappingl_origsynf_headtailsynf_temporal



#%% get hour for synthetic points from previous point!
# hour_debug
print(t_cswappingl_origsynf_headtailsynf_temporal.hour_debug.isna().any())
# True
t_cswappingl_origsynf_headtailsynf_temporal['hour_debug_filled'] = (
    t_cswappingl_origsynf_headtailsynf_temporal
    .groupby('container_tid')['hour_debug']
    .ffill()
)
print(t_cswappingl_origsynf_headtailsynf_temporal.hour_debug_filled.isna().any()) #False

#%% export df
#t_cswappingl_origsynf_headtailsynf_temporal.to_parquet(r'D:\paper3\Data\ClkSwpSynFilled_uid_length_timestamps_FINAL.parquet')
