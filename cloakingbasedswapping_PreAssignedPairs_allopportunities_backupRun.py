#%%
import geopandas as gpd
import pickle

# load data back in
t_forSwapping = gpd.read_parquet(r"d:\paper3\CloakedBasedSwappingAllPredefinedOpportunities\t_forSwapping_26723gaps.parquet")

with open(r"d:\paper3\CloakedBasedSwappingAllPredefinedOpportunities\helper_pool_dict_ordered.pkl", "rb") as f:
    helper_pool_dict_ordered = pickle.load(f)


#%% prep for swapping
# clk gaps are sorted in order of priority (less swapping options (by tid) will be processed first)

# prep data gdf
import numpy as np
import pandas as pd
import random

# reduce df to prevent memory issues (can get attributes back at a later stage)
t_forSwapping_r = t_forSwapping[['row_uid', 'tid_subid', 'uid']].copy()
t_forSwapping_r['orig_tid_subid'] = t_forSwapping_r['tid_subid'].copy()
t_forSwapping_r['new_tid_subid'] = t_forSwapping_r['tid_subid'].copy()
t_forSwapping_r['new_uid'] = t_forSwapping_r['uid'].copy()
t_forSwapping_r['swap_SwappingHeadTail'] = False
t_forSwapping_r['SwappingHeadTail'] = False
t_forSwapping_r['swap_n'] = 0
t_forSwapping_r['swap_n_containerChange'] = 0
t_forSwapping_r['swap_origin'] = [[] for _ in range(len(t_forSwapping_r))]
t_forSwapping_r['swap_destination'] = [[] for _ in range(len(t_forSwapping_r))]
t_forSwapping_r['swap_point_id_t'] = np.nan

                                                
# prep data lookup
point_to_tid_dict = dict(zip(t_forSwapping_r['row_uid'],
                   t_forSwapping_r['new_tid_subid'])) # tid_subid assignments change after swapping! must be updated within for loop

point_to_uid_dict_orig = dict(zip(t_forSwapping_r['row_uid'],
                   t_forSwapping_r['uid'])) 
# uid assignments change after swapping! must be updated within for loop
point_to_uid_dict_swapped = dict(zip(t_forSwapping_r['row_uid'],
                   t_forSwapping_r['new_uid'])) 

#od_dict = dict(zip(t_helper_random_assigned['main_row_uid'], [[] for _ in range(len(t_helper_random_assigned))])) # must chain odd later, i.e, look at values, are there to values? then its a odd chain
from collections import defaultdict
od_dict = defaultdict(list)
for key in helper_pool_dict_ordered.keys():
    od_dict[key]  # only storing clk gap, aka origin, and intialising an empty list

# add a swapping history dict
swap_history = defaultdict(list) # <-- container membership over time

# paramater settings for waiting room
max_retries = 15
retry_counts = defaultdict(int)

# waiting room swapping code
from tqdm.auto import tqdm
from collections import deque

# look at 5 clk gaps to see if code works
#from itertools import islice
#swap_queue = deque(islice(helper_pool_dict_ordered.items(), 5)) 

# run for all
swap_queue = deque(helper_pool_dict_ordered.items())

waiting = {}


pbar = tqdm(total=len(swap_queue), desc="Processing swaps")

