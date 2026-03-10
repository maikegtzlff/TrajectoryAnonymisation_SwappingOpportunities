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

#%% start swapping
from tqdm import tqdm

swap_queue = deque(helper_pool_dict_ordered_updated.keys())

pbar = tqdm(total=len(swap_queue), desc="Processing swaps")

while swap_queue:
    # select first clk gap from queque
    main_clkgp = swap_queue.popleft() 
    # skip if already swapped as part of a helper swap
    if main_clkgp in locked_main_splits:
        continue
    # get split points for head and tail of sensitive, main, trajectory
    main_head_end, main_tail_start = main_clkgp

    # prevent splitting previously created joins
    if pd.isna(main_head_end) or pd.isna(main_tail_start):
        continue # ignoring clkg gaps with only a head
    if tuple(sorted((main_head_end, main_tail_start))) in protected_splits:
        continue

    # get the trajectory of the main
    main_tid_head = pid_to_tid.get(main_head_end)
    main_tid_tail = pid_to_tid.get(main_tail_start)

    if main_tid_head is None or main_tid_tail is None:
        continue
    if main_tid_head != main_tid_tail:
        continue
    main_tid = main_tid_head

    main_traj = trajectory_index[main_tid]
    # --- verify main split points still valid
    if main_head_end not in main_traj or main_tail_start not in main_traj:
        continue
    # --- segment main into head and tail
    m_h_i = main_traj.index(main_head_end)
    m_t_i = main_traj.index(main_tail_start)
    if m_t_i != m_h_i + 1:
        continue
    #head: everything BEFORE tail_start
    #tail: everything FROM tail_start onwards (incl tail start)
    head_main = main_traj[:m_t_i]     # exclusive end index, so must be based on tail which is the next point
    tail_main = main_traj[m_t_i:]     # inclusive start index

    # --- pick a helper
    helper_candidates = helper_pool_dict_ordered_updated.get(main_clkgp, [])
    random.shuffle(helper_candidates)
    swap_success = False

    for h_head_end, h_tail_start in helper_candidates:
        # prevent splitting previously created head-tail joins
        if pd.isna(h_head_end) or pd.isna(h_tail_start):
            continue
        if tuple(sorted((h_head_end, h_tail_start))) in protected_splits:
            continue

        helper_tid = pid_to_tid.get(h_head_end)

        if helper_tid is None or helper_tid == main_tid:
            continue  # must be different trajectory

        helper_traj = trajectory_index[helper_tid]
        if h_head_end not in helper_traj or h_tail_start not in helper_traj:
            continue  # helper points no longer valid

        # --- slice helper trajectory
        h_h_i = helper_traj.index(h_head_end)
        h_t_i = helper_traj.index(h_tail_start)
        if h_t_i != h_h_i + 1:
            continue
        head_helper = helper_traj[:h_t_i]
        tail_helper = helper_traj[h_t_i:]

        # --- prevent points returning to a trajectory they were already part of
        invalid = False

        for pid in tail_helper:
            if main_tid in swap_history[pid]:
                invalid = True
                break

        for pid in tail_main:
            if helper_tid in swap_history[pid]:
                invalid = True
                break

        if invalid:
            continue

        # --- new trajectories after swap
        new_main_traj = head_main + tail_helper
        new_helper_traj = head_helper + tail_main

        # --- protect newly created joins (bidirectional)
        if tail_helper:
            ht_join_h = tuple(sorted((main_head_end, tail_helper[0])))
            protected_splits.add(ht_join_h)

        if tail_main:
            ht_join_m = tuple(sorted((h_head_end, tail_main[0])))
            protected_splits.add(ht_join_m)


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

        # --- track origin/destination
        if tail_helper:
            od_dict[main_head_end].append(tail_helper[0])
        if tail_main:
            od_dict[h_head_end].append(tail_main[0])

        # --- lock main split
        locked_main_splits.add(main_clkgp)

        swap_success = True
        break  # exit helper loop

    pbar.update(1)
    if not swap_success:
        # fallback to waiting room
        waiting[main_tid].append(main_clkgp)
        retry_counts[main_clkgp] += 1
        if retry_counts[main_clkgp] < max_retries:
            swap_queue.append(main_clkgp)

