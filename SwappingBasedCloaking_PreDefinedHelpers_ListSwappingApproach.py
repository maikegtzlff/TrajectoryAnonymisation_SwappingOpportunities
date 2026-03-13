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
# the 7 false make sense, they are not active swaps 
# ---> list based cloaking swapping prodced valid swapping splits
# if there are long gaps it is becuase of the sparse data
#%% export on VM 100
print(len(df_points_validation))
df_points_validation.to_parquet(r'D:\paper3\SwappingBasedCloaking_10March26_listApproach/Swapped_CloakingAreaBased_Validated_ListBasedSwappingApproach.parquet')



#%% load df_points_validated back in VM131
import geopandas as gpd
t_cswappingl = gpd.read_parquet(r"d:\paper3\FinalCloakedBasedSwapping\SwappingBasedCloaking_10March26_listApproach\Swapped_CloakingAreaBased_Validated_ListBasedSwappingApproach.parquet")
t_cswappingl.head()

#%% add syn traj back in where needed, i.e., clk gap did not participate in swap
import numpy as np
# get tuples back
t_cswappingl['main_clkgp_id_tuple'] = t_cswappingl['main_clkgp_id_tuple'].apply(
    lambda x: tuple(x) if isinstance(x, (list, tuple, np.ndarray)) else x
)
# clk gaps that need their orig syn points back because they did not participate in swapping
#t_cswappingl[t_cswappingl['main_clkgp_wHelper_id'].notna()] # not na and active_swap False = must fill with original syn points
t_cswappingl_needOrigSynPts = t_cswappingl[
    (t_cswappingl['main_clkgp_wHelper_id'].notna()) &
    (~t_cswappingl['active_swap'])
] # 20938 rows, number of unique clk gaps that did not participate in swapping: 

print(t_cswappingl_needOrigSynPts['main_clkgp_id_tuple'].nunique()) # 10474

#%% how do I know which points I need to add back in, and where? 
# based on point_id_unique
# for example
# the gap between main_head_end_131_174 and main_tail_start_131_174 in point_id_unique are all the syn points needed
# here from 132 to 173 (incl), point_id_unique 0f main_head_end is 131, unconnected main_tail_start is 174
# the numbers between main_clkgp_id_tuple  [131.0, 174.0]
#'active_swap', 'valid_swap'

# need all of those ysn points that I will back in as point ids list
# first, get the tuples of interest
import pandas as pd
tpl_tobefilledSyn = [
    tuple(int(x) if pd.notna(x) else None for x in tpl)
    for tpl in t_cswappingl_needOrigSynPts['main_clkgp_id_tuple'].unique()
]
tpl_tobefilledSyn

#%%
# drop the three tuples with nan as destination - no end point = no need to fill synthetically
import math
tpl_tobefilledSyn = [
    tpl for tpl in tpl_tobefilledSyn
    if tpl is not None and not any(pd.isna(x) for x in tpl)
]

points_between_unswappedClkGps = {
    tpl: list(range(tpl[0] + 1, tpl[1]))
    for tpl in tpl_tobefilledSyn
}
points_between_unswappedClkGps
#%% export dict
import pickle
with open(r"D:\paper3\FinalCloakedBasedSwapping/SynPoints_between_unswappedClkGps.pickle", "wb") as f:
    pickle.dump(points_between_unswappedClkGps, f)

#%% than turn into flat list
origsynpoints = sorted({
    point
    for points in points_between_unswappedClkGps.values()
    for point in points
})

print(len(origsynpoints)) # 1827 synthetic points that I am adding back
origsynpoints

#%% add these points back to the df
t_clkd_filled = gpd.read_parquet(r"d:\paper3\FinalCloakedBasedSwapping\filledtrajectories_gdfenriched2\traj_filled_baseline_ShiftedTimestamps_gapAware_CloakingGeomID_AllCloakingAreas_clean.parquet")
print(len(t_clkd_filled))

col_name = 'row_uid'
if col_name in t_clkd_filled.columns:
    print(f"Column '{col_name}' exists")
else:
    print(f"Column '{col_name}' does NOT exist")

print(t_clkd_filled.point_type.unique())
t_clkd_filled.head() 

#%% only keep the syn points that we want to add back
origsynpoints_df = t_clkd_filled[t_clkd_filled['row_uid'].isin(origsynpoints)].copy()
print(len(origsynpoints))
print(len(origsynpoints_df))
origsynpoints_df.point_type.unique() # only selected syn points :)

