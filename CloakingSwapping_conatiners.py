#%% load data
import geopandas as gpd
t = gpd.read_parquet(r"d:\paper3\Data\trajectories\traj_filled_baseline_ShiftedTimestamps_gapAware_CloakingGeomID_AllCloakingAreas_clean.parquet")
# columns for cloaking based swapping
# intersecting_cloaking_ids - cloaking areas passing only
# HeadEndCloakingAreaId - upcoming cloaking area
# HeadTail - point to split tid before cloaking area
# then delete all syntithic points until first raw point
# this is the first point of the tail

#%% it's actually better to have empty list rather than nan
# Ensure every cell is a proper list
t['intersecting_cloaking_ids'] = t['intersecting_cloaking_ids'].apply(
    lambda x: list(x) if isinstance(x, (list, np.ndarray)) else []
)

t.head()
#%%
t.HeadEndCloakingAreaId.value_counts().sum() #31,272

#%% flag trajectory ids that have been cloaked
tids_to_swap = t.loc[t['HeadEndCloakingAreaId'].notna(), 'tid_subid'].unique()
print(f"mumber of tid_subid requiring swapping: {len(tids_to_swap)}")
print(f"number of tid_subids in sample (total): {t.tid_subid.nunique()}")

t['tid_needs_swap'] = t['tid_subid'].isin(tids_to_swap)

print(t.tid_needs_swap.value_counts())
# points belonging to tids that must be swapped 
#True     5,655,069
#False    1,679,872

#%%
num_targets = len(tids_to_swap)
num_total = t.tid_subid.nunique()

percentage = (num_targets / num_total) * 100

print(f"{percentage:.2f}% of trajectories require swapping because of cloaking")

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






#%% precompute trajectory level information: finding matches
# approach: 11,791 target trajectories (the ones that are cloaked)
# for each target trajectory, all others become "helper" trajectories (must be a different uid)
# find 3 matches, then stop looking for matches. matches must be same cloaking area and same time bin.
# pick one of the 3 matches for swapping 


#%% PRECOMPUTE MATCHES PER CLOAKING GEOMETRY
from collections import defaultdict, Counter
import random
import pandas as pd

# --- 1️⃣ Trajectory summary per tid_subid ---
traj = (
    t.groupby('tid_subid')
    .agg({
        'uid':'first',
        'time_bin':'first',
        'HeadEndCloakingAreaId': lambda x: x.dropna().unique().tolist(),
        'intersecting_cloaking_ids': lambda x: set().union(*[
            i for i in x if isinstance(i, list)
        ])
    })
    .reset_index()
)

# Only trajectories needing swap
mains = traj[traj['HeadEndCloakingAreaId'].apply(len) > 0]
print(f"Main trajectories needing swap: {len(mains)}")

# --- 2️⃣ Pre-index trajectories for fast lookup ---
# By time_bin
tids_by_time = defaultdict(set)
for _, r in traj.iterrows():
    tids_by_time[r.time_bin].add(r.tid_subid)

# By intersecting_cloaking_ids
tids_by_cloak = defaultdict(set)
for _, r in traj.iterrows():
    for cid in r.intersecting_cloaking_ids:
        tids_by_cloak[cid].add(r.tid_subid)

# UID lookup
uid_lookup = dict(zip(traj.tid_subid, traj.uid))

# --- 3️⃣ Initialize tracking structures ---
matches = {}  # (tid_main, HEID) -> helper_tid
used_helpers_per_heid = defaultdict(set)  # HEID -> set of helper tids used for this HEID

# --- 4️⃣ Find matches ---
for _, main in mains.sample(frac=1).iterrows():  # shuffle mains
    tid_main = main.tid_subid
    uid_main = main.uid
    tb_main  = main.time_bin
    heids    = main.HeadEndCloakingAreaId

    for he in heids:
        unused_valid = set()
        reused_valid = set()

        # candidate helpers: same time_bin, passes this HEID
        cands = tids_by_time[tb_main] & tids_by_cloak.get(he, set())
        for c in cands:
            if c == tid_main:
                continue
            uid_c = uid_lookup[c]
            if uid_c == uid_main:
                continue
            # check single-use per HEID
            if c in used_helpers_per_heid[he]:
                reused_valid.add(c)
            else:
                unused_valid.add(c)

        # --- prioritize unused helpers ---
        if unused_valid:
            pool = list(unused_valid)[:3]
            pick = random.choice(pool)
            used_helpers_per_heid[he].add(pick)
        # --- fallback to reuse (different main trajectory) ---
        elif reused_valid:
            pool = list(reused_valid)[:3]
            pick = random.choice(pool)
        else:
            # no valid helper found for this HEID
            continue

        matches[(tid_main, he)] = pick

