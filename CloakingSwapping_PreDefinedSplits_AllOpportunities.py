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

#%% restart the while loop after crash!
pbar = tqdm(total=len(swap_queue), desc="Processing swaps (resume)") # 11719 left in swap_que, 5458 left in 3rd run
while swap_queue:
    # (0) get splitting points
    main_sid, helper_sid_list = swap_queue.popleft()
    # normalise to list first (incase waiting room strutcure is meesed up)
    if isinstance(helper_sid_list, tuple):
        helper_sid_list = [helper_sid_list]

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

    for h_head_end, h_tail_start in h_tid_attempts:

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
        # must be a list!
        waiting.setdefault(main_tid, []).append((main_sid, [random.choice(helper_sid_list)]))
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
    # is len(main) correct?
    if helper_destination_i < len(main): # only attach main tail to helper head if main has a tail
        main.at[helper_destination_i, "swap_destination"].append(f'helper_{h_head_end}_destination')
    helper.at[helper_origin_i, "swap_origin"].append(f'helper_{h_head_end}_origin')
    helper.at[main_destination_i, "swap_destination"].append(f'main_{main_sid}_destination')

    # need to record row_uid of these instead 
    # dict should be finde because it is based on point ids!
    main_origin_id =  main.at[m_cut_index, "row_uid"] 
    main_destination_id = helper.at[(h_cut_index_tailStart), "row_uid"] 
    helper_origin_id = helper.at[h_cut_index_headEnd, "row_uid"]
    # only attach a helper destination id if main has a tail, it is ok for helper to end in clk area
    if helper_destination_i < len(main):
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

#%% broke at 32%
#8482/26723 [14:29:36<32:50:31,  6.48s/it]

#--------------------------------------------------------------------------
#ValueError                                Traceback (most recent call last)
#File c:\Users\Maike\miniconda3\envs\trajectories\Lib\site-packages\pandas\core\indexes\range.py:413, in RangeIndex.get_loc(self, key)
#    412 try:
#--> 413     return self._range.index(new_key)
#    414 except ValueError as err:

#ValueError: 58 is not in range

#The above exception was the direct cause of the following exception:

#KeyError                                  Traceback (most recent call last)
#Cell In[47], line 140
#    137 helper_destination_i = m_cut_index+1
#    139 main.at[main_origin_i, "swap_origin"].append(f'main_{main_sid}_origin')
#--> 140 main.at[helper_destination_i, "swap_destination"].append(f'helper_{helper_sid_r}_destination')
#    141 helper.at[helper_origin_i, "swap_origin"].append(f'helper_{helper_sid_r}_origin')
#    142 helper.at[main_destination_i, "swap_destination"].append(f'main_{main_sid}_destination')

#File c:\Users\Maike\miniconda3\envs\trajectories\Lib\site-packages\pandas\core\indexing.py:2575, in _AtIndexer.__getitem__(self, key)
#   2572         raise ValueError("Invalid call for scalar access (getting)!")
#   2573     return self.obj.loc[key]
#-> 2575 return super().__getitem__(key)

#File c:\Users\Maike\miniconda3\envs\trajectories\Lib\site-packages\pandas\core\indexing.py:2527, in _ScalarAccessIndexer.__getitem__(self, key)
#...
#--> 415         raise KeyError(key) from err
#    416 if isinstance(key, Hashable):
#    417     raise KeyError(key)

# KeyError: 58

#%% can I still use the 32% that were processed or is this error fundamental?
#these are the updated versions of my dfs and dict after the KeyError 58
# dfs
t_forSwapping_r["swap_SwappingHeadTail"] = t_forSwapping_r["swap_SwappingHeadTail"].astype("string")
t_forSwapping_r["SwappingHeadTail"] = t_forSwapping_r["SwappingHeadTail"].astype("string")
t_forSwapping_r.to_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\PredefinedSplitsAllOpportunities\8482OutOf26723ClkGpsProcessed/ClkGpsSwappedT.parquet")

#%% dictionaries
with open(r"D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\PredefinedSplitsAllOpportunities\8482OutOf26723ClkGpsProcessed/waiting.pkl", "wb") as f:
    pickle.dump(waiting, f)
#<-- do I know which ones have been processed?
with open(r"D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\PredefinedSplitsAllOpportunities\8482OutOf26723ClkGpsProcessed/swap_queue.pkl", "wb") as f:
    pickle.dump(swap_queue, f)
with open(r"D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\PredefinedSplitsAllOpportunities\8482OutOf26723ClkGpsProcessed/point_to_tid_dict.pkl", "wb") as f:
    pickle.dump(point_to_tid_dict, f)
# od dict should be finde because it is based on point ids!
with open(r"D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\PredefinedSplitsAllOpportunities\8482OutOf26723ClkGpsProcessed/od_dict.pkl", "wb") as f:
    pickle.dump(od_dict, f)

#%%
print(len(swap_queue)+8482) # 20201 and not 26723 
print(len(swap_queue)+8482+len(waiting)) # 24076 - also I thouight waiting was aded back to swap queque
#   if retry_counts[pair] < max_retries:
#                    swap_queue.append(pair)   # re-add to the queue
#%% find the missing ~2647
queued_sids = {sid for sid, _ in swap_queue}
waiting_sids = {sid for pairs in waiting.values() for sid, _ in pairs}
processed_sids = set(od_dict.keys())   # main origins that already swapped

all_sids = set(helper_pool_dict_ordered.keys())
missing_sids = all_sids - queued_sids - waiting_sids - processed_sids
print(len(missing_sids))   # always 0, shouldn't be 0

#%% the problematic swap
main
helper
swapped_df

main_origin_id
main_destination_id
helper_origin_id
helper_destination_id

success_tid

main_sid # 3996491 the last point before the main clk gap which does not not have another point in that tid (after swapping?)
main_tid #'20200511_42b6a40c0c9fa6f4eb636e84f13447946c2f4943_5793'
# 3051681
# '20200314_19a6a0f68c2542f7f1bc44a7db86d0d4da93ddb9_5116' for the second crash
helper_tid
helper_sid_list

#%% second bug
#helper_sid_r - does not seem to be defined, but I am assigning it to a column and id didn't throw and error message?
# (3958746, 3958747) - have they all been assigned the same one? then this is not useful for tracking
print(t_forSwapping_r.SwappingHeadTail.unique())
# yes, all helper (tail or head) are  'tail_helper_(3958746, 3958747)', 'head_helper_(3958746, 3958747)',
# invalid
mask = t_forSwapping_r["SwappingHeadTail"].astype(str).str.contains("helper_\\(")
t_forSwapping_r.loc[mask, "SwappingHeadTail"] = "invalid label"
print(t_forSwapping_r.SwappingHeadTail.unique())

t_forSwapping_r.to_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\PredefinedSplitsAllOpportunities\8482OutOf26723ClkGpsProcessed/ClkGpsSwappedT.parquet")

