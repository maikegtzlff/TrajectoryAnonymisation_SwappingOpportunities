#%% load libraries
import pandas as pd
import geopandas as gpd
import movingpandas as mpd
import shapely as shp
#import hvplot.pandas

from geopandas import GeoDataFrame, read_file
from shapely.geometry import Point, LineString, Polygon
from datetime import datetime, timedelta
#from holoviews import opts

import warnings

warnings.filterwarnings("ignore")

mpd.show_versions()

#%% load data and create trajectories
#gdf = gpd.read_parquet(r"e:\paper2\Data\shortestpath_output\syntheticTrajPoints\traj_filled_baseline_ShiftedTimestamps_gapAware.parquet")
# look at other trajectory versions
# no distinction between syn and raw
#gdf = gpd.read_parquet(r"e:\paper2\Data\shortestpath_output\syntheticTrajPoints\traj_filled_RELEASE.parquet")
gdf = gpd.read_parquet(r"e:\paper2\Data\shortestpath_output\syntheticTrajPoints\filled_origPointId.parquet")
print(len(gdf))
gdf.head() 


# orig point id = id + unix timestamp
print(gdf.orig_point_id.isna().any()) # has na --> na = synthetic point
print(gdf.point_id.isna().any())


gdf[['orig_point_id','point_id', 'tid_subid', 'speed_source', 'osmid_best']].head()
#%%
print((gdf['orig_point_id'].notna() == gdf['speed_source'].isna()).all().all()) # whenever there is an original point id, there is not speed source (True, good)
print((gdf['orig_point_id'].isna() == gdf['speed_source'].notna()).all().all()) # and the other way round, when there is no orig point id (aka point is synthetic), there is always a speed source attribute (because the point is synthetic),good
#%%
gdf[['orig_point_id', 'speed_source']]

#%% add a new column to clearly distinguish raw from synthetic points 
import numpy as np
gdf['RawVsSyn'] = np.where(gdf['orig_point_id'].isna(), 'synthetic', 'raw')
gdf.head() 

#%% columns of interest
#tid_subid, osmid_best and RawVsSyn
# have a "segmented"tid, i.e. by osmid_best
# gdf['tid_subid'] is date plus uid plus a number
gdf['tid_segmented'] = gdf['tid_subid'] + '_edge_' + gdf['osmid_best'] # all tids on the same edge have the same tid
gdf.head() 


#%% make a copy of the timestamp columns
gdf['unix_timestamp_final'] = gdf['unix_timestamp'] 


#%% create trajectories
#tc = mpd.TrajectoryCollection(gdf, "tid_segmented", t="unix_timestamp")
tc = mpd.TrajectoryCollection(gdf, "tid_subid", t="unix_timestamp")
tc # TrajectoryCollection with 1,091,756 trajectories
# silently droopping points unless:
# must have at least 2 >points per tid...
# must have valid timestamps
# non-empty geometries



#%% export as lines (easier to look at)
tc_lines = tc.to_line_gdf()
tc_lines.head()

#%%
print(len(tc_lines)) #              4,515,512
tc_lines.tid_segmented.nunique() #  1,091,756 --> multiple lines have the same tid

#%% add hour of day columns
import pandas as pd

tc_lines["hour_akl"] = (
    pd.to_datetime(tc_lines["unix_timestamp_final"], unit="s", utc=True)
      .dt.tz_convert("Pacific/Auckland")
      .dt.hour
)
tc_lines.head()

#%%
import numpy as np

tc_lines["time_period"] = np.where(
    (tc_lines["hour_akl"] >= 7) & (tc_lines["hour_akl"] < 9),
    "morning peak",
    np.where(
        (tc_lines["hour_akl"] >= 9) & (tc_lines["hour_akl"] < 16),
        "flat peak",
        np.where(
            (tc_lines["hour_akl"] >= 16) & (tc_lines["hour_akl"] < 20),
            "evening peak",
            "night time"
        )
    )
)

tc_lines.head()


#%% export 
#tc_lines.to_parquet(r"E:\paper3\data/filled_origPointId_Lines_SegmentedByEdge.parquet")
#tc_lines.to_parquet(r"E:\paper3\data/filled_origPointId_Lines.parquet")
tc_lines.to_parquet(r"E:\paper3\data/filled_origPointId_Lines_timestamps.parquet")






#%% swapping at nodes, i.e. the one in st Marys bay
import geopandas as gpd
print(gpd.__version__)
#t1 = gpd.read_file(r"e:\paper3\data\SampleTids\SwappingAtNodes\20191214_fbe906873514e9223ef147d6b827dd559c378aa7_3031.gpkg")
t1 = gpd.read_file(r"E:/paper3/data/SampleTids/SwappingAtNodes/t1.geojson")
t2 = gpd.read_file(r"e:\paper3\data\SampleTids\SwappingAtNodes\20200603_fb81403777a9bb326af83b6132c747d414ab0a12_6016_points.gpkg")
t2.head()
#%% must find nodes for each edge
#  nodes are part of my edge/graph data
#from joblib import load
#G = load(r"D:\paper2\Data\Output\cloaking_2sig_100150\traj_cloaked_anotated_mapmatched\OriginDestination_CloakingAreas\NetworkShortestPath\graph.joblib")

