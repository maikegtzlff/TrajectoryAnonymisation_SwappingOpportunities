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
#%% ADD DATETIME COLUMN TO SWAPPED EDGES DF
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







######################################################################################
#%% CLUSTERING
#%% clusteirng stops using DBSCAN in scikit-learn
# distance 60m, 4 stops







#%%
import os
print(os.getcwd())
os.chdir(r"E:\paper3")
print(os.getcwd())

import geopandas as gpd
stop_points_edges = gpd.read_parquet(r"e:\paper3\data\HomeDetection\edgeSwapped_split_StopPoints.parquet")
#(r"D:\paper3\Data\output\Evaluation_HomeDetection/edgeSwapped_split_StopPoints.parquet")
stop_points_edges.rename(columns={'container_uid': 'uid'}, inplace=True)


#%% clusteirng stops using DBSCAN in scikit-learn
# distance 60m, 4 stops
import importlib
import s_clustering_final as cstp
importlib.reload(cstp)

cstp.cluster_users_to_parquet_resumable(
    stop_points_edges,
    radius_km=0.06,
    min_points=4,
    output_dir=r"E:\paper3\data\HomeDetection\Clustering_EdgeSwapped",
    small_threshold=50000,
    large_threshold=100000
)

# Clustering users:  99%|█████████▊| 70/71 [4:06:51<03:31, 211.59s/it]  
# only 1 user that is problematic (crashing RAM - other 26 user pre-processed)
#%% all clsuter info as one df
import pandas as pd

clustered_files = [os.path.join(r"E:\paper3\data\HomeDetection\Clustering_EdgeSwapped", f)
                   for f in os.listdir(r"E:\paper3\data\HomeDetection\Clustering_EdgeSwapped") 
                   if f.endswith(".parquet")]

all_clustered = pd.concat([pd.read_parquet(f) for f in clustered_files], ignore_index=True)
print(len(all_clustered)) # 25,379,389
#%%
all_clustered.head() # cluster and clsuter_id. cluster_id is user plus cluster. Geometry


#%%
import os 
os.chdir(r"E:\paper3")
import s_clustering_final as cstp

ranked_clusters_edges = cstp.rank_clusters(all_clustered)

#%%
print(len(ranked_clusters_edges)) # 103986
ranked_clusters_edges.head()

#%%
all_clustered.to_parquet(r"E:\paper3\data\HomeDetection/EdgeSwappingStopPointsClusters.parquet")
all_clustered.to_parquet(r"\\tsclient\R\paper3\Data\swappedtrajs\StopPoints\clusteringStopPointsPostSwapping/EdgeSwappingStopPointsClusters.parquet")

ranked_clusters_edges.to_parquet(r"E:\paper3\data\HomeDetection/EdgeSwappingStopPointsClusters_rankedAll.parquet")
ranked_clusters_edges.to_parquet(r"\\tsclient\R\paper3\Data\swappedtrajs\StopPoints\clusteringStopPointsPostSwapping/EdgeSwappingStopPointsClusters_rankedAll.parquet")


#%% reduce to the top 2 location by user
ranked_clusters_edges_top2 = ranked_clusters_edges[ranked_clusters_edges['rank'] <= 2]
ranked_clusters_edges_top2['HomeWork'] = ranked_clusters_edges_top2['rank'].map({1: 'home', 2: 'work'})
ranked_clusters_edges_top2 # 192 rows

#%%
ranked_clusters_edges_top2.to_parquet(r"E:\paper3\data\HomeDetection/EdgeSwappingStopPointsClusters_rankedTop2.parquet")
ranked_clusters_edges_top2.to_parquet(r"\\tsclient\R\paper3\Data\swappedtrajs\StopPoints\clusteringStopPointsPostSwapping/EdgeSwappingStopPointsClusters_rankedTop2.parquet")

#%% add back geometry and find centroid
# those are the orginal point geometries
# can either calculate centroid, or find 95% MCP and get centroid (see chapter 1 )

#%% take the cluster centroid as the significant location



#%% point after swapping not the exact same, or within buffer?
# take the cluster centroid as the significant location



####################
#%% run clustering on nodes
import os
print(os.getcwd())
os.chdir(r"E:\paper3")
print(os.getcwd())

