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
# 0️ Prepare points
# --------------------------
gdf['container_id'] = -1          # will be set per container
gdf['orig_tid'] = gdf['tid_subid']
gdf['orig_uid'] = gdf['uid']
gdf['swap_count'] = 0
gdf['visited_containers'] = gdf.apply(lambda _: [], axis=1)  # track path history

# --------------------------
# 1️ Initialize containers
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
# 2️ Build key → container mapping
# --------------------------
key_to_cids = defaultdict(set)
for c in containers:
    for k in c['keys']:
        key_to_cids[k].add(c['cid'])

# --------------------------
# 3️ Queue-based swapping loop
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
# 4️ Container summary stats
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


#%%
print(final_gdf.n_container_changes.max()) # 0 - old column, not used by code --> drop
print(final_gdf.tid_change_count.max()) # 0 - we track identy based on container_id, not tid_subid. drop

print(final_gdf.swap_count.max()) #55 - one point moved container 55 times
print(final_gdf.swap_count.median()) #9 --> 10 containers visted total: overall high connectivity
print(final_gdf.swap_count.min()) #0
print(final_gdf.visited_containers.apply(len).max()) # 56 number of containers visited
# 55 swaps & 56 containers visited = confirmds: no duplicate container entries, no re-entry, no accidential double-counting
# checked order and consistency in QGIS: looks good

print((final_gdf.tid_subid == final_gdf.orig_tid).any()) # same, both represent source tid

#%%
total = len(final_gdf)

pct_never = (final_gdf.swap_count == 0).mean() * 100
pct_once_or_more = (final_gdf.swap_count >= 1).mean() * 100
pct_10_plus = (final_gdf.swap_count >= 10).mean() * 100
pct_20_plus = (final_gdf.swap_count >= 20).mean() * 100

print(f"Total points: {total:,}") # 7,334,941
print(f"Never swapped: {pct_never:.2f}%") # 9.41%
print(f"Swapped ≥1 time: {pct_once_or_more:.2f}%") #90.59%
print(f"Swapped ≥10 times: {pct_10_plus:.2f}%") #47.26%
print(f"Swapped ≥20 times: {pct_20_plus:.2f}%") # 9.60%

print("\nHigh-percentile swaps:")
print(final_gdf.swap_count.quantile([0.9, 0.95, 0.99]))
#High-percentile churn:
#0.90    19.0
#0.95    23.0
#0.99    30.0

#%% histograms
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter

plt.style.use("ggplot")

def percent_formatter(x, pos):
    return f"{x:.1f}%"

def thousands_formatter(x, pos):
    return f"{int(x):,}"


#%% swap_count — distribution
swap_counts = final_gdf["swap_count"]

plt.figure(figsize=(8, 5))
plt.hist(swap_counts, bins=50)
plt.xlabel("swap count (number of container moves)")
plt.ylabel("number of points")
plt.title("Distribution of container swaps per point")

plt.gca().yaxis.set_major_formatter(FuncFormatter(thousands_formatter))
plt.tight_layout()
plt.show()
#%% sawp count as percentage
counts, bins = np.histogram(swap_counts, bins=50)
percentages = counts / counts.sum() * 100
bin_centers = 0.5 * (bins[:-1] + bins[1:])

plt.figure(figsize=(8, 5))
plt.bar(bin_centers, percentages, width=np.diff(bins), align="center")
plt.xlabel("swap count (number of container moves)")
plt.ylabel("percentage of points")
plt.title("Percentage of points by swap count")

plt.gca().yaxis.set_major_formatter(FuncFormatter(percent_formatter))
plt.tight_layout()
plt.show()

#%% conatiners visited --> more meaningful
containers_visited = final_gdf["visited_containers"].apply(len)

plt.figure(figsize=(8, 5))
plt.hist(containers_visited, bins=50)
plt.xlabel("number of containers visited")
plt.ylabel("number of points")
plt.title("Distribution of containers visited per point")

plt.gca().yaxis.set_major_formatter(FuncFormatter(thousands_formatter))
plt.tight_layout()
plt.show()
#%% as percentage
counts, bins = np.histogram(containers_visited, bins=50)
percentages = counts / counts.sum() * 100
bin_centers = 0.5 * (bins[:-1] + bins[1:])

plt.figure(figsize=(8, 5))
plt.bar(bin_centers, percentages, width=np.diff(bins), align="center")
plt.xlabel("number of containers visited")
plt.ylabel("percentage of points")
plt.title("Percentage of points by number of containers visited")

