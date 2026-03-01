#%% load data
import geopandas as gpd
import pandas as pd
t_forSwapping = gpd.read_parquet(r"d:\paper3\Data\output\CloakingBasedSwapping\t_forSwapping.parquet")
valid_assigned_helpers_df = pd.read_parquet(r"d:\paper3\Data\output\CloakingBasedSwapping\valid_assigned_helpers_df.parquet")

#%% start swapping - runs in under 8 minutes
from tqdm import tqdm
import pandas as pd
import numpy as np
import time

# --------------------------
# 0️⃣ Initialize tracking columns
# --------------------------
t_forSwapping['tid_subid_orig'] = t_forSwapping['tid_subid']        # original trajectory ID
t_forSwapping['tid_subid_after_swap'] = t_forSwapping['tid_subid']  
t_forSwapping['swap_pair_id'] = pd.NA
t_forSwapping['head_end_flag'] = False
t_forSwapping['tail_start_flag'] = False
t_forSwapping['swap_count'] = 0
t_forSwapping['visited_containers'] = t_forSwapping.apply(lambda _: [], axis=1)

# Precompute row_uid → point_id_t mapping
row_uid_to_pid = t_forSwapping.set_index('row_uid')['point_id_t'].to_dict()

# Precompute trajectory indices for faster slicing
tid_index_map = t_forSwapping.groupby('tid_subid').groups

# Track helper rows that have already been used for splitting
used_helper_rows = set()

# Initialize swap counter and log
swap_counter = 0
swap_log = []

# --------------------------
# 1️⃣ Merge main_row info for sorting safely
# --------------------------
valid_assigned_helpers_df = valid_assigned_helpers_df.merge(
    t_forSwapping[['row_uid', 'tid_subid', 'point_id_t']],
    left_on='main_row_uid', right_on='row_uid', how='left',
    suffixes=('', '_tfs')
)
valid_assigned_helpers_df = valid_assigned_helpers_df.rename(
    columns={'tid_subid': 'tid_subid_main'}
)
valid_assigned_helpers_df = valid_assigned_helpers_df.sort_values(['tid_subid_main', 'point_id_t'])

start_time = time.time()

