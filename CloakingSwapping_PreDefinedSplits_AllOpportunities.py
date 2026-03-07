#%% filled traj - baseline
import geopandas as gpd
import numpy as np

t = gpd.read_parquet(r"d:\paper3\Data\trajectories\traj_filled_baseline_ShiftedTimestamps_gapAware_CloakingGeomID_AllCloakingAreas_clean.parquet")
t.drop(['tid_subid_after_swap', 'swap_pair_id', 'head_end_flag', 'tail_start_flag', 'tid_subid_orig'], axis=1, inplace=True)
t['CloakingGapSwap'] = np.where(t['row_uid'].isin(valid_assigned_helpers_df.main_row_uid.unique()), True, False)
# Forward fill for each gap_number
for gap_num in t.loc[start_mask, 'gap_number'].unique():
    # Get indices for last_ and first_ with this gap number
    last_idx = t[(start_mask) & (t['gap_number'] == gap_num)].index
    first_idx = t[(stop_mask) & (t['gap_number'] == gap_num)].index
    
    for l_idx, f_idx in zip(last_idx, first_idx):
        # Fill True from last_ to first_ (inclusive or exclusive depending on your needs)
        t.loc[l_idx:f_idx, 'CloakingGapSwap_filled'] = True
t.drop(columns='gap_number', inplace=True)
print(t[t['CloakingGapSwap_filled'] == True]['point_type'].unique()) # raw but they should mainly be synthetic
t[t['CloakingGapSwap_filled'] == True][['point_type', 'gap_label_pair_final_syn_fixed', 'CloakingGapSwap', 'CloakingGapSwap_filled']]

#t_forSwapping = t[~((t['CloakingGapSwap_filled']) & (t['point_type'] == 'synthetic'))].copy()

#%% results along the way
all_candidates = gpd.read_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping/AllSwappingCandidates_cloaking.parquet")
import pandas as pd
main_rows = pd.read_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping/main_rows.parquet")


#%%
print(len(all_candidates)) #23,909,882
print(all_candidates.row_uid.nunique()) #245,681
print(all_candidates.main_row_uid.nunique()) #27,609 - same as number of entries in all_candidates_lists
all_candidates.head() 


#%% apply new restirctions to helper candidate selection
# helper must have at least two points in the cloaking zone
# sort first
all_candidates = all_candidates.sort_values(["main_row_uid", "row_uid"])

# check consecutive differences within group
prev_diff = all_candidates.groupby("main_row_uid")["row_uid"].diff()
next_diff = all_candidates.groupby("main_row_uid")["row_uid"].diff(-1)

# keep rows that are part of a consecutive pair
all_candidates_consecutive = all_candidates[(prev_diff == 1) | (next_diff == -1)]
print(len(all_candidates)) # 23909882
print(len(all_candidates_consecutive)) #22474123
print(len(all_candidates)-len(all_candidates_consecutive))
all_candidates_consecutive.head()

#%% helper must have at least one (raw) point after the cloaking zone

# get this information from the main df
# (a) flag last points first
t_forSwapping = t_forSwapping.sort_values(["tid_subid", "row_uid"])
t_forSwapping["end_of_tid_subid"] = (
    t_forSwapping.groupby("tid_subid")["row_uid"]
    .transform("max")
    .eq(t_forSwapping["row_uid"])
)
print(t_forSwapping["end_of_tid_subid"].value_counts())

end_of_tid_subid_list = t_forSwapping[t_forSwapping["end_of_tid_subid"] == True]['row_uid'].unique()


#%% question to ask: is this point the last point of the tid subid? yes --> cannot be a helper as the tail would (begin) and end in the mix zone
# not only is this point but also "their partner", i.e. the consecutive point before, after
# if there is more than 2 consecutive point, any of the consecutive point pairs could be considered a swapping opporutnity
# when working through swapping opportunities we must ensure that no duplicates are being created...
# flag them as last point first, remove last point, look for consecutive points again

# (b) add flag to helpers
all_candidates_consecutive["end_of_tid_subid"] = (all_candidates_consecutive["row_uid"].isin(end_of_tid_subid_list))
print(all_candidates_consecutive["end_of_tid_subid"].unique())