#%% 2nd error message  7804/11719 [15:08:36<7:27:11,  6.85s/it]

#---------------------------------------------------------------------------
#AttributeError                            Traceback (most recent call last)
#Cell In[77], line 16
#      9 success_tid = False
#     11 # find helper tid with a different tid
#     12 # (point_to_tid_dict always represents the current tid state, 
#     13 # compability of original tid has been validated during pre-processing)
#     14 # helper_sid is stored as a pair (tuple) in a list
#     15 # pick a random swapping pair
#---> 16 h_tid_attempts = helper_sid_list.copy()
#     17 # reducing sampling bias by shuffling the list of helper pairs first
#     18 random.shuffle(h_tid_attempts)

#AttributeError: 'tuple' object has no attribute 'copy'



# helper_sid_list is not a list, it's a tuple (2537673, 2537674)
# this is the case when only one pair is a suitable swapping candidate rather than having multiple options
# assigning (main_sid, helper_pair) rather than (main_sid, helper_sid_list) back to swap que
# or the waiting room fall back cuasing (main_sid, (h_head, h_tail))

#%%
print(len(swap_queue)) #5458



#%%
#t_forSwapping_r["swap_SwappingHeadTail"] = t_forSwapping_r["swap_SwappingHeadTail"].astype("string")
#t_forSwapping_r["SwappingHeadTail"] = t_forSwapping_r["SwappingHeadTail"].astype("string")
t_forSwapping_r.to_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\PredefinedSplitsAllOpportunities\8482OutOf26723ClkGpsProcessed/ClkGpsSwappedT_2ndCrash.parquet")

#%% dictionaries
with open(r"D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\PredefinedSplitsAllOpportunities\8482OutOf26723ClkGpsProcessed/waiting_2ndCrash.pkl", "wb") as f:
    pickle.dump(waiting, f)
#<-- do I know which ones have been processed?
with open(r"D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\PredefinedSplitsAllOpportunities\8482OutOf26723ClkGpsProcessed/swap_queue_2ndCrash.pkl", "wb") as f:
    pickle.dump(swap_queue, f)
with open(r"D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\PredefinedSplitsAllOpportunities\8482OutOf26723ClkGpsProcessed/point_to_tid_dict_2ndCrash.pkl", "wb") as f:
    pickle.dump(point_to_tid_dict, f)
# od dict should be finde because it is based on point ids!
with open(r"D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\PredefinedSplitsAllOpportunities\8482OutOf26723ClkGpsProcessed/od_dict_2ndCrash.pkl", "wb") as f:
    pickle.dump(od_dict, f)




#%% after resuming the loop - 0/5458
print(len(swap_queue)) # now 0, meaning non of the remaining swaps were succesfull
# I do think the remaining swaps came from the waiting room
# waiting is still 6010 long
print(len(waiting))
# loop ends with waiting still containing items
# waiting was not re-rtiggered because their new tid has not changed

 
# remaining swaps must have failed because main_tid == helper_tid
# or helpers became invalid after ealier swaps...
# swaps can invalidate future swaps
print("waiting trajectories:", len(waiting)) #6010
print("waiting swap pairs:", sum(len(v) for v in waiting.values())) #10435


#%% run swapping again on waiting room
# estimate potentallly succesful swaps
# %%
invalid_pair = 0
same_tid = 0
valid = 0

for pairs in waiting.values():
    for main_sid, helper_list in pairs:

        main_tid = point_to_tid_dict.get(main_sid)

        if isinstance(helper_list, tuple):
            helper_list = [helper_list]

        if not isinstance(helper_list, list):
            continue

        for pair in helper_list:

            if not isinstance(pair, tuple):
                continue

            h_head, h_tail = pair

            if point_to_tid_dict[h_head] != point_to_tid_dict[h_tail]:
                invalid_pair += 1
            elif point_to_tid_dict[h_head] == main_tid:
                same_tid += 1
            else:
                valid += 1

print("invalid helper pair:", invalid_pair)
print("same tid as main:", same_tid)
print("still valid:", valid)

# waiting tids are stored by main_tid but main_tid changes...
#invalid helper pair: 10434 --> helper tid is not the same for head and tail
#same tid as main: 0
#still valid: 1

#%%
# %%
total_helpers = 0
broken_helpers = 0

for pairs in waiting.values():
    for main_sid, helper_list in pairs:

        if isinstance(helper_list, tuple):
            helper_list = [helper_list]

        for pair in helper_list:

            if not isinstance(pair, tuple):
                continue

            h_head, h_tail = pair
            total_helpers += 1

            if point_to_tid_dict[h_head] != point_to_tid_dict[h_tail]:
                broken_helpers += 1

print("helper survival rate:", (total_helpers - broken_helpers) / total_helpers)
#helper survival rate: 9.583133684714902e-05 --> >99.99% of helpers become invalid

#%% export what I have, look for uncovered clk gaps, try swapping again/see if their original desitnation is still there
t_forSwapping_r.to_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\PredefinedSplitsAllOpportunities\8482OutOf26723ClkGpsProcessed/ClkGpsSwappedT_final.parquet")

#%% dictionaries
with open(r"D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\PredefinedSplitsAllOpportunities\8482OutOf26723ClkGpsProcessed/waiting_final.pkl", "wb") as f:
    pickle.dump(waiting, f)

with open(r"D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\PredefinedSplitsAllOpportunities\8482OutOf26723ClkGpsProcessed/point_to_tid_dict_final.pkl", "wb") as f:
    pickle.dump(point_to_tid_dict, f)
# od dict should be finde because it is based on point ids!
with open(r"D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\PredefinedSplitsAllOpportunities\8482OutOf26723ClkGpsProcessed/od_dict_final.pkl", "wb") as f:
    pickle.dump(od_dict, f)

#%% export swapping history
with open(r"D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\PredefinedSplitsAllOpportunities\8482OutOf26723ClkGpsProcessed/swap_history_final.pkl", "wb") as f:
    pickle.dump(swap_history, f)
#%% swapping historys as a df
swap_hist_df = (
    pd.DataFrame(
        [(k, v) for k, vals in swap_history.items() for v in vals],
        columns=["row_uid", "tid_history"]
    )
)
swap_hist_df.to_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\PredefinedSplitsAllOpportunities\8482OutOf26723ClkGpsProcessed/swap_hist_df_final.parquet")
swap_hist_df.head()
# row_uid is the point of interest
# tid_history should be all assigned tids in orther
#%%
swap_hist_df.tid_history.unique() # but they all only have one value? not a list

#%%
swap_history # has multiple tids per point, 1971600 for example
#%% look at point 1971600 in df
swap_hist_df[swap_hist_df['row_uid'] == 1971600] # ok, each tid version of the point is stored as its own row
#%%
swap_hist_df_list = pd.DataFrame({
    'row_uid': swap_history.keys(),
    'tid_history': swap_history.values()
})
swap_hist_df_list.head()
#%%
swap_hist_df_list.to_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\PredefinedSplitsAllOpportunities\8482OutOf26723ClkGpsProcessed/swap_hist_df_list.parquet")
swap_hist_df_list[swap_hist_df_list['row_uid'] == 1971600]