# --------------------------
# 2️⃣ Process swaps sequentially
# --------------------------
for _, swap in tqdm(valid_assigned_helpers_df.iterrows(), total=len(valid_assigned_helpers_df), desc="Processing swaps"):
    swap_counter += 1
    main_row_uid = swap['main_row_uid']
    main_tid_orig = t_forSwapping.loc[t_forSwapping.row_uid == main_row_uid, 'tid_subid_orig'].values[0]
    helper_tid = swap['helper_tid']

    # --------------------------
    # Skip swap if same container
    # --------------------------
    if main_tid_orig == helper_tid:
        continue

    clkpassed = swap['clkpassed']

    # --------------------------
    # Split main trajectory
    # --------------------------
    main_pid = row_uid_to_pid[main_row_uid]
    main_idx = tid_index_map[main_tid_orig]

    main_mask_head = main_idx[
        t_forSwapping.loc[main_idx, 'point_id_t'] <= main_pid
    ]
    main_mask_tail = main_idx[
        t_forSwapping.loc[main_idx, 'point_id_t'] > main_pid
    ]

    # --------------------------
    # Split helper trajectory
    # --------------------------
    helper_idx = tid_index_map[helper_tid]
    helper_points = t_forSwapping.loc[helper_idx]

    helper_points = helper_points[
        helper_points['intersecting_cloaking_ids'].apply(lambda x: clkpassed in x)
    ]

    helper_points = helper_points[
        ~helper_points['row_uid'].isin(used_helper_rows)
    ]

    if len(helper_points) == 0:
        continue

    helper_split_row = helper_points.sample(1).iloc[0]
    helper_split_pid = helper_split_row['point_id_t']
    used_helper_rows.add(helper_split_row['row_uid'])

    helper_mask_head = helper_idx[
        t_forSwapping.loc[helper_idx, 'point_id_t'] <= helper_split_pid
    ]
    helper_mask_tail = helper_idx[
        t_forSwapping.loc[helper_idx, 'point_id_t'] > helper_split_pid
    ]

    # --------------------------
    # Safety check BEFORE marking heads/tails
    # --------------------------
    main_tail_mask_safe = main_mask_tail[
        t_forSwapping.loc[main_mask_tail, 'visited_containers']
        .apply(lambda x: helper_tid not in x)
    ]

    helper_tail_mask_safe = helper_mask_tail[
        t_forSwapping.loc[helper_mask_tail, 'visited_containers']
        .apply(lambda x: main_tid_orig not in x)
    ]

    if len(main_tail_mask_safe) == 0 or len(helper_tail_mask_safe) == 0:
        continue

    # --------------------------
    # NOW mark heads/tails (only if swap will happen)
    # --------------------------
    t_forSwapping.loc[main_mask_head, 'head_end_flag'] = (
        t_forSwapping.loc[main_mask_head, 'point_id_t'] == main_pid
    )

    t_forSwapping.loc[main_tail_mask_safe, 'tail_start_flag'] = (
        t_forSwapping.loc[main_tail_mask_safe, 'point_id_t'] == main_pid + 1
    )

    t_forSwapping.loc[helper_mask_head, 'head_end_flag'] = (
        t_forSwapping.loc[helper_mask_head, 'point_id_t'] == helper_split_pid
    )

    t_forSwapping.loc[helper_tail_mask_safe, 'tail_start_flag'] = (
        t_forSwapping.loc[helper_tail_mask_safe, 'point_id_t'] == helper_split_pid + 1
    )

    # --------------------------
    # Prevent cycles
    # --------------------------
    main_tail_mask_safe = main_mask_tail[
        t_forSwapping.loc[main_mask_tail, 'visited_containers'].apply(lambda x: helper_tid not in x)
    ]
    helper_tail_mask_safe = helper_mask_tail[
        t_forSwapping.loc[helper_mask_tail, 'visited_containers'].apply(lambda x: main_tid_orig not in x)
    ]
    if len(main_tail_mask_safe) == 0 or len(helper_tail_mask_safe) == 0:
        continue

    # --------------------------
    # Apply swaps
    # --------------------------
    t_forSwapping.loc[main_tail_mask_safe, 'tid_subid_after_swap'] = helper_tid
    t_forSwapping.loc[helper_tail_mask_safe, 'tid_subid_after_swap'] = main_tid_orig

    # Increment swap count
    t_forSwapping.loc[main_tail_mask_safe, 'swap_count'] += 1
    t_forSwapping.loc[helper_tail_mask_safe, 'swap_count'] += 1

    # Update visited_containers
    t_forSwapping.loc[main_tail_mask_safe, 'visited_containers'] = t_forSwapping.loc[main_tail_mask_safe, 'visited_containers'].apply(lambda x: x + [helper_tid])
    t_forSwapping.loc[helper_tail_mask_safe, 'visited_containers'] = t_forSwapping.loc[helper_tail_mask_safe, 'visited_containers'].apply(lambda x: x + [main_tid_orig])

    # Assign swap_pair_id
    t_forSwapping.loc[main_tail_mask_safe, 'swap_pair_id'] = swap_counter
    t_forSwapping.loc[helper_tail_mask_safe, 'swap_pair_id'] = swap_counter

    # --------------------------
    # Log swap
    # --------------------------
    swap_log.append({
        'swap_id': swap_counter,
        'main_tid': main_tid_orig,
        'helper_tid': helper_tid,
        'main_tail_points': len(main_tail_mask_safe),
        'helper_tail_points': len(helper_tail_mask_safe),
        'timestamp': time.time() - start_time
    })

print(f"Swapping completed for {swap_counter} assigned pairs.")

# Convert swap log to DataFrame
swap_log_df = pd.DataFrame(swap_log)

#%%
container_summary = []

for cid, df_container in t_forSwapping.groupby('tid_subid_after_swap', sort=False):
    container_summary.append({
        'container_id': cid,
        'num_points': len(df_container),
        'head_rows_count': df_container['head_end_flag'].sum(),
        'tail_rows_count': df_container['tail_start_flag'].sum(),
        'median_swap_count': df_container['swap_count'].median(),
        'max_swap_count': df_container['swap_count'].max(),
        'n_unique_orig_tid': df_container['tid_subid_orig'].nunique(),
    })

container_summary_df = pd.DataFrame(container_summary).sort_values('num_points', ascending=False)
container_summary_df.reset_index(drop=True, inplace=True)

print(container_summary_df.head(10))


