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



#%% ####################################################################
#%% are clustered points of rank 1 and 2 within the cloaking geometries?
import pandas as pd
StpPntsClstered_intersection = pd.read_parquet(r"E:\paper3\data\HomeDetection\NodesSwappingStopPointsClusters_rankedTop2.parquet")
StpPntsClstered_edges = pd.read_parquet(r"E:\paper3\data\HomeDetection\EdgeSwappingStopPointsClusters_rankedTop2.parquet")

StpPntsClstered_edges.head() # rank and uid to match ranked location of each user to before swapping
#%%
StpPntsClstered_edges['rank_uid'] = StpPntsClstered_edges['rank'].astype(int).astype(str) + "_" + StpPntsClstered_edges['uid']
StpPntsClstered_intersection['rank_uid'] = StpPntsClstered_intersection['rank'].astype(int).astype(str) + "_" + StpPntsClstered_intersection['uid']
StpPntsClstered_intersection.head()
#%% no geometry yet! tidy up and add geom back
StpPntsClstered_edges = StpPntsClstered_edges[['rank_uid', 'uid', 'cluster_id', 'rank']].copy()
StpPntsClstered_intersection = StpPntsClstered_intersection[['rank_uid', 'uid', 'cluster_id', 'rank']].copy()




#%% get cluster geometry
stop_points_nodes_clustered = pd.read_parquet(r"E:\paper3\data\HomeDetection/NodeSwappingStopPointsClusters.parquet")
stop_points_edges_clustered = pd.read_parquet(r"E:\paper3\data\HomeDetection/EdgeSwappingStopPointsClusters.parquet")

#%%
stop_points_edges_clustered = gpd.GeoDataFrame(
    stop_points_edges_clustered,
    geometry=gpd.points_from_xy(
        stop_points_edges_clustered['lng'],
        stop_points_edges_clustered['lat']
    ),
    crs="EPSG:2193"
)

# get centroid by cluster_id
stop_points_edges_clustered_centroids = (
    stop_points_edges_clustered.groupby('cluster_id')['geometry']
    .apply(lambda x: x.unary_union.centroid)
    .reset_index()
)

stop_points_edges_clustered_centroids = gpd.GeoDataFrame(stop_points_edges_clustered_centroids, geometry='geometry', crs=2193)
stop_points_edges_clustered_centroids # calculated centroids for all, only needed them for ranks 1 to 2

#%% join centroid to top 2
StpPntsClstered_edges = StpPntsClstered_edges.merge(stop_points_edges_clustered_centroids, on = "cluster_id", how="left")
print(type(StpPntsClstered_edges))
StpPntsClstered_edges.head()

#%%
StpPntsClstered_edges = gpd.GeoDataFrame(StpPntsClstered_edges, geometry='geometry', crs="EPSG:2193")
StpPntsClstered_edges.to_parquet(r"E:\paper3\data\HomeDetection/StpPntsClstered_edges_top2.parquet")

#%%
cloaking_geom = gpd.read_file(r"e:\paper3\data\HomeDetection\polys.gpkg")
print(cloaking_geom.crs)
cloaking_geom = cloaking_geom.to_crs(2193)
print(cloaking_geom.crs)
cloaking_geom.head() # rank_uid

#%% merge on rank_uid
print(cloaking_geom.crs)
print(StpPntsClstered_edges.crs)

if cloaking_geom.crs == StpPntsClstered_edges.crs:

    StpPntsClstered_edges_cloakingGeom = StpPntsClstered_edges.merge(cloaking_geom[['rank_uid', 'geometry']], on='rank_uid', suffixes=('_point', '_polygon'))

    # is "new" significant location inside old significant location?
    StpPntsClstered_edges_cloakingGeom['intersects_sigLoc'] = StpPntsClstered_edges_cloakingGeom.apply(lambda row: row['geometry_point'].intersects(row['geometry_polygon']), axis=1)
    print(StpPntsClstered_edges_cloakingGeom['intersects_sigLoc'].value_counts())
    # 
    #intersects_sigLoc
    #False    188
    #True       4

    # this is a 1-1 approach: does rank 1 intersect with sig loc 1



