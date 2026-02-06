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
    df.rename(columns={'point_id': 'point_id_t'}, inplace=True)
    df['time_bin_label'] = df['time_bin']
    df['time_bin'] = df['time_bin'].map(mapping)

    missing = df['time_bin'].isna().any()
    if missing:
        raise ValueError("Unexpected time_bin value found")


#%%
trajectories[0].head()


#%% initialize containers etc
for cid, df in enumerate(trajectories):
    df["container_id"] = cid                # immutable
    df["orig_tid"] = df["tid_subid"]         # immutable
    df["orig_uid"] = df["uid"]               # immutable
    df["point_id"] = range(len(df))          # or existing
    df["n_container_changes"] = 0

#%% actually worki with one gdf instead
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


#%%
import importlib
import os
os.chdir("D:\paper3")
import utils_EdgeSwapping_containers as sw
importlib.reload(sw)

from collections import deque, defaultdict
import pandas as pd
import time

# --------------------------
# 1️⃣ Ensure consistent key types for all containers
# --------------------------
for c in containers:
    c['points']['u'] = c['points']['u'].astype(str)
    c['points']['v'] = c['points']['v'].astype(str)
    c['points']['time_bin'] = c['points']['time_bin'].astype(int)

    c['keys'] = list(zip(c['points']['u'], c['points']['v'], c['points']['time_bin']))
    c['key_to_idx'] = {k: i for i, k in enumerate(c['keys'])}
    c['length'] = len(c['points'])
    c['uids'] = set(c['points']['uid'])

# --------------------------
# 2️⃣ Build key → container mapping
# --------------------------
key_to_cids = defaultdict(set)
for c in containers:
    for k in c['keys']:
        key_to_cids[k].add(c['cid'])

# --------------------------
# 3️⃣ Initialize queue, swap memory, swap log
# --------------------------
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