pbar.close()
# Processing swaps:  61%|██████    | 16249/26723 [04:22<02:49, 61.82it/s]  

#%%
#pid_to_tid	        which trajectory a point belongs to
#trajectory_index	ordered list of points in trajectory
# swap_history
# protected_splits - head/tail connections that have been used and cannot be used again for splittinfg
# waiting: have been retried 15 times each
#%% export these 
import os
os.chdir(r"D:\paper3\SwappingBasedCloaking_10March26_listApproach") 
print(os.getcwd())

with open('pid_to_tid.pkl', 'wb') as f:  
    pickle.dump(pid_to_tid, f)

with open('trajectory_index.pkl', 'wb') as f:  
    pickle.dump(trajectory_index, f)

with open('swap_history.pkl', 'wb') as f:  
    pickle.dump(swap_history, f)

with open('protected_splits.pkl', 'wb') as f:  
    pickle.dump(protected_splits, f)

with open('waiting.pkl', 'wb') as f:  
    pickle.dump(waiting, f)

#%%
import pandas as pd

# 1️⃣ Build a DataFrame of points → final trajectory
df_points = pd.DataFrame(list(pid_to_tid.items()), columns=['point_id', 'final_tid'])

# 2️⃣ Add original trajectory for reference if you kept it
original_pid_to_tid = dict(zip(t_forSwapping['point_id_unique'], t_forSwapping['tid_subid']))
df_points['original_tid'] = df_points['point_id'].map(original_pid_to_tid)

# 3️⃣ Sort by trajectory and point order
df_points = df_points.sort_values(['final_tid', 'point_id']).reset_index(drop=True)

# 4️⃣ Identify swapped points
# swapped if point's final_tid != original_tid
if 'original_tid' in df_points.columns:
    df_points['swapped'] = df_points['final_tid'] != df_points['original_tid']
else:
    df_points['swapped'] = False

# 5️⃣ Aggregate stats per trajectory
traj_stats = df_points.groupby('final_tid').agg(
    total_points=('point_id', 'count'),
    swapped_points=('swapped', 'sum'),
    swap_fraction=('swapped', 'mean')
).reset_index()

#%%
print(traj_stats.swapped_points.min()) # 0 trajectories are the same as before
print(traj_stats.swapped_points.median()) # 4 
print(traj_stats.swapped_points.max()) # 4322
print(traj_stats.swapped_points.value_counts())
#swapped_points
#0       9532
#27        33
#26        32
#50        32
#31        31
#        ... 
#2384       1
#1310       1
#1153       1
#948        1
#1173       1
print(traj_stats.swap_fraction.min()) # 0 trajectories are the same as before
print(traj_stats.swap_fraction.median()) # 0.02
print(traj_stats.swap_fraction.max()) # 0.99

traj_stats
#%%
print(traj_stats.final_tid.nunique()) # 19189
print(traj_stats[traj_stats['swapped_points'] >=5].final_tid.unique())

#%%
t_forSwapping[t_forSwapping['main_clkgp_wHelper'] != 'nan'][['point_id_unique', 'main_clkgp_wHelper', 'main_headEND_pointid',
       'main_tailStart_pointid', 'main_clkgp_id', 'main_clkgp_wHelper_id']].head()






#%% look at one trajectory with swaps
t_swapped_sample = df_points[df_points['final_tid']=='20201201_9af1aaa9ad4d076028a31102ef23fd16eeee2e32_7412']
# add geometry
t_swapped_sample.rename(columns={'point_id': 'point_id_unique'}, inplace=True)
print(len(t_swapped_sample)) # 954
t_swapped_sample = t_forSwapping[['point_id_unique', 'main_clkgp_wHelper_id', 'main_headEND_pointid', 'main_tailStart_pointid', 'match_geometry']].merge(t_swapped_sample, on= 'point_id_unique', how='right')
print(len(t_swapped_sample)) # 954
type(t_swapped_sample) #geopandas.geodataframe.GeoDataFrame