#%% but rank 1 should also not sintersect with sig loc 2 of user
import pandas as pd

results = []

for uid in StpPntsClstered_edges['rank_uid'].unique():
    pts = StpPntsClstered_edges[StpPntsClstered_edges['rank_uid'] == uid]
    polys = cloaking_geom[cloaking_geom['rank_uid'] == uid]

    # safety check
    if pts.empty or polys.empty:
        results.append((uid, False))
        continue

    # check all combinations within the uid
    intersects = False

    for p in pts['geometry']:
        if polys['geometry'].intersects(p).any():
            intersects = True
            break

    results.append((uid, intersects))

result_df = pd.DataFrame(results, columns=['rank_uid', 'intersects'])
print(result_df['intersects'].value_counts())
#intersects
#False    188
#True       4

#%%
counts = result_df['intersects'].value_counts()
percent = result_df['intersects'].value_counts(normalize=True) * 100

summary = pd.DataFrame({
    'count': counts,
    'percentage': percent.round(1)
})

print(summary)
# same as before, when comparing first rank to first rank

#%% not sure how 4 can be within the cloaking geom...

TrueClusterCentroid = StpPntsClstered_edges[StpPntsClstered_edges['rank_uid'].isin(result_df[result_df['intersects']==True]['rank_uid'].unique())]
TrueClusterCentroid.to_parquet(r"E:\paper3\data\HomeDetection\testing/StpPntsClstered_edgesCentroidWithinCentroid.parquet")
# all more towards the outside of the cloalking geometry (could provide figures?)
# cloaking geometry is calculated with some randomness for each signifcant location (and cloak?) so this could be variable
# cluster centroid?

#%% look at all clustered stop points/
stop_points_edges_clustered[stop_points_edges_clustered['cluster_id'].isin(TrueClusterCentroid['cluster_id'].unique())].to_parquet(r"E:\paper3\data\HomeDetection\testing/StpPntsClstered_edgesCentroidWithin.parquet")

#%%
#TrueClusterCentroid
cloaking_geom_True = cloaking_geom[cloaking_geom['rank_uid'].isin(TrueClusterCentroid['rank_uid'].unique())]







#%%##### intersections
# StpPntsClstered_intersection has rank
# stop_points_nodes_clustered needs to be a gdf, then find centroid
stop_points_nodes_clustered = pd.read_parquet(r"E:\paper3\data\HomeDetection/NodeSwappingStopPointsClusters.parquet")

stop_points_nodes_clustered = gpd.GeoDataFrame(
    stop_points_nodes_clustered,
    geometry=gpd.points_from_xy(
        stop_points_nodes_clustered['lng'],
        stop_points_nodes_clustered['lat']
    ),
    crs="EPSG:2193"
)

print(type(stop_points_nodes_clustered))
print(stop_points_nodes_clustered.crs)
stop_points_nodes_clustered.head()
#%%
# get centroid by cluster_id
stop_points_nodes_clustered_centroids = (
    stop_points_nodes_clustered.groupby('cluster_id')['geometry']
    .apply(lambda x: x.unary_union.centroid)
    .reset_index()
)
print(type(stop_points_nodes_clustered_centroids))
print(stop_points_nodes_clustered_centroids.crs)

#%%
print(type(stop_points_nodes_clustered_centroids))
print(stop_points_nodes_clustered_centroids.crs)
stop_points_nodes_clustered_centroids.head() 

#%% clusters had not been ranked yet?
import os
print(os.getcwd())
os.chdir(r"E:\paper3")

import s_clustering_final as cstp

ranked_stop_points_nodes_clustered = cstp.rank_clusters(stop_points_nodes_clustered)
ranked_stop_points_nodes_clustered

#%% only interested in top 2 ranks per uid
#%% reduce to the top 2 location by user
ranked_stop_points_nodes_clustered_top2 = ranked_stop_points_nodes_clustered[ranked_stop_points_nodes_clustered['rank'] <= 2]
ranked_stop_points_nodes_clustered_top2['HomeWork'] = ranked_stop_points_nodes_clustered['rank'].map({1: 'home', 2: 'work'})
ranked_stop_points_nodes_clustered_top2 

