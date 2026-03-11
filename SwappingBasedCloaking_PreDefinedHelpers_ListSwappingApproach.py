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
# 
#                       
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
t_swapped_sample = trajectory_index_df[trajectory_index_df['final_tid']=='20201201_9af1aaa9ad4d076028a31102ef23fd16eeee2e32_7412']
t_swapped_sample.rename(columns={'point_id': 'point_id_unique'}, inplace=True)
print(len(t_swapped_sample)) # 541
t_swapped_sample = t_forSwapping[['point_id_unique', 'main_clkgp_wHelper_id', 'main_headEND_pointid', 'main_tailStart_pointid', 'match_geometry']].merge(t_swapped_sample, on= 'point_id_unique', how='right')
print(len(t_swapped_sample)) # 541
type(t_swapped_sample) #geopandas.geodataframe.GeoDataFrame

#%% add labels for helper split points
# add tuple for clkgp
t_swapped_sample['main_clkgp_id_tuple'] = list(zip(t_swapped_sample['main_headEND_pointid'], t_swapped_sample['main_tailStart_pointid']))
t_swapped_sample['main_clkgp_id_tuple'] = t_swapped_sample['main_clkgp_id_tuple'].apply(
    lambda x: None if (isinstance(x, tuple) and pd.isna(x[0]) and pd.isna(x[1])) else x
)
# look up the valid helpers!
t_swapped_sample['valid_helpers'] = t_swapped_sample['main_clkgp_id_tuple'].map(helper_pool_dict_ordered_updated)
t_swapped_sample[t_swapped_sample['main_clkgp_id_tuple'].notna()]

# these are all main to helper combinitions
#helper_pool_dict_ordered_updated


#%%
valid_helpers_for_main_head_end_7333189_7333190 = t_swapped_sample.loc[45, 'valid_helpers']
print(len(valid_helpers_for_main_head_end_7333189_7333190)) # 372 potentail swapping pair helpers

print('point_id of split point, this is a main head end', t_swapped_sample.loc[45, 'point_id_unique'])
print('main head end - will attach a tail start, i.e., must look at next row')
print('point_id of next row', t_swapped_sample.loc[45+1, 'point_id_unique'])

#%% is the point from the row above in this list?
# looking at helper head ends
print(5970075 in [tup[0] for tup in valid_helpers_for_main_head_end_7333189_7333190]) # False, i.e., point 5970075 is not a valid main_head_end_7333189_7333190 helper!
# looking at helper start tail: because the main was a head end we know we must look at the helper tail start, not the helper head end
print(5970075 in [tup[1] for tup in valid_helpers_for_main_head_end_7333189_7333190]) # TRUE

#%% lets look at the other two swaps manually
t_swapped_sample[t_swapped_sample['main_clkgp_id_tuple'].notna()]
# point 5970535 at index 506 main_head_end_5970535_5970536
# point 5970536 at index 507 main_tail_start_5970535_5970536
# these are the same mains! i.e., this main has not been split into heads and tails
# which means we can fill with the original syn points
# valid swap is correctly identified as flase, but also, this is not a swap...
# it is also not a swap/ split poit because original_tid is the same. no swap took place
# 
t_swapped_sample.original_tid.nunique() # 2, i.e., only 1 swap happened (and we have verified it is valid)


#%% vectorised validation approach
# 1️⃣ Define a function to check if the next point is a valid helper tail start
def is_valid_helper_tail(row):
    # skip if no valid helpers
    if not isinstance(row['valid_helpers'], list) or len(row['valid_helpers']) == 0:
        return False
    # get next point in trajectory (tail start)
    try:
        next_pid = row['next_point_id']  # you'll need to create this column
    except KeyError:
        return False
    # check if next_pid is any helper tail_start
    return any(next_pid == tup[1] for tup in row['valid_helpers'])

# 2️⃣ Add a column for next point_id in the trajectory
t_swapped_sample['next_point_id'] = t_swapped_sample['point_id_unique'].shift(-1)

# 3️⃣ Apply the validation function to every row
t_swapped_sample['valid_swap'] = t_swapped_sample.apply(is_valid_helper_tail, axis=1)