############################
#%% AFTER: have all gaps been swapped? if not, add syn points back in
# I don't think they have, but because of swaps adding the previous syn points back in might not be possible either
# adding syn points back only works if first and last point before sensitive location remained within the same tid
# what i would do first: run swapping again on the 'missed' cloaking gaps 

# how do I identify coverage of cloaking gaps 
# maybe I should have ticked them of as "succesfully participated in a swap as main"

# this is a dict of clk gaps (i.e., the last point before the cloaking gap)
#helper_pool_dict_ordered
print(len(helper_pool_dict_ordered)) # 26,723
# we also have the original and new tid,
# before swapping the point before and after had the same tid
# when were row_uid calculated? including or excluding the filled syn traj
# must identify "tail" start of clk gap before swapping, then comapre tid of that point to after swapping

# change in point_to_tid_dict before and after swapping?
# could also be a df with columns: point after clkg gap, orig tid, new tid
# --> find point after clk gap
# before swapping
#t_forSwapping # HeadEndCloakingAreaId gives the cloaking area after
# t_forSwapping.CloakingGapSwap.unique() is True or False
# print(t_forSwapping.CloakingGapSwap_filled.unique()) # also True or False
#t_forSwapping.CloakingGapSwap_filled.value_counts() 
#CloakingGapSwap_filled
#False    7325551
#True        1182
# t_forSwapping.CloakingGapSwap.value_counts()
#CloakingGapSwap
#False    7300010
#True       26723 # as expected

#t_forSwapping.gap_number.value_counts().reset_index()['count'].min() # min is 2
# does gap_number identify cloaking gaps within a trajectory, i.e., point before and after?

# unique clk gap number by tid
t_forSwapping['tid_gap_number'] = np.where(
    t_forSwapping['gap_number'].notna(),
    t_forSwapping['gap_number'].astype(str) + "_" + t_forSwapping['tid_subid'].astype(str),
    None
)
#%% keys of clk gaps
clk_gaps_keys = list(helper_pool_dict_ordered.keys())
clk_gaps_keys = [int(k) for k in clk_gaps_keys]
set(type(k) for k in clk_gaps_keys)
#%% flag the ones that are in helper_pool_dict_ordered
t_forSwapping['is_clk_gap_key'] = np.where(
    t_forSwapping['row_uid'].isin(clk_gaps_keys),
    True,
    False
)
print(t_forSwapping['is_clk_gap_key'].unique())
t_forSwapping.head()
#%% should be the same as CloakingGapSwap
print(t_forSwapping.CloakingGapSwap.value_counts())
#CloakingGapSwap
#False    7300010
#True       26723

print(t_forSwapping.is_clk_gap_key.value_counts())
#is_clk_gap_key
#False    7300010
#True       26723

(t_forSwapping.CloakingGapSwap == t_forSwapping.is_clk_gap_key).any() # true, good

#%%
t_forSwapping[t_forSwapping.tid_gap_number.notna()][['row_uid', 'is_clk_gap_key', 'tid_gap_number']]

#%% 62590 rows, that is more than double of the 27k cloaking gaps i processed
tid_swapclkgap_number_list = t_forSwapping[t_forSwapping['is_clk_gap_key'] == True].tid_gap_number.unique() #26723 
print(len(tid_swapclkgap_number_list)) #26723

tid_swapclkgap_ptids = t_forSwapping[t_forSwapping['tid_gap_number'].isin(tid_swapclkgap_number_list)]
tid_swapclkgap_ptids[['row_uid', 'is_clk_gap_key', 'tid_gap_number']] # 53411 long, 53411 /2 = 26705.5 - doesn't quite equal out
#%%
tid_swapclkgap_ptids =  tid_swapclkgap_ptids[['row_uid', 'tid_subid','is_clk_gap_key', 'tid_gap_number', 'HeadEndCloakingAreaId', 'HeadTail']].copy()
#%%
tid_swapclkgap_ptids_counts = tid_swapclkgap_ptids.tid_gap_number.value_counts().reset_index() # some only appear once 
print(len(tid_swapclkgap_ptids_counts)) # 26723, good - all input clk gaps covered
print(tid_swapclkgap_ptids_counts['count'].min()) #1
print(tid_swapclkgap_ptids_counts['count'].median()) #2
print(tid_swapclkgap_ptids_counts['count'].max()) #2

# look at the ones with 1, does that mean they have no tail? i.e., all tid_gap_number with count 1 have is_clk_gap_key True
tid_swapclkgap_ptids[tid_swapclkgap_ptids['tid_gap_number'].isin(tid_swapclkgap_ptids_counts[tid_swapclkgap_ptids_counts['count']==1].tid_gap_number.unique())]
# 35
# (53411 -35)/2 is 26688 and 26688+35 is 26723 - all ckl gaps are covered

# as expected, they are all True. good.
# how do I figure out if they have been swapped? 
# see if they have a tid point afterwards

#%% add flag to clk gaps without destination
tid_swapclkgap_ptids['clkgap_noDestination'] = tid_swapclkgap_ptids['tid_gap_number'].isin(tid_swapclkgap_ptids_counts.query('count == 1')['tid_gap_number'])
tid_swapclkgap_ptids.clkgap_noDestination.value_counts()
#clkgap_noDestination
#False    53376
#True        35 - good

# must look at this
# how do I figure out if they have been swapped? 
# see if they have a tid point afterwards

#%% label origin destination of clk gap
tid_swapclkgap_ptids['od'] = np.where(
    tid_swapclkgap_ptids['is_clk_gap_key'] == True,
    "o_"+tid_swapclkgap_ptids["tid_gap_number"],
    "d_"+tid_swapclkgap_ptids["tid_gap_number"]
)
tid_swapclkgap_ptids

#%% figure out whether the main of a clkg gap has been swapped or not
# logic
# tid_subid of the detintaion point, i.e. clk_gap_key has changed
# the 35 that do not have a tail, do they have a consecutive point in the updated df?

# after swapping
# t_forSwapping_r
# interested in point id and new_tid_subid
tid_swapclkgap_ptids = tid_swapclkgap_ptids.merge(t_forSwapping_r[['row_uid', 'new_tid_subid', 'swap_n']], on = "row_uid", how="left")
tid_swapclkgap_ptids['tid_changed'] = (tid_swapclkgap_ptids['tid_subid'] != tid_swapclkgap_ptids['new_tid_subid'])
tid_swapclkgap_ptids # tid_changed is False but swap_n is not 0 - hows that possible...
# swap_n != 0 but tid_subid != new_tid_subid

# biggest indicator that clk is covered by swapping: tid of origin has changed, aka tid_changed True
# tid_changed False is ok for origins, as long as the destination is True

