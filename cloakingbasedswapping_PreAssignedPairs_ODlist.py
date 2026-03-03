#%%
import numpy as np
import geopandas as gpd
import pandas as pd

t_forSwapping = gpd.read_parquet(r"d:\paper3\t_forSwapping.parquet")
t_helper_random_assigned = pd.read_parquet(r"d:\paper3\CloakingGaps_swappingPairs_PointLevel.parquet")


#%% 
#  468/11549 [39:12<15:28:49,  5.03s/it]
# ---> 81 helper.loc[main_destination_i, "swap_destination"].append(f'main_{main_sid}_destination')
# KeyError: np.int64(1030)
# not in index

#%% debug

#%% last succesfull loop should've produced ouput
print(t_forSwapping_r.swap_n.max()) # 5 so swap count works
print(t_forSwapping_r.SwappingHeadTail.unique()) # ['False' 'head_main_131' 'tail_helper_773962' ... 'tail_helper_2734588' 'head_helper_2734588' 'tail_main_342441']
t_forSwapping_r.head()

#%% export before I accidentally overrun the loop output
swapped_df.to_parquet(r"D:\paper3\cloakingbasedswapping_PreassignedPairs_ODlist_debugging/swapped_df_brokenLoop.parquet")
helper.to_parquet(r"D:\paper3\cloakingbasedswapping_PreassignedPairs_ODlist_debugging/helper_brokenLoop.parquet")
main.to_parquet(r"D:\paper3\cloakingbasedswapping_PreassignedPairs_ODlist_debugging/main_brokenLoop.parquet")
#t_forSwapping_r.to_parquet(r"D:\paper3\cloakingbasedswapping_PreassignedPairs_ODlist_debugging/t_forSwapping_r_Swapped_brokenLoop.parquet")

import pickle
with open(r"D:\paper3\cloakingbasedswapping_PreassignedPairs_ODlist_debugging/point_to_tid_dict_brokenLoop.pkl", "wb") as f:
    pickle.dump(point_to_tid_dict, f)
with open(r"D:\paper3\cloakingbasedswapping_PreassignedPairs_ODlist_debugging/od_dict_BrokenLoop.pkl", "wb") as f:
    pickle.dump(od_dict, f)
#%%
t_forSwapping_r["swap_SwappingHeadTail"] = t_forSwapping_r["swap_SwappingHeadTail"].astype(str)
t_forSwapping_r["SwappingHeadTail"] = t_forSwapping_r["SwappingHeadTail"].astype(str)
t_forSwapping_r.to_parquet(r"D:\paper3\cloakingbasedswapping_PreassignedPairs_ODlist_debugging/t_forSwapping_r_Swapped_brokenLoop.parquet")


#%% look at the problematic one that is causing the index error
#KeyError: np.int64(1030)
#helper.loc[main_destination_i, "swap_destination"].append(f'main_{main_sid}_destination')
#           main_destination_i 1030
#                               swap_destination is  the column
#                                                  the value I would add to the list of 
#                                                   swap destinations for this point
#                                                   f'main_{main_sid}_destination'
#                                                     main_sid is 7315343

#   main_origin_i = m_cut_index
#    main_destination_i = h_cut_index+1
#    helper_origin_i = h_cut_index
#    helper_destination_i = m_cut_index+1
    
#    main.loc[main_origin_i, "swap_origin"].append(f'main_{main_sid}_origin')
#    main.loc[helper_destination_i, "swap_destination"].append(f'helper_{helper_sid}_destination')

# main origin and destination should've worked
# helper_HelperSID_origin cannot be in column yet - but column has a value
# I'd have said from previous swap, but swap_n is 0

# PROBLEM HERE
#     helper.loc[helper_origin_i, "swap_origin"].append(f'helper_{helper_sid}_origin')
#    helper.loc[main_destination_i, "swap_destination"].append(f'main_{main_sid}_destination')



# this is the problem
# helper.loc[main_destination_i]
# print(len(helper)) # 1030 rows 
# print(helper.index.max()) # 1029 - point is classed as swap_origin, helper_1270511_origin

#h_cut_index = helper.index[helper["row_uid"] == helper_sid][0]    
# h_cut_index is 1029
# helper_sid is 5243076
# but when i look at the helper df row_uid of index 1029 is 1270511

# WORKAROUND
# if index of any tail is outside of range, move split by one?


# BUT 
# main_sid 7315343
# helper_sid 5243076


#main = t_forSwapping_r[t_forSwapping_r['new_tid_subid'] == main_tid].reset_index(drop=True)
#helper = t_forSwapping_r[t_forSwapping_r['new_tid_subid'] == helper_tid].reset_index(drop=True)

#m_cut_index = main.index[main["row_uid"] == main_sid][0]
#h_cut_index = helper.index[helper["row_uid"] == helper_sid][0]    

#main_origin_i = m_cut_index
#main_destination_i = h_cut_index+1
#helper_origin_i = h_cut_index
#helper_destination_i = m_cut_index+1
    
#main.loc[main_origin_i, "swap_origin"].append(f'main_{main_sid}_origin')
#main.loc[helper_destination_i, "swap_destination"].append(f'helper_{helper_sid}_destination')
#helper.loc[helper_origin_i, "swap_origin"].append(f'helper_{helper_sid}_origin')
#helper.loc[main_destination_i, "swap_destination"].append(f'main_{main_sid}_destination')