# ✅ Now you have a column 'valid_swap' that is True if the main_head_end correctly matches a helper_tail_start
print(t_swapped_sample[['point_id_unique', 'next_point_id', 'valid_swap']].head(20))

# t_swapped_sample[t_swapped_sample['valid_swap']==True]
# only the one I manually validated is True --> that is the only split aka swap



#%% plot in Q
t_swapped_sample['valid_helpers_str'] = t_swapped_sample['valid_helpers'].apply(
    lambda x: f"{x[0]},{x[1]}" if isinstance(x, tuple) else None
)
t_swapped_sample.to_parquet(r"\\tsclient\R\paper3\fromVM100/cloakingBasedSwapingListApproach_sampleT_swapid_validated.parquet")


# looks amazing (but also, only one swap not repeated swaps)




#%% look at a final tid that has more than 2 orig tid
#trajectory_index_df_origtid_n # 4 orig_tid for this final_tid
swppedTidSample = trajectory_index_df_origtid_n.loc[19184, 'final_tid'] # 20201201_cd3cfafd8c20d5edc2510b25a1e0b86b574cfd93_7412
# look at this tid
swppedTidSample_df = trajectory_index_df[trajectory_index_df['final_tid']== swppedTidSample]
swppedTidSample_df.rename(columns={'point_id': 'point_id_unique'}, inplace=True)
print(len(swppedTidSample_df)) # 541
swppedTidSample_df = t_forSwapping[['point_id_unique', 'main_clkgp_wHelper_id', 'main_headEND_pointid', 'main_tailStart_pointid', 'match_geometry']].merge(swppedTidSample_df, on= 'point_id_unique', how='right')
print(len(swppedTidSample_df)) # 541

# add labels for helper split points
# add tuple for clkgp
swppedTidSample_df['main_clkgp_id_tuple'] = list(zip(swppedTidSample_df['main_headEND_pointid'], swppedTidSample_df['main_tailStart_pointid']))
swppedTidSample_df['main_clkgp_id_tuple'] = swppedTidSample_df['main_clkgp_id_tuple'].apply(
    lambda x: None if (isinstance(x, tuple) and pd.isna(x[0]) and pd.isna(x[1])) else x
)
# look up the valid helpers!
swppedTidSample_df['valid_helpers'] = swppedTidSample_df['main_clkgp_id_tuple'].map(helper_pool_dict_ordered_updated)
swppedTidSample_df[swppedTidSample_df['main_clkgp_id_tuple'].notna()] # more than 4, so not all will acually be swaps
# basically looking at clkg gaps, but know that not all ckkl gaps have been processed succesully

#%% validate these automatically
swppedTidSample_df['next_point_id'] = swppedTidSample_df['point_id_unique'].shift(-1)
swppedTidSample_df['valid_swap'] = swppedTidSample_df.apply(is_valid_helper_tail, axis=1)
print(swppedTidSample_df['valid_swap'].value_counts())
#False    560
#True       1
swppedTidSample_df[['point_id_unique', 'next_point_id', 'valid_swap']]
#%% then validate by hand
# look at these 
print(len(swppedTidSample_df[swppedTidSample_df['main_clkgp_id_tuple'].notna()])) #5
swppedTidSample_df[swppedTidSample_df['main_clkgp_id_tuple'].notna()][['point_id_unique', 'order_in_traj','main_clkgp_wHelper_id', 'original_tid', 'valid_swap']]
#%% two of them are the same main pair --> validation False is correct, they did not swap
# main_head_end_7333945_7333946 and main_tail_start_7333945_7333946
# there is no point in between them, they have the same orig tid. this needs to be filled with syn points, id did not participate in cloaking

# the other three are different
# main_tail_start_3375477_3375478 
# main_head_end_3375582_3375583
# but main_tail_start_3375477_3375478 and main_head_end_3375582_3375583 have the same orig tid, so no swap happened
# there is 420 -  316 points inbetween them, would need to know if thei have the same orig tid 

