#%% rerun cloaking swapping to save swap history
import geopandas as gpd
import pickle

t_forSwapping = gpd.read_parquet(r"e:\paper3\FinalCloakedBasedSwapping\t_forSwapping_26723gaps_labelled.parquet")
#%%
with open(r"\\tsclient\R\paper3\helper_pool_dict_ordered_updated.pkl", "rb") as f:
    helper_pool_dict_ordered_updated = pickle.load(f)



#%% ORDERED LISTS FOR CLOAKED BASED SWAPPING WORK BEST
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


#%% swapping history
# swap_id_map: tracks the latest swap_id per pid only, i.e., overwrites prev ones
# swap_history: tracks trajectory mebership over time, keeping record of multiple swaps per point
# od_dict: split points  to new connection points, one entry per swap event 

# true number of swaps
total_swaps = swap_counter
print('total swaps: ', total_swaps)
total_swaps2 = len(locked_main_splits)
print('should be the same as: ', total_swaps2)

# total number of unique points involved in swaps
points_involved = [pid for pid, hist in swap_history.items() if len(hist) > 1]
total_points_involved = len(points_involved)
print('\ntotal points involved: ', total_points_involved)

# average number of points moved per swap
# estimate only
swap_sizes = []
# inside your swap block:
moved_points = len(tail_helper) + len(tail_main)
swap_sizes.append(moved_points)
avg_points_per_swap = np.mean(swap_sizes)
print('\nestimate of average number of points moved per swap: ', avg_points_per_swap)
# alternative approach
total_point_moves = sum(len(hist) - 1 for hist in swap_history.values())
avg_points_per_swap2 = total_point_moves / total_swaps
print('estimate of average number of points moved per swap: ', avg_points_per_swap2)

#total swaps:  16250
#should be the same as:  16250

#total points involved:  4245729

#estimate of average number of points moved per swap:  1196.0
#estimate of average number of points moved per swap:  1125.9600615384616

#%%
# total swaps
total_swaps = swap_counter

# total points moved (counts repeated moves)
total_points_moved = sum(len(hist) - 1 for hist in swap_history.values())

# average points per swap
avg_points_per_swap = total_points_moved / total_swaps

print("Total swaps:", total_swaps)
print("Total points moved:", total_points_moved)
print("Average points per swap:", avg_points_per_swap)

#Total swaps: 16250
#Total points moved: 18296851
#Average points per swap: 1125.9600615384616

#%%
unique_points_swapped = sum(1 for hist in swap_history.values() if len(hist) > 1)
unique_points_swapped #4245729
