#%% Home detection
import geopandas as gpd
import pandas as pd

import numpy as np

#gdf_edges_swppd = gpd.read_parquet(r"D:\paper3\Data\output/final_points_edgeSwap_FINAL.parquet")

gdf_nodess_swppd = gpd.read_parquet(r"d:\paper3\Data\filled_trajectories_list\trajectories_swapped_nodes_FINAL.parquet")

#t_cswappingl_origsynf_headtailsynf = gpd.read_parquet(r"D:\paper3\Data\ClkSwpSynFilled_uid_length_timestamps_FINAL.parquet")

#t_cswappingl_origsynf_headtailsynf['container_id'] = t_cswappingl_origsynf_headtailsynf['final_tid_origsynfilled']
#t_cswappingl_origsynf_headtailsynf['container_id'] = t_cswappingl_origsynf_headtailsynf['final_tid_origsynfilled']
#t_cswappingl_origsynf_headtailsynf['orig_uid'] = t_cswappingl_origsynf_headtailsynf['original_tid'].str.split('_').str[1]
#t_cswappingl_origsynf_headtailsynf.orig_uid.unique() # how to handle synthetic ones> 
#t_cswappingl_origsynf_headtailsynf['orig_uid'] = np.where(
#    t_cswappingl_origsynf_headtailsynf['orig_uid'] == 'orig',
#    t_cswappingl_origsynf_headtailsynf['original_tid'],
#    t_cswappingl_origsynf_headtailsynf['orig_uid']
#)

#%% ADD DATETIME COLUMN TO SWAPPED EDGES DF
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
gdf_edges_swppd['sec_fromTrajStart'] = (
    gdf_edges_swppd['sec_fromPrevPoint']
    .fillna(0)
    .groupby(gdf_edges_swppd['container_id'])
    .cumsum()
)
gdf_edges_swppd['date_unix_midnight'] = (
    pd.to_datetime(gdf_edges_swppd['container_date'].astype(str), format='%Y%m%d')
    .dt.tz_localize('Pacific/Auckland')
    .astype('int64') // 10**9
)
gdf_edges_swppd['time_bin_start_sec'] = gdf_edges_swppd['time_bin_start'] *3600
gdf_edges_swppd['sec_fromTrajStart'] = gdf_edges_swppd['sec_fromTrajStart'].astype(int)

gdf_edges_swppd['container_unix_timestamp'] = gdf_edges_swppd['date_unix_midnight'] + gdf_edges_swppd['time_bin_start_sec'] + gdf_edges_swppd['sec_fromTrajStart']

gdf_edges_swppd['container_datetime'] = pd.to_datetime(
    gdf_edges_swppd['container_unix_timestamp'], unit='s', utc=True
).dt.tz_convert('Pacific/Auckland')

gdf_edges_swppd[[ 'container_datetime', 'container_date', 'time_bin_start']]


#%% export df 
gdf_edges_swppd.to_parquet(r"D:\paper3\Data\output/final_points_edgeSwap_FINAL_ContainerDatetime.parquet")


#%% ADD DATETIME TO NODES BASED SWAPPED DF
print(gdf_nodess_swppd.columns)

# must know timebin breaks
# 7 <= hour < 9:    "morning peak"
# 9 <= hour < 16:   "flat peak"
# 16 <= hour < 20:  "evening peak"
# "night time"

#time_bin_start_dict = {
#    'night time': 21,
#    'morning peak': 7,
#    'flat peak': 9,
#    'evening peak': 16,
#}

#mapping = {
#    'night time': 0,
#    'morning peak': 1,
#    'flat peak': 2,
#    'evening peak': 3,
#}

time_bin_start_dict = {
    0 : 21,
    1: 7,
    2: 9,
    3: 16,
}

