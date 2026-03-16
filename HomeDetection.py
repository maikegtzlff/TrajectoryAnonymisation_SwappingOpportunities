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




#%% MovingPandas for StopDection
import movingpandas as mpd

edges_traj_collection = mpd.TrajectoryCollection(
    gdf_edges_swppd,
    traj_id_col='sub_container_id',
    t='container_datetime'
)


#%% stop detection
from datetime import datetime, timedelta
# 3 minutes, 65meters - based on chapter 1 parameters
detector = mpd.TrajectoryStopDetector(edges_traj_collection)
stop_points = detector.get_stop_points(
    min_duration=timedelta(seconds=180), max_diameter=65
)
len(stop_points)
# ran for 153 nminutes 
# 114,895 stop points detected
#%%

#%% fake time stamps might eaxagurate long stays - maybe not, maybe I'm overthinking. time stamps are based on seconds to previous point.
# changed in time_bin might lead to artificially long stops, i.e., start of stop in time bin one, then a differnet time bin at the end of the stop, but fake timestamps are based on the start of the the time bin
print(stop_points.duration_s.min())
print(stop_points.duration_s.median()/60)   # minutes
print(stop_points.duration_s.max()/3600)    # hours

# min stop: 180 seconds, the threshold I set
# median stop: 12 minutes
# maximum stop duration 30 hours.... see comment above

#%% add attributes to stop points
stop_points = stop_points.reset_index(drop=False)
stop_points
#%% map uid
#gdf_edges_swppd.columns
stop_points = stop_points.merge(gdf_edges_swppd[['sub_container_id', 'container_tid_subid', 'container_uid']], left_on = 'traj_id', right_on = 'sub_container_id', how='left')
stop_points.head()

#%%
stop_points.to_parquet(r"D:\paper3\Data\output\Evaluation_HomeDetection/edgeSwapped_split_StopPoints.parquet")



#%%
import os
print(os.getcwd())
os.chdir(r"E:\paper3")
print(os.getcwd())

import geopandas as gpd
stop_points = gpd.read_parquet(r"e:\paper3\data\HomeDetection\edgeSwapped_split_StopPoints.parquet")


#%% clusteirng stops using DBSCAN in scikit-learn
# distance 60m, 4 stops
import s_clustering_final as cstp
stop_points.rename(columns={'container_uid': 'uid'}, inplace=True)

print('start clustering')
stop_points_ranked = cstp.get_ranked_clusters(stop_points, 60, 4)

# rank cluster basedon on ~ total time spent at each location 

# and visitation frequency

# take the cluster centroid as the significant location



#%% point after swapping not the exact same, or within buffer?





#%% 