#%% add the orig syn points back to fill the unswapped clg gaps
origsynpoints_df.rename(columns={'row_uid': 'point_id_unique', 'tid_subid': 'original_tid'}, inplace=True)
origsynpoints_df[['point_id_unique', 'original_tid', 'point_type', 'match_geometry']]

#%% replace synthetic with "orig_synthetic"
print(origsynpoints_df.point_type.unique())
origsynpoints_df['point_type'] = 'orig_synthetic'
print(origsynpoints_df.point_type.unique())




#%% want a new tuple based on order_in_traj column for the clkg that were not swapped
t_cswappingl_needOrigSynPts[t_cswappingl_needOrigSynPts['main_clkgp_wHelper_id'].notna()].sort_values(by='main_clkgp_id_tuple')

#%%
# rows with non-None main_clkgp_id_tuple
df_valid = t_cswappingl_needOrigSynPts[t_cswappingl_needOrigSynPts['main_clkgp_id_tuple'].notna()].copy()
# tuple elements as int 
df_valid['main_clkgp_id_tuple'] = df_valid['main_clkgp_id_tuple'].apply(
    lambda tup: tuple(int(x) for x in tup if pd.notna(x))
)
# dict: point_id_unique to order_in_traj
point_to_order = dict(zip(t_cswappingl_needOrigSynPts['point_id_unique'], t_cswappingl_needOrigSynPts['order_in_traj']))
df_valid['order_in_traj_tuple'] = df_valid['main_clkgp_id_tuple'].apply(
    lambda tpl: tuple(point_to_order.get(pid, None) for pid in tpl)
)
t_cswappingl_needOrigSynPts.loc[df_valid.index, 'order_in_traj_tuple'] = df_valid['order_in_traj_tuple']

t_cswappingl_needOrigSynPts[t_cswappingl_needOrigSynPts['main_clkgp_wHelper_id'].notna()] # good!

#%% add the order_in_traj_tuple back to the main df!!
# attributes I want and key
#t_cswappingl_needOrigSynPts[['point_id_unique', 'order_in_traj_tuple']]
t_cswappingl = t_cswappingl.merge(t_cswappingl_needOrigSynPts[['point_id_unique', 'order_in_traj_tuple']], on='point_id_unique', how='left')
t_cswappingl



#%% add points to swapped df
t_cswappingl_origsynf = pd.concat([t_cswappingl, origsynpoints_df[['point_id_unique', 'original_tid', 'point_type', 'match_geometry']].copy()])
t_cswappingl_origsynf
#%% after filling, 
t_cswappingl_origsynf = t_cswappingl_origsynf.sort_values('point_id_unique').reset_index(drop=True)
t_cswappingl_origsynf
#%% look at one gap I remember (131 to 174)
t_cswappingl_origsynf[
    (t_cswappingl_origsynf['point_id_unique'] >= 130) &
    (t_cswappingl_origsynf['point_id_unique'] <= 176)
][['point_id_unique', 'order_in_traj_tuple', 'order_in_traj']]


#%% order_in_traj must be updated, best in a new column
t_cswappingl_origsynf = t_cswappingl_origsynf.reset_index(drop=True)
# don't think I needed the order_in_traj_tuple... using interpolate on NaN instead
t_cswappingl_origsynf['order_in_traj_filled'] = t_cswappingl_origsynf['order_in_traj'].interpolate(method='linear') 

#%% looking at a known clkg gap
t_cswappingl_origsynf[
    (t_cswappingl_origsynf['point_id_unique'] >= 130) &
    (t_cswappingl_origsynf['point_id_unique'] <= 176)
][['point_id_unique', 'order_in_traj_tuple', 'order_in_traj', 'order_in_traj_filled']]

#%% look at another clk gap
#t_cswappingl_needOrigSynPts[t_cswappingl_needOrigSynPts['main_clkgp_wHelper_id'].notna()].sort_values(by='main_clkgp_id_tuple')
t_cswappingl_origsynf[
    (t_cswappingl_origsynf['point_id_unique'] >= 3250) &
    (t_cswappingl_origsynf['point_id_unique'] <= 3400)
][['point_id_unique', 'order_in_traj_tuple', 'order_in_traj', 'order_in_traj_filled']] # worked