# if both, origin and destination are False, AND swap_n is 0, then the clk is not coevred bt swapping
# and can be filled with the previously generated synthetic trajectories, as od has not changed

#%% could also check if those points have a history
swap_history
# or look at the ones still in the waiting room!
#%%
print(len(tid_swapclkgap_ptids[tid_swapclkgap_ptids['swap_n']==0])) # 8497 rows
tid_swapclkgap_ptids[tid_swapclkgap_ptids['swap_n']==0].tid_changed.unique() # all False

# is  this the same number that is missing from all the processed gaps
#8497

#%% progressbar status before breaking
#8482/26723 [14:29:36<32:50:31,  6.48s/it]
#11719 left in swap_que

#2nd error message  7804/11719 [15:08:36<7:27:11,  6.85s/it]
#5458 left in  swap_que after 2nd run (initial run, 2nd run)

# succesful swaps at clk gaps
n_clkgaps_success = 8482 + 7804 # 16286 out of 26723 
print(n_clkgaps_success)
# round(n_clkgaps_success / 26723 * 100) # 61%
26723-n_clkgaps_success # 10437 - exactly the value I got from waiting before?

print("waiting trajectories:", len(waiting)) #6010 - this is the number of tid in waiting, beacue tid are the key
# we are "waiting" for this tid to change to triger looking at those clkg gaps again

print("waiting swap pairs:", sum(len(v) for v in waiting.values())) #10435, len(v) is the  number of swap pairs waiting for that trajectory
# for example
# '20191123_6de38e429e314e246d7914531e45f7e32864a863_2564': [
# (501108, (1171474, 1171475)),
#  (499819, (6628334, 6628335)),
#  (500118, (4883160, 4883161))],
# tid 20191123_6de38e429e314e246d7914531e45f7e32864a863_2564 has three cloaking gaps: 501108, 499819, and 500118
# gives us the
# but is missing 2/ or we have identified 2 above that have actually been swapped.
# not quite the same as 26723-n_clkgaps_success, 2 are not in waiting

#%% get clk gap keys from waiting (waiting key is tid)
keys_from_waiting = {
    tid
    for v in waiting.values()
    for tid, _ in v
}
keys_from_waiting
#%% rerun swapping on the updated t df for these 10,435 clk gaps!
# update helper_pool_dict_ordered
waiting_helper_pool_dict = {k: helper_pool_dict_ordered[k] for k in keys_from_waiting if k in helper_pool_dict_ordered}
swap_queue = deque(waiting_helper_pool_dict.items())

print(len(swap_queue)) # 10435, as expected
#waiting = {} 

#%% restart the while loop after crash!
pbar = tqdm(total=len(swap_queue), desc="Processing swaps (waiting room run)") 
while swap_queue:
    # (0) get splitting points
    main_sid, helper_sid_list = swap_queue.popleft()
    # normalise to list first (incase waiting room strutcure is meesed up)
    if isinstance(helper_sid_list, tuple):
        helper_sid_list = [helper_sid_list]

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

    for h_head_end, h_tail_start in h_tid_attempts:

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
        # must be a list!
        waiting.setdefault(main_tid, []).append((main_sid, [random.choice(helper_sid_list)]))
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
    if helper_destination_i < len(main): # only attach main tail to helper head if main has a tail
        main.at[helper_destination_i, "swap_destination"].append(f'helper_{h_head_end}_destination')
    helper.at[helper_origin_i, "swap_origin"].append(f'helper_{h_head_end}_origin')
    helper.at[main_destination_i, "swap_destination"].append(f'main_{main_sid}_destination')

    # need to record row_uid of these instead 
    # dict should be finde because it is based on point ids!
    main_origin_id =  main.at[m_cut_index, "row_uid"] 
    main_destination_id = helper.at[(h_cut_index_tailStart), "row_uid"] 
    helper_origin_id = helper.at[h_cut_index_headEnd, "row_uid"]
    # only attach a helper destination id if main has a tail, it is ok for helper to end in clk area
    if helper_destination_i < len(main):
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



#  2/10435 [00:23<30:46:46, - processed two more, than finished
#%% n_clkgaps_success = 8482 + 7804 +2
# but waiting is now messed up, has way too many pairs
# print("waiting swap pairs:", sum(len(v) for v in waiting.values())) #10435, len(v) is the  number of swap pairs waiting for that trajectory
# waiting swap pairs: 20868
# should've reset waiting to {}
keys_from_waiting_before = keys_from_waiting.copy()
print(len(keys_from_waiting_before)) # 10435

#%%
keys_from_waiting = {
    tid
    for v in waiting.values()
    for tid, _ in v
}
print(len(keys_from_waiting)) # 10435 just like before...
keys_from_waiting

#%% ok use these keys_from_waiting to flag clk gaps that where not swapped
tid_swapclkgap_ptids['is_waiting'] = np.where(
    tid_swapclkgap_ptids['row_uid'].isin(keys_from_waiting),
    True,
    False)
tid_swapclkgap_ptids # all destinations will be False is_waiting
#%% must fill is_waiting value of that origin
# what do origin and destination have in common? tid_gap_number
# map HeadEnd values
headend_map = (
    tid_swapclkgap_ptids.loc[tid_swapclkgap_ptids['HeadTail'] == 'HeadEnd']
    .set_index('tid_gap_number')['is_waiting']
)

tid_swapclkgap_ptids['is_waiting_filled'] = tid_swapclkgap_ptids['is_waiting']
mask = tid_swapclkgap_ptids['HeadTail'].isna() | tid_swapclkgap_ptids['HeadTail'].isin(['nan', 'None', None])
tid_swapclkgap_ptids.loc[mask, 'is_waiting_filled'] = (
    tid_swapclkgap_ptids.loc[mask, 'tid_gap_number'].map(headend_map)
)
tid_swapclkgap_ptids # is_waiting_filled is valid for both origin and destination 
#%% (a) MUST ADD SYNTHETIC TRAJECTORIES BACK IN FOR THE UNSWAPPED TRAJECTORIES
print(tid_swapclkgap_ptids.is_clk_gap_key.value_counts())
#True     26723 --> all my clk gap keys
#False    26688 --> the destinations of clk gap. some (35) do not have a destination (26688-26723)

print(tid_swapclkgap_ptids.is_waiting.value_counts())
#False    42976
#True     10435 --> out of the 26723 cloaking gaps, 10435 have not been swapped.

#%%
#%% create a lookup of tid to uid
# Create a lookup from tid_subid to uid from the original df
tid_to_uid = dict(zip(t_forSwapping['tid_subid'], t_forSwapping['uid']))

# Map tid_subid to uid
tid_swapclkgap_ptids['uid_tid'] = tid_swapclkgap_ptids['tid_subid'].map(tid_to_uid)
tid_swapclkgap_ptids['uid_new_tid'] = tid_swapclkgap_ptids['new_tid_subid'].map(tid_to_uid)
tid_swapclkgap_ptids['uid_different'] = tid_swapclkgap_ptids['uid_tid'] != tid_swapclkgap_ptids['uid_new_tid']
print(tid_swapclkgap_ptids['uid_different'].unique())
tid_swapclkgap_ptids.head()

