#%% load data
import joblib
trajectories = joblib.load(r'D:\paper3\Data\filled_trajectories_list/trajectories_filled.joblib')
#%%
import pandas as pd
mapping = {
    'night time': 0,
    'morning peak': 1,
    'flat peak': 2,
    'evening peak': 3,
}

for df in trajectories:
    df['time_bin_label'] = df['time_bin']
    df['time_bin'] = df['time_bin'].map(mapping)

    missing = df['time_bin'].isna().any()
    if missing:
        raise ValueError("Unexpected time_bin value found")


#%% actually work with one gdf instead
import pandas as pd
import geopandas as gpd

gdf = pd.concat(trajectories, ignore_index=True)
gdf = gpd.GeoDataFrame(gdf, geometry='geometry', crs=trajectories[0].crs)

gdf.head()
#%%
gdf.to_parquet(r"D:\paper3\Data\filled_trajectories_list/trajectories_filled_gdf_preppedForSwapping.parquet")











#%% read data
import geopandas as gpd
gdf = gpd.read_parquet(r"D:\paper3\Data\filled_trajectories_list/trajectories_filled_gdf_preppedForSwapping.parquet")
gdf.rename(columns={'point_id_t': 'point_id'}, inplace=True)
assert gdf['point_id'].is_unique, "point_id is not unique! Check initialization."


#%%
import importlib
import os
os.chdir("D:\paper3")
import utils_EdgeSwapping_containers as sw
importlib.reload(sw)

import pandas as pd
import numpy as np
from collections import defaultdict, deque
import time

# --------------------------
# 0️⃣ Prepare points
# --------------------------
# Assume your GeoDataFrame is called gdf, with columns:
# ['point_id', 'tid_subid', 'uid', 'u', 'v', 'time_bin', 'geometry', 'unix_timestamp']

gdf['container_id'] = -1          # will be set per container
gdf['orig_tid'] = gdf['tid_subid']
gdf['orig_uid'] = gdf['uid']
gdf['swap_count'] = 0
gdf['visited_containers'] = gdf.apply(lambda _: [], axis=1)  # track path history

# --------------------------
# 1️⃣ Initialize containers
# --------------------------
containers = []
for cid, (tid, df_tid) in enumerate(gdf.groupby("tid_subid", sort=False)):
    df_tid = df_tid.copy()
    df_tid['container_id'] = cid
    df_tid['visited_containers'] = df_tid['visited_containers'].apply(lambda x: [cid])  # first container visited
    containers.append({
        'cid': cid,
        'tid': tid,
        'points': df_tid,
        'keys': list(zip(df_tid['u'].astype(str), df_tid['v'].astype(str), df_tid['time_bin'].astype(int))),
        'key_to_idx': {k: i for i, k in enumerate(df_tid[['u','v','time_bin']].itertuples(index=False, name=None))},
        'uids': set(df_tid['uid']),
        'length': len(df_tid)
    })

# --------------------------
# 2️⃣ Build key → container mapping
# --------------------------
key_to_cids = defaultdict(set)
for c in containers:
    for k in c['keys']:
        key_to_cids[k].add(c['cid'])

# --------------------------
# 3️⃣ Queue-based swapping loop
# --------------------------
queue = deque(range(len(containers)))
seen_swaps = set()
swap_log = []
swap_counter = 0
start_time = time.time()
points_processed_so_far = 0