#%% add rank_uid
ranked_stop_points_nodes_clustered_top2['rank_uid'] = ranked_stop_points_nodes_clustered_top2['rank'].astype(int).astype(str) + "_" + ranked_stop_points_nodes_clustered_top2['uid']
ranked_stop_points_nodes_clustered_top2[['cluster_id', 'rank_uid']]

#%%
stop_points_nodes_clustered_centroids = stop_points_nodes_clustered_centroids.merge(ranked_stop_points_nodes_clustered_top2[['cluster_id', 'rank_uid']], on = "cluster_id", how="right")
print(type(stop_points_nodes_clustered_centroids))
stop_points_nodes_clustered_centroids

#%%
print(cloaking_geom.crs)
print(stop_points_nodes_clustered_centroids.crs)

if cloaking_geom.crs == stop_points_nodes_clustered_centroids.crs:

    #stop_points_nodes_clustered_centroids_cloakingGeom = stop_points_nodes_clustered_centroids.merge(cloaking_geom[['rank_uid', 'geometry']], on='rank_uid', suffixes=('_point', '_polygon'))

    # is "new" significant location inside old significant location?
    results = []

    for uid in stop_points_nodes_clustered_centroids['rank_uid'].unique():
        pts = stop_points_nodes_clustered_centroids[stop_points_nodes_clustered_centroids['rank_uid'] == uid]
        polys = cloaking_geom[cloaking_geom['rank_uid'] == uid]

        # safety check
        if pts.empty or polys.empty:
            results.append((uid, False))
            continue

        # check all combinations within the uid
        intersects = False

        for p in pts['geometry']:
            if polys['geometry'].intersects(p).any():
                intersects = True
                break

        results.append((uid, intersects))

    stop_points_nodes_clustered_centroids_SigLoc = pd.DataFrame(results, columns=['rank_uid', 'intersects'])
    
    counts = stop_points_nodes_clustered_centroids_SigLoc['intersects'].value_counts()
    percent = stop_points_nodes_clustered_centroids_SigLoc['intersects'].value_counts(normalize=True) * 100

    summary = pd.DataFrame({
        'count': counts,
        'percentage': percent.round(1)
    })

    print(summary)

#            count  percentage
#intersects                   
#False         190        99.0
#True            2         1.0

#%% subset the true ones for plotting
new_SigLoc_True_nodes = stop_points_nodes_clustered_centroids_SigLoc[stop_points_nodes_clustered_centroids_SigLoc['intersects']==True]
# add geometry back
new_SigLoc_True_nodes = stop_points_nodes_clustered_centroids[['rank_uid', 'geometry']].merge(new_SigLoc_True_nodes, on='rank_uid', how='right')
print(type(new_SigLoc_True_nodes))

new_SigLoc_True_cloakingGeom = stop_points_nodes_clustered_centroids_SigLoc[stop_points_nodes_clustered_centroids_SigLoc['intersects']==True]
cloaking_geom_True_nodes = cloaking_geom[cloaking_geom['rank_uid'].isin(new_SigLoc_True_cloakingGeom['rank_uid'].unique())]


#%% ######################### edges
# stop_points_edges_clustered needs to be a gdf, then find centroid
print(stop_points_edges_clustered.crs)
# get centroid by cluster_id
stop_points_edges_clustered_centroids = (
    stop_points_edges_clustered.groupby('cluster_id')['geometry']
    .apply(lambda x: x.unary_union.centroid)
    .reset_index()
)
print(type(stop_points_edges_clustered_centroids))
print(stop_points_edges_clustered_centroids.crs)
stop_points_edges_clustered_centroids.head() 

#%% get ranks
import os
print(os.getcwd())
os.chdir(r"E:\paper3")

import s_clustering_final as cstp

ranked_stop_points_edges_clustered = cstp.rank_clusters(stop_points_edges_clustered)
ranked_stop_points_edges_clustered