#%%
tid_swapclkgap_ptids['uid_different'].value_counts()
#False    29,571
#True     23,840

#%% split into swapped and undwapped clk gaps
clk_gap_swapped = tid_swapclkgap_ptids[tid_swapclkgap_ptids['is_waiting_filled']==False]
clk_gap_swapped # the False of tid_changed can be explained by the head maintaining the original tid


#%% what if is_waiting_filled is false and tid_changed is false and swap_n is 0, then this clk gap cannot have participated in swapping
clk_gap_swapped[clk_gap_swapped['swap_n']==0] 
# one point that is not in waiting, has experienced 0 swaps, tid has not changed, and it does not have a destination
# this point needs to be classified as 'not swapped'

#%% clk_gap_swapped = not in waiting room, should've technically been processed succesfully
# quality control, not in waiting room but tid has not changed
# which would be to be expected for heads, but not tails
print(clk_gap_swapped[clk_gap_swapped['tid_changed']==False]['is_clk_gap_key'].unique()) # both true and false, i.e., both destination and origin
print(clk_gap_swapped[clk_gap_swapped['tid_changed']==False]['is_clk_gap_key'].value_counts())
# but mostly origin (as expected)
#True     5448
#False      55
clk_gap_swapped[clk_gap_swapped['tid_changed']==False]
# part of processed, only seen as processed if popped from swap queque and being swapped

# trust the process and see them as swapped
#%% real question is whether head and tail tid are the same, becuase they could've just changed as part of being a helper
clk_gap_swapped['new_tid_same'] = clk_gap_swapped.groupby('tid_gap_number')['new_tid_subid'] \
    .transform(lambda x: x.nunique() == 1)
print(clk_gap_swapped['new_tid_same'].value_counts())
# array([False,  True]) - they sould not be 
#False    32446 --> the two rows are different (as expected)
#True       114 --> the two rows are the same_new_tid --> problematic
clk_gap_swapped[clk_gap_swapped['new_tid_same']==True] # some have tid_changed, and different number of swaps
# old tid 20191117_7cf738514ffcb46516c2982ca9abf6b221c17...
# new tid 20200801_7cf738514ffcb46516c2982ca9abf6b221c17...
# that has also very clearly changed within the same user, just another day!

# must conmpare uid before and after

#%% debugging: were helpers correct?
#all_candidates_consecutive_NotEndingInMixZone = gpd.read_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\preDefinedSwappingPairs_all/all_candidates_consecutive_NotEndingInMixZone.parquet")

#helper_pool_dict_ordered # <-- swap_queque
# what this is:
# a dictonary for clk_gap  head end point
# and the split points for helper
# for each key (aka clk_gap head point) the uid of the helper pairs must not have the same uid
# lookup uid, and reconnect 
# assume t_forSwapping_r has columns: 'row_uid' and 'uid'
# helper_pool_dict_ordered: dict where keys = row_uid, values = list of row_uid

# Create a lookup from row_uid to uid from the original df
rowuid_to_uid = dict(zip(t_forSwapping['row_uid'], t_forSwapping['uid']))

rows = []
for main_row_uid, helper_pairs in helper_pool_dict_ordered.items():
    for head, tail in helper_pairs:
        rows.append({
            'main_row_uid': main_row_uid,
            'helper_head_end': head,
            'helper_tail_start': tail
        })

# Create DataFrame
helper_pool_dict_ordered_df = pd.DataFrame(rows)
helper_pool_dict_ordered_df.head()

#%% add uid to all three columns
helper_pool_dict_ordered_df['uid_main'] = helper_pool_dict_ordered_df['main_row_uid'].map(rowuid_to_uid)
helper_pool_dict_ordered_df['uid_helper_end'] = helper_pool_dict_ordered_df['helper_head_end'].map(rowuid_to_uid)
helper_pool_dict_ordered_df['uid_helper_tail_start'] = helper_pool_dict_ordered_df['helper_tail_start'].map(rowuid_to_uid)

helper_pool_dict_ordered_df
#%%
# Add a column that checks if uid_main is different from both helper uids
# Use only Series comparisons
helper_pool_dict_ordered_df['uid_main_unique'] = (
    (helper_pool_dict_ordered_df['uid_main'] != helper_pool_dict_ordered_df['uid_helper_end']) &
    (helper_pool_dict_ordered_df['uid_main'] != helper_pool_dict_ordered_df['uid_helper_tail_start'])
)

helper_pool_dict_ordered_df['uid_main_unique'].unique() # all True, so pre-assignment is not the issue
#%% quality control:
# is every is_waiting_filled (aka both origin and destination point) which is True (aka not swapped)
# also False for tid_changed/ 0 for swap_n
tid_swapclkgap_ptids[tid_swapclkgap_ptids['is_waiting_filled']==True]
# when tid_changed --> must have changed as part of being a helper!
# CANNOT RECONNECT WITH swapped tid


#%%tid_change False an swap_n 1
# priotise tid change over swap count
tid_swapclkgap_ptids[tid_swapclkgap_ptids['row_uid'].isin([12373,12377])]

# not all swap_n are 0
# I think that is because the trajectory acted as a helper somewhere else! 
# which might be WHY we cannot find a valid helper for it's own cloaking gap now
# would it  be good to report the percentage? 


#%%
print(len(swapped_df))
swapped_gdf = t_forSwapping[['row_uid', 'match_geometry']].merge(swapped_df, on='row_uid', how='right')
print(len(swapped_gdf))
swapped_gdf # remember, this is the sapped df, i.e. two new tid_subid
#%%
swapped_gdf.new_tid_subid.unique()
#%%
t_forSwapping_r[t_forSwapping_r['new_tid_subid']=='20200328_a0ac0ba30aa04f38f0dfa6bc8f289fa924f6f543_5432'].to_parquet(r'D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\PredefinedSplitsAllOpportunities\8482OutOf26723ClkGpsProcessed/swapped_df_sample1.parquet')
t_forSwapping_r[t_forSwapping_r['new_tid_subid']=='20201117_42b6a40c0c9fa6f4eb636e84f13447946c2f4943_7294'].to_parquet(r'D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\PredefinedSplitsAllOpportunities\8482OutOf26723ClkGpsProcessed/swapped_df_sample2.parquet')






#%%
with pd.option_context('display.max_rows', None):
    print(swapped_df[swapped_df['new_tid_subid']=='20200328_a0ac0ba30aa04f38f0dfa6bc8f289fa924f6f543_5432'][['row_uid', 'tid_subid', 'new_tid_subid', 'new_tid_subid', 'swap_origin', 'swap_destination','swap_point_id_t']].head(150))