# date comes from here container_tid_subid - date is before first _, add to new column
gdf_nodess_swppd['time_bin_start'] = gdf_nodess_swppd['time_bin'].map(time_bin_start_dict)
gdf_nodess_swppd['container_date'] = gdf_nodess_swppd['container_tid_subid'].str.split('_').str[0].astype(int)
gdf_nodess_swppd['sec_fromTrajStart'] = (
    gdf_nodess_swppd['sec_fromPrevPoint']
    .fillna(0)
    .groupby(gdf_nodess_swppd['container_id'])
    .cumsum()
)
gdf_nodess_swppd['date_unix_midnight'] = (
    pd.to_datetime(gdf_nodess_swppd['container_date'].astype(str), format='%Y%m%d')
    .dt.tz_localize('Pacific/Auckland')
    .astype('int64') // 10**9
)
gdf_nodess_swppd['time_bin_start_sec'] = gdf_nodess_swppd['time_bin_start'] *3600
gdf_nodess_swppd['sec_fromTrajStart'] = gdf_nodess_swppd['sec_fromTrajStart'].astype(int)

gdf_nodess_swppd['container_unix_timestamp'] = gdf_nodess_swppd['date_unix_midnight'] + gdf_nodess_swppd['time_bin_start_sec'] + gdf_nodess_swppd['sec_fromTrajStart']

gdf_nodess_swppd['container_datetime'] = pd.to_datetime(
    gdf_nodess_swppd['container_unix_timestamp'], unit='s', utc=True
).dt.tz_convert('Pacific/Auckland')

gdf_nodess_swppd[[ 'container_datetime', 'container_date', 'time_bin_start']]


#%% export df 
gdf_nodess_swppd.to_parquet(r"d:\paper3\Data\filled_trajectories_list\trajectories_swapped_nodes_FINAL_ContainerDatetime.parquet")




#%% add datetime column to cloaked swapped
time_bin_start_dict = {
    'night time': 21,
    'morning peak': 7,
    'flat peak': 9,
    'evening peak': 16,
}
# date comes from here container_tid_subid - date is before first _, add to new column
t_cswappingl_origsynf_headtailsynf['time_bin_start'] = t_cswappingl_origsynf_headtailsynf['time_bin_label'].map(time_bin_start_dict)
t_cswappingl_origsynf_headtailsynf['container_date'] = t_cswappingl_origsynf_headtailsynf['container_id'].str.split('_').str[0].astype(int)
t_cswappingl_origsynf_headtailsynf['sec_fromTrajStart'] = (
    t_cswappingl_origsynf_headtailsynf['sec_fromPrevPoint']
    .fillna(0)
    .groupby(t_cswappingl_origsynf_headtailsynf['container_id'])
    .cumsum()
)
t_cswappingl_origsynf_headtailsynf['date_unix_midnight'] = (
    pd.to_datetime(t_cswappingl_origsynf_headtailsynf['container_date'].astype(str), format='%Y%m%d')
    .dt.tz_localize('Pacific/Auckland')
    .astype('int64') // 10**9
)
t_cswappingl_origsynf_headtailsynf['time_bin_start_sec'] = t_cswappingl_origsynf_headtailsynf['time_bin_start'] *3600
t_cswappingl_origsynf_headtailsynf['sec_fromTrajStart'] = t_cswappingl_origsynf_headtailsynf['sec_fromTrajStart'].astype(int)

t_cswappingl_origsynf_headtailsynf['container_unix_timestamp'] = t_cswappingl_origsynf_headtailsynf['date_unix_midnight'] + t_cswappingl_origsynf_headtailsynf['time_bin_start_sec'] + t_cswappingl_origsynf_headtailsynf['sec_fromTrajStart']

t_cswappingl_origsynf_headtailsynf['container_datetime'] = pd.to_datetime(
    t_cswappingl_origsynf_headtailsynf['container_unix_timestamp'], unit='s', utc=True
).dt.tz_convert('Pacific/Auckland')

t_cswappingl_origsynf_headtailsynf[[ 'container_datetime', 'container_date', 'time_bin_start', 'container_unix_timestamp']]


#%% export df 
t_cswappingl_origsynf_headtailsynf.to_parquet(r"D:\paper3\output\swappedtrajs\ClkSwpSynFilled_uid_length_timestamps_FINAL_ContainerDatetime.parquet")
# VM13




######################################################################################
#%% STOP DETECTIONS
#%% MovingPandas for StopDection
import movingpandas as mpd
edges_traj_collection = mpd.TrajectoryCollection(
    gdf_edges_swppd,
    traj_id_col='sub_container_id',
    t='container_datetime'
)