#%% export
t_forSwapping.to_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping/t_forSwapping_swapped_hypridCloaked_2.parquet")
swap_log_df.to_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping/t_forSwapping_swapped_hypridCloaked_swap_log_df_2.parquet")
container_summary_df.to_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping/t_forSwapping_swapped_hypridCloaked_container_summary_df_2.parquet")
#%% export 5 containers
import os

# 1️⃣ Create folder to store container parquet files
output_folder = r"D:\paper3\Data\output\CloakingBasedSwapping\sampleOutputs/swapped_containers_sample"
os.makedirs(output_folder, exist_ok=True)

# 2️⃣ Identify containers with swaps
# We'll use 'tid_subid_after_swap' != 'tid_subid_orig' or swap_count > 0
swapped_containers = t_forSwapping[
    t_forSwapping['swap_count'] > 0
]['tid_subid_after_swap'].unique()

# 3️⃣ Pick 5 containers with multiple swaps (swap_count > 1)
container_swap_counts = t_forSwapping.groupby('tid_subid_after_swap')['swap_count'].sum()
selected_containers = container_swap_counts[container_swap_counts > 1].sort_values(ascending=False).head(5).index

# 4️⃣ Export each container to a separate parquet file
for container_id in selected_containers:
    df_container = t_forSwapping[t_forSwapping['tid_subid_after_swap'] == container_id]
    filename = f"{container_id}.parquet"
    df_container.to_parquet(os.path.join(output_folder, filename))
    print(f"Saved container {container_id} ({len(df_container)} rows) to {filename}")



#%%
print(
    t_forSwapping.head_end_flag.sum(),
    t_forSwapping.tail_start_flag.sum()
) #12597 8379 (before fixing teh flagging it was 12768 8422 - but they shoudl be the same)
# don't think flagging works

#%%
(t_forSwapping['tid_subid_after_swap'] 
 != t_forSwapping['tid_subid_orig']).sum() # 3624287 --> points  that have moved to a new tid


#%% exactly 1k head/tail flags are missing - not random
actual_swap_events = len(swap_log_df)
expected_flags = actual_swap_events * 2
print(expected_flags)   #           21976

print("Heads:", t_forSwapping.head_end_flag.sum())
print("Tails:", t_forSwapping.tail_start_flag.sum())
#Heads: 12597
#Tails: 8379
#                           Total    20976


#%% trying to fix flags
from tqdm import tqdm
import pandas as pd
import numpy as np
import time

# --------------------------
# 0️⃣ Initialize tracking columns
# --------------------------
t_forSwapping['tid_subid_orig'] = t_forSwapping['tid_subid']        # original trajectory ID
t_forSwapping['tid_subid_after_swap'] = t_forSwapping['tid_subid']  # start with original container
t_forSwapping['swap_pair_id'] = pd.NA
t_forSwapping['head_end_flag'] = False
t_forSwapping['tail_start_flag'] = False
t_forSwapping['swap_count'] = 0
t_forSwapping['visited_containers'] = t_forSwapping.apply(lambda _: [], axis=1)

# Segment tracking
t_forSwapping['segment_head_flag'] = False
t_forSwapping['segment_tail_flag'] = False
t_forSwapping['segment_origin'] = pd.NA
t_forSwapping['swap_segment_id'] = pd.NA
t_forSwapping['point_id_in_container'] = pd.NA

# Precompute row_uid → point_id_t mapping
row_uid_to_pid = t_forSwapping.set_index('row_uid')['point_id_t'].to_dict()

# Precompute trajectory indices for faster slicing
tid_index_map = t_forSwapping.groupby('tid_subid').groups

# Track helper rows that have already been used for splitting
used_helper_rows = set()

# Initialize swap counter and log
swap_counter = 0
swap_log = []

# Track last point_id_in_container per container
container_last_pid = {}

# --------------------------
# 1️⃣ Merge main_row info for sorting safely
# --------------------------
valid_assigned_helpers_df = valid_assigned_helpers_df.merge(
    t_forSwapping[['row_uid', 'tid_subid', 'point_id_t']],
    left_on='main_row_uid', right_on='row_uid', how='left',
    suffixes=('', '_tfs')
)
valid_assigned_helpers_df = valid_assigned_helpers_df.rename(
    columns={'tid_subid': 'tid_subid_main'}
)
valid_assigned_helpers_df = valid_assigned_helpers_df.sort_values(['tid_subid_main', 'point_id_t'])

start_time = time.time()

