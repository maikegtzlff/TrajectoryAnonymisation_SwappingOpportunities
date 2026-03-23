#%% same for filled trajectories, i.e. cloaked but NOT swapped
#import geopandas as gpd
# not clustered yet
#stop_points_t_filled = gpd.read_parquet(r"D:\paper3\Data\output\Evaluation_HomeDetection/cloakedFilledReleaseP2_StopPoints.parquet")
#stop_points_t_filled.stop_id.isna().any() # False
#stop_points_t_filled.head() # 74,442,390 stop points

##########################################################################################
#%% must double check stop points
##########################################################################################
#%% look at  t_filled
import pandas as pd
import geopandas as gpd 

t_filled = gpd.read_parquet(r"d:\paper3\Data\trajectories\traj_filled_baseline_ShiftedTimestamps_gapAware_CloakingGeomID_AllCloakingAreas_clean.parquet") 
print(len(t_filled)) # 7,334,941 - more stop points than t_filled points!
# stop points are wrong

print(t_filled['unix_timestamp_final'].dtype)
t_filled['unix_timestamp_final'] = pd.to_datetime(
    t_filled['unix_timestamp_final'], unit='s'
)
print(t_filled['unix_timestamp_final'].dtype)

#%%
sorted(t_filled.columns)

#%%
t_filled[['tid', 'tid_subid', 'unix_timestamp_final']].head()



#%% cloaking and filled...
print(t_filled.uid.nunique()) # 97
print(t_filled.uid.isna().any()) # False
print(t_filled.uid.unique()) # synthetic points must have bee assigned their matching uid

#%%
print(t_filled.unix_timestamp_final.isna().any()) # False, good
print(t_filled.tid_subid.isna().any()) # False, good
print(t_filled.geometry)
print(t_filled.match_geometry.isna().any()) # False, good


#%%
print(t_filled.crs)
t_filled = t_filled.to_crs(2193)
print(t_filled.crs)

#%%
import movingpandas as mpd
# stop points first
t_filled_tc = mpd.TrajectoryCollection(
    t_filled,
    traj_id_col='tid_subid',
    t='unix_timestamp_final'
)

print(t_filled_tc) # TrajectoryCollection with 19021 trajectories

#%% stop detection
from datetime import datetime, timedelta
# 3 minutes, 65meters - based on chapter 1 parameters
detector = mpd.TrajectoryStopDetector(t_filled_tc)

stop_points_t_filled = detector.get_stop_points(min_duration=timedelta(seconds=180), max_diameter=65)

print('number of stop points detected', len(stop_points_t_filled))

# before:
# number of stop points detected 0
# and 
# stop_points_t_filled.head() # 74,442,390 stop points

# now, 51 minutes,
# 117,124 points

#%% export stop points
stop_points_t_filled.head()

#%%
print(type(stop_points_t_filled))
#%%
stop_points_t_filled = stop_points_t_filled.reset_index()
stop_points_t_filled.head()

#%%
stop_points_t_filled = stop_points_t_filled.set_crs(2193)
print(stop_points_t_filled.crs)

stop_points_t_filled['uid'] = stop_points_t_filled['traj_id'].str.split("_").str[1]
print(stop_points_t_filled['uid'].nunique())
print(stop_points_t_filled['uid'].unique())

stop_points_t_filled.to_parquet(r"D:\paper3\Data\output\Evaluation_HomeDetection/cloakedFilledReleaseP3_final_StopPoints.parquet")

#%% must cluster stop points
import os
os.chdir(r"D:\paper3")

import s_clustering_final as cstp

cstp.cluster_users_to_parquet_resumable(
    stop_points_t_filled,
    radius_km=0.06,
    min_points=4,
    output_dir=r"D:\paper3\Data\SWAPPEDTRAJECTORIES\StopPoints\Clustering\tFilled"
)

#%% no problemativ ones, files have been created in folder
# look at the output
import glob
import os

# look at clustered stayp points of trajectories swapped at cloaking areas first
input_dir=r"D:\paper3\Data\SWAPPEDTRAJECTORIES\StopPoints\Clustering\tFilled" # 97 items, aka 97 users

