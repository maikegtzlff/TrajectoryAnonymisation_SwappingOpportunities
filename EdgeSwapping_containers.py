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

#%% initialize containers etc

#%%
import importlib
import os
os.chdir("D:\paper3")
import utils_EdgeSwapping_containers as sw
importlib.reload(sw)

from collections import defaultdict, deque
import pandas as pd
import time

# === 0️⃣ Prepare point-level columns ===
# gdf is your full GeoDataFrame (all trajectories concatenated)
# Keep original point_id, orig_tid, uid, timestamp, geometry
gdf = gdf.copy()
if 'swap_count' not in gdf.columns:
    gdf['swap_count'] = 0  # equivalent to old n_container_changes
if 'container_id' not in gdf.columns:
    gdf['container_id'] = -1  # will be set per container

# === 1️⃣ Initialize containers ===
containers = []
for cid, (tid, df_tid) in enumerate(gdf.groupby("tid_subid", sort=False)):
    df_tid = df_tid.copy()
    df_tid['container_id'] = cid
    df_tid['swap_count'] = 0  # n_container_changes equivalent

    container = {
        'cid': cid,
        'tid_subid': tid,
        'points': df_tid.reset_index(drop=True),
        'keys': list(zip(df_tid['u'].astype(str),
                         df_tid['v'].astype(str),
                         df_tid['time_bin'].astype(int))),
        'key_to_idx': {k: i for i, k in enumerate(zip(
            df_tid['u'].astype(str),
            df_tid['v'].astype(str),
            df_tid['time_bin'].astype(int)))},
        'length': len(df_tid),
        'uids': set(df_tid['uid'])
    }
    containers.append(container)

# === 2️⃣ Build key → container mapping ===
key_to_cids = defaultdict(set)
for c in containers:
    for k in c['keys']:
        key_to_cids[k].add(c['cid'])

# === 3️⃣ Initialize queue, swap memory, swap log ===
queue = deque(range(len(containers)))
seen_swaps = set()
swap_log = []
swap_counter = 0
start_time = time.time()
points_processed_so_far = 0

# --------------------------
# 4️⃣ Queue-based swapping loop
# --------------------------
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

        # UID constraint: skip if any overlap
        if not a['uids'].isdisjoint(b['uids']):
            continue

        # Compute safe intersection of keys
        common_keys = set(a['keys']).intersection(set(b['key_to_idx'].keys()))
        for k in common_keys:
            # double-check key exists in both
            if k not in a['key_to_idx'] or k not in b['key_to_idx']:
                continue  # skip safely

            sig = tuple(sorted([cid_a, cid_b]) + list(k))
            if sig in seen_swaps:
                continue
            seen_swaps.add(sig)

            # Split indices
            idx_a = a['key_to_idx'][k]
            idx_b = b['key_to_idx'][k]

            # Extract tails
            tail_a = a['points'].iloc[idx_a+1:]
            tail_b = b['points'].iloc[idx_b+1:]

            # Swap tails
            new_a_points = pd.concat([a['points'].iloc[:idx_a+1], tail_b], ignore_index=True)
            new_b_points = pd.concat([b['points'].iloc[:idx_b+1], tail_a], ignore_index=True)

            # Update container_id
            new_a_points['container_id'] = cid_a
            new_b_points['container_id'] = cid_b

            # Increment swap_count for swapped points
            new_a_points.loc[idx_a+1:, 'swap_count'] += 1
            new_b_points.loc[idx_b+1:, 'swap_count'] += 1

            # Update container points
            a['points'] = new_a_points
            b['points'] = new_b_points

            # Recompute keys, key_to_idx, length, and uids
            for container in [a, b]:
                container['keys'] = list(zip(container['points']['u'], container['points']['v'], container['points']['time_bin']))
                container['key_to_idx'] = {k: i for i, k in enumerate(container['keys'])}
                container['length'] = len(container['points'])
                container['uids'] = set(container['points']['uid'])

            # Re-add to queue for further swaps
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

            # Print first swap and every 500th swap
            if swap_counter == 1 or swap_counter % 10000 == 0:
                print(f"[Swap {swap_counter}] Processed ~{points_processed_so_far} points")

print("\nAll swaps completed!")
swap_log_df = pd.DataFrame(swap_log)
#[Swap 210000] Processed ~107397243 points


