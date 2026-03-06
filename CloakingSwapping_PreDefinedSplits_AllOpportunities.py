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


#%% (2) count options per main_row
main_supply = (
    main_to_helpers
    .groupby('main_row_uid')['tid_subid']
    .nunique()
    .rename('n_helper_traj')
)

#%% (3) sort mains by scarcity (hardest first) <-- this idea still applies
main_order = (
    main_supply
    .sort_values()          # fewest options first
    .index
)
#main_order[0] = main with only ONE possible helper trajectory - 5365117

#%% (4) track usage constraint: a helper trajectory can only be used ONCE per cloaking area
from collections import defaultdict
used_helpers_per_clk = defaultdict(set)


# (5) scarcity-aware assignment loop
assigned = []

for m in tqdm(main_order, desc="Scarcity-aware assignment"):

    # get cloaking area of this main_row
    clk = main_rows.loc[
        main_rows.row_uid == m,
        'HeadEndCloakingAreaId'
    ].values[0]

    # all candidate helper trajectories for this main
    cands = main_to_helpers[
        (main_to_helpers.main_row_uid == m) &
        (~main_to_helpers.tid_subid.isin(used_helpers_per_clk[clk]))
    ]

    if len(cands) == 0:
        continue

    # choose helper trajectory
    chosen_tid = cands.tid_subid.sample(1).iloc[0]

    assigned.append((m, chosen_tid, clk))

    # mark helper trajectory as used at this cloaking area
    used_helpers_per_clk[clk].add(chosen_tid)