#%% validate order_in_traj_filled
# if order_in_traj is not nan it should not have changed
t_cswappingl_origsynf['order_in_traj_filled_valid'] = np.nan
mask = t_cswappingl_origsynf['order_in_traj'].notna()
t_cswappingl_origsynf.loc[mask, 'order_in_traj_filled_valid'] = t_cswappingl_origsynf.loc[mask, 'order_in_traj'] == t_cswappingl_origsynf.loc[mask, 'order_in_traj_filled']
print(t_cswappingl_origsynf.order_in_traj_filled_valid.unique()) # [True nan]
# adding point ids to the orig syn points worked

#%% must update final_tid for these syn points!
t_cswappingl_origsynf['final_tid_origsynfilled'] = t_cswappingl_origsynf['final_tid']

# Boolean mask for NaNs
is_nan = t_cswappingl_origsynf['final_tid'].isna()

# Each contiguous block (NaN or not) gets a unique number
nan_groups = (is_nan != is_nan.shift()).cumsum()

# Only consider the groups that are NaN blocks
nan_block_ids = nan_groups[is_nan].unique()

# Loop over each NaN block
for grp in nan_block_ids:
    block_idx = t_cswappingl_origsynf.index[nan_groups == grp]
    start_idx = block_idx[0]
    end_idx = block_idx[-1]

    # Value before and after the block
    val_before = t_cswappingl_origsynf.at[start_idx-1, 'final_tid'] if start_idx > 0 else None
    val_after = t_cswappingl_origsynf.at[end_idx+1, 'final_tid'] if end_idx+1 < len(t_cswappingl_origsynf) else None

    # Fill only if both are equal and not NaN
    if val_before is not None and val_before == val_after:
        t_cswappingl_origsynf.loc[start_idx:end_idx, 'final_tid_origsynfilled'] = val_before

t_cswappingl_origsynf[['final_tid', 'final_tid_origsynfilled']]

#%% connect od of active swaps via synthetic trajectories
t_cswappingl_origsynf['final_tid_origsynfilled'].isna().any() # none are Nan, good
#%% again, validating by ensuring final_tid of non nan values has not changed
t_cswappingl_origsynf['final_tid_origsynfilled_valid'] = np.nan
mask = t_cswappingl_origsynf['final_tid'].notna()
t_cswappingl_origsynf.loc[mask, 'final_tid_origsynfilled_valid'] = t_cswappingl_origsynf.loc[mask, 'final_tid'] == t_cswappingl_origsynf.loc[mask, 'final_tid_origsynfilled']
print(t_cswappingl_origsynf.final_tid_origsynfilled_valid.unique()) # [True nan]


#%% export
import geopandas as gpd
t_cswappingl_origsynf = gpd.read_parquet(r"D:\paper3\FinalCloakedBasedSwapping/Swapped_CloakingAreaBased_Validated_ListBasedSwappingApproach_origsynfilledIfneeded.parquet")

t_cswappingl_origsynf = t_cswappingl_origsynf.sort_values(
    by=['final_tid_origsynfilled', 'order_in_traj_filled'],
    ascending=[True, True]  
).reset_index(drop=True)  
t_cswappingl_origsynf.head()

#%%
t_cswappingl_origsynf.to_parquet(r"D:\paper3\FinalCloakedBasedSwapping/Swapped_CloakingAreaBased_Validated_ListBasedSwappingApproach_origsynfilledIfneeded.parquet")

#%% add synthethic trajectories to swaps
# must get clk_gp id and the start and end point
# origin and destination
# head to tail

# valid_swap should be Ture (or active_swap)
t_cswappingl_origsynf[t_cswappingl_origsynf['active_swap'] == True] # 59683 both the same length
# thse are the active swaps but no "gap identifier"

#%% first: identify pairs of active swaps
# simple approach first, "pairs" can be more than origin destination, inlcuding "intermediate" swaps
# import pandas as pd
import numpy as np

# Initialize the column
t_cswappingl_origsynf['true_pair_id'] = np.nan

pair_counter_global = 0

def assign_true_blocks(group):
    global pair_counter_global
    is_true = group['active_swap'] == True
    # contiguous blocks
    block_id = (is_true != is_true.shift()).cumsum()
    
    # Only blocks where True exists
    true_blocks = block_id[is_true].unique()
    
    for blk in true_blocks:
        idxs = group.index[block_id == blk]
        pair_counter_global += 1
        group.loc[idxs, 'true_pair_id'] = pair_counter_global
    
    return group