# main_tail_start_3375477_3375478 --> start of a main tail
# --> the point ABOVE should be from a different tid if the clk gap participated in swappipng
# if the point above has the same orig tid and is only one consecutive point less no swapp happend --> i.e., False falg is correct
# index 316
valid_helpers_for_main_tail_start_3375477_3375478 = swppedTidSample_df.loc[316, 'valid_helpers']
print(len(valid_helpers_for_main_tail_start_3375477_3375478)) # 
print('point_id of previous row', swppedTidSample_df.loc[316-1, 'point_id_unique']) # 7333954
print(swppedTidSample_df.loc[316-1, 'point_id_unique'] in [tup[0] for tup in valid_helpers_for_main_tail_start_3375477_3375478]) # TRUE!!!
print(swppedTidSample_df.loc[316-1, 'point_id_unique'] in [tup[1] for tup in valid_helpers_for_main_tail_start_3375477_3375478]) 
# both false
# even though it definitley is a swap, 5970344 is not the same segment as 7333954
# or it would be a very long segment, look at point id
print(swppedTidSample_df.loc[316, 'original_tid']) 
print(swppedTidSample_df.loc[316-1, 'original_tid']) 
# THEY are also differnet orig tids
swppedTidSample_df[swppedTidSample_df['point_id_unique'].isin([7333954, 3375478])]



# main_head_end_3375582_3375583 is marked as valid swap
# --> the end of a head
# --> the next point should be a helper tail start
# index 420

# main_tail_start_3813681_3813682
# --> start of a main tail, look at point before: same orig tid? consecutive point_id_uniqu?
# index 422


#%% would be helpful to distinguish between False and NA in the automated classification
# does the function take head vs tail into account?
print(swppedTidSample_df.main_clkgp_wHelper_id.dtypes)
print(swppedTidSample_df.main_clkgp_wHelper_id.unique())
swppedTidSample_df['main_clkgp_wHelper_id'] = swppedTidSample_df['main_clkgp_wHelper_id'].replace('nan_<NA>_<NA>', None)
print(swppedTidSample_df['main_clkgp_wHelper_id'].isna().any())
print(swppedTidSample_df.main_clkgp_wHelper_id.unique())

#%% initialise column
swppedTidSample_df['valid_swap'] = None

for idx, row in swppedTidSample_df.loc[swppedTidSample_df['main_clkgp_wHelper_id'].notna()].iterrows():

    helpers = row['valid_helpers']
    # skip rows that do not have a list of helpers...
    if not isinstance(helpers, list) or len(helpers) == 0:
        continue

    helper_id = row['main_clkgp_wHelper_id']

    # determine which row to inspect
    if helper_id.startswith('main_head_end_'):
        check_idx = idx + 1
        pos = 1   # helper tail_start position in tuple
    elif helper_id.startswith('main_tail_start_'):
        check_idx = idx - 1
        pos = 0   # helper head_end position in tuple
    else:
        continue

    # skip if out of bounds
    if check_idx not in swppedTidSample_df.index:
        continue

    other_pid = swppedTidSample_df.loc[check_idx, 'point_id_unique']

    # check helper tuples
    if any(other_pid == tup[pos] for tup in helpers):
        swppedTidSample_df.loc[idx, 'valid_swap'] = True
        swppedTidSample_df.loc[check_idx, 'valid_swap'] = True
    

print(swppedTidSample_df.valid_swap.value_counts()) # 5 True, coming from 
# False    556
#True       5

# but can only be true if a swap happened
#%%
swppedTidSample_df[swppedTidSample_df['valid_swap']==True]

#%%
print(swppedTidSample_df[swppedTidSample_df['valid_swap'] == True].main_clkgp_wHelper_id.nunique())
swppedTidSample_df[swppedTidSample_df['valid_swap'] == True]
#%%
swppedTidSample_df.to_csv(r"\\tsclient\R\paper3\fromVM100/swpSample_validated.csv") # looks good





# apply to full df
#%%
trajectory_index_df.groupby('final_tid')['original_tid'].nunique().reset_index().original_tid.max()

#%% must merge columns back to df_points
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