# (c) remove helpers that are the last point
print(len(all_candidates_consecutive)) # 22474123
all_candidates_consecutive_NotEndingInMixZone = all_candidates_consecutive[all_candidates_consecutive["end_of_tid_subid"] == False]
print(len(all_candidates_consecutive_NotEndingInMixZone), 'after removing points ending in mix-zone') # 22447442

# (d) ensure there is two points within the mix zones
# repeat this
all_candidates_consecutive_NotEndingInMixZone = all_candidates_consecutive_NotEndingInMixZone.sort_values(["main_row_uid", "row_uid"])

# check consecutive differences within group
prev_diff = all_candidates_consecutive_NotEndingInMixZone.groupby("main_row_uid")["row_uid"].diff()
next_diff = all_candidates_consecutive_NotEndingInMixZone.groupby("main_row_uid")["row_uid"].diff(-1)

# keep rows that are part of a consecutive pair
all_candidates_consecutive_NotEndingInMixZone = all_candidates_consecutive_NotEndingInMixZone[(prev_diff == 1) | (next_diff == -1)]
print(len(all_candidates_consecutive_NotEndingInMixZone)) #22443170
print(all_candidates_consecutive_NotEndingInMixZone.main_row_uid.nunique()) # for 26,723 cloaking gaps
all_candidates_consecutive_NotEndingInMixZone.head()


#%% do I have to take care of overlapping cloaking geometries or has this been pre-filtered already?



#%% previous helper selection approach
#%%
all_candidates_consecutive_NotEndingInMixZone.groupby('clkpassed')['tid_subid'].nunique().describe()
#count     173.000000
#mean      133.728324
#std       221.206079
#min         1.000000
#25%         9.000000
#50%        45.000000
#75%       161.000000
#max      1396.000000

#%% frequency of tid by clk area - dropping duplicate cklpassed tid pairs --> one count per trajectory and cloaking are
all_candidates_consecutive_NotEndingInMixZone[['clkpassed','tid_subid']].drop_duplicates() \
    .groupby('clkpassed').size().sort_values().head(20)

#%%
print(len(all_candidates_consecutive_NotEndingInMixZone)) # 22443170 valid swap points points
print(all_candidates_consecutive_NotEndingInMixZone.main_row_uid.nunique()) #for 26723 cloaking gaps

all_candidates_consecutive_NotEndingInMixZone.groupby('main_row_uid')['row_uid'] \
    .nunique() \
    .agg(['min', 'median', 'max'])
#min           2.0
#median       96.0
#max       20587.0

#%%
group_stats = (
    all_candidates_consecutive_NotEndingInMixZone
    .groupby('main_row_uid')
    .agg(
        n_row_uid=('row_uid', 'nunique'),
        n_tid_subid=('tid_subid', 'nunique')
    )
)

print(group_stats.agg(['min', 'median', 'max']))
#        n_row_uid  n_tid_subid
#min           2.0          1.0
#median       96.0         17.0 # on average 96 points to swap with, from 17 tid. i.e., 17 chances that the tid is not the same as the current tid 
# if tid is the same - try other point, then move main to waiting room
#max       20587.0        608.0

group_stats
#%%

#%% (2) count options per main_row
main_supply = (
    all_candidates_consecutive_NotEndingInMixZone
    .groupby('main_row_uid')['tid_subid'] # by tid or point pair?
    # tid is dynamic (nature of swapping)
    # therefore the prioritiy of working through swaps should be based on number of points
    # one tid can be used as a helper for many sensitive trajectories
    # BUT we do want a balanced used of helper trajectories
    .nunique()
    .rename('n_helper_traj')
)
main_supply

#%% (3) sort mains by scarcity (hardest first) <-- this idea still applies because I want tid use to be balanced
# i.e., do not keep reusing one helper tid if there is other options that have not participated in swapping yet
# increased variability? like a gene mix
main_order = (
    main_supply
    .sort_values()          # fewest options first
    .index
)
print(len(main_order)) #26723, same as before, good
main_order[0] # 4374923 = main with only ONE possible helper trajectory 

#%% swapping approach
# main_order (list): optimised-order in which we try and swap cloaking gaps
# (dictionary): swapping opportunities at cloaking gap
helper_pool = all_candidates_consecutive_NotEndingInMixZone[['main_row_uid','row_uid']].sort_values(['main_row_uid','row_uid'])
helper_pool_dict = {}

