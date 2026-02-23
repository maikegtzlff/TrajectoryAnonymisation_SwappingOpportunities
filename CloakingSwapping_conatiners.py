#%% load data
import geopandas as gpd
t = gpd.read_parquet(r"d:\paper3\Data\trajectories\traj_filled_baseline_ShiftedTimestamps_gapAware_CloakingGeomID_AllCloakingAreas_clean.parquet")
# columns for cloaking based swapping
# intersecting_cloaking_ids - cloaking areas passing only
# HeadEndCloakingAreaId - upcoming cloaking area
# HeadTail - point to split tid before cloaking area
# then delete all syntithic points until first raw point
# this is the first point of the tail

#%%
t.HeadEndCloakingAreaId.value_counts().sum() #31,272

#%% look at intersecting_cloaking_ids
import numpy as np

def is_non_empty(x):
    if x is None:
        return False
    elif isinstance(x, list):
        return len(x) > 0
    elif isinstance(x, np.ndarray):
        return len(x) > 0
    else:
        return False

non_empty_mask = t['intersecting_cloaking_ids'].apply(is_non_empty)

print("Number of non-empty lists/arrays:", non_empty_mask.sum())
print("Any non-empty?", non_empty_mask.any())
print(t.loc[non_empty_mask, 'intersecting_cloaking_ids'].head())


#%% it's actually better to have empty list rather than nan
# Ensure every cell is a proper list
t['intersecting_cloaking_ids'] = t['intersecting_cloaking_ids'].apply(
    lambda x: list(x) if isinstance(x, (list, np.ndarray)) else []
)


#%% test code on a sample
# Build a dict: cloaking ID → list of tid_subid
from collections import defaultdict

cloaking_to_tids = defaultdict(set)
for tid, grp in t.groupby("tid_subid"):
    for ids in grp['intersecting_cloaking_ids']:
        if isinstance(ids, list):
            for cid in ids:
                cloaking_to_tids[cid].add(tid)
print(cloaking_to_tids) 

#%%
# Group once by tid_subid and keep HeadEndCloakingAreaId
tid_to_headend = t.groupby('tid_subid')['HeadEndCloakingAreaId'].first().dropna()

# Build list of main tids that have at least one helper
main_tids_with_helper = [
    main_tid
    for main_tid, main_he_id in tid_to_headend.items()
    if (cloaking_to_tids.get(main_he_id, set()) - {main_tid})
]

# Select first main trajectory
main_tid = main_tids_with_helper[0]
main_he_id = tid_to_headend[main_tid]

# Indices of main points
main_points_idx = t[t['tid_subid'] == main_tid].index

# Helper tids
helper_tids = list(cloaking_to_tids[main_he_id] - {main_tid})
helper_points_idx = t[t['tid_subid'].isin(helper_tids)].index

# Build sample
gdf_sample = t.loc[main_points_idx.union(helper_points_idx)].copy()




#%%
from collections import defaultdict, deque
import pandas as pd
import numpy as np
import time

# --------------------------
# 0️⃣ Prepare points
# --------------------------
gdf = t.copy()
gdf['container_id'] = -1
gdf['visited_containers'] = gdf.apply(lambda _: [], axis=1)
gdf['swap_count'] = 0
gdf['tail_start'] = False
gdf['HeadID'] = np.nan
gdf['new_tid'] = np.nan
gdf['orig_tid'] = gdf['tid_subid']

# --------------------------
# 1️⃣ Precompute mappings
# --------------------------
tid_to_indices = {tid: gdf.index[gdf['tid_subid'] == tid].to_numpy() for tid in gdf['tid_subid'].unique()}

# CloakingAreaId → main points
cloaking_to_main_points = defaultdict(list)
for idx, row in gdf.iterrows():
    if pd.notna(row['HeadEndCloakingAreaId']):
        cloaking_to_main_points[row['HeadEndCloakingAreaId']].append(idx)

# CloakingAreaId → helper points
cloaking_to_helper_points = defaultdict(list)
for idx, row in gdf.iterrows():
    if isinstance(row['intersecting_cloaking_ids'], list):
        for ce_id in row['intersecting_cloaking_ids']:
            cloaking_to_helper_points[ce_id].append(idx)

# Candidate helpers per HeadEndCloakingAreaId
precomputed_candidates = {}
for he_id, main_idxs in cloaking_to_main_points.items():
    candidates = [
        i for i in cloaking_to_helper_points.get(he_id, [])
        if gdf.at[i, 'uid'] not in gdf.loc[main_idxs, 'uid'].values
    ]
    precomputed_candidates[he_id] = deque(candidates)  # use deque for efficient popping

# List of main tid_subids
main_tid_subids = [tid for tid, grp in gdf.groupby('tid_subid') if grp['HeadEndCloakingAreaId'].notna().any()]

# --------------------------
# 2️⃣ Swapping loop (multi-helper)
# --------------------------
queue = deque(main_tid_subids)
swap_counter = 0
swap_log = []
start_time = time.time()