#%% prep data gdf
# reduce df to prevent memory issues (can get attributes back at a later stage)
t_forSwapping_r = t_forSwapping[['row_uid', 'tid_subid']].copy()
t_forSwapping_r['orig_tid_subid'] = t_forSwapping_r['tid_subid'].copy()
t_forSwapping_r['new_tid_subid'] = t_forSwapping_r['tid_subid'].copy()
t_forSwapping_r['swap_SwappingHeadTail'] = False
t_forSwapping_r['SwappingHeadTail'] = False
t_forSwapping_r['swap_n'] = 0
t_forSwapping_r['swap_origin'] = [[] for _ in range(len(t_forSwapping_r))]
t_forSwapping_r['swap_destination'] = [[] for _ in range(len(t_forSwapping_r))]
t_forSwapping_r['swap_point_id_t'] = np.nan

                                                
# prep data lookup
swapping_pairs = dict(zip(t_helper_random_assigned['main_row_uid'],
                   t_helper_random_assigned['helper_row_uid'])) # dictonaires are unoarded

point_to_tid_dict = dict(zip(t_forSwapping_r['row_uid'],
                   t_forSwapping_r['new_tid_subid'])) # tid_subid assignments change after swapping!

#od_dict = dict(zip(t_helper_random_assigned['main_row_uid'], [[] for _ in range(len(t_helper_random_assigned))])) # must chain odd later, i.e, look at values, are there to values? then its a odd chain
from collections import defaultdict
od_dict = defaultdict(list)
for key in t_helper_random_assigned['main_row_uid']:
    od_dict[key]  
od_dict


# run swapping
from tqdm.auto import tqdm
from collections import deque

swap_queue = deque(swapping_pairs.items())
waiting = {}

pbar = tqdm(total=len(swap_queue), desc="Processing swaps")

while swap_queue:
    # (0) get splitting points
    main_sid, helper_sid = swap_queue.popleft()

    # (1) isolate the swapping pair from main df
    # (1a) get tid_subid for both main and helper
    main_tid = point_to_tid_dict[main_sid]
    helper_tid = point_to_tid_dict[helper_sid]

    # --- early validation 1 ---
    # swapping points are from different tid
    # otherwise move swapping pair to waiting room until tid changes
    if main_tid == helper_tid:
        waiting.setdefault(main_tid, []).append((main_sid, helper_sid))
        print(f"added {main_sid, helper_sid} to waiting room because they are assigned the same tid")
        continue
    
    # (1b) subset by tid and reset index
    main = t_forSwapping_r[
        t_forSwapping_r['new_tid_subid'] == main_tid
    ].reset_index(drop=True)

    helper = t_forSwapping_r[
        t_forSwapping_r['new_tid_subid'] == helper_tid
    ].reset_index(drop=True)

    # (2) split main and helper into heads and tail
    m_cut_index = main.index[main["row_uid"] == main_sid][0]
    h_cut_index = helper.index[helper["row_uid"] == helper_sid][0]

    # --- early validation 2 ---
    # tail must have points (aka index after cut must exist)
    if (m_cut_index + 1 > main.index.max()):
        waiting.setdefault(main_tid, []).append((main_sid, helper_sid))
        print(f'added {main_sid, helper_sid} to waiting room because main tail has no points')
        continue
    if (h_cut_index + 1 > helper.index.max()):
        waiting.setdefault(helper_tid, []).append((main_sid, helper_sid))
        print(f'added {main_sid, helper_sid} to waiting room because  helper tail has no points')
        continue

    # --- swap is valid, proceed ---
    # (2a) general split
    main["swap_SwappingHeadTail"] = np.where(
        main.index <= m_cut_index,
        "head_main",
        "tail_main"
    )
    helper["swap_SwappingHeadTail"] = np.where(
        helper.index <= h_cut_index,
        "head_helper",
        "tail_helper"
    ) 
    
    # (2b) split to track swapps
    main["SwappingHeadTail"] = np.where(
        main.index <= m_cut_index,
        f"head_main_{main_sid}",
        f"tail_main_{main_sid}"
    )
    helper["SwappingHeadTail"] = np.where(
        helper.index <= h_cut_index,
        f"head_helper_{helper_sid}",
        f"tail_helper_{helper_sid}"
    ) 

    # (2c) record origin destination for these swaps!
    main_origin_i = m_cut_index
    main_destination_i = h_cut_index+1
    helper_origin_i = h_cut_index
    helper_destination_i = m_cut_index+1
    
    main.loc[main_origin_i, "swap_origin"].append(f'main_{main_sid}_origin')
    main.loc[helper_destination_i, "swap_destination"].append(f'helper_{helper_sid}_destination')
    helper.loc[helper_origin_i, "swap_origin"].append(f'helper_{helper_sid}_origin')
    helper.loc[main_destination_i, "swap_destination"].append(f'main_{main_sid}_destination')

    # need to record row_uid of these instead 
    main_origin_id =  main.at[m_cut_index, "row_uid"] 
    main_destination_id = helper.at[(h_cut_index+1), "row_uid"] 
    helper_origin_id = helper.at[h_cut_index, "row_uid"]
    helper_destination_id = main.at[(m_cut_index+1), "row_uid"]  

    od_dict[main_origin_id].append(main_destination_id)
    od_dict[helper_origin_id].append(helper_destination_id)

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

    # (4) MUST UPDATE TID IN RECORDS
    # drop these from the master df
    t_forSwapping_r = t_forSwapping_r[~t_forSwapping_r['row_uid'].isin(swapped_df['row_uid'])]
    # concat updated attributes of these points
    t_forSwapping_r = pd.concat([t_forSwapping_r, swapped_df], ignore_index=True)

    # MUST UPDATE ALL KEY-VALUES in DICTONARY --> overwrite dictonary
    point_to_tid_dict = dict(zip(t_forSwapping_r['row_uid'],
                   t_forSwapping_r['new_tid_subid'])) # tid_subid assignments change after swapping!


    # (5) update progress bar
    pbar.update(1)

pbar.close()