#pbar = tqdm(total=len(swap_queue), desc="Processing swaps (resume)")
while swap_queue:
    # (0) get splitting points
    main_sid, helper_sid_list = swap_queue.popleft()
    # normalise to list first (incase waiting room strutcure is meesed up)
    #if isinstance(helper_sid_list, tuple):
    #    helper_sid_list = [helper_sid_list]
    # fixed waiting room storage, don't need to check for tuple here

    # main_sid is the point id, get tid of main
    main_tid = point_to_tid_dict[main_sid]
    # initiate tracking of valid tid swapping pairs
    success_tid = False

    # find helper tid with a different tid
    # (point_to_tid_dict always represents the current tid state, 
    # compability of original tid has been validated during pre-processing)
    # helper_sid is stored as a pair (tuple) in a list
    # pick a random swapping pair
    h_tid_attempts = helper_sid_list.copy()
    # reducing sampling bias by shuffling the list of helper pairs first
    random.shuffle(h_tid_attempts)

    # get uid of main
    main_uid = point_to_uid_dict_orig[main_sid]

    for h_head_end, h_tail_start in h_tid_attempts:

        # (0) the uid of the new_tid must be different to the original uid
        if main_uid == point_to_uid_dict_swapped[h_head_end]: # pair invalid because uid of both points is the same --> skip 
            continue

        # (1) helper pair must still belong to the same trajectory
        if point_to_tid_dict[h_head_end] != point_to_tid_dict[h_tail_start]: # pair invalid because tid of both points is not the same --> skip
            continue

        # (2) helper must be different trajectory from main
        helper_tid = point_to_tid_dict[h_head_end]
        if helper_tid != main_tid: # valid helper found
            success_tid = True
            break   # exit the loop
        else:
            continue

    if not success_tid:
        # fallback to waiting room
        #waiting.setdefault(main_tid, []).append((main_sid, random.choice(helper_sid_list)))
        #waiting.setdefault(main_tid, []).append((main_sid, [random.choice(helper_sid_list)]))
        # not random but all 
        waiting.setdefault(main_tid, []).append((main_sid, tuple(helper_sid_list)))
        continue

    

    # (1) isolate the swapping pair from main df
    # (1a) get tid_subid for helper
    helper_tid = point_to_tid_dict[h_head_end] # TID OF POINT WILL CHANGE, we are updating dict at the end of the loop
    helper_uid = point_to_uid_dict_swapped[h_head_end]

    # (1b) subset by tid and reset index
    main = t_forSwapping_r[t_forSwapping_r['new_tid_subid'] == main_tid].reset_index(drop=True)
    helper = t_forSwapping_r[t_forSwapping_r['new_tid_subid'] == helper_tid].reset_index(drop=True)

    # (2) split main and helper into heads and tail
    m_cut_index = main.index[main["row_uid"] == main_sid][0]
    h_cut_index_headEnd = helper.index[helper["row_uid"] == h_head_end][0]
    h_cut_index_tailStart = helper.index[helper["row_uid"] == h_tail_start][0]
    # ensure that helper pair is still consecutive and not corrupted by previous swaps
    # assert h_cut_index_tailStart == h_cut_index_headEnd + 1, "Helper pair not consecutive"
    if h_cut_index_tailStart != h_cut_index_headEnd + 1:
        print('helper head and tail are corrupt')
        # skip this helper pair, pick a new one
        waiting.setdefault(main_tid, []).append((main_sid, tuple(helper_sid_list)))
        continue 
        #success_tid = False
        #continue_loop = True  # trigger outer loop to pick next pair

    # (2a) general split
    main["swap_SwappingHeadTail"] = np.where(main.index <= m_cut_index, "head_main", "tail_main")
    helper["swap_SwappingHeadTail"] = np.where(helper.index <= h_cut_index_headEnd, "head_helper", "tail_helper") 
    
    # (2b) split to track swaps
    # this follows the old logid:one split point for head and tail
    # when we have two
    # therefore, helper_sid_r is currently not assigned
    # what this labelling does
    # is it helpful?
    main["SwappingHeadTail"] = np.where(main.index <= m_cut_index, f"head_main_{main_sid}", f"tail_main_{main_sid}")
    helper["SwappingHeadTail"] = np.where(helper.index <= h_cut_index_headEnd, f"head_helper_{h_head_end}", f"tail_helper_{h_head_end}") # using the point id of the helper head end to be consistent with labeling of main

    # (2c) record origin destination for these swaps!
    main_origin_i = m_cut_index
    main_destination_i = h_cut_index_tailStart
    helper_origin_i = h_cut_index_headEnd
    helper_destination_i = m_cut_index+1
    
    # this follows the old logic, too
    main.at[main_origin_i, "swap_origin"].append(f'main_{main_sid}_origin')
    len_main = len(main)
    if helper_destination_i < len_main: # only attach main tail to helper head if main has a tail
        main.at[helper_destination_i, "swap_destination"].append(f'helper_{h_head_end}_destination')
    helper.at[helper_origin_i, "swap_origin"].append(f'helper_{h_head_end}_origin')
    helper.at[main_destination_i, "swap_destination"].append(f'main_{main_sid}_destination')

    # need to record row_uid of these instead 
    # dict should be finde because it is based on point ids!
    main_origin_id =  main.at[m_cut_index, "row_uid"] 
    main_destination_id = helper.at[(h_cut_index_tailStart), "row_uid"] 
    helper_origin_id = helper.at[h_cut_index_headEnd, "row_uid"]
    # only attach a helper destination id if main has a tail, it is ok for helper to end in clk area
    if helper_destination_i < len_main:
        helper_destination_id = main.at[helper_destination_i, "row_uid"]
        od_dict[helper_origin_id].append(helper_destination_id)

    od_dict[main_origin_id].append(main_destination_id)

    # (3) swap by updating tid 
    # (3a) update tail tid of main
    # overwrites the full column
    main['new_tid_subid'] = np.where(
        main['swap_SwappingHeadTail'] == "tail_main",   # for rows that are the tail of the main
        helper_tid,                                     # new_tid_subid is updated to helper_tid
        main_tid                                        # otherwise, i.e., not tail and therefore must be head, take tid of main
    )
    # update head tid of helper
    helper['new_tid_subid'] = np.where(
        helper['swap_SwappingHeadTail'] == "head_helper",   
        helper_tid,                                     # helper_tid and main_tid have been retrived from new_tid_subid at the beginning of the loop 
        main_tid                                        # based on the split point to tid dictonary                            
    )

    # now update uid
    main['new_uid'] = np.where(
        main['swap_SwappingHeadTail'] == "tail_main",   
        helper_uid,                                    
        main_uid                                        
    )
    helper['new_uid'] = np.where(
        helper['swap_SwappingHeadTail'] == "head_helper",   
        helper_uid,                                      
        main_uid                                                                   
    )

    # (3b) update point_id (actually move points to new container, i.e., order by new point id)
    swapped_df = pd.concat([main, helper])
    swapped_df = swapped_df.sort_values(
        by=['new_tid_subid', 'swap_SwappingHeadTail', 'row_uid'],
        ascending=[True, True, True]  
    ).reset_index(drop=True)
    # now that points are sorted we can add point ids
    swapped_df['swap_point_id_t'] = swapped_df.groupby('new_tid_subid').cumcount() + 1

    # add swap count
    swapped_df['swap_n'] = swapped_df['swap_n'] +1
    # only count segments that swap containers, not the ones that remain in the container
    mask = swapped_df['swap_SwappingHeadTail'].isin(['tail_main','head_helper'])
    swapped_df.loc[mask, 'swap_n_containerChange'] += 1

    # record swapping history
    for row_uid, new_tid in zip(swapped_df["row_uid"], swapped_df["new_tid_subid"]):
        if not swap_history[row_uid] or swap_history[row_uid][-1] != new_tid:
            swap_history[row_uid].append(new_tid)

    # (4) MUST UPDATE TID IN RECORDS
    # drop these from the master df
    #t_forSwapping_r = t_forSwapping_r[~t_forSwapping_r['row_uid'].isin(swapped_df['row_uid'])]
    # concat updated attributes of these points
    #t_forSwapping_r = pd.concat([t_forSwapping_r, swapped_df], ignore_index=True)
    # faster: update rows in place
    rows = swapped_df['row_uid']
    cols = [
        'new_tid_subid','new_uid','swap_SwappingHeadTail','SwappingHeadTail',
        'swap_point_id_t','swap_n','swap_origin','swap_destination'
    ]
    t_forSwapping_r.loc[
        t_forSwapping_r['row_uid'].isin(rows),
        cols
    ] = swapped_df[cols].values


    # MUST UPDATE ALL KEY-VALUES in DICTONARY --> overwrite dictonary
    point_to_tid_dict = dict(zip(t_forSwapping_r['row_uid'],
                   t_forSwapping_r['new_tid_subid'])) # tid_subid assignments change after swapping!
    point_to_uid_dict_swapped = dict(zip(t_forSwapping_r['row_uid'],
                   t_forSwapping_r['new_uid'])) # actually swapped df doesn't have a uid

    # (5) track which new_tid_subid has changed - so that release from waiting room can be triggered
    affected_tids = {main_tid, helper_tid}

    for tid in affected_tids:
        if tid in waiting:
            for pair in waiting[tid]:
                if retry_counts[pair] < max_retries:
                    swap_queue.append(pair)   # re-add to the queue
                    retry_counts[pair] += 1
            del waiting[tid]              # remove from waiting

    # (6) update progress bar
    pbar.update(1)

