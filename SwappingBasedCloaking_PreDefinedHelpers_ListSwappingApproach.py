#%%look at clkgps ouptu later, for now try a list based approach to swapping
import pandas as pd
import geopandas as gpd

#ClkGpsSwappedT = pd.read_parquet(r"d:\paper3\SwappingBasedCloaking_9March26\fromVM131\ClkGpsSwappedT.parquet")
# geometry is stored in t_forSwapping, must add it back
#print(len(t_forSwapping)-len(ClkGpsSwappedT)) # lost 8208 points!

t_forSwapping = gpd.read_parquet(r"d:\paper3\SwappingBasedCloaking_9March26\t_forSwapping_26723gaps.parquet")
#print(len(t_forSwapping))
#print(len(ClkGpsSwappedT))
#print(len(t_forSwapping)-len(ClkGpsSwappedT)) # lost didn't loose any points during swapping (lost points before)

#ClkGpsSwappedT = t_forSwapping[['row_uid', 'unix_timestamp_final', 'speed_mps', 'speed_source', 'time_bin', 'time_bin_label', 'intersecting_cloaking_ids', 'Sensitive_CloakingAreaId', 'HeadTail', 'HeadEndCloakingAreaId', 'match_geometry']].merge(ClkGpsSwappedT, on='row_uid', how='right')

import pickle
with open(r"\\tsclient\R\paper3\fromVM_201\helper_pool_dict_ordered.pkl", "rb") as f:
    helper_pool_dict_ordered = pickle.load(f)


#%%  list based approach
# must define the main tail start point too
main_splits_list = list(helper_pool_dict_ordered.keys())
t_forSwapping.head()

# flag mains in df to find tail start
#HeadTail only gives HeadEnd - we also want TailStart!
# HeadTail
# nan        7295461
# HeadEnd      31272 - 26k of those of pre-defined helpers, only working with those for now
# pre-defined ensures that orig tid and uid are folloing the constraints

#%% 
import numpy as np
t_forSwapping['main_clkgp_wHelper'] = np.where(
    t_forSwapping['row_uid'].isin(main_splits_list),
    'main_head_end', 
    np.NaN
) 
print(t_forSwapping['main_clkgp_wHelper'].unique())
t_forSwapping.head()

#%% label the tail start
t_forSwapping = t_forSwapping.sort_values(['tid_subid', 'row_uid'])

head_mask = t_forSwapping['main_clkgp_wHelper'] == 'main_head_end'
tail_mask = t_forSwapping.groupby('tid_subid')['main_clkgp_wHelper'].shift(1) == 'main_head_end'

t_forSwapping.loc[tail_mask, 'main_clkgp_wHelper'] = 'main_tail_start'

print(t_forSwapping['main_clkgp_wHelper'].unique())
t_forSwapping[t_forSwapping['main_clkgp_wHelper'] != 'nan']

# they had the same gap_number within the tid, could've identified them this way
#%% overview of main gaps
# these are the points segmenting a main into head and tail
t_forSwapping[t_forSwapping['main_clkgp_wHelper'] != 'nan'][['row_uid', 'tid_subid', 'time_bin', 'HeadEndCloakingAreaId', 'main_clkgp_wHelper']]

#%% label specific to this gap:
import pandas as pd
import numpy as np

# RENAME POINT COLUMN, row_uid is too confusing
t_forSwapping = t_forSwapping.rename(columns={'row_uid': 'point_id_unique'})

t_forSwapping = t_forSwapping.sort_values(['tid_subid', 'point_id_unique']).copy()
t_forSwapping['main_headEND_pointid'] = np.where(
    t_forSwapping['main_clkgp_wHelper'] == 'main_head_end',
    t_forSwapping['point_id_unique'],
    np.nan
)
t_forSwapping['main_tailStart_pointid'] = np.where(
    t_forSwapping['main_clkgp_wHelper'] == 'main_tail_start', 
    t_forSwapping['point_id_unique'],
    np.nan
)

