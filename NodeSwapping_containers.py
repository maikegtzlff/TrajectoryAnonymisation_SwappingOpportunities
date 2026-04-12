#%%
import geopandas as gpd

#%% identify nodes that are intersections
#  nodes are part of my edge/graph data
nodes = gpd.read_parquet(r"D:\paper2\Data\Output\cloaking_2sig_100150\traj_cloaked_anotated_mapmatched\OriginDestination_CloakingAreas\NetworkShortestPath/nodes.parquet")
nodes.head() # id casn be either u or v in edges (depending on orientation)
# no street count attribute

#edges = gpd.read_parquet(r"D:\paper2\Data\Output\cloaking_2sig_100150\traj_cloaked_anotated_mapmatched\OriginDestination_CloakingAreas\NetworkShortestPath/edges.parquet")
#edges.head() # id is osmid, u and v are nodes,  (maxspeed)

#%% look at Graph
from joblib import load
G = load(r"D:\paper2\Data\Output\cloaking_2sig_100150\traj_cloaked_anotated_mapmatched\OriginDestination_CloakingAreas\NetworkShortestPath\graph.joblib")
#%%
import networkx as nx

# Check if the graph is directed
if G.is_directed():
    print("G is a directed graph") # directed
else:
    print("G is an undirected graph")

#%%
import networkx as nx
import pandas as pd

# Get degree of all nodes
degrees = dict(G.degree()) # total degree of each node (in and out)
# directed count
#in_deg = dict(G.in_degree())
#out_deg = dict(G.out_degree())


# Convert to DataFrame
df_degree = pd.DataFrame.from_dict(degrees, orient='index', columns=['street_count'])
df_degree.reset_index(inplace=True)
df_degree.rename(columns={'index': 'node_id'}, inplace=True)
df_degree

#%% label intersections
import numpy as np
df_degree['intersection'] = np.where(df_degree['street_count'] > 2, True, False)
df_degree.head()



#%% add intersection classification to trajectories
import geopandas as gpd
gdf = gpd.read_parquet(r"E:\paper3\data\trajectories_list/trajectories_filled_gdf_preppedForSwapping.parquet")
gdf.rename(columns={'point_id_t': 'point_id'}, inplace=True)
assert gdf['point_id'].is_unique, "point_id is not unique! Check initialization."

#%% add intersection information to gdf
intersection_map = df_degree.set_index('node_id')['intersection'].to_dict()

gdf['u'] = gdf['u'].astype(int)
gdf['v'] = gdf['v'].astype(int)

gdf['u_intersection'] = gdf['u'].map(intersection_map)
gdf['v_intersection'] = gdf['v'].map(intersection_map)
gdf.head()

#%%
gdf['u_intersection_id'] = np.where(gdf['u_intersection'], gdf['u'], np.nan)
gdf['v_intersection_id'] = np.where(gdf['v_intersection'], gdf['v'], np.nan)
gdf.head()


#%% export df
gdf.to_parquet(r"E:\paper3\data\trajectories_list/trajectories_filled_gdf_preppedForSwapping_Intersections.parquet")

#%%
#%%
gdf.columns # I have u and v, but no edge --> must identify last v based on timestamp order

#%% add identifier for swap - i.e., last point on edge
gdf = gdf.sort_values(['tid_subid', 'unix_timestamp'])

gdf['v_intersection_id_swap'] = np.where(
    (gdf['v_intersection'] == True) &
    (gdf['v'] != gdf.groupby('tid_subid')['v'].shift(-1)),
    gdf['v'],
    np.nan
)

gdf.head(100)

# don't think I am actually using these, marking node arrival instead in code chunk below

#%% working with utils file
import os
os.chdir(r"D:\paper3")


import utils_NodeSwapping_containers as nsw
from collections import deque
import time

import importlib
importlib.reload(nsw) 

#%%# --------------------------
# build containers from trajectories
# --------------------------
print("Building containers from trajectories...")
containers = nsw.build_containers_from_gdf(gdf, swap_mode='node')
print(f"Built {len(containers)} containers.")

#%% save containers for reloading
import pickle
with open(r"D:\paper3\Data\filled_trajectories_list/containers_node_swapping.pkl", "wb") as f:
    pickle.dump(containers, f)

#%% --------------------------
# multi-iteration node swaps
# --------------------------
import importlib
importlib.reload(nsw) 

print("Running node swaps (queue-based)...")
start_time = time.time()
swap_log = nsw.run_node_swaps_queue_incremental(containers, print_every=500)
print(f"Node swaps completed in {(time.time() - start_time)/60:.2f} minutes.")
print(f"Total swaps: {len(swap_log)}")