# --- 5️⃣ Reporting ---
print(f"Total HEID-based matches: {len(matches)}")
helper_usage = Counter(matches.values())
print(f"Unique helpers used: {len(helper_usage)}")
print(f"Helpers reused (any HEID): {sum(v>1 for v in helper_usage.values())}")
print(f"Max reuse count: {max(helper_usage.values()) if helper_usage else 0}")

# --- 6️⃣ Check for violations ---
violations = []
for he, helpers in used_helpers_per_heid.items():
    counts = Counter(helpers)
    for h, c in counts.items():
        if c > 1:
            violations.append((h, he, c))
print(f"Number of helpers violating single-use per HEID: {len(violations)}")
print("Example violations:", violations[:10])

# --- 7️⃣ Optional: record which HEIDs have no helpers ---
matched_heids = set(h for (_, h) in matches.keys())
all_heids = set(h for lst in mains['HeadEndCloakingAreaId'] for h in lst)
heids_without_helpers = all_heids - matched_heids
print(f"Number of HEIDs without helpers: {len(heids_without_helpers)}")

#Main trajectories needing swap: 11791
#Total HEID-based matches: 14102
#Unique helpers used: 4678
#Helpers reused (any HEID): 1639
#Max reuse count: 151
#Number of helpers violating single-use per HEID: 0
#Example violations: []
#Number of HEIDs without helpers: 10


#%% #################################################
#### investiagte matches
#####################################################

# matches dictonary keys
# matches[(tid_main, HEID)] : helper_tid

first_item = next(iter(matches.items()))
print("First item:", first_item)
# first_item[0] is the key, first_item[1] is the value
# First item: 
# (('20200604_465b146da7c31336a60ae621318be651e9da3571_6017',   - target tid
# '2_465b146da7c31336a60ae621318be651e9da3571'),                - sensitive cloaking geometry
# '20200108_c0958ca33142e6ba01506af590d7c37475bbdb75_3532')     - identified helper tid

# does not mention time bin

#%% look at helper tid
ht = t[t['tid_subid']=='20200108_c0958ca33142e6ba01506af590d7c37475bbdb75_3532'].copy()

# at least one row must have the cloaking geometry id '2_465b146da7c31336a60ae621318be651e9da3571' in intersecting_cloaking_ids

#%% locate cloaking geom in helper tid
target_heid = '2_465b146da7c31336a60ae621318be651e9da3571'
mask = ht['intersecting_cloaking_ids'].apply(
    lambda x: isinstance(x, (list, set)) and target_heid in x
)
matching_rows = ht[mask]
matching_rows

#%% now check time bin constarint 
#target tid 20200604_465b146da7c31336a60ae621318be651e9da3571_6017
# and cloaking geom 2_465b146da7c31336a60ae621318be651e9da3571
tt = t[t['tid_subid']=='20200604_465b146da7c31336a60ae621318be651e9da3571_6017'].copy()
tt_cid = tt[tt['HeadEndCloakingAreaId']=='2_465b146da7c31336a60ae621318be651e9da3571'] 
print(len(tt_cid))
# here, only entering this specific cloaking geometry once
print(tt_cid.time_bin_label.unique()) # helper trajectory must pass cloaking geom at night time
tt_cid.time_bin.unique() # 0

#%% check time bin of helper t
print(matching_rows.time_bin_label.unique()) # ['flat peak' 'evening peak'] --> time bin is in fact not matching, this tid should have not been considered a matching candidate!
matching_rows.time_bin.unique() # 2 
#####################################################
#####################################################






#%% HEID-aware swapping - might take long
import numpy as np

t_swapped = t.copy()
used_helpers_per_heid_point = defaultdict(set)  # track used helper points (indices)

# Pre-group main trajectories for fast lookup
t_by_tid = {tid: df for tid, df in t_swapped.groupby('tid_subid')}