nodes = gpd.read_parquet(r"D:\paper2\Data\Output\cloaking_2sig_100150\traj_cloaked_anotated_mapmatched\OriginDestination_CloakingAreas\NetworkShortestPath/nodes.parquet")
edges = gpd.read_parquet(r"D:\paper2\Data\Output\cloaking_2sig_100150\traj_cloaked_anotated_mapmatched\OriginDestination_CloakingAreas\NetworkShortestPath/edges.parquet")
edges.head() # id is osmid, u and v are nodes,  (maxspeed)
#%%
nodes.head() # id casn be either u or v in edges (depending on orientation)

#%% look at map-matched points
#t_mm = gpd.read_parquet(r'd:\paper2\Data\Output\cloaking_2sig_100150\traj_cloaked_anotated_mapmatched\traj_mm.parquet')
#print(t_mm.columns)
#t_mm.head()


#%% assigning u and v to map-matched points
edges['osmid_uv'] = edges['id'].astype('str') + '_' + edges['u'].astype('str')  + '_' + edges['v'].astype('str') 
edges.head()

#%% get all nodes on edge
import numpy as np

nodesOnEdge_dict = (
    edges
    .groupby("id", sort=False)
    .apply(lambda g: list(map(int, g["u"].tolist() + [g["v"].iloc[-1]])))
    .to_dict()
)


nodesOnEdge_dict

#%% get u and v for each point
print(t1.crs)
edges = edges.to_crs(t1.crs)
print(edges.crs)

#%%
# only interested in osmid_uv (and geometry)
lines_gdf = edges[['osmid_uv', 'geometry']].copy()

points_with_lines = gpd.sjoin_nearest(
    t1,
    lines_gdf,
    how="left",
    distance_col="dist_to_line"
)

points_with_lines # accept duplicates, as long as dist_to_line is 0 and osmid of somid_uv is the sme
# they dont have an osmid_best because they are synthetic - why?
# but then I'd have two points with the same geometry. I want to keep the u v information. not the geometries

#compare osmid_best with new osmid
print((points_with_lines.osmid_best == points_with_lines.osmid_uv).any()) # false - yes because some have no best osmid
points_with_lines[['osmid_uv_osmid', 'u', 'v']] = points_with_lines['osmid_uv'].str.split('_', expand=True)
points_with_lines[['osmid_uv_osmid', 'u', 'v']] = points_with_lines[['osmid_uv_osmid', 'u', 'v']].astype(int)

print(points_with_lines.dist_to_line.median())  # 0.17
print(points_with_lines.dist_to_line.min())     # 0
print(points_with_lines.dist_to_line.max())     # 0.73
points_with_lines.head() # dist to line way too large

# Group by point_id and combine u and v into lists
points_combined = points_with_lines.groupby('point_id').agg({
    'u': lambda x: list(x),
    'v': lambda x: list(x),
    'osmid_uv': 'first',                 
    'dist_to_line': 'first'              
}).reset_index()

# Optional: flatten v into the u list if you want
points_combined['u'] = points_combined.apply(lambda row: row['u'] + row['v'], axis=1)
points_combined = points_combined.drop(columns='v')

# join back to df
points_combined = points_combined.rename(columns={'u': 'point_nodes_inbetween'})
t1 = t1.merge(points_combined, on='point_id', how='left')
t1.head()



#%%
points_with_lines_1 = points_with_lines.copy()

#%% now do the same for t2
# only interested in osmid_uv (and geometry)
points_with_lines = gpd.sjoin_nearest(
    t2,
    lines_gdf,
    how="left",
    distance_col="dist_to_line"
)

print(len(t2))
points_with_lines # accept duplicates (5), as long as dist_to_line is 0 and osmid of somid_uv is the sme
# they dont have an osmid_best because they are synthetic - why?
# but then I'd have two points with the same geometry. I want to keep the u v information. not the geometries


# compare osmid_best with new osmid
print((points_with_lines.osmid_best == points_with_lines.osmid_uv).any()) # false - yes because some have no best osmid
points_with_lines[['osmid_uv_osmid', 'u', 'v']] = points_with_lines['osmid_uv'].str.split('_', expand=True)
points_with_lines[['osmid_uv_osmid', 'u', 'v']] = points_with_lines[['osmid_uv_osmid', 'u', 'v']].astype(int)

