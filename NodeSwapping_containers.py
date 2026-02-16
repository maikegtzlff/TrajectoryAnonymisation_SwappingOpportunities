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
import utils_NodeSwapping_containers as nsw


#%% swap based on common v: swapping logic (v_intersection_id_swap, time_bin)
# mark node arrivals - 26 minutes
points_by_tid = {}

for tid, df_tid in gdf.groupby("tid_subid", sort=False):
    points_list = []
    df_tid = df_tid.sort_values("time_bin").reset_index(drop=True)

    for i, row in df_tid.iterrows():
        # Node arrival: last point before leaving edge
        if i == len(df_tid) - 1:
            is_node_arrival = True
        else:
            next_row = df_tid.iloc[i+1]
            is_node_arrival = (row.v != next_row.v)

        p = nsw.Point(
            point_id=row.point_id,
            u=row.u,
            v=row.v,
            time_bin=int(row.time_bin),
            geometry=row.geometry,
            timestamp=row.unix_timestamp,
            uid=row.uid,
            orig_tid=row.tid_subid,
            v_is_intersection=row.v_intersection,
            is_node_arrival=is_node_arrival
        )
        points_list.append(p)

    points_by_tid[tid] = points_list

#%% initialize containers
containers = []
for cid, (tid, points_list) in enumerate(points_by_tid.items()):
    container = nsw.Container(
        container_id=cid,
        points=points_list,
        tid_subid=tid,
        key_set=set(),
        swap_mode="node"
    )
    container.rebuild_key_set()
    containers.append(container)

#%% run node swaps
swap_log = nsw.run_node_swaps_queue(containers)

#%% export final gdf
import geopandas as gpd
import pandas as pd

rows = []
for c in containers:
    for p in c.points:
        rows.append({
            "point_id": p.point_id,
            "orig_tid": p.orig_tid,
            "container_id": c.container_id,
            "u": p.u,
            "v": p.v,
            "time_bin": p.time_bin,
            "uid": p.uid,
            "v_is_intersection": p.v_is_intersection,
            "is_node_arrival": p.is_node_arrival,
            "geometry": p.geometry,
            "timestamp": p.timestamp
        })

final_gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs=gdf.crs)
#final_gdf.to_parquet(r"D:\paper3\Data\output/final_points_nodeSwap.parquet")

# Also export swap log
swap_log_df = pd.DataFrame(swap_log)
#swap_log_df.to_parquet(r"D:\paper3\Data\output/swap_log_nodeSwap.parquet", index=False)