# Apply per group
t_cswappingl_origsynf = t_cswappingl_origsynf.groupby('final_tid_origsynfilled', group_keys=False)\
                                             .apply(assign_true_blocks)

# true_pair_id:label each continuous sequence of active_swap == True

#%%
t_cswappingl_origsynf[t_cswappingl_origsynf['active_swap'] == True] # 59683 both the same length

#%%
t_cswappingl_origsynf.to_parquet(r"D:\paper3\FinalCloakedBasedSwapping/Swapped_CloakingAreaBased_Validated_ListBasedSwappingApproach_origsynfilledIfneeded.parquet")

#%% true_pair_id:label each continuous sequence of active_swap == True
# can be more than 2, ideally two onlye (OD), otherwise it is (O-D0-D)
t_cswappingl_origsynf.true_pair_id.value_counts() # some are up to 8?

#%%
sample_activeSwapBlcok = t_cswappingl_origsynf[t_cswappingl_origsynf['true_pair_id'] == 4834.0].copy()
print(sample_activeSwapBlcok.final_tid.unique())                # 20200110_fbe906873514e9223ef147d6b827dd559c378aa7_3576
print(sample_activeSwapBlcok.order_in_traj_filled.unique())     # from 314 to 321
sample_activeSwapBlcok

#%% look at full tid in Q
t_cswappingl_origsynf[t_cswappingl_origsynf['final_tid'] == '20200110_fbe906873514e9223ef147d6b827dd559c378aa7_3576'].to_parquet(r'D:\paper3\FinalCloakedBasedSwapping\lookingAtSamples/20200110_fbe906873514e9223ef147d6b827dd559c378aa7_3576.parquet')
# not ideal, but looks good

#%% histogram of 'individual vs chained origin-destination'
import matplotlib.pyplot as plt

pair_sizes = (
    t_cswappingl_origsynf
    .dropna(subset=['true_pair_id'])
    .groupby('true_pair_id')
    .size()
)
#%%
plt.style.use('ggplot')

plt.hist(pair_sizes, bins=range(1, pair_sizes.max()+2), align='left')
plt.xlabel("Number of points (o-d chain if >2)")
plt.ylabel("Frequency")
plt.title("Number of origin-destination points of trajectory identifiers swaps at segmentation points")
plt.xlim(left=1.5
)

plt.show()
#%% must need a n od id that fits the syn points in both globally and locally
# create a new, current global point id (to allow sorting by)
t_cswappingl_origsynf = (
    t_cswappingl_origsynf
    .sort_values(['final_tid_origsynfilled', 'order_in_traj_filled'])
    .reset_index(drop=True)      
    .reset_index(names='point_id_global') 
)
t_cswappingl_origsynf

#%% must find a good way to handle destinations that also serve as origins, i.e. more than two True in a rows/ true_pair_id of len longer than 2
t_cswappingl_origsynf_OD = t_cswappingl_origsynf[t_cswappingl_origsynf.true_pair_id.notna()]

#%% points are ordered, i.e. the first occurence of a new true_pair is the origin
# the next orrurence of a true_pair id value is theh destination of the previous point
# when od are chained the destination also acts as an origin
# can we explode?
# need a list (tuple) of od values
# explode to make sure every destination has an origin

# previous and next point ids inside each pair block
t_cswappingl_origsynf_OD['prev_pid'] = t_cswappingl_origsynf_OD.groupby('true_pair_id')['point_id_global'].shift(1)
t_cswappingl_origsynf_OD['next_pid'] = t_cswappingl_origsynf_OD.groupby('true_pair_id')['point_id_global'].shift(-1)

# origin and destination columns
t_cswappingl_origsynf_OD['origin_label'] = None
t_cswappingl_origsynf_OD['destination_label'] = None

# Origin: current row is origin if it has a next point in the same true_pair_id
mask_origin = t_cswappingl_origsynf_OD['next_pid'].notna()
t_cswappingl_origsynf_OD.loc[mask_origin, 'origin_label'] = (
    t_cswappingl_origsynf_OD.loc[mask_origin, 'point_id_global'].astype(str)
    + "_" + t_cswappingl_origsynf_OD.loc[mask_origin, 'true_pair_id'].astype(int).astype(str)
    + "_Origin"
)