files = glob.glob(os.path.join(input_dir, "*.parquet"))

gdfs = [gpd.read_parquet(f) for f in files]
clusteredStopPoints_tfilled= pd.concat(gdfs, ignore_index=True)
clusteredStopPoints_tfilled # 84,646 rows

#%%
clusteredStopPoints_tfilled.to_parquet(r"D:\paper3\Data\SWAPPEDTRAJECTORIES\StopPoints\Clustering/t_filled_clusteredStoppoints.parquet")

#%%
clusteredStopPoints_tfilled.crs
#%%
clusteredStopPoints_tfilled = clusteredStopPoints_tfilled.to_crs(2193)
ranked_clusteredStopPoints_tfilled = cstp.rank_clusters(clusteredStopPoints_tfilled)
ranked_clusteredStopPoints_tfilled

#%%
ranked_clusteredStopPoints_tfilledtop2 = ranked_clusteredStopPoints_tfilled[ranked_clusteredStopPoints_tfilled['rank'] <= 2]
ranked_clusteredStopPoints_tfilledtop2['HomeWork'] = ranked_clusteredStopPoints_tfilledtop2['rank'].map({1: 'home', 2: 'work'})
ranked_clusteredStopPoints_tfilledtop2 # 190 rows

#%% find centroids of clusters
clusteredStopPoints_tfilled_centroids = (
    clusteredStopPoints_tfilled.groupby('cluster_id')['geometry']
    .apply(lambda x: x.unary_union.centroid)
    .reset_index()
)

clusteredStopPoints_tfilled_centroids = gpd.GeoDataFrame(clusteredStopPoints_tfilled_centroids, geometry='geometry', crs=2193)

print(len(clusteredStopPoints_tfilled_centroids))
print(clusteredStopPoints_tfilled_centroids.cluster_id.nunique())

clusteredStopPoints_tfilled_centroids.head()

#%%
print(len(ranked_clusteredStopPoints_tfilledtop2))
ranked_clusteredStopPoints_tfilledtop2 = clusteredStopPoints_tfilled_centroids[['cluster_id', 'geometry']].merge(ranked_clusteredStopPoints_tfilledtop2, on='cluster_id', how='right')
print(len(ranked_clusteredStopPoints_tfilledtop2))

ranked_clusteredStopPoints_tfilledtop2

#%%
ranked_clusteredStopPoints_tfilledtop2.to_parquet(r"D:\paper3\Data\SWAPPEDTRAJECTORIES\StopPoints\Clustering/ranked_clusteredStopPoints_tfilledtop2.parquet")




#%% must get rank_uid
ranked_clusteredStopPoints_tfilledtop2['tfilled_rank_uid'] = ranked_clusteredStopPoints_tfilledtop2['rank'].astype(int).astype(str) + '_' + ranked_clusteredStopPoints_tfilledtop2['uid']
ranked_clusteredStopPoints_tfilledtop2[['rank', 'uid', 'tfilled_rank_uid']].head()


#%% uid is orig uid
# create dictonary: no contributing uids


#############
#%% prep data

#%% group geometryies by uid (becuase we have 2 sig per user)
cloaking_geom = gpd.read_file(r"\\tsclient\R\paper3\Data\swappedtrajs\StopPoints\clusteringStopPointsPostSwapping\polys.gpkg")
print(cloaking_geom.crs)
#%%
cloaking_geom = cloaking_geom.to_crs(2193)
print(cloaking_geom.crs)
#%%
cloaking_geom = cloaking_geom.drop(columns=['uid'])
cloaking_geom = cloaking_geom.rename(columns={'rank_uid': 'orig_rank_uid'})
cloaking_geom.head()
#%%
cloaking_geom = cloaking_geom.rename(columns={'orig_uid': 'uid'})
cloaking_geom.head()
#%%
# 2 points × 2 polygons = 4 comparisons
tfilled_intersect = ranked_clusteredStopPoints_tfilledtop2.merge(
    cloaking_geom,
    on='uid',  
    suffixes=('_pt', '_poly')
)

