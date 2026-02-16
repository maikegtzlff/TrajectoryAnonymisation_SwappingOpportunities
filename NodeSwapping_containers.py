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

#%% add identifier for swap - i.e., last point on edge
gdf = gdf.sort_values(['tid_subid', 'unix_timestamp'])

gdf['v_intersection_id_swap'] = np.where(
    (gdf['v_intersection'] == True) &
    (gdf['v'] != gdf.groupby('tid_subid')['v'].shift(-1)),
    gdf['v'],
    np.nan
)

gdf.head(100)





#%% swap based on common v: swapping logic (v_intersection_id_swap, time_bin)

#%% (1) build containers
import numpy as np
from collections import defaultdict

containers = {}

for tid_subid, df_tid in gdf.groupby('tid_subid'):

    df_tid = df_tid.reset_index(drop=True)

    # Build keys (only valid where intersection exists)
    keys = [
        (row.v_intersection_id_swap, row.time_bin)
        for row in df_tid.itertuples()
        if not pd.isna(row.v_intersection_id_swap)
    ]

    # Map key → row index
    key_to_idx = {
        (row.v_intersection_id_swap, row.time_bin): i
        for i, row in enumerate(df_tid.itertuples())
        if not pd.isna(row.v_intersection_id_swap)
    }

    containers[tid_subid] = {
        'points': df_tid,
        'keys': keys,
        'key_to_idx': key_to_idx
    }

#%% build key index: who shares intersections at the same time
key_index = defaultdict(list)

for cid, container in containers.items():
    for k in container['keys']:
        key_index[k].append(cid)
#%%
key_index
#%% example
key_index[(25769971.0, 2)] # all containers that meet at node 25769971 at that time 2

#%% swap logic: swapping tails after the intersection node
import pandas as pd
import numpy as np
import random
from collections import defaultdict

def intersection_swap(gdf, n_iterations=5):

    current_df = gdf.copy()

    swap_log = []
    swap_counter = 0

    for iteration in range(n_iterations):

        print(f"Iteration {iteration+1}")

        containers = {}

        # -----------------------------
        # STEP 1: Build containers
        # -----------------------------
        for tid_subid, df_tid in current_df.groupby('tid_subid'):

            df_tid = df_tid.sort_values('timestamp').reset_index(drop=True)

            keys = []
            key_to_idx = {}

            for i, row in enumerate(df_tid.itertuples()):
                if not pd.isna(row.v_intersection_id_swap):
                    k = (row.v_intersection_id_swap, row.time_bin)
                    keys.append(k)
                    key_to_idx[k] = i

            containers[tid_subid] = {
                'points': df_tid,
                'keys': keys,
                'key_to_idx': key_to_idx
            }

        # -----------------------------
        # STEP 2: Build key index
        # -----------------------------
        key_index = defaultdict(list)

        for cid, container in containers.items():
            for k in container['keys']:
                key_index[k].append(cid)

        # -----------------------------
        # STEP 3: Perform swaps
        # -----------------------------
        swaps_this_round = 0

        for k, cids in key_index.items():

            if len(cids) < 2:
                continue

            random.shuffle(cids)

            for i in range(0, len(cids)-1, 2):

                cid_a = cids[i]
                cid_b = cids[i+1]

                a = containers[cid_a]
                b = containers[cid_b]

                idx_a = a['key_to_idx'][k]
                idx_b = b['key_to_idx'][k]

                head_a = a['points'].iloc[:idx_a+1]
                tail_a = a['points'].iloc[idx_a+1:]

                head_b = b['points'].iloc[:idx_b+1]
                tail_b = b['points'].iloc[idx_b+1:]

                # If one tail empty → skip
                if len(tail_a) == 0 or len(tail_b) == 0:
                    continue

                new_a = pd.concat([head_a, tail_b]).reset_index(drop=True)
                new_b = pd.concat([head_b, tail_a]).reset_index(drop=True)

                containers[cid_a]['points'] = new_a
                containers[cid_b]['points'] = new_b

                swap_counter += 1
                swaps_this_round += 1

                swap_log.append({
                    'iteration': iteration+1,
                    'swap_id': swap_counter,
                    'container_a': cid_a,
                    'container_b': cid_b,
                    'intersection_id': k[0],
                    'time_bin': k[1],
                    'tail_len_a': len(tail_a),
                    'tail_len_b': len(tail_b)
                })

        print(f"Swaps this iteration: {swaps_this_round}")

        # -----------------------------
        # STEP 4: Rebuild dataframe
        # -----------------------------
        current_df = pd.concat(
            [c['points'] for c in containers.values()],
            ignore_index=True
        )

        # IMPORTANT:
        # Recompute v_intersection_id_swap because trajectories changed
        current_df = current_df.sort_values(['tid_subid', 'unix_timestamp'])

        current_df['v_intersection_id_swap'] = np.where(
            (current_df['v_intersection'] == True) &
            (current_df['v'] != current_df.groupby('tid_subid')['v'].shift(-1)),
            current_df['v'],
            np.nan
        )

    return current_df, pd.DataFrame(swap_log)


#%% final gdf
swapped_df, swap_log = intersection_swap(gdf, n_iterations=10)