# --------------------------
# 2️⃣ Process swaps sequentially
# --------------------------
for _, swap in tqdm(valid_assigned_helpers_df.iterrows(), total=len(valid_assigned_helpers_df), desc="Processing swaps"):
    swap_counter += 1
    main_row_uid = swap['main_row_uid']
    main_tid_orig = t_forSwapping.loc[t_forSwapping.row_uid == main_row_uid, 'tid_subid_orig'].values[0]
    helper_tid = swap['helper_tid']

    # Skip swap if same container
    if main_tid_orig == helper_tid:
        continue

    clkpassed = swap['clkpassed']

    # --------------------------
    # Split main trajectory
    # --------------------------
    main_pid = row_uid_to_pid[main_row_uid]
    main_idx = tid_index_map[main_tid_orig]
    main_mask_head = main_idx[t_forSwapping.loc[main_idx, 'point_id_t'] <= main_pid]
    main_mask_tail = main_idx[t_forSwapping.loc[main_idx, 'point_id_t'] > main_pid]

    # --------------------------
    # Split helper trajectory
    # --------------------------
    helper_idx = tid_index_map[helper_tid]
    helper_points = t_forSwapping.loc[helper_idx]
    helper_points = helper_points[
        helper_points['intersecting_cloaking_ids'].apply(lambda x: clkpassed in x)
    ]
    helper_points = helper_points[~helper_points['row_uid'].isin(used_helper_rows)]
    if len(helper_points) == 0:
        continue

    helper_split_row = helper_points.sample(1).iloc[0]
    helper_split_pid = helper_split_row['point_id_t']
    used_helper_rows.add(helper_split_row['row_uid'])
    helper_mask_head = helper_idx[t_forSwapping.loc[helper_idx, 'point_id_t'] <= helper_split_pid]
    helper_mask_tail = helper_idx[t_forSwapping.loc[helper_idx, 'point_id_t'] > helper_split_pid]

    # --------------------------
    # Safety check BEFORE marking heads/tails
    # --------------------------
    main_tail_mask_safe = main_mask_tail[
        t_forSwapping.loc[main_mask_tail, 'visited_containers'].apply(lambda x: helper_tid not in x)
    ]
    helper_tail_mask_safe = helper_mask_tail[
        t_forSwapping.loc[helper_mask_tail, 'visited_containers'].apply(lambda x: main_tid_orig not in x)
    ]
    if len(main_tail_mask_safe) == 0 or len(helper_tail_mask_safe) == 0:
        continue

    # --------------------------
    # Assign segment-level flags and origin
    # --------------------------
    swap_segment_id = swap_counter

    # Main trajectory
    t_forSwapping.loc[main_mask_head, ['segment_head_flag', 'segment_tail_flag', 'segment_origin', 'swap_segment_id']] = [
        True, False, 'main', swap_segment_id
    ]
    t_forSwapping.loc[main_tail_mask_safe, ['segment_head_flag', 'segment_tail_flag', 'segment_origin', 'swap_segment_id']] = [
        False, True, 'main', swap_segment_id
    ]

    # Helper trajectory
    t_forSwapping.loc[helper_mask_head, ['segment_head_flag', 'segment_tail_flag', 'segment_origin', 'swap_segment_id']] = [
        True, False, 'helper', swap_segment_id
    ]
    t_forSwapping.loc[helper_tail_mask_safe, ['segment_head_flag', 'segment_tail_flag', 'segment_origin', 'swap_segment_id']] = [
        False, True, 'helper', swap_segment_id
    ]

    # --------------------------
    # Apply swaps
    # --------------------------
    t_forSwapping.loc[main_tail_mask_safe, 'tid_subid_after_swap'] = helper_tid
    t_forSwapping.loc[helper_tail_mask_safe, 'tid_subid_after_swap'] = main_tid_orig

    # Increment swap count
    t_forSwapping.loc[main_tail_mask_safe, 'swap_count'] += 1
    t_forSwapping.loc[helper_tail_mask_safe, 'swap_count'] += 1

    # Update visited_containers
    t_forSwapping.loc[main_tail_mask_safe, 'visited_containers'] = t_forSwapping.loc[main_tail_mask_safe, 'visited_containers'].apply(lambda x: x + [helper_tid])
    t_forSwapping.loc[helper_tail_mask_safe, 'visited_containers'] = t_forSwapping.loc[helper_tail_mask_safe, 'visited_containers'].apply(lambda x: x + [main_tid_orig])

    # Assign swap_pair_id
    t_forSwapping.loc[main_tail_mask_safe, 'swap_pair_id'] = swap_counter
    t_forSwapping.loc[helper_tail_mask_safe, 'swap_pair_id'] = swap_counter

    # --------------------------
    # Assign sequential point_id_in_container
    # --------------------------
    def assign_container_pids(container_id, mask):
        df_seg = t_forSwapping.loc[mask]
        last_pid = container_last_pid.get(container_id, 0)
        df_seg['point_id_in_container'] = np.arange(last_pid + 1, last_pid + 1 + len(df_seg))
        container_last_pid[container_id] = df_seg['point_id_in_container'].iloc[-1]
        t_forSwapping.loc[mask, 'point_id_in_container'] = df_seg['point_id_in_container']

    assign_container_pids(helper_tid, main_tail_mask_safe)
    assign_container_pids(main_tid_orig, helper_tail_mask_safe)

    # --------------------------
    # Log swap
    # --------------------------
    swap_log.append({
        'swap_id': swap_counter,
        'main_tid': main_tid_orig,
        'helper_tid': helper_tid,
        'main_tail_points': len(main_tail_mask_safe),
        'helper_tail_points': len(helper_tail_mask_safe),
        'timestamp': time.time() - start_time
    })