print("Starting HEID-aware swapping...")
for i, ((main_tid, heid), helper_tid) in enumerate(matches.items(), 1):
    main_df = t_by_tid[main_tid].sort_index()
    tb_main = main_df.loc[main_df.HeadEndCloakingAreaId == heid, 'time_bin'].iloc[0]
    uid_main = main_df.uid.iloc[0]

    # 1️⃣ Find split point in main trajectory
    head_end_idx = main_df.index[
        (main_df.HeadEndCloakingAreaId == heid) &
        (main_df.HeadTail == 'HeadEnd')
    ]
    if len(head_end_idx) == 0:
        continue  # no split point found
    split_idx = head_end_idx[0]

    # 2️⃣ Define tail: points after split, remove synthetic at start
    tail_indices = main_df.index[main_df.index.get_loc(split_idx)+1:]
    if len(tail_indices) == 0:
        continue
    # remove synthetic points at start of tail
    non_synthetic_start = next((i for i, idx in enumerate(tail_indices)
                                if main_df.loc[idx, 'point_type'] != 'synthetic'), 0)
    tail_indices = tail_indices[non_synthetic_start:]
    if len(tail_indices) == 0:
        continue  # nothing left after removing synthetic

    # 3️⃣ Pick valid helper point
    helper_candidates_idx = t_swapped.index[
        (t_swapped.tid_subid == helper_tid) &
        (t_swapped['intersecting_cloaking_ids'].apply(
            lambda x: heid in x if isinstance(x, (list, set)) else False)) &
        (t_swapped.time_bin == tb_main) &
        (t_swapped.uid != uid_main)
    ]
    # remove already used helper points for this HEID
    helper_candidates_idx = [idx for idx in helper_candidates_idx
                             if idx not in used_helpers_per_heid_point[heid]]
    if not helper_candidates_idx:
        continue  # no valid helper left

    # randomly pick one
    chosen_helper_idx = np.random.choice(helper_candidates_idx)
    helper_container_value = t_swapped.loc[chosen_helper_idx, 'container_id']
    used_helpers_per_heid_point[heid].add(chosen_helper_idx)

    # 4️⃣ Assign helper container_id to tail points
    t_swapped.loc[tail_indices, 'container_id'] = helper_container_value

    # 5️⃣ Optional progress printing
    if i % 1000 == 0:
        print(f"Processed {i} / {len(matches)} HEID matches...")

print("HEID-aware swapping complete!")



#%% 
#%%
# 1️⃣ Count of trajectories with any HEID swap applied
swapped_per_tid = (
    t_swapped.groupby('tid_subid')['container_id']
    .nunique()
)

num_tids_swapped = (swapped_per_tid > 1).sum()
num_tids_no_change = (swapped_per_tid == 1).sum()

print(f"Trajectories with at least one tail swapped: {num_tids_swapped}")
print(f"Trajectories unchanged: {num_tids_no_change}")

# concerning
#Trajectories with at least one tail swapped: 3477
#Trajectories unchanged: 15712



#%% Number of unique original container IDs in each new container_id
unique_orig_counts = t_swapped.groupby('container_id')['container_id_orig'].nunique().reset_index()

print(unique_orig_counts.container_id_orig.min()) # 1
print(unique_orig_counts.container_id_orig.median()) # 1
print(unique_orig_counts.container_id_orig.max())  # 35





#%% by tid to look at in Q
import os

# Folder to save individual trajectory files
output_folder = r"D:\paper3\Data\output/Cloakingswapped_trajectories"  # change path as needed
os.makedirs(output_folder, exist_ok=True)

# Identify container_ids with >1 original container
multi_orig_cids = unique_orig_counts.loc[unique_orig_counts['container_id_orig'] > 1, 'container_id']

# Export each group as a parquet GeoDataFrame
for cid in multi_orig_cids:
    gdf_group = t_swapped[t_swapped['container_id'] == cid]
    
    # Clean filename
    safe_cid = str(cid).replace('/', '_').replace('\\', '_')
    file_path = os.path.join(output_folder, f"{safe_cid}.parquet")
    
    # Export as GeoParquet
    gdf_group.to_parquet(file_path, index=False)

print(f"Exported {len(multi_orig_cids)} merged container_id files to {output_folder}")