#%%
print(len(gdf)) #7,334,941
print(len(swap_log_df)) # number of swaps perfomerd: 215,805
# one tail swap between two containers at one key
total_points_moved = swap_log_df['tail_points_a'].sum() + swap_log_df['tail_points_b'].sum()
print(total_points_moved) #109,406,029

#%%
print(len(containers[0]['points'])) # 266
containers[0]['points'].orig_tid.nunique() # 19

#%%
print(len(gdf)) #7,334,941

#for c in containers:
#    cid = c['cid']
#    n_points = len(c['points'])
#    print(f"Container {cid}: {n_points} points")

final_gdf = pd.concat([c['points'] for c in containers], ignore_index=True)
print(f"Total points across all containers: {len(final_gdf)}")
print(len(gdf)==len(final_gdf))

#%% quality control: duplicate points?
total_original = len(gdf)
# 3️⃣ Check for duplicates
duplicate_points = final_gdf['point_id'].duplicated().sum()
print(f"Number of duplicate points after swaps: {duplicate_points}")

# 4️⃣ Check for missing points
missing_points = total_original - final_gdf['point_id'].nunique()
print(f"Number of points lost: {missing_points}")

# 5️⃣ Optional: list point_ids that are missing (if any)
if missing_points > 0:
    missing_ids = set(gdf['point_id']) - set(final_gdf['point_id'])
    print("Missing point_ids:", missing_ids)

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

final_gdf.to_parquet(r"D:\paper3\Data\output/final_points.parquet")

# container-level results
# one row per container, summarizing the points it contains after all swaps
# shows how trajectories merged, how many original trajectories contributed, and swap activity
#container_id	        Container identifier
#tid_subid	            Original trajectory label for container (head label)
#num_points	            Total points in container
#num_orig_trajectories	How many original trajectories contributed points
#avg_swaps_per_point	Mean number of swaps per point in container
#max_swaps	            Maximum swap count for any point in container
#temporal_span	        Time difference between first and last point (optional)
container_summary = []
for c in containers:
    df = c['points']
    container_summary.append({
        'container_id': c['cid'],
        'tid_subid': c['tid'],
        'num_points': len(df),
        'num_orig_trajectories': df['orig_tid'].nunique(),
        'avg_swaps_per_point': df['swap_count'].mean(),
        'max_swaps': df['swap_count'].max(),
        'temporal_span': df['timestamp'].max() - df['timestamp'].min() if 'timestamp' in df.columns else None
    })

container_summary_df = pd.DataFrame(container_summary)
container_summary_df.to_parquet(r"D:\paper3\Data\output/container_summary_df.parquet")


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
swap_log_df.to_parquet(r"D:\paper3\Data\output\swap_log_df.parquet", index=False)






#%%
import pandas as pd
import geopandas as gpd

# --------------------------
# 1️⃣ Combine all container points into a single GeoDataFrame
# --------------------------
final_gdf = pd.concat([c['points'] for c in containers], ignore_index=True)

# Make sure geometry is preserved
if 'geometry' in final_gdf.columns:
    final_gdf = gpd.GeoDataFrame(final_gdf, geometry='geometry', crs=gdf.crs)

# Optional: sort for readability
if 'point_id' in final_gdf.columns:
    final_gdf = final_gdf.sort_values(['container_id', 'point_id']).reset_index(drop=True)

print("Final GeoDataFrame ready")
print(final_gdf.head())
print(f"Total points: {len(final_gdf)}")

# --------------------------
# 2️⃣ Generate per-container summary
# --------------------------
container_summary = []

for c in containers:
    df = c['points']
    summary = {
        'container_id': c['cid'],
        'tid_subid': c['tid'],                     # original container label
        'num_points': len(df),
        'num_orig_trajectories': df['orig_tid'].nunique(),
        'avg_swaps_per_point': df['swap_count'].mean(),
        'max_swaps': df['swap_count'].max(),
        'temporal_span': df['timestamp'].max() - df['timestamp'].min() if 'timestamp' in df.columns else None
    }
    container_summary.append(summary)

container_summary_df = pd.DataFrame(container_summary)
container_summary_df = container_summary_df.sort_values('container_id').reset_index(drop=True)

print("Container summary ready")
print(container_summary_df.head())

# --------------------------
# 3️⃣ Optional: Export results
# --------------------------
# final_gdf.to_file("final_trajectories.geojson", driver="GeoJSON")
# final_gdf.to_csv("final_trajectories.csv", index=False)
# container_summary_df.to_csv("container_summary.csv", index=False)