t_forSwapping['main_headEND_pointid'] = t_forSwapping['main_headEND_pointid'].fillna(
    t_forSwapping.groupby('tid_subid')['main_headEND_pointid'].shift(1)
)
t_forSwapping['main_tailStart_pointid'] = t_forSwapping['main_tailStart_pointid'].fillna(
    t_forSwapping.groupby('tid_subid')['main_tailStart_pointid'].shift(-1)
)
# make them integer
t_forSwapping['main_headEND_pointid'] = t_forSwapping['main_headEND_pointid'].astype('Int64')
t_forSwapping['main_tailStart_pointid'] = t_forSwapping['main_tailStart_pointid'].astype('Int64')

# add pair, i.e. clkg identifier
t_forSwapping['main_clkgp_id'] = list(
    zip(t_forSwapping['main_headEND_pointid'], t_forSwapping['main_tailStart_pointid'])
)
print(t_forSwapping['main_clkgp_id'].nunique()) # 26724 - same as clk gaps in swapping (one extra)
print(t_forSwapping['main_clkgp_id'].value_counts().reset_index()['count'].unique()) # good, each identifier only appears once or twice, the others are NA,NA pairs, i.e., invalid pais

# add head/tail unique label
t_forSwapping['main_clkgp_wHelper_id'] = t_forSwapping['main_clkgp_wHelper'] + '_' + t_forSwapping['main_headEND_pointid'].astype(str) + '_' + t_forSwapping['main_tailStart_pointid'].astype(str)
t_forSwapping[t_forSwapping['main_clkgp_wHelper'] != 'nan']

#%%
t_forSwapping.to_parquet(r"d:\paper3\SwappingBasedCloaking_9March26\t_forSwapping_26723gaps_labelled.parquet")

#%% now update 
key_map = dict(zip(t_forSwapping[t_forSwapping['main_clkgp_wHelper'] != 'nan']['point_id_unique'], t_forSwapping[t_forSwapping['main_clkgp_wHelper'] != 'nan']['main_clkgp_id']))
helper_pool_dict_ordered_updated = {key_map.get(k, k): v for k, v in helper_pool_dict_ordered.items()}

print(len(helper_pool_dict_ordered))
print(len(helper_pool_dict_ordered_updated))
helper_pool_dict_ordered_updated

#%%
with open(r"\\tsclient\R\paper3\helper_pool_dict_ordered_updated.pkl", "wb") as f:
    pickle.dump(helper_pool_dict_ordered_updated, f)







#%% load data
import geopandas as gpd
import pickle

t_forSwapping = gpd.read_parquet(r"d:\paper3\SwappingBasedCloaking_9March26\t_forSwapping_26723gaps_labelled.parquet")

with open(r"\\tsclient\R\paper3\helper_pool_dict_ordered_updated.pkl", "rb") as f:
    helper_pool_dict_ordered_updated = pickle.load(f)


#%% 
# import libraries
import pandas as pd
from collections import defaultdict, deque
import random
import numpy as np

# prep for swap
# add trajectory index: tid -> ordered list of row_uids
trajectory_index = {}
pid_to_tid = {}
for tid, df_tid in t_forSwapping.groupby('tid_subid'):
    traj_list = df_tid.sort_values('point_id_unique')['point_id_unique'].tolist()  
    trajectory_index[tid] = traj_list
    for uid in traj_list:
        pid_to_tid[uid] = tid

# initialise tracking of swaps
swap_history = defaultdict(list)
locked_main_splits = set()  
od_dict = defaultdict(list)
retry_counts = defaultdict(int)
waiting = defaultdict(list)
max_retries = 15


protected_splits = set()
#%% sarwt swapping - new approach track swap_id
# initialise swap_id tracking
# -------------------------------
# Prepare swap tracking
# -------------------------------
swap_id_map = {}  # point_id -> swap_id for all points that moved
swap_counter = 0  # incremental counter for generating unique swap ids

