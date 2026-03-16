#%% Home detection
import geopandas as gpd
import numpy as np

gdf_edges_swppd = gpd.read_parquet(r"D:\paper3\Data\output/final_points_edgeSwap_FINAL.parquet")

gdf_nodess_swppd = gpd.read_parquet(r"d:\paper3\Data\filled_trajectories_list\trajectories_swapped_nodes_FINAL.parquet")

t_cswappingl_origsynf_headtailsynf = gpd.read_parquet(r"D:\paper3\Data\ClkSwpSynFilled_uid_length_timestamps_FINAL.parquet")

t_cswappingl_origsynf_headtailsynf['container_id'] = t_cswappingl_origsynf_headtailsynf['final_tid_origsynfilled']
t_cswappingl_origsynf_headtailsynf['container_id'] = t_cswappingl_origsynf_headtailsynf['final_tid_origsynfilled']
t_cswappingl_origsynf_headtailsynf['orig_uid'] = t_cswappingl_origsynf_headtailsynf['original_tid'].str.split('_').str[1]
#t_cswappingl_origsynf_headtailsynf.orig_uid.unique() # how to handle synthetic ones> 
t_cswappingl_origsynf_headtailsynf['orig_uid'] = np.where(
    t_cswappingl_origsynf_headtailsynf['orig_uid'] == 'orig',
    t_cswappingl_origsynf_headtailsynf['original_tid'],
    t_cswappingl_origsynf_headtailsynf['orig_uid']
)

#%% must have dateime column
print(gdf_edges_swppd.columns)

# must know timebin breaks
# 7 <= hour < 9:    "morning peak"
# 9 <= hour < 16:   "flat peak"
# 16 <= hour < 20:  "evening peak"
# "night time"

time_bin_start_dict = {
    'night time': 21,
    'morning peak': 7,
    'flat peak': 9,
    'evening peak': 16,
}
# date comes from here container_tid_subid - date is before first _, add to new column
gdf_edges_swppd['time_bin_start'] = gdf_edges_swppd['time_bin_label'].map(time_bin_start_dict)
gdf_edges_swppd['container_date'] = gdf_edges_swppd['container_tid_subid'].str.split('_').str[0].astype(int)
gdf_edges_swppd[['point_id_global', 'container_id', 'time_bin_label', 'sec_fromPrevPoint', 'time_bin_start_dict', 'container_date']]

#%%
gdf_edges_swppd['sec_fromTrajStart'] = (
    gdf_edges_swppd['sec_fromPrevPoint']
    .fillna(0)
    .groupby(gdf_edges_swppd['container_id'])
    .cumsum()
)

gdf_edges_swppd[['point_id_global', 'container_id', 'sec_fromPrevPoint', 'sec_fromTrajStart']]

#%%
gdf_edges_swppd['date_unix_midnight'] = (
    pd.to_datetime(gdf_edges_swppd['container_date'].astype(str), format='%Y%m%d')
    .dt.tz_localize('Pacific/Auckland')
    .astype('int64') // 10**9
)
gdf_edges_swppd[['container_date', 'date_unix_midnight']]

#%%
gdf_edges_swppd['time_bin_start_sec'] = gdf_edges_swppd['time_bin_start'] *3600

gdf_edges_swppd[['container_date', 'date_unix_midnight', 'time_bin_start', 'time_bin_start_sec']]

#%%
gdf_edges_swppd['sec_fromTrajStart'] = gdf_edges_swppd['sec_fromTrajStart'].astype(int)

gdf_edges_swppd['container_unix_timestamp'] = gdf_edges_swppd['date_unix_midnight'] + gdf_edges_swppd['time_bin_start_sec'] + gdf_edges_swppd['sec_fromTrajStart']
gdf_edges_swppd[['container_date', 'container_unix_timestamp', 'time_bin_start', 'date_unix_midnight', 'time_bin_start_sec', 'sec_fromTrajStart']]

#%%
import pandas as pd
gdf_edges_swppd['container_datetime'] = pd.to_datetime(
    gdf_edges_swppd['container_unix_timestamp'], unit='s', utc=True
).dt.tz_convert('Pacific/Auckland')

gdf_edges_swppd[[ 'container_datetime', 'container_date', 'time_bin_start']]



#%% identify stop points, cluster to find locations, rank to determine significance

#%% have locations at rank 1 and 2 changed?


#%% what timestamp information do I need for Stop Detection (movingpandas)

#%% create timestamps

# must set trheshold for stop detection (seconds andmax diameter, look at chapter 1)