for main_id, g in helper_pool.groupby("main_row_uid"):
    rows = g["row_uid"].values
    pairs = [(rows[i], rows[i+1]) for i in range(len(rows)-1) if rows[i+1] - rows[i] == 1]
    if pairs:
        helper_pool_dict[main_id] = pairs
# how many pairs does each cloaking gap have:
print({k: len(v) for k,v in helper_pool_dict.items()})

# can I order these by main_order? - don't need main_order anymore
helper_pool_dict_ordered = {k: helper_pool_dict[k] for k in main_order if k in helper_pool_dict}
helper_pool_dict_ordered

# then pick a random pair during swapping
#import random
#random_pair = random.choice(pair_dict[131])

# export these all
import pickle
# don't actually needed anymore
with open(r"D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\preDefinedSwappingPairs_all/main_order.pkl", "wb") as f:
    pickle.dump(main_order, f)

# the swapping partner lookup! - will pikc one of the paints randomly per clk gap
with open(r"D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\preDefinedSwappingPairs_all/helper_pool_dict_ordered.pkl", "wb") as f:
    pickle.dump(helper_pool_dict_ordered, f)

# again, dont need this, exporting just in case
all_candidates_consecutive_NotEndingInMixZone.to_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\preDefinedSwappingPairs_all/all_candidates_consecutive_NotEndingInMixZone.parquet")




#%% fill clk gaps without swapping partner
clk_gaps_forSwapping = all_candidates_consecutive_NotEndingInMixZone.main_row_uid.unique()# these are the ones we have a sappwing partner for
print(len(clk_gaps_forSwapping)) #26,723







#%%but t has more clk gaps (30k ishh)
# must ensure only synthetic points from ckl gaps eligible for swapping are removed
t = gpd.read_parquet(r"d:\paper3\Data\trajectories\traj_filled_baseline_ShiftedTimestamps_gapAware_CloakingGeomID_AllCloakingAreas_clean.parquet")
# columns for cloaking based swapping
# intersecting_cloaking_ids - cloaking areas passing only
# HeadEndCloakingAreaId - upcoming cloaking area
# HeadTail - point to split tid before cloaking area
# then delete all syntithic points until first raw point
# this is the first point of the tail

# it's actually better to have empty list rather than nan
import numpy as np
t['intersecting_cloaking_ids'] = t['intersecting_cloaking_ids'].apply(
    lambda x: list(x) if isinstance(x, (list, np.ndarray)) else []
)

t.head()
#%%
print(t.tid_subid.nunique()) # 19,189 trajectories
t.HeadEndCloakingAreaId.value_counts().sum() #31,272

#%% flag trajectory ids that have been cloaked
tids_to_swap = t.loc[t['HeadEndCloakingAreaId'].notna(), 'tid_subid'].unique()
print(f"mumber of tid_subid requiring swapping: {len(tids_to_swap)}")       # 11,791
print(f"number of tid_subids in sample (total): {t.tid_subid.nunique()}")   # 19,189

#%% remove synthetic points for cloaking gaps that will experience a gap (to make code below less complex)
t['CloakingGapSwap'] = np.where(t['row_uid'].isin(all_candidates_consecutive_NotEndingInMixZone.main_row_uid.unique()), True, False)
t['CloakingGapSwap'].value_counts()
#CloakingGapSwap
#False    7308218
#True       26723 - same number as main_rows identified, good!

#%% identify cloaking gaps aka mark synthetic points in cloaking gaps
t['gap_number'] = t['gap_label_pair_final_syn_fixed'].str.extract(r'(?:last_|first_)(\d+)')[0]
start_mask = t['gap_label_pair_final_syn_fixed'].str.startswith('last_', na=False) & t['CloakingGapSwap']
stop_mask = t['gap_label_pair_final_syn_fixed'].str.startswith('first_', na=False)
t['CloakingGapSwap_filled'] = False

# forward fill for each gap_number
for gap_num in t.loc[start_mask, 'gap_number'].unique():
    # get indices for last_ and first_ with this gap number
    last_idx = t[(start_mask) & (t['gap_number'] == gap_num)].index
    first_idx = t[(stop_mask) & (t['gap_number'] == gap_num)].index
    
    for l_idx, f_idx in zip(last_idx, first_idx):
        # fill True from last_ to first_ (inclusive or exclusive depending on your needs)
        t.loc[l_idx:f_idx, 'CloakingGapSwap_filled'] = True