tfilled_intersect['intersects'] = tfilled_intersect.geometry_pt.intersects(tfilled_intersect.geometry_poly)

tfilled_intersect['intersects'].value_counts()

#
#intersects
#False    374
#True       6


#%% look at the True intersect one - how many different container_uid are involved?
print(tfilled_intersect[tfilled_intersect['intersects']==True]['uid'].nunique()) # 5
# 47 out of 97 users have at least one significant location intersecting with one of their contributor's significant locations
# less than half..

tfilled_reidentified = tfilled_intersect[tfilled_intersect['intersects']==True]
print(len(tfilled_reidentified)) #6

print(tfilled_reidentified.orig_rank_uid.nunique()) # 6 THIS IS THE IMPORTANT ONE: number of significant locations "re-identified"
print(tfilled_reidentified.tfilled_rank_uid.nunique()) # 6 how many new frequent locations "expose" these signfiicant locations? i.e., how often is a sig loc epxosed?






#%% how often are specific original significant locations re-identified?
tfilled_reidentified.groupby(['orig_rank_uid']).size().sort_values(ascending=False)

#contributor_rank_uid
# shows the 6 locations, sums up to 6
#1_0d105d8c884c653542c76c25aee0bcf4dd040e7e    1
#1_0d5010abd3d6f0bcd8cee8c66cb58784af4357a1    1
#1_395f27c5f3520fe7bac57d9bdeb34ae458550223    1
#2_0d105d8c884c653542c76c25aee0bcf4dd040e7e    1
#2_5f0d79bddb4fdacfac9de60263266c7d73317f0a    1
#2_d8e1b548c25df0c24d8d8d493d4e6db0ad25c792    1

#%% look at these manually
tfilled_freq = tfilled_reidentified['orig_rank_uid'].value_counts()
tfilled_reidentified_sorted = tfilled_reidentified.set_index('orig_rank_uid').loc[tfilled_freq.index].reset_index()
tfilled_reidentified_sorted[['orig_rank_uid', 'tfilled_rank_uid', 'uid']] 
# same user, both new sig loc reidentiy the SAME ONE ORIG location (not always, but one scenario)
# --> "significant locations" of "new" user must be close together, if they both "re-identify" the same original signficant location



#%% want to map those locations and the cloaking geometry


import geopandas as gpd

tfilled_reidentified['geompt_4326'] = gpd.GeoSeries(tfilled_reidentified['geometry_pt'], crs=2193).to_crs(4326)
tfilled_reidentified['geompoly_4326'] = gpd.GeoSeries(tfilled_reidentified['geometry_poly'], crs=2193).to_crs(4326)

import folium

center = [
    tfilled_reidentified['geompt_4326'].y.mean(),
    tfilled_reidentified['geompt_4326'].x.mean()
]

m = folium.Map(location=center, zoom_start=13)

folium.GeoJson(
    gpd.GeoDataFrame(geometry=tfilled_reidentified['geompt_4326']),
    name="t filled",
    style_function=lambda x: {"color": "blue"}
).add_to(m)

folium.GeoJson(
    gpd.GeoDataFrame(geometry=tfilled_reidentified['geompoly_4326']),
    name="sig loc",
    style_function=lambda x: {"color": "red"}
).add_to(m)

folium.LayerControl().add_to(m)

import webbrowser
file_path = "map.html"
m.save(file_path)
webbrowser.open(file_path)


#%% sig loc "identifed" after edge/node/cloaking area swapping
cloaking_geom_ri = gpd.read_parquet(r'D:\paper3\Data\SWAPPEDTRAJECTORIES\StopPoints\SigLocReidentification/cloaking_geom_ri.parquet')
cloaking_geom_ri


#%% are the tfilled ones the same?
extra_unique = pd.Series(tfilled_reidentified['orig_rank_uid'].unique())

included = extra_unique.isin(cloaking_geom_ri['contributor_rank_uid']).sum()
not_included = (~extra_unique.isin(cloaking_geom_ri['contributor_rank_uid'])).sum()

print(included) # 4 are the same 
print(not_included) # 2 not (i.e must add 2 to list)