# Destination: current row is destination if it has a previous point in the same true_pair_id
mask_dest = t_cswappingl_origsynf_OD['prev_pid'].notna()
t_cswappingl_origsynf_OD.loc[mask_dest, 'destination_label'] = (
    t_cswappingl_origsynf_OD.loc[mask_dest, 'prev_pid'].astype(int).astype(str)
    + "_" + t_cswappingl_origsynf_OD.loc[mask_dest, 'true_pair_id'].astype(int).astype(str)
    + "_Destination"
)

#t_cswappingl_origsynf_OD = t_cswappingl_origsynf_OD.drop(columns=['prev_pid', 'next_pid'])
t_cswappingl_origsynf_OD

#%% run shortest path between all od 
# shortest path: how should od be structured? one row for o, one for d? coloumns? i.e. two id columns and two geometry columns

# I NEED OD PAIRS to run my shortest path code
# cannot calculate shortest path if the nearest node to both OD points is the same - this is good, takes care of very short distances where we would not want to insert synthethic trajectories anyway
# looks like I had origin and destination as seperate rows, grouped by odid
# also taking uid into account
# this will be the "final_uid" after swapping

# these are the columns I need
# odid
# uid
# orig and dest points in the same row

# how should odd chains be handled?
# looking at t_cswappingl_origsynf_OD I would say I need duplicates of the rows that have a value in both origin_label AND destination_label
# if they have both values, they are destination first, before becoming origin again
# how will this impact synthetic points generation?
# cannot dissolve the shortest paths because I want to maintain the raw points (i.e, od, along the path)

# reduce od df to essential information
t_cswappingl_origsynf_OD_odid = t_cswappingl_origsynf_OD[['point_id_global', 'match_geometry', 'final_tid', 'true_pair_id', 'origin_label', 'destination_label']].copy()
# add uid
t_cswappingl_origsynf_OD_odid['final_uid'] = t_cswappingl_origsynf_OD_odid['final_tid'].str.split('_').str[1]

#%% have one row per odid, i.e., add destination of origin to same row
#print(t_cswappingl_origsynf_OD_odid.loc[[614, 615, 616]][['origin_label', 'destination_label']])

print(len(t_cswappingl_origsynf_OD_odid))
# get rows that are both origin and destination
both_mask = t_cswappingl_origsynf_OD_odid['origin_label'].notna() & t_cswappingl_origsynf_OD_odid['destination_label'].notna()
# split by od label
t_cswappingl_origsynf_OD_odid_origin = t_cswappingl_origsynf_OD_odid[both_mask].copy()
t_cswappingl_origsynf_OD_odid_origin['destination_label'] = None

t_cswappingl_origsynf_OD_odid_dest_only = t_cswappingl_origsynf_OD_odid[both_mask].copy()
t_cswappingl_origsynf_OD_odid_dest_only['origin_label'] = None

# return to rows that didn't need splitting
t_cswappingl_origsynf_OD_odid = pd.concat([t_cswappingl_origsynf_OD_odid[~both_mask], t_cswappingl_origsynf_OD_odid_origin, t_cswappingl_origsynf_OD_odid_dest_only], ignore_index=True)

# sort by point id
t_cswappingl_origsynf_OD_odid = t_cswappingl_origsynf_OD_odid.sort_values(by=['point_id_global'])
t_cswappingl_origsynf_OD_odid = t_cswappingl_origsynf_OD_odid.reset_index(drop=True)

print(len(t_cswappingl_origsynf_OD_odid)) # should be longer: 59683 vs 67116

#%% add odid
# check that every point is either origin or destination, never both
print(not (t_cswappingl_origsynf_OD_odid['origin_label'].notna() & t_cswappingl_origsynf_OD_odid['destination_label'].notna()).any(), 'expected True')
t_cswappingl_origsynf_OD_odid['odid'] = (
    t_cswappingl_origsynf_OD_odid['origin_label']
    .fillna(t_cswappingl_origsynf_OD_odid['destination_label'])
    .str.rsplit('_', n=1).str[0]
)
print(len(t_cswappingl_origsynf_OD_odid)) # 67116
print(t_cswappingl_origsynf_OD_odid.odid.nunique()) #33558, which is half of the df length
print(t_cswappingl_origsynf_OD_odid.odid.value_counts().reset_index()['count'].max())
print(t_cswappingl_origsynf_OD_odid.odid.value_counts().reset_index()['count'].min())
# 2, as expected. each odid only has one origin and one destination
# also, add a dictionary lookup: key: odid, value, the origin and destination value