while queue:
    tid_main = queue.popleft()
    main_idx = tid_to_indices[tid_main]
    main_points = gdf.loc[main_idx]

    # All head points in this main
    head_idxs = main_points.index[main_points['HeadEndCloakingAreaId'].notna()]

    for idx_head in head_idxs:
        he_id = gdf.at[idx_head, 'HeadEndCloakingAreaId']

        # Pop the next helper (if available) for this head
        if not precomputed_candidates[he_id]:
            continue
        idx_helper = precomputed_candidates[he_id].popleft()
        tid_helper = gdf.at[idx_helper, 'tid_subid']
        helper_idx = tid_to_indices[tid_helper]

        # Tail indices
        tail_main_idx = main_idx[main_idx > idx_head]
        tail_helper_idx = helper_idx[helper_idx > idx_helper]
        if len(tail_main_idx) == 0 and len(tail_helper_idx) == 0:
            continue

        # Assign new trajectory ID
        swap_counter += 1
        new_tid = swap_counter

        # Vectorized slice for main head+tail
        all_main_idx = np.concatenate([[idx_head], tail_main_idx]) if len(tail_main_idx) > 0 else np.array([idx_head])
        gdf.loc[all_main_idx, ['new_tid', 'orig_tid']] = pd.DataFrame({
            'new_tid': new_tid,
            'orig_tid': tid_main
        }, index=all_main_idx)
        gdf.loc[tail_main_idx, 'swap_count'] += 1
        gdf.loc[tail_main_idx, 'visited_containers'] = gdf.loc[tail_main_idx, 'visited_containers'].apply(
            lambda x: x + [gdf.at[idx_head, 'container_id']]
        )

        # Vectorized slice for helper head+tail
        if len(tail_helper_idx) > 0:
            all_helper_idx = np.concatenate([[idx_helper], tail_helper_idx])
            gdf.loc[all_helper_idx, ['new_tid', 'orig_tid']] = pd.DataFrame({
                'new_tid': new_tid,
                'orig_tid': tid_helper
            }, index=all_helper_idx)
            gdf.loc[tail_helper_idx, 'swap_count'] += 1
            gdf.loc[tail_helper_idx, 'visited_containers'] = gdf.loc[tail_helper_idx, 'visited_containers'].apply(
                lambda x: x + [gdf.at[idx_helper, 'container_id']]
            )

        # Tail start marking
        raw_tail_main_mask = gdf.loc[tail_main_idx, 'point_type'] != 'synthetic'
        if raw_tail_main_mask.any():
            first_real_idx = tail_main_idx[raw_tail_main_mask.argmax()]
            gdf.at[first_real_idx, 'tail_start'] = True

        # HeadID assignment
        tail_end_idx = first_real_idx if raw_tail_main_mask.any() else tail_main_idx[-1] if len(tail_main_idx) > 0 else idx_head
        gdf.loc[idx_head:tail_end_idx, 'HeadID'] = he_id

        # Queue helper if it has heads
        helper_head_mask = gdf.loc[helper_idx, 'HeadEndCloakingAreaId'].notna()
        if helper_head_mask.any() and tid_helper not in queue:
            queue.append(tid_helper)

# --------------------------
# 3️⃣ Clean-up
# --------------------------
gdf = gdf[gdf['point_type'].notna()].reset_index(drop=True)
swap_log_df = pd.DataFrame(swap_log)
print(f"Swapping complete! {swap_counter} swaps performed in {time.time()-start_time:.1f}s")
#%%
swap_log_df

#%%
gdf.head()
#%%
print(gdf.new_tid.unique())
print(gdf.HeadID.unique())
print(gdf.tail_start.unique())
#print(gdf.visited_containers.unique())
print(gdf.swap_count.unique())
print(gdf.container_id.unique())

#%%
print(gdf.tail_start.sum())
print(gdf.new_tid.nunique())
print(gdf[gdf.tail_start]['new_tid'].nunique())


#%%
gdf.groupby('new_tid')['orig_tid'].value_counts().median() # 39 orig tid on average contributing to a new tid

#%% look at some of these in Q
# only look at trajectories thwat took part in a swap
multi_map = (
    gdf.groupby('new_tid')['orig_tid']
       .nunique()
       .loc[lambda x: x > 1]
       .index
)

print(len(multi_map))
gdf_multi = gdf[gdf.new_tid.isin(multi_map)]

gdf_multi['point_id_newtid'] = (
    gdf_multi.groupby('new_tid')
             .cumcount()
)

from pathlib import Path
import re

out_dir = Path(r"D:\paper3\Data\tetsing/swapped_only")
out_dir.mkdir(parents=True, exist_ok=True)

def safe_tid(t):
    return re.sub(r'[\\/*?:"<>|]', "_", str(t))

for tid, sub in gdf_multi.groupby("new_tid"):
    sub.reset_index(drop=True)\
       .to_parquet(out_dir / f"{safe_tid(tid)}_cloakingSwapped.parquet", index=False)
    
#%%
print(gdf.container_id.unique())
gdf.visited_containers.unique()
#%%
gdf.to_parquet(r'D:\paper3\Data/t_CloakedSwapped.parquet')