# -------------------------------
# Start swapping (modified)
# -------------------------------
from tqdm import tqdm
from collections import deque

swap_queue = deque(helper_pool_dict_ordered_updated.keys())
pbar = tqdm(total=len(swap_queue), desc="Processing swaps")

while swap_queue:
    main_clkgp = swap_queue.popleft()
    
    if main_clkgp in locked_main_splits:
        continue

    main_head_end, main_tail_start = main_clkgp

    if pd.isna(main_head_end) or pd.isna(main_tail_start):
        continue
    if tuple(sorted((main_head_end, main_tail_start))) in protected_splits:
        continue

    main_tid_head = pid_to_tid.get(main_head_end)
    main_tid_tail = pid_to_tid.get(main_tail_start)
    if main_tid_head is None or main_tid_tail is None or main_tid_head != main_tid_tail:
        continue
    main_tid = main_tid_head

    main_traj = trajectory_index[main_tid]
    m_h_i = main_traj.index(main_head_end)
    m_t_i = main_traj.index(main_tail_start)
    if m_t_i != m_h_i + 1:
        continue

    head_main = main_traj[:m_t_i]
    tail_main = main_traj[m_t_i:]

    helper_candidates = helper_pool_dict_ordered_updated.get(main_clkgp, [])
    random.shuffle(helper_candidates)
    swap_success = False

    for h_head_end, h_tail_start in helper_candidates:
        if pd.isna(h_head_end) or pd.isna(h_tail_start):
            continue
        if tuple(sorted((h_head_end, h_tail_start))) in protected_splits:
            continue

        helper_tid = pid_to_tid.get(h_head_end)
        if helper_tid is None or helper_tid == main_tid:
            continue

        helper_traj = trajectory_index[helper_tid]
        if h_head_end not in helper_traj or h_tail_start not in helper_traj:
            continue

        h_h_i = helper_traj.index(h_head_end)
        h_t_i = helper_traj.index(h_tail_start)
        if h_t_i != h_h_i + 1:
            continue
        head_helper = helper_traj[:h_t_i]
        tail_helper = helper_traj[h_t_i:]

        # --- prevent points returning to a trajectory they were already part of
        invalid = any(main_tid in swap_history[pid] for pid in tail_helper) or \
                  any(helper_tid in swap_history[pid] for pid in tail_main)
        if invalid:
            continue

        # --- perform swap
        new_main_traj = head_main + tail_helper
        new_helper_traj = head_helper + tail_main

        # --- protect joins (bidirectional)
        if tail_helper:
            protected_splits.add(tuple(sorted((main_head_end, tail_helper[0]))))
        if tail_main:
            protected_splits.add(tuple(sorted((h_head_end, tail_main[0]))))

        # --- update trajectory_index
        trajectory_index[main_tid] = new_main_traj
        trajectory_index[helper_tid] = new_helper_traj

        # --- update pid -> tid mapping and swap history
        for pid in new_main_traj:
            pid_to_tid[pid] = main_tid
            swap_history[pid].append(main_tid)
        for pid in new_helper_traj:
            pid_to_tid[pid] = helper_tid
            swap_history[pid].append(helper_tid)

        # --- assign swap_id to all points that moved
        swap_counter += 1
        swap_id = f"swap_{swap_counter}"
        for pid in tail_helper + tail_main:
            swap_id_map[pid] = swap_id

        # --- track origin/destination
        if tail_helper:
            od_dict[main_head_end].append(tail_helper[0])
        if tail_main:
            od_dict[h_head_end].append(tail_main[0])

        locked_main_splits.add(main_clkgp)
        swap_success = True
        break

    if not swap_success:
        waiting[main_tid].append(main_clkgp)
        retry_counts[main_clkgp] += 1
        if retry_counts[main_clkgp] < max_retries:
            swap_queue.append(main_clkgp)

    pbar.update(1)