#%% only interested in top 2 ranks per uid
#%% reduce to the top 2 location by user
ranked_stop_points_edges_clustered_top2 = ranked_stop_points_edges_clustered[ranked_stop_points_edges_clustered['rank'] <= 2]
ranked_stop_points_edges_clustered_top2['HomeWork'] = ranked_stop_points_edges_clustered['rank'].map({1: 'home', 2: 'work'})
# add rank_uid
ranked_stop_points_edges_clustered_top2['rank_uid'] = ranked_stop_points_edges_clustered_top2['rank'].astype(int).astype(str) + "_" + ranked_stop_points_edges_clustered_top2['uid']
ranked_stop_points_edges_clustered_top2[['cluster_id', 'rank_uid']]

#%%
stop_points_edges_clustered_centroids = stop_points_edges_clustered_centroids.merge(ranked_stop_points_edges_clustered_top2[['cluster_id', 'rank_uid']], on = "cluster_id", how="right")
print(type(stop_points_edges_clustered_centroids))
print(stop_points_edges_clustered_centroids.crs)
stop_points_edges_clustered_centroids

#%%
stop_points_edges_clustered_centroids = stop_points_edges_clustered_centroids.set_crs(2193)
#%%
print(cloaking_geom.crs)
print(stop_points_edges_clustered_centroids.crs)

if cloaking_geom.crs == stop_points_edges_clustered_centroids.crs:

    # is "new" significant location inside old significant location?
    results = []

    for uid in stop_points_edges_clustered_centroids['rank_uid'].unique():
        pts = stop_points_edges_clustered_centroids[stop_points_edges_clustered_centroids['rank_uid'] == uid]
        polys = cloaking_geom[cloaking_geom['rank_uid'] == uid]

        # safety check
        if pts.empty or polys.empty:
            results.append((uid, False))
            continue

        # check all combinations within the uid
        intersects = False

        for p in pts['geometry']:
            if polys['geometry'].intersects(p).any():
                intersects = True
                break

        results.append((uid, intersects))

    stop_points_edges_clustered_centroids_SigLoc = pd.DataFrame(results, columns=['rank_uid', 'intersects'])
    
    counts = stop_points_edges_clustered_centroids_SigLoc['intersects'].value_counts()
    percent = stop_points_edges_clustered_centroids_SigLoc['intersects'].value_counts(normalize=True) * 100

    summary = pd.DataFrame({
        'count': counts,
        'percentage': percent.round(1)
    })

    print(summary)
else:
    print('crs did not match')

#            count  percentage
#intersects                   
#False         188        97.9
#True            4         2.1

#%%



#%% subset the true ones for plotting
new_SigLoc_True_edges = stop_points_edges_clustered_centroids_SigLoc[stop_points_edges_clustered_centroids_SigLoc['intersects']==True]
# add geometry back
stop_points_edges_clustered_centroids_SigLoc = stop_points_edges_clustered_centroids[['rank_uid', 'geometry']].merge(stop_points_edges_clustered_centroids_SigLoc, on='rank_uid', how='right')
new_SigLoc_True_edges = stop_points_edges_clustered_centroids_SigLoc[['rank_uid', 'geometry']].merge(new_SigLoc_True_edges, on='rank_uid', how='right')
print(type(new_SigLoc_True_edges))

new_SigLoc_True_cloakingGeom_edges = stop_points_edges_clustered_centroids_SigLoc[stop_points_edges_clustered_centroids_SigLoc['intersects']==True]
cloaking_geom_True_edges = cloaking_geom[cloaking_geom['rank_uid'].isin(new_SigLoc_True_cloakingGeom_edges['rank_uid'].unique())]




#%%#####################################################################
#%% individual plots: cloaking 
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects

uids = sorted(TrueClusterCentroid['rank_uid'].unique())

fig, axes = plt.subplots(2, 2, figsize=(12, 12))
axes = axes.flatten()

