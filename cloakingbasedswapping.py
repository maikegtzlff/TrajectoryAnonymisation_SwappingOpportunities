#%% load data
import geopandas as gpd
import pandas as pd
t_forSwapping = gpd.read_parquet(r"d:\paper3\cloakedBasedSwapping\t_forSwapping.parquet")
valid_assigned_helpers_df = pd.read_parquet(r"d:\paper3\cloakedBasedSwapping\valid_assigned_helpers_df.parquet")
print('loaded data')

#%% start swapping
from tqdm import tqdm
import pandas as pd
import numpy as np
import time

# --------------------------
# 0️⃣ Initialize tracking columns
# --------------------------
t_forSwapping['tid_subid_orig'] = t_forSwapping['tid_subid']        # original trajectory ID
t_forSwapping['tid_subid_after_swap'] = t_forSwapping['tid_subid']  # assume no swap initially
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

    main_mask_head = main_idx[t_forSwapping.loc[main_idx, 'point_id_t'] <= main_pid]
    main_mask_tail = main_idx[t_forSwapping.loc[main_idx, 'point_id_t'] > main_pid]

    t_forSwapping.loc[main_mask_head, 'head_end_flag'] = t_forSwapping.loc[main_mask_head, 'point_id_t'] == main_pid
    t_forSwapping.loc[main_mask_tail, 'tail_start_flag'] = t_forSwapping.loc[main_mask_tail, 'point_id_t'] == main_pid + 1

    # --------------------------
    # Split helper trajectory
    # --------------------------
    helper_idx = tid_index_map[helper_tid]
    helper_points = t_forSwapping.loc[helper_idx]

    # Use cloaking list
    helper_points = helper_points[helper_points['intersecting_cloaking_ids'].apply(lambda x: clkpassed in x)]
    helper_points = helper_points[~helper_points['row_uid'].isin(used_helper_rows)]
    if len(helper_points) == 0:
        continue

    # Pick random split point
    helper_split_row = helper_points.sample(1).iloc[0]
    helper_split_pid = helper_split_row['point_id_t']
    used_helper_rows.add(helper_split_row['row_uid'])

    helper_mask_head = helper_idx[t_forSwapping.loc[helper_idx, 'point_id_t'] <= helper_split_pid]
    helper_mask_tail = helper_idx[t_forSwapping.loc[helper_idx, 'point_id_t'] > helper_split_pid]

    t_forSwapping.loc[helper_mask_head, 'head_end_flag'] = t_forSwapping.loc[helper_mask_head, 'point_id_t'] == helper_split_pid
    t_forSwapping.loc[helper_mask_tail, 'tail_start_flag'] = t_forSwapping.loc[helper_mask_tail, 'point_id_t'] == helper_split_pid + 1

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
t_forSwapping.to_parquet(r"D:\paper3\cloakedBasedSwapping\output_hybridApproach_131/t_forSwapping_swapped_hypridCloaked.parquet")
swap_log_df.to_parquet(r"D:\paper3\cloakedBasedSwapping\output_hybridApproach_131/t_forSwapping_swapped_hypridCloaked_swap_log_df.parquet")
container_summary_df.to_parquet(r"D:\paper3\cloakedBasedSwapping\output_hybridApproach_131/t_forSwapping_swapped_hypridCloaked_container_summary_df.parquet")