print(points_with_lines.dist_to_line.median())  # 0.15
print(points_with_lines.dist_to_line.min())     # 0
print(points_with_lines.dist_to_line.max())     # 1.02
points_with_lines.head() # dist to line way too large

#%% get uv for each tid_subid
# again, as dictionary? drop duplicates?

# %%
# Group by point_id and combine u and v into lists
points_combined = points_with_lines.groupby('point_id').agg({
    'u': lambda x: list(x),
    'v': lambda x: list(x),
    'osmid_uv': 'first',                 
    'dist_to_line': 'first'              
}).reset_index()

# Optional: flatten v into the u list if you want
points_combined['u'] = points_combined.apply(lambda row: row['u'] + row['v'], axis=1)
points_combined = points_combined.drop(columns='v')

# join back to df
points_combined = points_combined.rename(columns={'u': 'point_nodes_inbetween'})
t2 = t2.merge(points_combined, on='point_id', how='left')
t2.head()

#%% compare the two point_nodes_inbetween/ keep matching ones
# Convert list to tuple in both DataFrames
#t1['point_nodes_inbetween'] = t1['point_nodes_inbetween'].apply(lambda x: tuple(x) if isinstance(x, list) else x)
#t2['point_nodes_inbetween'] = t2['point_nodes_inbetween'].apply(lambda x: tuple(x) if isinstance(x, list) else x)

# j

#so_edge = t1.merge(t2, on='point_nodes_inbetween', how='inner')# so swapping opportunitiy
so_edge = t1.merge(t2, on='point_nodes_inbetween', how='inner')# so swapping opportunitiy

so_edge # 96 rows - but I can't do this for every trajectory combination
# but onley so_edge.point_nodes_inbetween.nunique()

#%% or merge them based on osmid_uv
so_edge_uv = points_with_lines_1.merge(points_with_lines, on='osmid_uv', how='inner')# so swapping opportunitiy
so_edge_uv.osmid_uv.nunique() # print 43
so_edge_uv # also 96 rows

# same as based ons point_nodes_inbetween



#%%
# 1️⃣ Ensure point_nodes_inbetween is hashable (tuple) in both
t1['point_nodes_inbetween'] = t1['point_nodes_inbetween'].apply(lambda x: tuple(x) if isinstance(x, list) else x)
t2['point_nodes_inbetween'] = t2['point_nodes_inbetween'].apply(lambda x: tuple(x) if isinstance(x, list) else x)

# 2️⃣ Merge t1 with t2 to get matching tid_subid and point_id
t1_swaps = t1.merge(
    t2[['point_nodes_inbetween', 'tid_subid', 'point_id']],
    on='point_nodes_inbetween',
    how='left',   # keep all rows in t1
    suffixes=('', '_swap')  # columns from t2 get _swap
)

# 3️⃣ Create the swapping opportunity columns
t1_swaps['swapping_opportunitiy_tid'] = t1_swaps['tid_subid_swap']
t1_swaps['swapping_opportunitiy_point_id'] = t1_swaps['point_id_swap']

# 4️⃣ Drop the temporary merge columns
t1_swaps = t1_swaps.drop(columns=['tid_subid_swap', 'point_id_swap'])

# ✅ Same for t2
t2_swaps = t2.merge(
    t1[['point_nodes_inbetween', 'tid_subid', 'point_id']],
    on='point_nodes_inbetween',
    how='left',
    suffixes=('', '_swap')
)
t2_swaps['swapping_opportunitiy_tid'] = t2_swaps['tid_subid_swap']
t2_swaps['swapping_opportunitiy_point_id'] = t2_swaps['point_id_swap']
t2_swaps = t2_swaps.drop(columns=['tid_subid_swap', 'point_id_swap'])
t2_swaps[t2_swaps.swapping_opportunitiy_tid.notna()] #96 rows

#%%
t1_swaps.to_parquet(r"E:\paper3\data\SampleTids\SwappingAtNodes/t1_swappingopportunitiesTot2.parquet")
t2_swaps.to_parquet(r"E:\paper3\data\SampleTids\SwappingAtNodes/t2_swappingopportunitiesTot1.parquet")



#%% work with dictonaries instead
# (1) builidng a loopuk dictonary for the trajectory of interest
import pandas as pd
# Ensure hashable keys
t2['point_nodes_inbetween'] = t2['point_nodes_inbetween'].apply(lambda x: tuple(x) if isinstance(x, list) else x)

# Create a dictionary
swap_lookup_t2 = dict(zip(t2['point_nodes_inbetween'], zip(t2['tid_subid'], t2['point_id'])))


# (2) apply the lookup to trajectory 1
# Make sure t1 keys are hashable
t1['point_nodes_inbetween'] = t1['point_nodes_inbetween'].apply(lambda x: tuple(x) if isinstance(x, list) else x)