#t.drop(columns='gap_number', inplace=True)

print(t[t['CloakingGapSwap_filled'] == True]['point_type'].unique()) # raw but they should mainly be synthetic
t[t['CloakingGapSwap_filled'] == True][['point_type', 'gap_label_pair_final_syn_fixed', 'CloakingGapSwap', 'CloakingGapSwap_filled']]
t.head()
#%%
t['CloakingGapSwap_filled'].value_counts()
#CloakingGapSwap_filled
#False    7325551
#True        9390 - number of points affected, not number of gaps (but it's less points than gaps...)

#%% drop CloakingGapSwap True from df as these gaps should not be filled
# but 'last' and 'first' are raw points and must remain, can only remove points where
# t['CloakingGapSwap_filled'] is True AND t['point_type'] is 'synthetic' 
# Create a new DataFrame without the filled synthetic rows
t_forSwapping2 = t[~((t['CloakingGapSwap_filled']) & (t['point_type'] == 'synthetic'))].copy()

# Optional: check counts
print(t_forSwapping.row_uid.nunique())
print(t_forSwapping2.row_uid.nunique())
print("Original rows:", len(t))
print("Rows after dropping selected synthetic filled:", len(t_forSwapping2))
print(t_forSwapping2['point_type'].value_counts())
#Original rows: 7334941
#Rows after dropping selected synthetic filled: 7331578
#point_type
#raw          6811202
#synthetic     520376

# updated results
#7331578
#7326733
#Original rows: 7334941
#Rows after dropping selected synthetic filled: 7326733
#point_type
#raw          6811202
#synthetic     515531

t_forSwapping2['CloakingGapSwap'].value_counts()
#CloakingGapSwap
#False    7300010
#True       26723 - looking good

#%%
t_forSwapping2.to_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping/t_forSwapping_26723gaps.parquet")









#%% run swapping
import geopandas as gpd
import pickle

# load data back in
t_forSwapping = gpd.read_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping/t_forSwapping_26723gaps.parquet")

with open(r"D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\preDefinedSwappingPairs_all/helper_pool_dict_ordered.pkl", "rb") as f:
    helper_pool_dict_ordered = pickle.load(f)


#%% update swapping logic - helper has bot split points defined already
# pick a random swapping point from the key - if its invalid try the next one
# then waiting room approach

#%% RUN SWAPPING - we must pick from have a pre-defined helper tail start
# clk gaps are sorted in order of priority (less swapping options (by tid) will be processed first)

# prep data gdf
import numpy as np
import pandas as pd
import random

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
point_to_tid_dict = dict(zip(t_forSwapping_r['row_uid'],
                   t_forSwapping_r['new_tid_subid'])) # tid_subid assignments change after swapping! must be updated within for loop

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