plt.gca().yaxis.set_major_formatter(FuncFormatter(percent_formatter))
plt.tight_layout()
plt.show()

#%%
tid_inContainer = final_gdf.groupby('container_id')['tid_subid'].nunique().reset_index()
tid_inContainer = tid_inContainer.rename(columns={"tid_subid": "n_tid_subid"})
print(tid_inContainer.n_tid_subid.min()) #1
print(tid_inContainer.n_tid_subid.median()) #15 --> typical container is highly mixed
print(tid_inContainer.n_tid_subid.max()) #38

tid_inContainer

#%%
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

plt.style.use("ggplot")

def thousands(x, pos):
    return f"{int(x):,}"

plt.figure(figsize=(8, 5))
plt.hist(tid_inContainer["n_tid_subid"], bins=30)
plt.xlabel("number of original trajectories per container")
plt.ylabel("number of containers")
plt.title("Mixing of original trajectories within containers")

plt.gca().yaxis.set_major_formatter(FuncFormatter(thousands))
plt.tight_layout()
plt.show()

#%% and as percentage
import numpy as np

values = tid_inContainer["n_tid_subid"]
counts, bins = np.histogram(values, bins=30)
percentages = counts / counts.sum() * 100
bin_centers = 0.5 * (bins[:-1] + bins[1:])

plt.figure(figsize=(8, 5))
plt.bar(bin_centers, percentages, width=np.diff(bins), align="center")
plt.xlabel("number of original trajectories per container")
plt.ylabel("percentage of containers")
plt.title("Percentage of containers by trajectory mixing level")

plt.gca().yaxis.set_major_formatter(lambda x, _: f"{x:.1f}%")
plt.tight_layout()
plt.show()

#%%
sorted_vals = np.sort(values)
cdf = np.arange(1, len(sorted_vals) + 1) / len(sorted_vals) * 100

plt.figure(figsize=(8, 5))
plt.plot(sorted_vals, cdf)
plt.xlabel("number of original trajectories per container")
plt.ylabel("percentage of containers")
plt.title("Cumulative distribution of container mixing")

plt.gca().yaxis.set_major_formatter(lambda x, _: f"{x:.0f}%")
plt.tight_layout()
plt.show()

#%% cumulative distirbution function
# %%
import matplotlib.pyplot as plt
import numpy as np

values = tid_inContainer["n_tid_subid"]
sorted_vals = np.sort(values)
cdf = np.arange(1, len(sorted_vals)+1) / len(sorted_vals) * 100  # percent

plt.figure(figsize=(8,5))
plt.plot(sorted_vals, cdf, marker='o', linestyle='-', color='blue')
plt.xlabel("Number of original trajectories per container")
plt.ylabel("Cumulative percentage of containers (%)")
plt.title("CDF: Mixing of original trajectories across containers")
plt.grid(True, linestyle='--', alpha=0.5)
plt.show()

# "longer dots" = multiple container with the same number of tid - marker overlaps 
# --> how many points share the same x value
# interpretation should be focued on the curve
# qyuick rise - many containers have tat number of tid_subid
# flat curve = few containers have values in that range

#%%
# Total number of swaps performed
total_swaps = len(swap_log_df)
print("Total swaps:", total_swaps) #147134

# Total points moved across all swaps
total_points_moved = swap_log_df['tail_points_a'].sum() + swap_log_df['tail_points_b'].sum()
print("Total points involved in swaps:", total_points_moved) # 71192794

# Average points moved per swap
avg_points_per_swap = total_points_moved / total_swaps
print("Average points moved per swap:", avg_points_per_swap) # 483.8636481030897

# Optional: distribution of points moved per swap
import matplotlib.pyplot as plt

plt.figure(figsize=(8,5))
plt.hist(swap_log_df['tail_points_a'] + swap_log_df['tail_points_b'], bins=50, color='skyblue', edgecolor='black')
plt.xlabel("Points moved in a single swap")
plt.ylabel("Number of swaps")
plt.title("Distribution of points involved per swap")
plt.show()

#%% drop outdated columns
final_gdf = final_gdf.drop(columns=["n_container_changes", "tid_change_count"])
final_gdf.to_parquet(r"D:\paper3\Data\output/final_points_edgeSwap.parquet")


#%% look at some stats
