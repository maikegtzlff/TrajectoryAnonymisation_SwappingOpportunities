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