while swap_queue:
    # (0) get splitting points
    main_sid, helper_sid_list = swap_queue.popleft()
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
    #while h_tid_attempts:
    #    helper_sid_r = random.choice(h_tid_attempts)
        # stores the helper head end point and the helper tail start point as a tuple
    #    h_head_end, h_tail_start = helper_sid_r 

        # IMPORTANT: (1st) the helper pair itself must still be valid after participating in previous swaps
    #    if point_to_tid_dict[h_head_end] != point_to_tid_dict[h_tail_start]:
    #        h_tid_attempts.remove(helper_sid_r)
    #        print('helper pair does not have the same tid anymore')
    #        continue

    #    # (2nd) the tid of the helper must be different to the tid of the main
    #    helper_tid = point_to_tid_dict[h_head_end] # we know now that tid of heand and tail are the same
    #    if helper_tid != main_tid:
    #        success_tid = True
    #        print('helper and main have the same tid')
    #        break # exit the while loop
    #    else:
            # remove this option and try another
    #        print('looking for another helper')
    #        h_tid_attempts.remove(helper_sid_r)
    
    # alternative helper picking approach: reducing sampling bias by shuffling the list
    random.shuffle(h_tid_attempts)
    for h_head_end, h_tail_start in h_tid_attempts:

        # (1) helper pair must still belong to the same trajectory
        if point_to_tid_dict[h_head_end] != point_to_tid_dict[h_tail_start]: # pair invalid → skip
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
        waiting.setdefault(main_tid, []).append((main_sid, random.choice(helper_sid_list)))
        print(f"added {main_sid} to waiting room because all helpers currently have the same tid")
        continue

    

    # (1) isolate the swapping pair from main df
    # (1a) get tid_subid for helper
    helper_tid = point_to_tid_dict[h_head_end] # TID OF POINT WILL CHANGE, we are updating dict at the end of the loop

    # (1b) subset by tid and reset index
    main = t_forSwapping_r[t_forSwapping_r['new_tid_subid'] == main_tid].reset_index(drop=True)
    helper = t_forSwapping_r[t_forSwapping_r['new_tid_subid'] == helper_tid].reset_index(drop=True)

    # (2) split main and helper into heads and tail
    m_cut_index = main.index[main["row_uid"] == main_sid][0]
    h_cut_index_headEnd = helper.index[helper["row_uid"] == h_head_end][0]
    h_cut_index_tailStart = helper.index[helper["row_uid"] == h_tail_start][0]

    # (2a) general split
    main["swap_SwappingHeadTail"] = np.where(main.index <= m_cut_index, "head_main", "tail_main")
    helper["swap_SwappingHeadTail"] = np.where(helper.index <= h_cut_index_headEnd, "head_helper", "tail_helper") 
    
    # (2b) split to track swapps
    main["SwappingHeadTail"] = np.where(main.index <= m_cut_index, f"head_main_{main_sid}", f"tail_main_{main_sid}")
    helper["SwappingHeadTail"] = np.where(helper.index <= h_cut_index_headEnd, f"head_helper_{helper_sid_r}", f"tail_helper_{helper_sid_r}") 

    # (2c) record origin destination for these swaps!
    main_origin_i = m_cut_index
    main_destination_i = h_cut_index_tailStart
    helper_origin_i = h_cut_index_headEnd
    helper_destination_i = m_cut_index+1
    
    main.at[main_origin_i, "swap_origin"].append(f'main_{main_sid}_origin')
    main.at[helper_destination_i, "swap_destination"].append(f'helper_{helper_sid_r}_destination')
    helper.at[helper_origin_i, "swap_origin"].append(f'helper_{helper_sid_r}_origin')
    helper.at[main_destination_i, "swap_destination"].append(f'main_{main_sid}_destination')

    # need to record row_uid of these instead 
    main_origin_id =  main.at[m_cut_index, "row_uid"] 
    main_destination_id = helper.at[(h_cut_index_tailStart), "row_uid"] 
    helper_origin_id = helper.at[h_cut_index_headEnd, "row_uid"]
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
    # record swapping history
    for row_uid, new_tid in zip(swapped_df["row_uid"], swapped_df["new_tid_subid"]):
        if not swap_history[row_uid] or swap_history[row_uid][-1] != new_tid:
            swap_history[row_uid].append(new_tid)

    # (4) MUST UPDATE TID IN RECORDS
    # drop these from the master df
    t_forSwapping_r = t_forSwapping_r[~t_forSwapping_r['row_uid'].isin(swapped_df['row_uid'])]
    # concat updated attributes of these points
    t_forSwapping_r = pd.concat([t_forSwapping_r, swapped_df], ignore_index=True)

    # MUST UPDATE ALL KEY-VALUES in DICTONARY --> overwrite dictonary
    point_to_tid_dict = dict(zip(t_forSwapping_r['row_uid'],
                   t_forSwapping_r['new_tid_subid'])) # tid_subid assignments change after swapping!

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

#%% swapping historys as a df
#swap_hist_df = (
#    pd.DataFrame(
#        [(k, v) for k, vals in swap_history.items() for v in vals],
#        columns=["row_uid", "tid_history"]
#    )
#)
############################
# AFTER: have all gaps been swapped? if not, add syn points back in

# (d) connect the swapped trajectories (ie main and tail via synthetic points)
# (d.1) calculate shortest path (clauclate desc statistics)
# (d.2) interpolate syn points based on speed lookup and downsample

# (e) evaluate cloaking based swapping