#%% add labels for helper split points
# add tuple for clkgp
t_swapped_sample['main_clkgp_id_tuple'] = list(zip(t_swapped_sample['main_headEND_pointid'], t_swapped_sample['main_tailStart_pointid']))
# look up the valid helpers!
t_swapped_sample['valid_helpers'] = t_swapped_sample['main_clkgp_id_tuple'].map(helper_pool_dict_ordered_updated)
t_swapped_sample.head()
#t_swapped_sample.main_clkgp_wHelper_id.unique()

# these are all main to helper combinitions
#helper_pool_dict_ordered_updated

#%%
t_swapped_sample['main_clkgp_id_tuple'] = t_swapped_sample['main_clkgp_id_tuple'].apply(
    lambda x: None if (isinstance(x, tuple) and pd.isna(x[0]) and pd.isna(x[1])) else x
)
t_swapped_sample.head()

#%%
valid_helpers_for_main_tail_start_1460887_146088 = t_swapped_sample.loc[1, 'valid_helpers']
print(len(valid_helpers_for_main_tail_start_1460887_146088)) # 609 swapping pairs
# is the point from the row above in this list?
print(180907 in [tup[0] for tup in valid_helpers_for_main_tail_start_1460887_146088]) # False, i.e., point is not a valid 180907 helper_head_end for this swap!
print(180907 in [tup[1] for tup in valid_helpers_for_main_tail_start_1460887_146088]) # False, i.e., point is not a valid 180907 helper_tail_start for this swap!
print('180907' in [tup[0] for tup in valid_helpers_for_main_tail_start_1460887_146088]) # still both False
print('180907' in [tup[1] for tup in valid_helpers_for_main_tail_start_1460887_146088])

#%% plot in Q
t_swapped_sample['valid_helpers_str'] = t_swapped_sample['valid_helpers'].apply(
    lambda x: f"{x[0]},{x[1]}" if isinstance(x, tuple) else None
)
t_swapped_sample.to_parquet(r"\\tsclient\R\paper3\fromVM100/cloakingBasedSwapingListApproach_sampleT.parquet")
# gaps are too far
# differentces in tid segments are not consistent with main_head helper_tail / helper_head main_tail
#%%
trajectory_index['20201201_9af1aaa9ad4d076028a31102ef23fd16eeee2e32_7412'] # I can see blocks of numbers, good

#%%






#%%
# mark points that swapped
df_points['swapped'] = df_points['original_tid'] != df_points['final_tid']

# view summary
print(df_points['swapped'].value_counts())

# optionally, see full details for swapped points
swapped_points_df = df_points[df_points['swapped']]
print(len(swapped_points_df)) # 3,709,681

#%%
# --- Diagnostic: Verify no protected edge was broken
broken_edges = []
for tid, traj in trajectory_index.items():
    traj_pairs = set(tuple(sorted((traj[i], traj[i+1]))) for i in range(len(traj)-1))
    for edge in protected_splits:
        if edge not in traj_pairs:
            broken_edges.append((edge, tid))

if broken_edges:
    print(f"⚠️ Broken protected edges detected: {len(broken_edges)}")
    for edge, tid in broken_edges[:10]:  # show first 10 for inspection
        print(f"Edge {edge} missing in trajectory {tid}")
else:
    print("✅ All protected edges preserved. No adjacency violations detected.")


#%%
# --- Rebuild swap_point_id_t and new_tid_subid in DataFrame
new_tid_subid_map = {}
swap_point_id_map = {}
for tid, traj in trajectory_index.items():
    for pos, uid in enumerate(traj):
        new_tid_subid_map[uid] = tid
        swap_point_id_map[uid] = pos + 1

t_forSwapping['new_tid_subid'] = t_forSwapping['point_id_unique'].map(new_tid_subid_map)
t_forSwapping['swap_point_id_t'] = t_forSwapping['point_id_unique'].map(swap_point_id_map)

#%%
t_forSwapping["new_tid_subid"] = t_forSwapping["point_id_unique"].map(uid_to_tid)