for i, uid in enumerate(uids):
    ax = axes[i]

    # cloaking area
    cloaking_geom_True[
        cloaking_geom_True['rank_uid'] == uid
    ].plot(
        ax=ax,
        color='black',
        alpha=0.15,   
        edgecolor='black'
    )

    # centroids
    TrueClusterCentroid[
        TrueClusterCentroid['rank_uid'] == uid
    ].plot(
        ax=ax,
        color='red',
        markersize=500   
    )


    # annotating
    if not TrueClusterCentroid.empty:
        point = TrueClusterCentroid.geometry.iloc[2] 

        x, y = point.x, point.y

        txt = ax.annotate(
            text=f"Significant location\n of swapped trajectory",
            xy=(x+10, y+10),
            xytext=(x + 25, y + 150), 
            arrowprops=dict(arrowstyle="-|>", color='black', linewidth=2, mutation_scale=45),
            fontsize=24
        )

        txt.set_path_effects([
            path_effects.Stroke(linewidth=4, foreground='white'),
            path_effects.Normal()
        ])

        txt.arrow_patch.set_path_effects([
            path_effects.Stroke(linewidth=6, foreground='white'),
            path_effects.Normal()
        ])

    #ax.set_title(f"rank_uid = {uid}")
    ax.set_axis_off()

plt.tight_layout()
plt.show()



#%% individual plots: intersection
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects

uids = sorted(new_SigLoc_True_nodes['rank_uid'].unique())

fig, axes = plt.subplots(2,1, figsize=(6, 6))
axes = axes.flatten()

for i, uid in enumerate(uids):
    ax = axes[i]

    # cloaking area
    cloaking_geom_True_nodes[
        cloaking_geom_True_nodes['rank_uid'] == uid
    ].plot(
        ax=ax,
        color='black',
        alpha=0.15,   
        edgecolor='black'
    )

    # centroids
    new_SigLoc_True_nodes[
        new_SigLoc_True_nodes['rank_uid'] == uid
    ].plot(
        ax=ax,
        color='red',
        markersize=500   
    )


    # annotating
    if not new_SigLoc_True_nodes.empty:
        point = new_SigLoc_True_nodes.geometry.iloc[1] 

        x, y = point.x, point.y

        txt = ax.annotate(
            text=f"Significant location\n of swapped trajectory",
            xy=(x+10, y+10),
            xytext=(x + 25, y + 150), 
            arrowprops=dict(arrowstyle="-|>", color='black', linewidth=2, mutation_scale=45),
            fontsize=24
        )

        txt.set_path_effects([
            path_effects.Stroke(linewidth=4, foreground='white'),
            path_effects.Normal()
        ])

        txt.arrow_patch.set_path_effects([
            path_effects.Stroke(linewidth=6, foreground='white'),
            path_effects.Normal()
        ])

    #ax.set_title(f"rank_uid = {uid}")
    ax.set_axis_off()

plt.tight_layout()
plt.show()


#%% plot: edge
# new_SigLoc_True_edges
# cloaking_geom_True_edges 

uids = sorted(new_SigLoc_True_edges['rank_uid'].unique())

fig, axes = plt.subplots(2,2, figsize=(12, 12))
axes = axes.flatten()

for i, uid in enumerate(uids):
    ax = axes[i]

    # cloaking area
    cloaking_geom_True_edges[
        cloaking_geom_True_edges['rank_uid'] == uid
    ].plot(
        ax=ax,
        color='black',
        alpha=0.15,   
        edgecolor='black'
    )

    # centroids
    new_SigLoc_True_edges[
        new_SigLoc_True_edges['rank_uid'] == uid
    ].plot(
        ax=ax,
        color='red',
        markersize=500   
    )


    # annotating
    if not new_SigLoc_True_edges.empty:
        point = new_SigLoc_True_edges.geometry.iloc[2] 

        x, y = point.x, point.y

        txt = ax.annotate(
            text=f"Significant location\n of swapped trajectory",
            xy=(x+10, y+10),
            xytext=(x + 25, y + 150), 
            arrowprops=dict(arrowstyle="-|>", color='black', linewidth=2, mutation_scale=45),
            fontsize=24
        )

        txt.set_path_effects([
            path_effects.Stroke(linewidth=4, foreground='white'),
            path_effects.Normal()
        ])

        txt.arrow_patch.set_path_effects([
            path_effects.Stroke(linewidth=6, foreground='white'),
            path_effects.Normal()
        ])

    #ax.set_title(f"rank_uid = {uid}")
    ax.set_axis_off()

plt.tight_layout()
plt.show()


#%% have one plot for all swapping methods! (if there is only 4 within the cloakin ggeom)
# problematic user:  ['0d5010abd3d6f0bcd8cee8c66cb58784af4357a1']