#%% have a origin geometry and a destination geometry
# df must be same crs as Graph, which is epsg4326
print(t_cswappingl_origsynf_OD_odid.crs)
t_cswappingl_origsynf_OD_odid = t_cswappingl_origsynf_OD_odid.to_crs(4326)
print(t_cswappingl_origsynf_OD_odid.crs)
t_cswappingl_origsynf_OD_odid['orig'] = t_cswappingl_origsynf_OD_odid['match_geometry'].where(t_cswappingl_origsynf_OD_odid['origin_label'].notna())
t_cswappingl_origsynf_OD_odid['dest'] = t_cswappingl_origsynf_OD_odid['match_geometry'].where(t_cswappingl_origsynf_OD_odid['destination_label'].notna())
t_cswappingl_origsynf_OD_odid.head()

#%% store od point ids as a dict
od_dict = t_cswappingl_origsynf_OD_odid.groupby('odid')['point_id_global'].apply(list).to_dict()
od_dict['226_1'] # [226, 227] origin first, then destination, origin is the smaller out of the two


#%% have one row per odid 
t_cswappingl_origsynf_OD_odid_final = (
    t_cswappingl_origsynf_OD_odid.drop(columns='match_geometry')
      .groupby('odid', as_index=False)
      .agg({
          'point_id_global': lambda x: tuple(x), # create odid tuple
          'final_uid': 'first',
          'final_tid': 'first',
          'true_pair_id': 'first',
          'origin_label': 'first',
          'destination_label': 'first',
          'orig': 'first',
          'dest': 'first',    
      })
)
t_cswappingl_origsynf_OD_odid_final.head()

#%% update odid
t_cswappingl_origsynf_OD_odid_final['true_pair_id'] = t_cswappingl_origsynf_OD_odid_final['true_pair_id'].astype(int)

t_cswappingl_origsynf_OD_odid_final['odid'] = (
    t_cswappingl_origsynf_OD_odid_final['true_pair_id'].astype(str)
    + '_orig_' + t_cswappingl_origsynf_OD_odid_final['point_id_global'].str[0].astype(str)
    + '_dest_' + t_cswappingl_origsynf_OD_odid_final['point_id_global'].str[1].astype(str)
)
t_cswappingl_origsynf_OD_odid_final.head()

#%% export dict
import os
import pickle

output_dir = r"E:\paper3\FinalCloakedBasedSwapping\shortestPath_CloakedBasedSwapping"
os.makedirs(output_dir, exist_ok=True)

t_cswappingl_origsynf.to_parquet(r"E:\paper3\FinalCloakedBasedSwapping\shortestPath_CloakedBasedSwapping/t_cswappingl_origsynf_crs4326.parquet")
#%%
t = t_cswappingl_origsynf_OD_odid_final.copy()
# convert geometry to WKT string
t['orig'] = t['orig'].apply(lambda g: g.wkt if g else None)
t['dest'] = t['dest'].apply(lambda g: g.wkt if g else None)
t.to_parquet(r"E:\paper3\FinalCloakedBasedSwapping\shortestPath_CloakedBasedSwapping/t_cswappingl_origsynf_OD_odid_final_crs4326.parquet")

with open(r"E:\paper3\FinalCloakedBasedSwapping\shortestPath_CloakedBasedSwapping/od_dict.pkl", "wb") as f:
    pickle.dump(od_dict, f)

#%% speed up processing by adding nearest node to df
import osmnx as ox
import joblib
G = joblib.load(r"D:\paper2\Data\Output\cloaking_2sig_100150\traj_cloaked_anotated_mapmatched\OriginDestination_CloakingAreas\NetworkShortestPath\graph.joblib")
#nodes = gpd.read_parquet(r"D:\paper2\Data\Output\cloaking_2sig_100150\traj_cloaked_anotated_mapmatched\OriginDestination_CloakingAreas\NetworkShortestPath/nodes.parquet")
#edges = gpd.read_parquet(r"D:\paper2\Data\Output\cloaking_2sig_100150\traj_cloaked_anotated_mapmatched\OriginDestination_CloakingAreas\NetworkShortestPath/edges.parquet")

# df must be same crs as Graph, which is epsg4326

#%% find nearest node before running shortest path
t_cswappingl_origsynf_OD_odid_final = gpd.GeoDataFrame(
    t_cswappingl_origsynf_OD_odid_final,
    geometry='orig',
    crs="EPSG:4326"  
)

