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


#%% fill clk gaps without swapping partner

#%% run swapping
import pickle

# load data back in
with open("pair_dict.pkl", "rb") as f:
    pair_dict_loaded = pickle.load(f)