pbar.close()
#%% broke at 16300/26723 [29:06:06<21:10:29,  7.31s/it]
# becuase ---> 67 h_tid_attempts = helper_sid_list.copy()
#AttributeError: 'tuple' object has no attribute 'copy'
# 26723-16300 = 10423

print(len(swap_queue)) #5525
print(len(waiting)) #2826 tids
print(sum(len(v) for v in waiting.values())) # 4897 actual clk gaps waiting
#16300+4897+5525 = 26722 - missing one

# tuple error comes from waiting room tids, fixed code and continues loop
# 0/5525
# immediately processed, as expected

#%% export, then run again taking care of uid constraint

t_forSwapping_r["swap_SwappingHeadTail"] = t_forSwapping_r["swap_SwappingHeadTail"].astype("string")
t_forSwapping_r["SwappingHeadTail"] = t_forSwapping_r["SwappingHeadTail"].astype("string")
t_forSwapping_r.to_parquet(r"D:\paper3\CloakedBasedSwappingAllPredefinedOpportunities\output/ClkGpsSwappedT.parquet")

with open(r"D:\paper3\CloakedBasedSwappingAllPredefinedOpportunities\output/waiting.pkl", "wb") as f:
    pickle.dump(waiting, f) #<-- do I know which ones have been processed?
with open(r"D:\paper3\CloakedBasedSwappingAllPredefinedOpportunities\output/point_to_tid_dict.pkl", "wb") as f:
    pickle.dump(point_to_tid_dict, f)
# od dict should be finde because it is based on point ids!
with open(r"D:\paper3\CloakedBasedSwappingAllPredefinedOpportunities\output/od_dict.pkl", "wb") as f:
    pickle.dump(od_dict, f)

with open(r"D:\paper3\CloakedBasedSwappingAllPredefinedOpportunities\output/swap_history.pkl", "wb") as f:
    pickle.dump(swap_history, f)