print(f"Swapping completed for {swap_counter} assigned pairs.")

# Convert swap log to DataFrame
swap_log_df = pd.DataFrame(swap_log)

#%%
t_forSwapping.head()

#%% check point ids within container
# now
for cid, g in df_sorted.groupby('tid_subid_after_swap'):
    if not (g.sort_values('point_id_in_container')['point_id_in_container'].is_monotonic_increasing):
        print(f"Container {cid} has non-monotonic point IDs")

#%%
df_sorted.to_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping/t_for_swapping_ptID_sorted.parquet")
#%%
head_counts = t_forSwapping.groupby(['tid_subid_after_swap', 'swap_pair_id'])['head_end_flag'].sum()
tail_counts = t_forSwapping.groupby(['tid_subid_after_swap', 'swap_pair_id'])['tail_start_flag'].sum()

print("Segments with multiple heads:", (head_counts > 1).sum())
print("Segments with multiple tails:", (tail_counts > 1).sum())
print("Segments missing head or tail:", ((head_counts != 1) | (tail_counts != 1)).sum())

#%%
for cid, g in t_forSwapping.groupby('tid_subid_after_swap'):
    print(f"Container {cid}: unique orig tids:", g['tid_subid_orig'].nunique())
# %%
#%%
main_segments = t_forSwapping[
    t_forSwapping['HeadTail'] == 'HeadEnd'
]
print(main_segments[['tid_subid_after_swap', 'tid_subid_orig', 'HeadEndCloakingAreaId', 'CloakingGapSwap']].head())

#%%
cid = t_forSwapping['tid_subid_after_swap'].value_counts().idxmax()
g = t_forSwapping[t_forSwapping['tid_subid_after_swap'] == cid].sort_values('point_id_in_container')
print(g[['point_id_in_container', 'point_id_t', 'tid_subid_orig', 'HeadTail', 'head_end_flag', 'tail_start_flag']])
# %%
#%%
t_forSwapping.groupby('tid_subid_after_swap')['point_id_in_container'].max()
# %%
#%%
t_forSwapping.groupby('tid_subid_after_swap')['swap_pair_id'].nunique()



#%%% ran for 3h 30min
# --------------------------
# 0️⃣ Initialize tracking columns
# --------------------------
t_forSwapping['tid_subid_orig'] = t_forSwapping['tid_subid']
t_forSwapping['tid_subid_after_swap'] = t_forSwapping['tid_subid_orig']
t_forSwapping['segment_index'] = pd.NA          # NEW: tracks order of segments in container
t_forSwapping['point_id_in_container'] = pd.NA  # NEW: sequential point index within container

# Precompute row_uid → point mapping
row_uid_to_idx = t_forSwapping.set_index('row_uid').index

# Precompute trajectory indices for faster slicing
tid_index_map = t_forSwapping.groupby('tid_subid_orig').groups

# Track helper rows that have already been used
used_helper_rows = set()

# Track last segment index per container
container_last_segment = {}  # container_id -> last segment index used
container_last_point_id = {} # container_id -> last point_id_in_container

# Swap counter just for logging
swap_counter = 0
swap_log = []