# stop detection
from datetime import datetime, timedelta
# 3 minutes, 65meters - based on chapter 1 parameters
detector = mpd.TrajectoryStopDetector(edges_traj_collection)
stop_points_edges = detector.get_stop_points(
    min_duration=timedelta(seconds=180), max_diameter=65
)
print('number of stop points detected', len(stop_points_edges))
# ran for 153 nminutes 
# 114,895 stop points detected

# fake time stamps might eaxagurate long stays - maybe not, maybe I'm overthinking. time stamps are based on seconds to previous point.
# changed in time_bin might lead to artificially long stops, i.e., start of stop in time bin one, then a differnet time bin at the end of the stop, but fake timestamps are based on the start of the the time bin
print('minimum stop duration in seconds:', stop_points_edges.duration_s.min())
print('median stop duration in minutes:', stop_points_edges.duration_s.median()/60)   # minutes
print('maximum stop duration in hours:', stop_points_edges.duration_s.max()/3600)    # hours

# min stop: 180 seconds, the threshold I set
# median stop: 12 minutes
# maximum stop duration 30 hours.... see comment above

# add attributes to stop points
stop_points_edges = stop_points_edges.reset_index(drop=False)

# map uid
stop_points_edges = stop_points_edges.merge(gdf_edges_swppd[['sub_container_id', 'container_tid_subid', 'container_uid']], left_on = 'traj_id', right_on = 'sub_container_id', how='left')
stop_points_edges.head()

# export before clustering
stop_points_edges.to_parquet(r"D:\paper3\Data\output\Evaluation_HomeDetection/edgeSwapped_split_StopPoints.parquet")


#%% stop detection for node-based swapping (split trajs)
import movingpandas as mpd
nodes_traj_collection = mpd.TrajectoryCollection(
    gdf_nodess_swppd,
    traj_id_col='sub_container_id',
    t='container_datetime'
)

# stop detection
from datetime import datetime, timedelta
# 3 minutes, 65meters - based on chapter 1 parameters
detector = mpd.TrajectoryStopDetector(nodes_traj_collection)
stop_points_nodes = detector.get_stop_points(
    min_duration=timedelta(seconds=180), max_diameter=65
)
print('number of stop points detected', len(stop_points_nodes))
# ran for 153 nminutes 
# 114,895 stop points detected

# fake time stamps might eaxagurate long stays - maybe not, maybe I'm overthinking. time stamps are based on seconds to previous point.
# changed in time_bin might lead to artificially long stops, i.e., start of stop in time bin one, then a differnet time bin at the end of the stop, but fake timestamps are based on the start of the the time bin
print('minimum stop duration in seconds:', stop_points_nodes.duration_s.min())
print('median stop duration in minutes:', stop_points_nodes.duration_s.median()/60)   # minutes
print('maximum stop duration in hours:', stop_points_nodes.duration_s.max()/3600)    # hours

# min stop: 180 seconds, the threshold I set
# median stop: 12 minutes
# maximum stop duration 30 hours.... see comment above

# add attributes to stop points
stop_points_nodes = stop_points_nodes.reset_index(drop=False)

# map uid
stop_points_nodes = stop_points_nodes.merge(gdf_nodess_swppd[['sub_container_id', 'container_tid_subid', 'container_uid']], left_on = 'traj_id', right_on = 'sub_container_id', how='left')
stop_points_nodes.head()

# export before clustering
stop_points_nodes.to_parquet(r"D:\paper3\Data\output\Evaluation_HomeDetection/nodesSwapped_split_StopPoints.parquet")

# ran for 626 minutes
#%% this is where all files are stored on VM201
#########################
#d:\paper3\Data\SWAPPEDTRAJECTORIES\ClkSwpSynFilled_uid_length_timestamps_FINAL_ContainerDatetime.parquet 
#d:\paper3\Data\SWAPPEDTRAJECTORIES\final_points_edgeSwap_FINAL_ContainerDatetime.parquet 
#d:\paper3\Data\SWAPPEDTRAJECTORIES\trajectories_swapped_nodes_FINAL_ContainerDatetime.parquet
# and R
#\\tsclient\R\paper3\Data\swappedtrajs\ClkSwpSynFilled_uid_length_timestamps_FINAL_ContainerDatetime.parquet 
#\\tsclient\R\paper3\Data\swappedtrajs\final_points_edgeSwap_FINAL_ContainerDatetime.parquet 
#\\tsclient\R\paper3\Data\swappedtrajs\trajectories_swapped_nodes_FINAL_ContainerDatetime.parquet