#%%
with pd.option_context('display.max_rows', None):
    print(swapped_df[swapped_df['new_tid_subid']=='20200328_a0ac0ba30aa04f38f0dfa6bc8f289fa924f6f543_5432'][['row_uid', 'tid_subid', 'new_tid_subid', 'new_tid_subid', 'swap_origin', 'swap_destination','swap_point_id_t']].iloc[150:300])
#%%
with pd.option_context('display.max_rows', None):
    print(swapped_df[swapped_df['new_tid_subid']=='20201117_42b6a40c0c9fa6f4eb636e84f13447946c2f4943_7294'][['row_uid', 'tid_subid', 'new_tid_subid', 'new_tid_subid', 'swap_origin', 'swap_destination','swap_point_id_t']])



#%% tracking swaps of last swapped_df
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

#
#%% try swapping again
# reduce df to prevent memory issues
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

# --- define lookup dicts ---
point_to_tid_dict = dict(zip(t_forSwapping_r['row_uid'], t_forSwapping_r['new_tid_subid']))
point_to_uid_dict_swapped = dict(zip(t_forSwapping_r['row_uid'], t_forSwapping_r['new_uid']))
point_to_uid_dict_orig = dict(zip(t_forSwapping_r['row_uid'], t_forSwapping_r['uid']))

import random
from collections import defaultdict, deque
from tqdm.auto import tqdm
import numpy as np
import pandas as pd

# ---- Helper function to pick a valid helper ----
def pick_valid_helper(main_sid, main_tid, helper_sid_list, t_forSwapping_r,
                      point_to_tid_dict, point_to_uid_dict_swapped):
    """
    Pick a valid helper pair for main_sid from helper_sid_list.
    Returns: (h_head_end, h_tail_start) or None if no valid helper.
    """
    h_tid_attempts = helper_sid_list.copy()
    random.shuffle(h_tid_attempts)  # reduce sampling bias
    main_uid = point_to_uid_dict_swapped[main_sid]

    for h_head_end, h_tail_start in h_tid_attempts:
        # 0. UID must differ from main
        if main_uid in (point_to_uid_dict_swapped[h_head_end], point_to_uid_dict_swapped[h_tail_start]):
            continue
        # 1. Helper head/tail must be same trajectory
        if point_to_tid_dict[h_head_end] != point_to_tid_dict[h_tail_start]:
            continue
        # 2. Helper must be different trajectory from main
        helper_tid = point_to_tid_dict[h_head_end]
        if helper_tid == main_tid:
            continue
        # 3. Helper head/tail must be consecutive
        helper_df = t_forSwapping_r[t_forSwapping_r['new_tid_subid'] == helper_tid].reset_index(drop=True)
        try:
            h_cut_index_headEnd = helper_df.index[helper_df["row_uid"] == h_head_end][0]
            h_cut_index_tailStart = helper_df.index[helper_df["row_uid"] == h_tail_start][0]
        except IndexError:
            continue
        if h_cut_index_tailStart != h_cut_index_headEnd + 1:
            continue
        # Valid helper found
        return (h_head_end, h_tail_start)
    return None

# ---- Initialize waiting room and retry tracking ----
waiting = {}
retry_counts = defaultdict(int)
max_retries = 15

# ---- Main swap loop ----
swap_queue = deque(helper_pool_dict_ordered.items())
pbar = tqdm(total=len(swap_queue), desc="Processing swaps")

while swap_queue:
    main_sid, helper_sid_list = swap_queue.popleft()
    main_tid = point_to_tid_dict[main_sid]

    # Pick a valid helper pair
    valid_helper = pick_valid_helper(main_sid, main_tid, helper_sid_list, t_forSwapping_r,
                                     point_to_tid_dict, point_to_uid_dict_swapped)
    if valid_helper is None:
        # No valid helper → add to waiting room
        waiting.setdefault(main_tid, []).append((main_sid, tuple(helper_sid_list)))
        continue

    h_head_end, h_tail_start = valid_helper
    helper_tid = point_to_tid_dict[h_head_end]
    helper_uid = point_to_uid_dict_swapped[h_head_end]

    # ---- Subset main and helper ----
    main = t_forSwapping_r[t_forSwapping_r['new_tid_subid'] == main_tid].reset_index(drop=True)
    helper = t_forSwapping_r[t_forSwapping_r['new_tid_subid'] == helper_tid].reset_index(drop=True)
    m_cut_index = main.index[main["row_uid"] == main_sid][0]
    h_cut_index_headEnd = helper.index[helper["row_uid"] == h_head_end][0]
    h_cut_index_tailStart = helper.index[helper["row_uid"] == h_tail_start][0]

    # ---- Split and label ----
    main["swap_SwappingHeadTail"] = np.where(main.index <= m_cut_index, "head_main", "tail_main")
    helper["swap_SwappingHeadTail"] = np.where(helper.index <= h_cut_index_headEnd, "head_helper", "tail_helper")
    main["SwappingHeadTail"] = np.where(main.index <= m_cut_index, f"head_main_{main_sid}", f"tail_main_{main_sid}")
    helper["SwappingHeadTail"] = np.where(helper.index <= h_cut_index_headEnd, f"head_helper_{h_head_end}", f"tail_helper_{h_head_end}")

    # ---- Record origin/destination ----
    main_origin_i = m_cut_index
    main_destination_i = h_cut_index_tailStart
    helper_origin_i = h_cut_index_headEnd
    helper_destination_i = m_cut_index+1

    main.at[main_origin_i, "swap_origin"].append(f'main_{main_sid}_origin')
    if helper_destination_i < len(main):
        main.at[helper_destination_i, "swap_destination"].append(f'helper_{h_head_end}_destination')
    helper.at[helper_origin_i, "swap_origin"].append(f'helper_{h_head_end}_origin')
    helper.at[main_destination_i, "swap_destination"].append(f'main_{main_sid}_destination')

    main_origin_id = main.at[m_cut_index, "row_uid"]
    main_destination_id = helper.at[h_cut_index_tailStart, "row_uid"]
    helper_origin_id = helper.at[h_cut_index_headEnd, "row_uid"]
    if helper_destination_i < len(main):
        helper_destination_id = main.at[helper_destination_i, "row_uid"]
        od_dict[helper_origin_id].append(helper_destination_id)
    od_dict[main_origin_id].append(main_destination_id)

    # ---- Perform swap ----
    main['new_tid_subid'] = np.where(main['swap_SwappingHeadTail'] == "tail_main", helper_tid, main_tid)
    helper['new_tid_subid'] = np.where(helper['swap_SwappingHeadTail'] == "head_helper", helper_tid, main_tid)
    main['new_uid'] = np.where(main['swap_SwappingHeadTail'] == "tail_main", helper_uid, point_to_uid_dict_swapped[main_sid])
    helper['new_uid'] = np.where(helper['swap_SwappingHeadTail'] == "head_helper", helper_uid, point_to_uid_dict_swapped[main_sid])

    # ---- Update swap_point_id_t and swap counts ----
    swapped_df = pd.concat([main, helper])
    swapped_df = swapped_df.sort_values(by=['new_tid_subid','swap_SwappingHeadTail','row_uid']).reset_index(drop=True)
    swapped_df['swap_point_id_t'] = swapped_df.groupby('new_tid_subid').cumcount() + 1
    swapped_df['swap_n'] += 1
    mask = swapped_df['swap_SwappingHeadTail'].isin(['tail_main','head_helper'])
    swapped_df.loc[mask, 'swap_n_containerChange'] += 1

    # ---- Update master df in place ----
    rows = swapped_df['row_uid']
    cols = ['new_tid_subid','new_uid','swap_SwappingHeadTail','SwappingHeadTail','swap_point_id_t','swap_n','swap_origin','swap_destination']
    t_forSwapping_r.loc[t_forSwapping_r['row_uid'].isin(rows), cols] = swapped_df[cols].values

    # ---- Update dicts ----
    point_to_tid_dict = dict(zip(t_forSwapping_r['row_uid'], t_forSwapping_r['new_tid_subid']))
    point_to_uid_dict_swapped = dict(zip(t_forSwapping_r['row_uid'], t_forSwapping_r['new_uid']))

    # ---- Handle waiting room ----
    affected_tids = {main_tid, helper_tid}
    for tid in affected_tids:
        if tid in waiting:
            for pair in waiting[tid]:
                if retry_counts[pair] < max_retries:
                    swap_queue.append(pair)
                    retry_counts[pair] += 1
            del waiting[tid]

    pbar.update(1)