# --------------------------
# 1️⃣ Merge main_row info for sorting safely
# --------------------------
valid_assigned_helpers_df = valid_assigned_helpers_df.merge(
    t_forSwapping[['row_uid', 'tid_subid_orig']],
    left_on='main_row_uid', right_on='row_uid', how='left',
    suffixes=('', '_tfs')
)
valid_assigned_helpers_df = valid_assigned_helpers_df.rename(
    columns={'tid_subid_orig': 'tid_subid_main'}
)
valid_assigned_helpers_df = valid_assigned_helpers_df.sort_values(['tid_subid_main', 'row_uid'])

# --------------------------
# 2️⃣ Process swaps sequentially
# --------------------------
for _, swap in tqdm(valid_assigned_helpers_df.iterrows(), total=len(valid_assigned_helpers_df), desc="Processing swaps"):

    swap_counter += 1
    main_row_uid = swap['main_row_uid']
    main_tid_orig = t_forSwapping.loc[t_forSwapping.row_uid == main_row_uid, 'tid_subid_orig'].values[0]
    helper_tid = swap['helper_tid']
    clkpassed = swap['clkpassed']

    # Skip swap if same container
    if main_tid_orig == helper_tid:
        continue

    # --------------------------
    # Split main trajectory into head/tail
    # --------------------------
    main_idx = tid_index_map[main_tid_orig]
    main_pid = main_row_uid

    main_mask_tail = main_idx[
        t_forSwapping.loc[main_idx, 'row_uid'] > main_pid
    ]

    # --------------------------
    # Split helper trajectory
    # --------------------------
    helper_idx = tid_index_map[helper_tid]
    helper_points = t_forSwapping.loc[helper_idx]
    helper_points = helper_points[
        helper_points['intersecting_cloaking_ids'].apply(lambda x: clkpassed in x)
    ]
    helper_points = helper_points[
        ~helper_points['row_uid'].isin(used_helper_rows)
    ]

    if len(helper_points) == 0:
        continue

    helper_split_row = helper_points.sample(1).iloc[0]
    helper_split_pid = helper_split_row['row_uid']
    used_helper_rows.add(helper_split_pid)

    helper_mask_tail = helper_idx[
        t_forSwapping.loc[helper_idx, 'row_uid'] > helper_split_pid
    ]

    if len(main_mask_tail) == 0 or len(helper_mask_tail) == 0:
        continue

    # --------------------------
    # Assign segment indices
    # --------------------------
    # Main tail moves to helper container
    main_container_id = helper_tid
    segment_id = container_last_segment.get(main_container_id, 0) + 1
    t_forSwapping.loc[main_mask_tail, 'tid_subid_after_swap'] = main_container_id
    t_forSwapping.loc[main_mask_tail, 'segment_index'] = segment_id
    container_last_segment[main_container_id] = segment_id

    # Helper tail moves to main container
    helper_container_id = main_tid_orig
    segment_id = container_last_segment.get(helper_container_id, 0) + 1
    t_forSwapping.loc[helper_mask_tail, 'tid_subid_after_swap'] = helper_container_id
    t_forSwapping.loc[helper_mask_tail, 'segment_index'] = segment_id
    container_last_segment[helper_container_id] = segment_id

    # --------------------------
    # Update point_id_in_container sequentially
    # --------------------------
    for container_id in [main_container_id, helper_container_id]:
        last_point_id = container_last_point_id.get(container_id, 0)
        mask = t_forSwapping['tid_subid_after_swap'] == container_id
        # Sort mask by original row_uid to maintain order inside segment
        mask_indices = t_forSwapping.loc[mask].sort_values('row_uid').index
        for i, idx in enumerate(mask_indices, start=last_point_id+1):
            t_forSwapping.at[idx, 'point_id_in_container'] = i
        container_last_point_id[container_id] = t_forSwapping.loc[mask_indices[-1], 'point_id_in_container']

    # --------------------------
    # Log swap
    # --------------------------
    swap_log.append({
        'swap_id': swap_counter,
        'main_tid': main_tid_orig,
        'helper_tid': helper_tid,
        'main_tail_points': len(main_mask_tail),
        'helper_tail_points': len(helper_mask_tail)
    })

# --------------------------
# 3️⃣ Convert swap log to DataFrame
# --------------------------
swap_log_df = pd.DataFrame(swap_log)
print(f"Swapping completed for {swap_counter} assigned pairs.")

#%% renumbering is incorrect