pbar.close()
#Processing swaps: 173314it [04:27, 647.71it/s]     
 
                       
#%%
# -------------------------------
# Rebuild df_points from trajectory_index
# -------------------------------
rows = []
for tid, traj in trajectory_index.items():
    for order, pid in enumerate(traj):
        rows.append({
            'final_tid': tid,
            'point_id': pid,
            'order_in_traj': order,
            'swap_id': swap_id_map.get(pid, None)
        })

trajectory_index_df = pd.DataFrame(rows)

# add original tid_subid for reference
original_pid_to_tid = dict(zip(t_forSwapping['point_id_unique'], t_forSwapping['tid_subid']))
trajectory_index_df['original_tid'] = trajectory_index_df['point_id'].map(original_pid_to_tid)


trajectory_index_df.head()
#%%
trajectory_index_df_origtid_n = trajectory_index_df.groupby('final_tid')['original_tid'].nunique().reset_index()
print(trajectory_index_df_origtid_n.original_tid.min()) # 1
print(trajectory_index_df_origtid_n.original_tid.max()) #26
print(trajectory_index_df_origtid_n.original_tid.median()) # 2
print(trajectory_index_df.swap_id.unique())

#%% validate swaps
#%% ensure this is the swapped df
trajectory_index_df.groupby('final_tid')['original_tid'].nunique().reset_index().original_tid.max()

#%% must merge columns back to swapped df
df_points_validation = trajectory_index_df.copy()
df_points_validation.rename(columns={'point_id': 'point_id_unique'}, inplace=True)
df_points_validation = t_forSwapping[['point_id_unique', 'main_clkgp_wHelper_id', 'main_headEND_pointid', 'main_tailStart_pointid', 'match_geometry']].merge(df_points_validation, on= 'point_id_unique', how='right')

#%% tidy up df
df_points_validation['main_clkgp_wHelper_id'] = df_points_validation['main_clkgp_wHelper_id'].replace('nan_<NA>_<NA>', None)
df_points_validation['main_headEND_pointid'] = df_points_validation['main_headEND_pointid'].replace('<NA>', None)
df_points_validation['main_tailStart_pointid'] = df_points_validation['main_tailStart_pointid'].replace('<NA>', None)
df_points_validation.head()

# add tuple for clkgp
df_points_validation['main_clkgp_id_tuple'] = list(zip(df_points_validation['main_headEND_pointid'], df_points_validation['main_tailStart_pointid']))
df_points_validation['main_clkgp_id_tuple'] = df_points_validation['main_clkgp_id_tuple'].apply(
    lambda x: None if (isinstance(x, tuple) and pd.isna(x[0]) and pd.isna(x[1])) else x
)
# look up the valid helpers!
df_points_validation['valid_helpers'] = df_points_validation['main_clkgp_id_tuple'].map(helper_pool_dict_ordered_updated)
df_points_validation[df_points_validation['main_clkgp_id_tuple'].notna()]

#%% (1) find active swap. i.e., split points
df_points_validation = df_points_validation.sort_values(['final_tid', 'order_in_traj']).copy()

def mark_active_swap(group):
    group = group.copy()
    n = len(group)
    if n < 2:
        # Single-row group → cannot be active swap
        group['active_swap'] = False
        return group

    # Compare consecutive pairs
    diff_next = group['original_tid'].values[:-1] != group['original_tid'].values[1:]

    # Initialize active_swap column
    active_swap = np.zeros(n, dtype=bool)

    # For each consecutive pair that differs, mark both rows
    active_swap[:-1] |= diff_next  # mark current row
    active_swap[1:]  |= diff_next  # mark next row

    group['active_swap'] = active_swap
    return group

df_points_validation = df_points_validation.groupby('final_tid', group_keys=False).apply(mark_active_swap)
print(df_points_validation.active_swap.value_counts())

#active_swap
#False    7267050
#True       59683