# save swap log
swap_log_df = pd.DataFrame(swap_log)
swap_log_df.to_parquet(r"D:\paper3\Data\filled_trajectories_list/swap_log_node.parquet", index=False)

# 478.28 minutes run time --> 8 hours
#Total swaps: 186212


#%% get total points involved in swaps and average points moved per swap
# Total points involved in all swaps
total_points = swap_log_df['points_moved_a'].sum() + swap_log_df['points_moved_b'].sum()

# Average points moved per swap
average_points_per_swap = total_points / len(swap_log_df)

print(f"Total points involved in swaps: {total_points}") #84232582
print(f"Average points moved per swap: {average_points_per_swap:.2f}") #452.35


#%%
import pickle

with open("D:\paper3\Data\filled_trajectories_list/containers_node_swapping_AfterSwapping.pkl", "wb") as f:
    pickle.dump(containers, f, protocol=pickle.HIGHEST_PROTOCOL)


#%%--------------------------
# Combine points from all containers into a final GeoDataFrame
# --------------------------
print("Assembling final points GeoDataFrame...")

from dataclasses import asdict

rows = []

for c in containers:
    c_dict = asdict(c)
    c_dict.pop("points")

    for p in c.points:
        rows.append({**c_dict, **asdict(p)})

final_df = pd.DataFrame.from_records(rows)

# Convert to GeoDataFrame
final_gdf = gpd.GeoDataFrame(final_df, geometry='geometry', crs=gdf.crs)
final_gdf.head()

#%% save final points
final_gdf.to_parquet(r"D:\paper3\Data\filled_trajectories_list/trajectories_swapped_nodes.parquet")

print(f"Number of points: {len(final_gdf)}")
print(f"Number of containers: {len(containers)}") #319189


#%% look at some of the mixed points in qgis
final_gdf[final_gdf['container_id']==1].to_parquet(r"D:\paper3\Data\output/trajectories_swapped_nodes_container1.parquet")

#%%
final_gdf[final_gdf['container_id']==0].to_parquet(r"D:\paper3\Data\output/trajectories_swapped_nodes_container0.parquet")
# looks good in Q, i.e. points are ordered 











#%% MUST ADD GLOBAL POINT ID
# point_id is the original point_id from the input gdf
# head remains in the same order, tails are appended --> within each conatiner, the point sequence is ordered

# ensure point order is correct

# load df without the problematic column
#%% load node swapping df without the one massive column
import pyarrow.parquet as pq
import pandas as pd
import geopandas as gpd
from shapely import wkb

pf = pq.ParquetFile(r"d:\paper3\Data\filled_trajectories_list\trajectories_swapped_nodes.parquet")

dfs = []
for i in range(pf.num_row_groups):
    try:
        # Skip key_set
        table = pf.read_row_group(i, columns=[
            "container_id", "tid_subid", "swap_mode", "point_id", 
            "u","v","time_bin","geometry","timestamp",
            "uid","orig_tid","v_intersection_id_swap","is_node_arrival"
        ])
        df = table.to_pandas()
        dfs.append(df)
    except Exception as e:
        print(f"Failed row group {i}: {e}")

full_df = pd.concat(dfs, ignore_index=True)
# Convert WKB to Shapely
full_df["geometry"] = full_df["geometry"].apply(wkb.loads)
gdf_nodess_swppd = gpd.GeoDataFrame(full_df, geometry="geometry")
gdf_nodess_swppd.set_crs("EPSG:2193", inplace=True)

#%% loko at the same container id as before to ensure point order is still in tact
orig_container1 = gpd.read_parquet(r"D:\paper3\Data\output/trajectories_swapped_nodes_container1.parquet")
orig_container0 = gpd.read_parquet(r"D:\paper3\Data\output/trajectories_swapped_nodes_container0.parquet")

container1 = gdf_nodess_swppd[gdf_nodess_swppd['container_id']==1].copy()
container0 = gdf_nodess_swppd[gdf_nodess_swppd['container_id']==0].copy()

# drop the problematic column from orig dfs
orig_container1 = orig_container1.drop(columns=['key_set'])
orig_container0 = orig_container0.drop(columns=['key_set'])

print(orig_container1.equals(container1)) #True
print(orig_container0.equals(container0)) #True


#%%
container1


#%% add global point_id
print(gdf_nodess_swppd['tid_subid'].nunique()) # 19189
# is there only one tid_subid by container id?
gdf_nodess_swppd.groupby('container_id')['tid_subid'].nunique().reset_index().tid_subid.max() # is 1 --> tid_subid is the container id

#%%
print(container1.point_id.unique()) # includes original tid, timestamp and order within original tid

#%% clean up gdf_nodess_swppd and add point id
gdf_nodess_swppd.reset_index(drop=True, inplace=True)
gdf_nodess_swppd.reset_index(inplace=True)
gdf_nodess_swppd.rename(columns={'index': 'point_id_global'}, inplace=True)
gdf_nodess_swppd