#%% get stops for cloaking based swapping
t_cswappingl_origsynf_headtailsynf = gpd.read_parquet(r"d:\paper3\Data\SWAPPEDTRAJECTORIES\ClkSwpSynFilled_uid_length_timestamps_FINAL_ContainerDatetime.parquet") 

#import movingpandas as mpd
cswappingl_tc = mpd.TrajectoryCollection(
    t_cswappingl_origsynf_headtailsynf,
    traj_id_col='container_id',
    t='container_datetime'
)

# stop detection
from datetime import datetime, timedelta
# 3 minutes, 65meters - based on chapter 1 parameters
detector = mpd.TrajectoryStopDetector(cswappingl_tc)
stop_points_cswappingl = detector.get_stop_points(
    min_duration=timedelta(seconds=180), max_diameter=65
)
print('number of stop points detected', len(stop_points_cswappingl))


# fake time stamps might eaxagurate long stays - maybe not, maybe I'm overthinking. time stamps are based on seconds to previous point.
# changed in time_bin might lead to artificially long stops, i.e., start of stop in time bin one, then a differnet time bin at the end of the stop, but fake timestamps are based on the start of the the time bin
print('minimum stop duration in seconds:', stop_points_cswappingl.duration_s.min())
print('median stop duration in minutes:', stop_points_cswappingl.duration_s.median()/60)   # minutes
print('maximum stop duration in hours:', stop_points_cswappingl.duration_s.max()/3600)    # hours


# add attributes to stop points
stop_points_cswappingl = stop_points_cswappingl.reset_index(drop=False)

# map uid
stop_points_cswappingl = stop_points_cswappingl.merge(t_cswappingl_origsynf_headtailsynf[['container_id', 'container_uid']], left_on = 'traj_id', right_on = 'container_id', how='left')
stop_points_cswappingl.head()

# export before clustering
stop_points_cswappingl.to_parquet(r"D:\paper3\Data\output\Evaluation_HomeDetection/cloakedSwapped_StopPoints.parquet")

#%%
stop_points_nodes.head()
#number of stop points detected 104173
#minimum stop duration in seconds: 180.0
#median stop duration in minutes: 10.25
#maximum stop duration in hours: 30.787222222222223

#%%
stop_points_cswappingl.head()
#number of stop points detected 115002
#minimum stop duration in seconds: 180.0
#median stop duration in minutes: 11.65
#maximum stop duration in hours: 30.675

#########################




######################################################################################
#%% CLUSTERING
import os 
os.chdir(r"D:\paper3")
import s_clustering_final as cstp

import geopandas as gpd
stop_points_cswappingl = gpd.read_parquet(r"D:\paper3\Data\output\Evaluation_HomeDetection/cloakedSwapped_StopPoints.parquet")
# taking up 70GB of RAM
# might be better to read them in individually/ in batches 

#%%
n_stps_c = stop_points_cswappingl.groupby(['container_uid']).size().reset_index()
n_stps_c
#%%
print(len(stop_points_cswappingl)) # 79,694,465

print(n_stps_c[0].min())        # 15,504
print(n_stps_c[0].median())     # 644,951
print(n_stps_c[0].max())        # 4,976,988
# longer thna edge splits
# the maximum one is more than half the data set

#%%
#%% clusteirng cloaking stops using DBSCAN in scikit-learn
stop_points_cswappingl.rename(columns={'container_uid': 'uid'}, inplace=True)

# distance 60m, 4 stops
cstp.cluster_users_to_parquet_resumable(
    stop_points_cswappingl,
    radius_km=0.06,
    min_points=4,
    output_dir=r"D:\paper3\Data\SWAPPEDTRAJECTORIES\StopPoints\Clustering\CloakingSwapping",
    small_threshold=50000,
    large_threshold=100000
)