while queue:
    cid_a = queue.popleft()
    a = containers[cid_a]

    # Candidate containers sharing at least one key
    candidate_cids = set()
    for k in a['keys']:
        candidate_cids.update(key_to_cids[k])
    candidate_cids.discard(cid_a)

    for cid_b in candidate_cids:
        b = containers[cid_b]

        # UID constraint: skip if any overlap of original uids
        if not a['uids'].isdisjoint(b['uids']):
            continue

        # Compute common keys
        common_keys = set(a['keys']).intersection(b['key_to_idx'].keys())
        for k in common_keys:
            if k not in a['key_to_idx'] or k not in b['key_to_idx']:
                continue

            # Prevent oscillation: check path-history
            idx_a = a['key_to_idx'][k]
            idx_b = b['key_to_idx'][k]

            tail_a = a['points'].iloc[idx_a+1:]
            tail_b = b['points'].iloc[idx_b+1:]

            if ((tail_a['visited_containers'].apply(lambda x: cid_b in x)).any() or
                (tail_b['visited_containers'].apply(lambda x: cid_a in x)).any()):
                continue  # skip swap if path-history violated

            sig = tuple(sorted([cid_a, cid_b]) + list(k))
            if sig in seen_swaps:
                continue
            seen_swaps.add(sig)

            # Swap tails
            new_a_points = pd.concat([a['points'].iloc[:idx_a+1], tail_b], ignore_index=True)
            new_b_points = pd.concat([b['points'].iloc[:idx_b+1], tail_a], ignore_index=True)

            # Update container_id and visited_containers
            new_a_points['container_id'] = cid_a
            new_b_points['container_id'] = cid_b
            new_a_points.loc[idx_a+1:, 'visited_containers'] = new_a_points.loc[idx_a+1:, 'visited_containers'].apply(lambda x: x + [cid_a])
            new_b_points.loc[idx_b+1:, 'visited_containers'] = new_b_points.loc[idx_b+1:, 'visited_containers'].apply(lambda x: x + [cid_b])

            # Increment swap counts
            new_a_points.loc[idx_a+1:, 'swap_count'] += 1
            new_b_points.loc[idx_b+1:, 'swap_count'] += 1

            # Update container points
            a['points'] = new_a_points
            b['points'] = new_b_points

            # Recompute keys, key_to_idx, length, uids
            for container in [a, b]:
                container['keys'] = list(zip(container['points']['u'].astype(str),
                                             container['points']['v'].astype(str),
                                             container['points']['time_bin'].astype(int)))
                container['key_to_idx'] = {k: i for i, k in enumerate(container['points'][['u','v','time_bin']].itertuples(index=False, name=None))}
                container['length'] = len(container['points'])
                container['uids'] = set(container['points']['uid'])

            # Re-add to queue
            if cid_a not in queue:
                queue.append(cid_a)
            if cid_b not in queue:
                queue.append(cid_b)

            # Update key → container mapping
            for key in a['keys']:
                key_to_cids[key].add(cid_a)
            for key in b['keys']:
                key_to_cids[key].add(cid_b)

            # Log swap
            swap_counter += 1
            points_processed_so_far += len(tail_a) + len(tail_b)
            swap_log.append({
                'swap_id': swap_counter,
                'container_a': cid_a,
                'container_b': cid_b,
                'key': k,
                'tail_points_a': len(tail_a),
                'tail_points_b': len(tail_b),
                'timestamp': time.time() - start_time
            })

            # Print first swap and every 500th
            if swap_counter == 1 or swap_counter % 500 == 0:
                print(f"[Swap {swap_counter}] Processed ~{points_processed_so_far} points")

print("\nAll swaps completed!")
swap_log_df = pd.DataFrame(swap_log)

# --------------------------
# 4️⃣ Container summary stats
# --------------------------
container_summary = []
for c in containers:
    df = c['points']
    container_summary.append({
        'container_id': c['cid'],
        'num_orig_trajectories': df['orig_tid'].nunique(),
        'num_unique_uids': df['orig_uid'].nunique(),
        'avg_swaps_per_point': df['swap_count'].mean(),
        'max_swaps': df['swap_count'].max(),
        'num_points': len(df)
    })

container_summary_df = pd.DataFrame(container_summary)
final_points = pd.concat([c['points'] for c in containers], ignore_index=True)


#%%
# Check for path-history violations
# 'visited_containers' is a column that stores a list/set of all containers a point has been in
violations = final_points[final_points.apply(lambda row: row['container_id'] in row['visited_containers'][:-1], axis=1)]

print(f"Number of points that violated path-history: {len(violations)}")
if len(violations) > 0:
    print(violations[['point_id', 'orig_tid', 'orig_uid', 'container_id', 'visited_containers']].head(10))
else:
    print("No violations — all points respected path-history constraint.")


#%% export both, final_gdf and containers and swap_log_df
# point level results
# each row is a point from the orginal trajectories, after all swaps
# shows which container each point ended up in, how many times it swaped, preserved oirginal tid
#point_id	                                Unique ID of the point
#orig_tid	                                Original trajectory this point belonged to
#container_id	                            Final container after all swaps
#swap_count	                                How many times this point changed containers
#u, v, time_bin, uid, timestamp, geometry	Original point info for analysis / plotting
final_gdf = pd.concat([c['points'] for c in containers], ignore_index=True)
if 'geometry' in final_gdf.columns:
    final_gdf = gpd.GeoDataFrame(final_gdf, geometry='geometry', crs=gdf.crs)

final_gdf.to_parquet(r"D:\paper3\Data\output/final_points_edgeSwap.parquet")

# container-level results
# one row per container, summarizing the points it contains after all swaps
# shows how trajectories merged, how many original trajectories contributed, and swap activity
#container_id	        Container identifier
#tid_subid	            Original trajectory label for container (head label)
#num_points	            Total points in container
#num_orig_trajectories	How many original trajectories contributed points
#avg_swaps_per_point	Mean number of swaps per point in container
#max_swaps	            Maximum swap count for any point in container

# --------------------------
# Container summary statistics
# --------------------------
print(container_summary_df.head())
container_summary_df.to_parquet(r"D:\paper3\Data\output/container_summary_edgeSwap.parquet")


#swap-level results
# each row: one swap between two containers at a particular key
# shows how points were shuffled and tail sizes
#swap_id        Sequential ID of the swap
#container_a	First container in swap
#container_b	Second container in swap
#key	        Swap point (u,v,time_bin)
#tail_points_a	Number of points moved from container A
#tail_points_b	Number of points moved from container B
#timestamp	    Time elapsed since start of swap loop
swap_log_df[['u', 'v', 'time_bin']] = pd.DataFrame(swap_log_df['key'].tolist(), index=swap_log_df.index)
swap_log_df = swap_log_df.drop(columns='key')
swap_log_df.to_parquet(r"D:\paper3\Data\output\swap_log__edgeSwap.parquet", index=False)