# Use .map() to create the new columns
t1[['swapping_opportunitiy_tid', 'swapping_opportunitiy_point_id']] = t1['point_nodes_inbetween'].map(
    lambda k: swap_lookup_t2.get(k, (None, None))
).apply(pd.Series)

#%% (3) and look for t3
# Suppose you have t3
t3['point_nodes_inbetween'] = t3['point_nodes_inbetween'].apply(lambda x: tuple(x) if isinstance(x, list) else x)
swap_lookup_t3 = dict(zip(t3['point_nodes_inbetween'], zip(t3['tid_subid'], t3['point_id'])))

# Update t1 columns only where they are still None
t1['swapping_opportunitiy_tid'] = t1.apply(
    lambda row: swap_lookup_t3[row['point_nodes_inbetween']][0]
                if pd.isna(row['swapping_opportunitiy_tid']) and row['point_nodes_inbetween'] in swap_lookup_t3
                else row['swapping_opportunitiy_tid'],
    axis=1
)
t1['swapping_opportunitiy_point_id'] = t1.apply(
    lambda row: swap_lookup_t3[row['point_nodes_inbetween']][1]
                if pd.isna(row['swapping_opportunitiy_point_id']) and row['point_nodes_inbetween'] in swap_lookup_t3
                else row['swapping_opportunitiy_point_id'],
    axis=1
)

# but this only adds opportuntities for swaps with t3 if there is no opportunity for this points to be swapped with t2



#%% append swapping opportuntities instead.
t1['swapping_opportunitiy_tid'] = [[] for _ in range(len(t1))]
t1['swapping_opportunitiy_point_id'] = [[] for _ in range(len(t1))]

def append_swaps(target, source):
    lookup = {}
    for k, tid, pid in zip(
        source['point_nodes_inbetween'],
        source['tid_subid'],
        source['point_id']
    ):
        lookup.setdefault(k, []).append((tid, pid))

    for i, k in target['point_nodes_inbetween'].items():
        if k in lookup:
            tids, pids = zip(*lookup[k])
            target.at[i, 'swapping_opportunitiy_tid'].extend(tids)
            target.at[i, 'swapping_opportunitiy_point_id'].extend(pids)

# Apply in order
append_swaps(t1, t2)
# look at swapping oppotunities
#t1[t1['swapping_opportunitiy_tid'].apply(len) > 0]
print((t1['swapping_opportunitiy_tid'].str.len() > 0).sum()) # 77, that is less than before
print((t1['swapping_opportunitiy_tid'].str.len() >1).sum()) # 13, some points have more than one match - good, just one point geomerty but all matching opportunities :)
print((t1['swapping_opportunitiy_tid'].str.len().max())) # 3 = some points have up to 3 swapping opportunities with t2


#%% find opportunities with t3
t3=gpd.read_file(r'E:/paper3/data/SampleTids/SwappingAtNodes/t3_20200212_f6f64a1846eb2f50552c23394c64a02663acadbc_4362_points.gpkg')
# must find nodes inbetween points first
# only interested in osmid_uv (and geometry)
points_with_lines = gpd.sjoin_nearest(
    t3,
    lines_gdf,
    how="left",
    distance_col="dist_to_line"
)


# compare osmid_best with new osmid
print((points_with_lines.osmid_best == points_with_lines.osmid_uv).any()) # false - yes because some have no best osmid
points_with_lines[['osmid_uv_osmid', 'u', 'v']] = points_with_lines['osmid_uv'].str.split('_', expand=True)
points_with_lines[['osmid_uv_osmid', 'u', 'v']] = points_with_lines[['osmid_uv_osmid', 'u', 'v']].astype(int)

print(points_with_lines.dist_to_line.median())  # 0.15
print(points_with_lines.dist_to_line.min())     # 0
print(points_with_lines.dist_to_line.max())     # 1.02

# Group by point_id and combine u and v into lists
points_combined = points_with_lines.groupby('point_id').agg({
    'u': lambda x: list(x),
    'v': lambda x: list(x),
    'osmid_uv': 'first',                 
    'dist_to_line': 'first'              
}).reset_index()

# Optional: flatten v into the u list if you want
points_combined['u'] = points_combined.apply(lambda row: row['u'] + row['v'], axis=1)
points_combined = points_combined.drop(columns='v')

# join back to df
points_combined = points_combined.rename(columns={'u': 'point_nodes_inbetween'})
t3 = t3.merge(points_combined, on='point_id', how='left')
t3.head()
#%%
t3['point_nodes_inbetween'] = t3['point_nodes_inbetween'].apply(lambda x: tuple(x) if isinstance(x, list) else x)

append_swaps(t1, t3)
print((t1['swapping_opportunitiy_tid'].str.len() > 0).sum()) # 96, that is 3 more than on t2 alone

#%% code above is not taking direction of travel or time into account, neither repeated swaps with the same other trajector/user