pbar.close()

#%% copy of what ran for
#  22954/26723 [42:47:00<8:18:53,  7.94s/it]
# reduce df to prevent memory issues
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

# --- define lookup dicts ---
point_to_tid_dict = dict(zip(t_forSwapping_r['row_uid'], t_forSwapping_r['new_tid_subid']))
point_to_uid_dict_swapped = dict(zip(t_forSwapping_r['row_uid'], t_forSwapping_r['new_uid']))
point_to_uid_dict_orig = dict(zip(t_forSwapping_r['row_uid'], t_forSwapping_r['uid']))
import random
from collections import defaultdict, deque
from tqdm.auto import tqdm
import numpy as np
import pandas as pd

# ---- Helper function to pick a valid helper ----
def pick_valid_helper(main_sid, main_tid, helper_sid_list, t_forSwapping_r,
                      point_to_tid_dict, point_to_uid_dict_swapped):
    """
    Pick a valid helper pair for main_sid from helper_sid_list.
    Returns: (h_head_end, h_tail_start) or None if no valid helper.
    """
    #h_tid_attempts = helper_sid_list.copy()
    h_tid_attempts = list(helper_sid_list)
    random.shuffle(h_tid_attempts)  # reduce sampling bias
    main_uid = point_to_uid_dict_swapped[main_sid]

    for h_head_end, h_tail_start in h_tid_attempts:
        # 0. UID must differ from main
        if main_uid in (point_to_uid_dict_swapped[h_head_end], point_to_uid_dict_swapped[h_tail_start]):
            continue
        # 1. Helper head/tail must be same trajectory
        if point_to_tid_dict[h_head_end] != point_to_tid_dict[h_tail_start]:
            continue
        # 2. Helper must be different trajectory from main
        helper_tid = point_to_tid_dict[h_head_end]
        if helper_tid == main_tid:
            continue
        # 3. Helper head/tail must be consecutive
        helper_df = t_forSwapping_r[t_forSwapping_r['new_tid_subid'] == helper_tid].reset_index(drop=True)
        try:
            h_cut_index_headEnd = helper_df.index[helper_df["row_uid"] == h_head_end][0]
            h_cut_index_tailStart = helper_df.index[helper_df["row_uid"] == h_tail_start][0]
        except IndexError:
            continue
        if h_cut_index_tailStart != h_cut_index_headEnd + 1:
            continue
        # Valid helper found
        return (h_head_end, h_tail_start)
    return None

# ---- Initialize waiting room and retry tracking ----
waiting = {}
retry_counts = defaultdict(int)
max_retries = 15

# ---- Main swap loop ----
swap_queue = deque(helper_pool_dict_ordered.items())

#%% resume run
pbar = tqdm(total=len(swap_queue), desc="Processing swaps")

while swap_queue:
    main_sid, helper_sid_list = swap_queue.popleft()
    main_tid = point_to_tid_dict[main_sid]

    # Pick a valid helper pair
    valid_helper = pick_valid_helper(main_sid, main_tid, helper_sid_list, t_forSwapping_r,
                                     point_to_tid_dict, point_to_uid_dict_swapped)
    if valid_helper is None:
        # No valid helper → add to waiting room
        waiting.setdefault(main_tid, []).append((main_sid, tuple(helper_sid_list)))
        continue

    h_head_end, h_tail_start = valid_helper
    helper_tid = point_to_tid_dict[h_head_end]
    helper_uid = point_to_uid_dict_swapped[h_head_end]

    # ---- Subset main and helper ----
    main = t_forSwapping_r[t_forSwapping_r['new_tid_subid'] == main_tid].reset_index(drop=True)
    helper = t_forSwapping_r[t_forSwapping_r['new_tid_subid'] == helper_tid].reset_index(drop=True)
    m_cut_index = main.index[main["row_uid"] == main_sid][0]
    h_cut_index_headEnd = helper.index[helper["row_uid"] == h_head_end][0]
    h_cut_index_tailStart = helper.index[helper["row_uid"] == h_tail_start][0]

    # ---- Split and label ----
    main["swap_SwappingHeadTail"] = np.where(main.index <= m_cut_index, "head_main", "tail_main")
    helper["swap_SwappingHeadTail"] = np.where(helper.index <= h_cut_index_headEnd, "head_helper", "tail_helper")
    main["SwappingHeadTail"] = np.where(main.index <= m_cut_index, f"head_main_{main_sid}", f"tail_main_{main_sid}")
    helper["SwappingHeadTail"] = np.where(helper.index <= h_cut_index_headEnd, f"head_helper_{h_head_end}", f"tail_helper_{h_head_end}")

    # ---- Record origin/destination ----
    main_origin_i = m_cut_index
    main_destination_i = h_cut_index_tailStart
    helper_origin_i = h_cut_index_headEnd
    helper_destination_i = m_cut_index+1

    main.at[main_origin_i, "swap_origin"].append(f'main_{main_sid}_origin')
    if helper_destination_i < len(main):
        main.at[helper_destination_i, "swap_destination"].append(f'helper_{h_head_end}_destination')
    helper.at[helper_origin_i, "swap_origin"].append(f'helper_{h_head_end}_origin')
    helper.at[main_destination_i, "swap_destination"].append(f'main_{main_sid}_destination')

    main_origin_id = main.at[m_cut_index, "row_uid"]
    main_destination_id = helper.at[h_cut_index_tailStart, "row_uid"]
    helper_origin_id = helper.at[h_cut_index_headEnd, "row_uid"]
    if helper_destination_i < len(main):
        helper_destination_id = main.at[helper_destination_i, "row_uid"]
        od_dict[helper_origin_id].append(helper_destination_id)
    od_dict[main_origin_id].append(main_destination_id)

    # ---- Perform swap ----
    main['new_tid_subid'] = np.where(main['swap_SwappingHeadTail'] == "tail_main", helper_tid, main_tid)
    helper['new_tid_subid'] = np.where(helper['swap_SwappingHeadTail'] == "head_helper", helper_tid, main_tid)
    main['new_uid'] = np.where(main['swap_SwappingHeadTail'] == "tail_main", helper_uid, point_to_uid_dict_swapped[main_sid])
    helper['new_uid'] = np.where(helper['swap_SwappingHeadTail'] == "head_helper", helper_uid, point_to_uid_dict_swapped[main_sid])

    # ---- Update swap_point_id_t and swap counts ----
    swapped_df = pd.concat([main, helper])
    swapped_df = swapped_df.sort_values(by=['new_tid_subid','swap_SwappingHeadTail','row_uid']).reset_index(drop=True)
    swapped_df['swap_point_id_t'] = swapped_df.groupby('new_tid_subid').cumcount() + 1
    swapped_df['swap_n'] += 1
    mask = swapped_df['swap_SwappingHeadTail'].isin(['tail_main','head_helper'])
    swapped_df.loc[mask, 'swap_n_containerChange'] += 1

    # ---- Update master df in place ----
    rows = swapped_df['row_uid']
    cols = ['new_tid_subid','new_uid','swap_SwappingHeadTail','SwappingHeadTail','swap_point_id_t','swap_n','swap_origin','swap_destination']
    t_forSwapping_r.loc[t_forSwapping_r['row_uid'].isin(rows), cols] = swapped_df[cols].values

    # ---- Update dicts ----
    point_to_tid_dict = dict(zip(t_forSwapping_r['row_uid'], t_forSwapping_r['new_tid_subid']))
    point_to_uid_dict_swapped = dict(zip(t_forSwapping_r['row_uid'], t_forSwapping_r['new_uid']))

    # ---- Handle waiting room ----
    affected_tids = {main_tid, helper_tid}
    for tid in affected_tids:
        if tid in waiting:
            for pair in waiting[tid]:
                if retry_counts[pair] < max_retries:
                    swap_queue.append(pair)
                    retry_counts[pair] += 1
            del waiting[tid]

    pbar.update(1)