#%%
df_points_validation = df_points_validation.sort_values(['final_tid', 'order_in_traj'])
df_points_validation[df_points_validation['active_swap'] == True][['point_id_unique', 'main_clkgp_wHelper_id', 'final_tid', 'original_tid', 'valid_helpers','active_swap']]

#%% (2) is a main involved in this split?
# Initialize
df_points_validation['main_involved_in_split'] = np.nan

# Only look at active_swap rows
active_idx = df_points_validation.index[df_points_validation['active_swap']]

# Shift main_clkgp_wHelper_id up/down to check neighbors
main_prev = df_points_validation['main_clkgp_wHelper_id'].shift(1)
main_next = df_points_validation['main_clkgp_wHelper_id'].shift(-1)

# For each active_swap row, check if main is involved in pair
main_in_pair = (
    df_points_validation['main_clkgp_wHelper_id'].notna() |
    main_prev.notna() |
    main_next.notna()
)

# Only keep for active_swap rows
df_points_validation.loc[df_points_validation['active_swap'], 'main_involved_in_split'] = main_in_pair[df_points_validation['active_swap']]

print(df_points_validation[df_points_validation['active_swap'] == True][['point_id_unique', 'main_clkgp_wHelper_id', 'final_tid', 'original_tid', 'valid_helpers','active_swap','main_involved_in_split']].main_involved_in_split.unique())
# all True, a main is involved in every split/swap (important for logic)
df_points_validation[df_points_validation['active_swap'] == True][['point_id_unique', 'main_clkgp_wHelper_id', 'final_tid', 'original_tid', 'valid_helpers','active_swap','main_involved_in_split']]

#%% (3) now validate helper logic
#%% (3) now validate helper logic
df_points_validation['valid_swap'] = np.nan

mask_main = df_points_validation['main_involved_in_split'] == True


# --------------------
# HEAD helpers
# --------------------
head_mask = mask_main & df_points_validation['main_clkgp_wHelper_id'].str.startswith('main_head_end_')
head_idx = df_points_validation.index[head_mask]

def check_head(row):
    helpers = row['valid_helpers']
    idx = row.name

    if idx + 1 not in df_points_validation.index:
        return None

    pid_below = df_points_validation.loc[idx + 1, 'point_id_unique']

    if not isinstance(helpers, list) or len(helpers) == 0:
        return False

    return any(pid_below == tup[1] for tup in helpers)

head_results = df_points_validation.loc[head_idx].apply(check_head, axis=1)

# assign to both rows
df_points_validation.loc[head_idx, 'valid_swap'] = head_results
df_points_validation.loc[head_idx + 1, 'valid_swap'] = head_results.values


# --------------------
# TAIL helpers
# --------------------
tail_mask = mask_main & df_points_validation['main_clkgp_wHelper_id'].str.startswith('main_tail_start_')
tail_idx = df_points_validation.index[tail_mask]

def check_tail(row):
    helpers = row['valid_helpers']
    idx = row.name

    if idx - 1 not in df_points_validation.index:
        return None

    pid_above = df_points_validation.loc[idx - 1, 'point_id_unique']

    if not isinstance(helpers, list) or len(helpers) == 0:
        return False

    return any(pid_above == tup[0] for tup in helpers)

tail_results = df_points_validation.loc[tail_idx].apply(check_tail, axis=1)

# assign to both rows
df_points_validation.loc[tail_idx, 'valid_swap'] = tail_results
df_points_validation.loc[tail_idx - 1, 'valid_swap'] = tail_results.values


print(df_points_validation.valid_swap.value_counts(dropna=False))
#valid_swap
#NaN      7267043
#True       59683
#False          7

#%%
df_points_validation[df_points_validation['valid_swap']==False]
# the 7 false make sense, they are not active swaps ---> list based cloaking swapping prodced valid swapping splits
# if there are long gaps it is becuase of the sparse data



#%% add syn traj back in where needed, i.e., clk gap did not participate in swap

#%% connect od of active swaps via synthetic trajectories

#%% evaluate swaps