import geopandas as gpd
stop_points_nodes = gpd.read_parquet(r"e:\paper3\data\HomeDetection\nodesSwapped_split_StopPoints.parquet")
#(r"D:\paper3\Data\output\Evaluation_HomeDetection/edgeSwapped_split_StopPoints.parquet")
stop_points_nodes.rename(columns={'container_uid': 'uid'}, inplace=True)


#%% clusteirng stops using DBSCAN in scikit-learn
# distance 60m, 4 stops
import importlib
import s_clustering_final as cstp
importlib.reload(cstp)

cstp.cluster_users_to_parquet_resumable(
    stop_points_nodes,
    radius_km=0.06,
    min_points=4,
    output_dir=r"E:\paper3\data\HomeDetection\Clustering_IntersectionSwapped",
    small_threshold=50000,
    large_threshold=100000
)
# RAM usage isn't high at all! (but it's crashing for nodes and edge based swaps...)
# until it is high for the last user
# Clustering users:  99%|█████████▉| 96/97 [1:10:32<02:43, 163.56s/it]
# is the problematic user that also crashed the node swapping stop points from clustering?

#%% look at processed users
folder = r"E:\paper3\data\HomeDetection\Clustering_IntersectionSwapped"

u_clustered = [os.path.splitext(f)[0]
              for f in os.listdir(folder)
              if f.endswith(".parquet")]


#%% get cluster ranks
# 
import os
os.chdir(r"E:\paper3")
import s_clustering_final as cstp

import pandas as pd

clustered_files = [os.path.join(r"E:\paper3\data\HomeDetection\Clustering_IntersectionSwapped", f)
                   for f in os.listdir(r"E:\paper3\data\HomeDetection\Clustering_IntersectionSwapped") 
                   if f.endswith(".parquet")]

stop_points_nodes_clustered = pd.concat([pd.read_parquet(f) for f in clustered_files], ignore_index=True)
print(len(stop_points_nodes_clustered)) # 25,379,389

ranked_clusters_nodess = cstp.rank_clusters(stop_points_nodes_clustered)

# reduce to the top 2 location by user
ranked_clusters_nodes_top2 = ranked_clusters_nodess[ranked_clusters_nodess['rank'] <= 2]
ranked_clusters_nodes_top2['HomeWork'] = ranked_clusters_nodes_top2['rank'].map({1: 'home', 2: 'work'})
ranked_clusters_nodes_top2 # 192 rows

#%% export all
stop_points_nodes_clustered.to_parquet(r"E:\paper3\data\HomeDetection/NodeSwappingStopPointsClusters.parquet")
stop_points_nodes_clustered.to_parquet(r"\\tsclient\R\paper3\Data\swappedtrajs\StopPoints\clusteringStopPointsPostSwapping/NodeSwappingStopPointsClusters.parquet")

ranked_clusters_nodess.to_parquet(r"E:\paper3\data\HomeDetection/NodeSwappingStopPointsClusters_rankedAll.parquet")
ranked_clusters_nodess.to_parquet(r"\\tsclient\R\paper3\Data\swappedtrajs\StopPoints\clusteringStopPointsPostSwapping/NodeSwappingStopPointsClusters_rankedAll.parquet")

ranked_clusters_nodes_top2.to_parquet(r"E:\paper3\data\HomeDetection/NodesSwappingStopPointsClusters_rankedTop2.parquet")
ranked_clusters_nodes_top2.to_parquet(r"\\tsclient\R\paper3\Data\swappedtrajs\StopPoints\clusteringStopPointsPostSwapping/NodesSwappingStopPointsClusters_rankedTop2.parquet")


#%% identify the problematic user 
import geopandas as gpd
stop_points_nodes = gpd.read_parquet(r"e:\paper3\data\HomeDetection\nodesSwapped_split_StopPoints.parquet")
stop_points_nodes.rename(columns={'container_uid': 'uid'}, inplace=True)

prbl_u = stop_points_nodes[~stop_points_nodes['uid'].isin(u_clustered)].uid.unique()
print('problematic user: ', prbl_u)
# problematic user:  ['0d5010abd3d6f0bcd8cee8c66cb58784af4357a1']