pbar.close()

# 2102 clk gaps remaining for rerun
# 1787/2102 


#%% now lookf for inconsistencies
# -----------------------------
# Audit: check head/tail inconsistencies
# -----------------------------
# -----------------------------
# Audit: check head/tail inconsistencies (including unlabeled points)
# -----------------------------
audit_records = []

for tid_subid in t_forSwapping_r['new_tid_subid'].unique():
    subset = t_forSwapping_r[t_forSwapping_r['new_tid_subid'] == tid_subid].sort_values('swap_point_id_t')
    
    if len(subset) < 2:
        continue

    swap_labels = subset['swap_SwappingHeadTail'].values
    row_uids = subset['row_uid'].values

    for i in range(len(swap_labels)-1):
        current_label = swap_labels[i]
        next_label = swap_labels[i+1]

        # Normalize labels: if False or None, treat as 'unlabeled'
        current_label_str = str(current_label) if isinstance(current_label, str) else 'unlabeled'
        next_label_str = str(next_label) if isinstance(next_label, str) else 'unlabeled'

        # Head-helper followed by tail-helper is OK
        if current_label_str.startswith('head_helper') and next_label_str.startswith('tail_helper'):
            continue
        # Head-helper not followed by tail-helper → inconsistency
        elif current_label_str.startswith('head_helper') and not next_label_str.startswith('tail_helper'):
            audit_records.append({
                'tid_subid': tid_subid,
                'row_uid_head': row_uids[i],
                'row_uid_tail': row_uids[i+1],
                'current_label': current_label_str,
                'next_label': next_label_str,
                'issue': 'head not followed by tail'
            })
        # Tail-helper followed by non-tail → possible corruption
        elif current_label_str.startswith('tail_helper') and not next_label_str.startswith('tail_helper'):
            audit_records.append({
                'tid_subid': tid_subid,
                'row_uid_head': row_uids[i],
                'row_uid_tail': row_uids[i+1],
                'current_label': current_label_str,
                'next_label': next_label_str,
                'issue': 'tail followed by non-tail'
            })
        # Optional: track unlabeled points for completeness
        elif current_label_str == 'unlabeled' or next_label_str == 'unlabeled':
            audit_records.append({
                'tid_subid': tid_subid,
                'row_uid_head': row_uids[i],
                'row_uid_tail': row_uids[i+1],
                'current_label': current_label_str,
                'next_label': next_label_str,
                'issue': 'unlabeled point'
            })

# Convert to DataFrame
helper_audit_df = pd.DataFrame(audit_records)

print(f"Total inconsistent or unlabeled sequences: {len(helper_audit_df)}")
helper_audit_df.head(20)

#Total inconsistent or unlabeled sequences: 2803701
# run for 218 mins

#t_forSwapping_r.swap_SwappingHeadTail.unique() - takes helper and head into acocunt, so should be correct
#%%
helper_audit_df.issue.value_counts(dropna=False) # array(['unlabeled point', 'head not followed by tail'], dtype=object)
#issue
#unlabeled point              1492479
#head not followed by tail    1311222
#%% must export the swapping results!!!
helper_audit_df.to_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping_ConfirmedInconsistencies/helper_audit_df.parquet")
t_forSwapping_r.to_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping_ConfirmedInconsistencies/t_forSwapping_r_cloakingBased_inconsistent.parquet")


with open(r"D:\paper3\Data\output\CloakingBasedSwapping_ConfirmedInconsistencies/waiting.pkl", "wb") as f:
    pickle.dump(waiting, f)
with open(r"D:\paper3\Data\output\CloakingBasedSwapping_ConfirmedInconsistencies/point_to_tid_dict.pkl", "wb") as f:
    pickle.dump(point_to_tid_dict, f)
with open(r"D:\paper3\Data\output\CloakingBasedSwapping_ConfirmedInconsistencies/point_to_uid_dict_swapped.pkl", "wb") as f:
    pickle.dump(point_to_uid_dict_swapped, f)
with open(r"D:\paper3\Data\output\CloakingBasedSwapping_ConfirmedInconsistencies/point_to_uid_dict_orig.pkl", "wb") as f:
    pickle.dump(point_to_uid_dict_orig, f)

#%% next steps
# (d) connect the swapped trajectories (ie main and tail via synthetic points)
# (d.1) calculate shortest path (clauclate desc statistics)
# (d.2) interpolate syn points based on speed lookup and downsample

# (e) evaluate cloaking based swapping

#%% also, look at the swapped trajectories in qgis