# extract origin and destination coordinates
t_cswappingl_origsynf_OD_odid_final["orig_x"] = t_cswappingl_origsynf_OD_odid_final.orig.x
t_cswappingl_origsynf_OD_odid_final["orig_y"] = t_cswappingl_origsynf_OD_odid_final.orig.y
# now change active geometry column to dest
t_cswappingl_origsynf_OD_odid_final = t_cswappingl_origsynf_OD_odid_final.set_geometry('dest')
t_cswappingl_origsynf_OD_odid_final["dest_x"] = t_cswappingl_origsynf_OD_odid_final.dest.x
t_cswappingl_origsynf_OD_odid_final["dest_y"] = t_cswappingl_origsynf_OD_odid_final.dest.y

# snap origins to nearest node
t_cswappingl_origsynf_OD_odid_final["u_node"] = ox.distance.nearest_nodes(
    G,
    X=t_cswappingl_origsynf_OD_odid_final["orig_x"],
    Y=t_cswappingl_origsynf_OD_odid_final["orig_y"]
)
# snap destinations to nearest node
t_cswappingl_origsynf_OD_odid_final["v_node"] = ox.distance.nearest_nodes(
    G,
    X=t_cswappingl_origsynf_OD_odid_final["dest_x"],
    Y=t_cswappingl_origsynf_OD_odid_final["dest_y"]
)

#%%
t_cswappingl_origsynf_OD_odid_final.head()

#%% can already filter out the ones that have the same node! no need to attempt shortest path caluclation
t_cswappingl_origsynf_OD_odid_final['same_nearest_node'] = t_cswappingl_origsynf_OD_odid_final['u_node'] == t_cswappingl_origsynf_OD_odid_final['v_node']
t_cswappingl_origsynf_OD_odid_final['same_nearest_node'].value_counts()

# same_nearest_node
#False    32588
#True       970

print(len(t_cswappingl_origsynf_OD_odid_final)) # 33558
t_cswappingl_origsynf_OD_odid_final_sp = t_cswappingl_origsynf_OD_odid_final[t_cswappingl_origsynf_OD_odid_final['same_nearest_node']==False]
print(len(t_cswappingl_origsynf_OD_odid_final_sp)) #32588

#%%
t_cswappingl_origsynf_OD_odid_final_sp.to_parquet(r"D:\paper3\FinalCloakedBasedSwapping\shortestPath_CloakedBasedSwapping/t_cswappingl_origsynf_OD_odid_final_sp.parquet")




#%% RUN SHORTEST PATH
import utils_shortestPath as sp

t_cswappingl_origsynf_OD_odid_final_sp = t_cswappingl_origsynf_OD_odid_final_sp.rename(columns={'final_uid': 'uid'})

# running this on 32588 origin destination pairs
sp.process_od_rows(t_cswappingl_origsynf_OD_odid_final_sp, G, 'E:\paper3\FinalCloakedBasedSwapping\shortestPath_CloakedBasedSwapping\shortestPathBetweenHeadTail', chunk_size=500)

#%% load them all back into one df



#%% might have to look at odid duplicate
#duplicates_per_odid = (
#    shortestpath_gdf
#    .groupby('odid')
#    .apply(lambda x: x.duplicated(keep=False).sum())
#    .reset_index(name='num_duplicate_rows')
#)
#print(duplicates_per_odid)
#%% look for missing edges on shortest path
# add a segment id to keep df sortedt
#shortestpath_gdf_cleaned["segment"] = shortestpath_gdf_cleaned.groupby("odid").cumcount()
#shortestpath_gdf_cleaned["odid_segmentid"] = shortestpath_gdf_cleaned["segment"].astype(str) + "_odid_" + shortestpath_gdf_cleaned["odid"].astype(str)
#shortestpath_gdf_cleaned.head()

#%% now compare v with next u
# for each odid, shift u up to compare with  v
#shortestpath_gdf_cleaned["next_u"] = shortestpath_gdf_cleaned.groupby("odid")["u"].shift(-1) # if there is no next row next_u becomes NaN
# and ignore the NaN
#shortestpath_gdf_cleaned["noSegmentMissing"] = (
#    shortestpath_gdf_cleaned["v"] == shortestpath_gdf_cleaned["next_u"]
#) | shortestpath_gdf_cleaned["next_u"].isna()
# results
#shortestpath_gdf_cleaned["noSegmentMissing"].unique() # only expected True
#%% interpolate synthetic points

#%% evaluate cloaking based swaps 