#%% 
# uid is orig uid
# tid_subid is container tid

gdf_nodess_swppd = gdf_nodess_swppd.rename(columns={'uid': 'orig_uid', 
                                                    'tid_subid': 'container_tid_subid',
                                                    })
# add container uid
gdf_nodess_swppd['conteiner_uid'] = gdf_nodess_swppd['container_tid_subid'].str.split('_').str[1]

gdf_nodess_swppd.head()

#%% look at timebins by container
df = gdf_nodess_swppd.copy()
# Compute difference within each container
df['time_bin_diff'] = df.groupby('container_id')['time_bin'].diff()

# Identify any negative jump (non-consecutive)
df['non_consecutive'] = df['time_bin_diff'] < 0

# Flag containers with problems
bad_containers = df.groupby('container_id')['non_consecutive'].any()
df['flag_problem'] = df['time_bin_diff'] < 0
df[df['flag_problem']] # NO JUMPS IN TIME BINS, good!


#%% add seconds to previous point
# block identifier for orig_tid, incase orig_tid is repeated (shouldn't be repeated, thiss is a safety measure only)
# how do I handle segment shifts? none for now
gdf_nodess_swppd['orig_tid_block'] = gdf_nodess_swppd.groupby('container_id')['orig_tid'].transform(lambda x: (x != x.shift()).cumsum())
gdf_nodess_swppd['sec_fromPrevPoint'] = gdf_nodess_swppd.groupby(['container_id','orig_tid_block'])['timestamp'].diff()
gdf_nodess_swppd


#%% calculate trajectory lengths
if gdf_nodess_swppd.crs.to_epsg() != 2193:  
    print("ransforming to EPSG:2193")
    gdf_nodess_swppd = gdf_nodess_swppd.to_crs(epsg=2193)

gdf_nodess_swppd['prev_geom'] = gdf_nodess_swppd.groupby('container_id')['geometry'].shift(1)

gdf_nodess_swppd['segment_length_m'] = gdf_nodess_swppd.geometry.distance(gdf_nodess_swppd['prev_geom'])
gdf_nodess_swppd['segment_length_m'] = gdf_nodess_swppd['segment_length_m'].fillna(0)

# look at container length
gdf_nodess_swppd_length = gdf_nodess_swppd.groupby('container_id')['segment_length_m'].sum().reset_index()
gdf_nodess_swppd_length.rename(columns={'segment_length_m':'total_length_m'}, inplace=True)
gdf_nodess_swppd_length.describe()

#       container_id  total_length_m
#count  19189.000000    1.918900e+04
#mean    9594.000000    3.240677e+05
#std     5539.531493    1.937131e+05
#min        0.000000    0.000000e+00
#25%     4797.000000    1.891513e+05    #189 km
#50%     9594.000000    2.976239e+05    #297 km
#75%    14391.000000    4.308629e+05
#max    19188.000000    1.565484e+06    #1565 km

# CONTAINER ARE TOO LONG TO BE DAILY TRAJECTORIES


#%% split the tid of the swapped df by creating subtrajectories of the conatiner_id
# ensuring that both segments of the split tid have reasonable lengths
import numpy as np
import random

min_len_threshold = 10000
max_len_threshold = 45000

# cumulative distance for each container
gdf_nodess_swppd['traj_length_container_segment'] = gdf_nodess_swppd.groupby('container_id')['segment_length_m'].cumsum()

container_total = gdf_nodess_swppd.groupby('container_id')['segment_length_m'].sum()

gdf_nodess_swppd['sub_container_id'] = gdf_nodess_swppd['container_id']

for cid, total_len in container_total.items():
     
    rand_offset_max_len = random.uniform(0, 3) * 1000       # random offset up to 3km for max trajectory length
    rand_offset_min_len = random.uniform(0, 1.5) * 1000     # random offset up to 1.5km for min trajectory length
    # either add or substract the offset
    min_len_plusminus = random.choice([-1, 1])    
    max_len_plusminus = random.choice([-1, 1]) 
    # final traj length constraint for this container
    max_len = max_len_threshold + (rand_offset_max_len * max_len_plusminus)
    min_len = min_len_threshold + (rand_offset_min_len * min_len_plusminus)             
 

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

#count    219314.000000
#mean      28354.486963
#std       12400.942074
#min           0.000000
#25%       18895.850224 --> 18km
#50%       28067.359440 --> 28km
#75%       37307.375296
#max      116026.201449 --> 116k much better
#%% export
gdf_nodess_swppd_length.to_parquet(r"d:\paper3\Data\filled_trajectories_list\trajectories_swapped_nodes_FINAL.parquet")
