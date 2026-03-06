#%%
import geopandas as gpd
import pandas as pd
t_forSwapping = gpd.read_parquet(r"d:\paper3\Data\output\CloakingBasedSwapping\t_forSwapping.parquet")
valid_assigned_helpers_df = pd.read_parquet(r"d:\paper3\Data\output\CloakingBasedSwapping\valid_assigned_helpers_df.parquet")

#%% have found the matching helper trajectory segment 
# but must actually identify a splitting point outside the swapping loop
# update: WANT 2 TRAJECTORY POINTS OF HELPER TO BE WITHIN CLOAKING AREA TO BE A VALID HELPER

#%% first: must add time bin to valid_assigned_helpers_df
t_timebins = t_forSwapping[['row_uid', 'time_bin', 'time_bin_label']].copy()
t_timebins = t_timebins.rename(columns={'row_uid': 'main_row_uid', 'time_bin':'main_time_bin'})
print(len(valid_assigned_helpers_df))
# adding time bin of main to df
valid_assigned_helpers_df = valid_assigned_helpers_df.merge(t_timebins, on ='main_row_uid',how="left")
print(len(valid_assigned_helpers_df)) # nothing lost
valid_assigned_helpers_df = valid_assigned_helpers_df.rename(columns={'clkpassed': 'helper_clkpassed', 'helper_tid':'helper_tid_subid'})
valid_assigned_helpers_df.head() # added time bin to last point of heads - that is the main time bin, the one it must align with!


#%% now: find all potential swapping candidates according to valid_assigned_helpers_df
# reduce to helpers to work with less data when exploding
print(valid_assigned_helpers_df.helper_tid_subid.nunique()) # 7067
t_helper = t_forSwapping[t_forSwapping['tid_subid'].isin(valid_assigned_helpers_df.helper_tid_subid.unique())].copy()
print(len(t_helper)) # 4,404,118
# now explode
t_helper = t_helper.explode('intersecting_cloaking_ids')
print(len(t_helper)) # 4,442,621

#%% find points where helper_tid, clpassed and time_bin matches valid_assigned_helpers_df
t_helper = t_helper.rename(columns={'row_uid': 'helper_row_uid', 'intersecting_cloaking_ids': 'helper_clkpassed', 'tid_subid':'helper_tid_subid', 'time_bin':'helper_time_bin'})
t_helper = t_helper[['helper_row_uid', 'helper_clkpassed', 'helper_tid_subid', 'helper_time_bin']].copy()

# filtering helper points for main cloaking gaps based on matching cloaking area and timestamp
# only intersted in potantial swap/splitting points at this stage, not the full tid anymore
valid_assigned_helpers_df = valid_assigned_helpers_df.rename(columns={'main_time_bin': 'time_bin'})
t_helper = t_helper.rename(columns={'helper_time_bin':'time_bin'})

print(len(t_helper))
print(len(valid_assigned_helpers_df))
t_helper = t_helper.merge(valid_assigned_helpers_df, on= ['helper_clkpassed', 'helper_tid_subid', 'time_bin'], how='inner')
print(len(t_helper))

print(t_helper.columns) # main_row_uid with assigned helper_row_uid - because of inner merge only points with overlapping cloaking areas and time_bins and the pre-definsed helper_tid remain
# ['helper_row_uid', 'helper_clkpassed', 'helper_tid_subid', 'time_bin','main_row_uid', 'time_bin_label']
print((t_helper['helper_row_uid'] == t_helper['main_row_uid']).any(), 'expected False') # False
t_helper.head() 
# 77,920 helper pool, but helper and main row_uid cannot be the same! 



#%% a main_row_uid can't be a helper - actually it can, only not for it's own
print(t_helper['helper_row_uid'].isin(t_helper.main_row_uid.unique()).any()) # True, can't be true!
#t_helper[t_helper['helper_row_uid'].isin(t_helper['main_row_uid'])].sort_values(['helper_row_uid']).to_csv(r"\\tsclient\R\paper3\fromVM_201\debugging/helperPointAssignment.csv")
t_helper[t_helper['helper_row_uid'].isin(t_helper['main_row_uid'])].sort_values(['helper_row_uid'])
# not all potential helpers for that main_row though
# shows the helpers where the helper is a main_row, does not chow the main_row_uid istels

# must figure out if these main_row_uids, the ones that would be served by a helper that IS a main row have alternative points 
# realsitically they won't as helper tid and cloaking area have been pre-filtered already...

#%% UPDATE: WANT TO ENSURE THAT HELPER TRAJECTORY DOES NOT END IN CLOAKING ZONE
# helper trajectory must have a point outside the helper zone for that time bin
# i.e. look at max point per helper_tid and time_bin combo, then find those points and look for consecutive points?
t_forSwapping = t_forSwapping.sort_values('row_uid')  
row_uid_to_tid = t_forSwapping.set_index('row_uid')['tid_subid']
t_helper['tid_subid_mapped'] = t_helper['helper_row_uid'].map(row_uid_to_tid)
t_helper['helper_endsinClkAgera'] = t_helper.groupby('tid_subid_mapped')['helper_row_uid'].transform('last') == t_helper['helper_row_uid']
print(len(t_helper)) #77,920 same as before
t_helper.helper_endsinClkAgera.value_counts(normalize=True) * 100
#helper_endsinClkAgera
#False    90.930441
#True      9.069559

#%% in that case: a trajectory would be swapped twice at the same cloaking geometry - maybe it is overlapping cloaking geometries? though I did remove those
print(t_helper[t_helper['helper_row_uid'].isin(t_helper['main_row_uid'])]['main_row_uid'].nunique())
mah_id = t_helper[t_helper['helper_row_uid'].isin(t_helper['main_row_uid'])]['main_row_uid'].unique()
mah_id_df = t_helper[t_helper['main_row_uid'].isin(mah_id)] # helpers which are also mains, or as the name suggests mains as helpers

# this would tell me how many helper tids each main_row_uid has assigned, but since these are pre-defined we know it is only 1
print(mah_id_df.groupby('main_row_uid')['helper_tid_subid'].nunique().reset_index(name='n_helper_tid')['n_helper_tid'].max()) # 1

# this tells me how many points each assigned helper tid has
mah_id_df_pts = mah_id_df.groupby('main_row_uid')['helper_tid_subid'].value_counts().reset_index() # cannot randolmy chose from these
print(mah_id_df_pts['count'].min()) # ideally not 1 (is 1)
print(mah_id_df_pts['count'].median()) # 2
print(mah_id_df_pts['count'].max()) # 740
# alternatively, drop these main_row_uids from being swapped - would have to add the synthetic trajectories back in
# decided to keep them (but swap them last)



#%% look at all options for mains that have a main as their helper
# from 'mains as helpers' get the 'problematic' mains to look for alterantives
# are all helpers mains?
mains_list = valid_assigned_helpers_df.main_row_uid.unique()
print(set(mah_id_df.helper_row_uid.unique()).issubset(set(mains_list))) # False, not all the helpers are mains (good)

mah_id_df['helper_is_main'] = mah_id_df['helper_row_uid'].isin(mains_list)
# look at the alterantives per main_row_uid 
# must have passed the helper_clkpassed geometry, otherwise they wouldn't have been assigned

print(len(mah_id_df)) #1473

#%%
#%%I want to know which other clk they passed - i.e., did they pass the main clk area that has been assigned to be a helper
#mah_id_df'helper_main_clk_sen'
print(mah_id_df.columns)
hm_list = mah_id_df[mah_id_df['helper_is_main'] == True]['helper_row_uid'].unique() #122 helpers are also mains
# for these main helpers, get their sensitive cloaking id
hm_clkid = t_forSwapping[t_forSwapping['row_uid'].isin(hm_list)][['row_uid', 'Sensitive_CloakingAreaId']]
hm_clkid = hm_clkid.rename(columns={'row_uid':'helper_row_uid'})
# add these back to df
mah_id_df = mah_id_df.merge(hm_clkid, on ="helper_row_uid", how='left')
# now, also add all intersecting clkPassed of helper point, to determine whether the point overlaps with the clk of main
mah_allcklpssd = t_forSwapping[t_forSwapping['row_uid'].isin(mah_id_df.helper_row_uid.unique())][['row_uid', 'intersecting_cloaking_ids']]
mah_allcklpssd = mah_allcklpssd.rename(columns={'row_uid':'helper_row_uid'})
mah_id_df = mah_id_df.merge(mah_allcklpssd, on ="helper_row_uid", how='left')
print(len(mah_id_df)) #1473, still

mah_id_df
#%%
agg_df = mah_id_df.groupby('helper_tid_subid')['Sensitive_CloakingAreaId'] \
           .apply(lambda x: list(x.dropna().unique())) \
           .reset_index() \
           .rename(columns={'Sensitive_CloakingAreaId': 'Sensitive_CloakingAreaId_OfHelperMain'})
#agg_df['num_values'] = agg_df['Sensitive_CloakingAreaId_OfHelperMain'].apply(len) # all 1
mah_id_df = mah_id_df.merge(agg_df, on='helper_tid_subid', how='left')
print(len(mah_id_df)) #1473, still

mah_id_df

#%% pick one random point per helper to split helper into head and tail
#def pick_helper(group):
#    # 1st prioroity: segment is not part of main as helper
#    candidates = group[group['segment_helper_is_main'] == False]
#    if len(candidates) > 0:
#        return candidates.sample(1)['helper_row_uid'].iloc[0]
#    # 2nd priority: segment can be part of main as helper, but point itself isnt
#    fallback = group[group['segment_helper_is_main'] == True]
#    preferred = fallback[fallback['helper_is_main'] == False]
    
#    if len(preferred) > 0:
#        return preferred.sample(1)['helper_row_uid'].iloc[0]
#    # final pick: only helper_is_main == True available
#    return fallback.sample(1)['helper_row_uid'].iloc[0]

#%% FIND HELPER PAIRS INSTEAD (overcoming sparse trajectorires)
def pick_helper_pair(group):

    def pick_consecutive(df):
        # make sure helper_endsinClkAgera is False
        df = df[df['helper_endsinClkAgera'] == False]

        # sort by main_row_uid then helper_row_uid
        df = df.sort_values(['main_row_uid', 'helper_row_uid'])

        # find consecutive pairs
        pairs = df[df["helper_row_uid"].diff(-1).abs() == 1]

        if len(pairs) == 0:
            return None

        # pick random start of pair
        start = pairs.sample(1).iloc[0]["helper_row_uid"]
        return [start, start + 1]

    # Priority 1
    candidates = group[
        (group['segment_helper_is_main'] == False) &
        (group['helper_endsinClkAgera'] == False)
    ]
    pair = pick_consecutive(candidates)
    if pair is not None:
        return pair

    # Priority 2
    fallback = group[group['segment_helper_is_main'] == True]
    preferred = fallback[
        (fallback['helper_is_main'] == False) &
        (fallback['helper_endsinClkAgera'] == False)
    ]

    pair = pick_consecutive(preferred)
    if pair is not None:
        return pair

    # Priority 3
    fallback = fallback[fallback['helper_endsinClkAgera'] == False]
    pair = pick_consecutive(fallback)
    if pair is not None:
        return pair

    # if no pair satisfies helper_endsinClkAgera==False
    return None

#%% apply this to all "problematic helpers"; IMPORTANT
# sorting is important 
mah_id_df = mah_id_df.sort_values(['main_row_uid', 'helper_row_uid'])
# segment helpers
mah_id_df['segment_helper_row_uid'] = mah_id_df.groupby('main_row_uid')['helper_row_uid'] \
                                 .transform(lambda x: (x.diff() > 1).cumsum() + 1)
# class segment as main helper or not
mah_id_df['segment_helper_is_main'] = mah_id_df.groupby('segment_helper_row_uid')['helper_is_main'] \
                                  .transform('any')

# pick helpers randomly 
selected_mahelpers = (
    mah_id_df.groupby('main_row_uid', group_keys=False)
      .apply(pick_helper_pair)
      .reset_index(name='selected_helper_row_uid')
)

print(selected_mahelpers.isna().any(axis=1).sum()) # 28 out of 61 problematic helpers have no helper pair
print(len(selected_mahelpers))
selected_mahelpers



#%% now pick a random point for the unproblematic helpers
# remove problematic helpers from sample
print(len(t_helper)) # 77,920
random_t_helper_pool = t_helper[~t_helper['main_row_uid'].isin(mah_id)] # helpers which are unproblematic (aka not a main themselves)
print(len(random_t_helper_pool)) # 76,447
print('')
print(random_t_helper_pool.main_row_uid.nunique()) # 11,488
print(mah_id_df.main_row_uid.nunique())
print(t_helper.main_row_uid.nunique())
print((random_t_helper_pool.main_row_uid.nunique()+mah_id_df.main_row_uid.nunique()) == t_helper.main_row_uid.nunique())
# True when I run it in this block, but false when run independenlty


# UPDATE  remove points that end in the clk area
random_t_helper_pool_moreprivacy = random_t_helper_pool[
    random_t_helper_pool['helper_endsinClkAgera'] == False
]
# False after becuase I am removing end points!
print(random_t_helper_pool_moreprivacy.main_row_uid.nunique()) # 9,231
# this is the numnber we need to assign priority helpers too

#%%
# randomly pick unproblematic helpers - NEED 2 CONSECUTIVE POINTS PER HELPER
#t_helper_random = random_t_helper_pool.groupby('main_row_uid', group_keys=False).sample(n=1)
def pick_two_consecutive(group):
    # sort by helper_row_uid to ensure consecutive ordering
    group = group.sort_values('helper_row_uid')
    
    # find all consecutive starts
    consecutive_starts = group['helper_row_uid'][:-1][
        group['helper_row_uid'].diff(-1).abs() == 1
    ]
    
    if len(consecutive_starts) == 0:
        return None  # no valid consecutive pair
    
    # pick one random start
    start = consecutive_starts.sample(1).iloc[0]
    return pd.Series([start, start + 1])

t_helper_random_pairs = (
    random_t_helper_pool.groupby('main_row_uid', group_keys=False)
    .apply(pick_two_consecutive)
    .dropna()  # remove main_row_uid without consecutive pairs
    .reset_index()
)

t_helper_random_pairs_moreprivacy = (
    random_t_helper_pool_moreprivacy.groupby('main_row_uid', group_keys=False)
    .apply(pick_two_consecutive)
    .dropna()  # remove main_row_uid without consecutive pairs
    .reset_index()
)


# FOR FUTURE REFERENCE: COULD KEEP THE UNUSED POTENTIAL HELPERS AS BACKUP TO FALL BACK TO IN THE SWAPPING LOOP
# OR GO BACK TO THESE IF A GAP COULD NOT BE SWAPPED WITHIN THE LOOP

# rename columns
t_helper_random_pairs.columns = ['main_row_uid', 'helper_row_uid_1', 'helper_row_uid_2']
t_helper_random_pairs_moreprivacy.columns = ['main_row_uid', 'helper_row_uid_1', 'helper_row_uid_2']

# random pairs need to be a list in one colum
# integer not float
t_helper_random_pairs["helper_row_uid_1"] = t_helper_random_pairs["helper_row_uid_1"].astype(int)
t_helper_random_pairs["helper_row_uid_2"] = t_helper_random_pairs["helper_row_uid_2"].astype(int)
t_helper_random_pairs_moreprivacy["helper_row_uid_1"] = t_helper_random_pairs_moreprivacy["helper_row_uid_1"].astype(int)
t_helper_random_pairs_moreprivacy["helper_row_uid_2"] = t_helper_random_pairs_moreprivacy["helper_row_uid_2"].astype(int)

t_helper_random_pairs["helper_row_uid"] = t_helper_random_pairs[["helper_row_uid_1", "helper_row_uid_2"]].values.tolist()
t_helper_random_pairs_moreprivacy["helper_row_uid"] = t_helper_random_pairs_moreprivacy[["helper_row_uid_1", "helper_row_uid_2"]].values.tolist()

# this is the numnber we need to assign priority helpers too
print('number of mains that needed a helper (pair):', random_t_helper_pool.main_row_uid.nunique()) # 9,231
print('number of main points in the ranom helper df:', t_helper_random_pairs.main_row_uid.nunique()) # 5,707
print('but are there any nan?')
print(t_helper_random_pairs["helper_row_uid"].isna().sum()) # 0 - perfect, all unproblematic one 

# this is the numnber we need to assign priority helpers too
print('number of mains that needed a helper (pair):', random_t_helper_pool_moreprivacy.main_row_uid.nunique()) # 9,231
print('number of main points in the ranom helper df:', t_helper_random_pairs_moreprivacy.main_row_uid.nunique()) # 5,707
print('but are there any nan?')
print(t_helper_random_pairs_moreprivacy["helper_row_uid"].isna().sum()) # 0 - perfect, all unproblematic one 

t_helper_random_pairs_moreprivacy

#number of mains that needed a helper (pair): 11488
#number of main points in the ranom helper df: 7211
#but are there any nan? 0
# not ending in mix zone
#number of mains that needed a helper (pair): 9231
#number of main points in the ranom helper df: 5707
#but are there any nan? 0



#%%  reunite helper selection
# prep df for concat
# rename column of problematic helpers
selected_mahelpers = selected_mahelpers.rename(columns={'selected_helper_row_uid': 'helper_row_uid'})
# only want a record of main_row_uid and helper_row_uid
t_helper_random_pairs_moreprivacy = t_helper_random_pairs_moreprivacy[['main_row_uid', 'helper_row_uid']]
t_helper_random_pairs_moreprivacy 

#%% do either of these have nan, if so, why?
# also why is t_helper_random_pairs so short, am I missing rows? compare to old script 
print(selected_mahelpers["helper_row_uid"].isna().sum()) # 28 - which is nearly half out of 61
# this are None, i.e. we did not find a suitable match - that is ok
# drop the na (as done for the main helper df)
selected_mahelpers = selected_mahelpers.dropna(subset=["helper_row_uid"])
# will fill in dropped clk gaps later

#%% append  these to t_helper_random because I want them to be swapped last, incase it is a main that is acting as a helper
t_helper_random_assigned = pd.concat([t_helper_random_pairs_moreprivacy, selected_mahelpers]).reset_index(drop=True)
t_helper_random_assigned 
# before len 11549 
# now only 5740  rows, becuas we must have at least 2 helper points within the cloaked zone AND one point after the cloaked zone

#%% export swapping pairs
t_helper_random_assigned.to_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping/CloakingGaps_swappingPairs_PointLevel_pairsNotEndingInMixZone_final.parquet")



#%% SWAPPING
# (a) must updated t_for_swapping so that gaps that have no swapping partner are filled with syn points again

# (b) run swapping

# (c) have all gaps been swapped? we do have backup points to base swapping on which might work
# alternatively, add syn points back in

# (d) connect the swapped trajectories (ie main and tail via synthetic points)
# (d.1) calculate shortest path (clauclate desc statistics)
# (d.2) interpolate syn points based on speed lookup and downsample

# (e) evaluate cloaking based swapping

#%% COMBINE SWAPPING METHODS
# minimise trajectory length to median plus minus std



#%% SWAPPING
import geopandas as gpd
import pandas as pd
t_forSwapping = gpd.read_parquet(r"d:\paper3\Data\output\CloakingBasedSwapping\t_forSwapping.parquet")
t_helper_random_assigned = pd.read_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping/CloakingGaps_swappingPairs_PointLevel_pairsNotEndingInMixZone_final.parquet")


#%% prep data gdf
import numpy as np
# reduce df to prevent memory issues (can get attributes back at a later stage)
t_forSwapping_r = t_forSwapping[['row_uid', 'tid_subid']].copy()
t_forSwapping_r['orig_tid_subid'] = t_forSwapping_r['tid_subid'].copy()
t_forSwapping_r['new_tid_subid'] = t_forSwapping_r['tid_subid'].copy()
t_forSwapping_r['swap_SwappingHeadTail'] = False
t_forSwapping_r['SwappingHeadTail'] = False
t_forSwapping_r['swap_n'] = 0
t_forSwapping_r['swap_origin'] = pd.Series(dtype='string')
t_forSwapping_r['swap_destination'] = pd.Series(dtype='string')
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

#for main_sid, helper_sid in swapping_pairs.items():

# add a progess bar
from tqdm.auto import tqdm
for main_sid, helper_sid in tqdm(swapping_pairs.items(), desc="Processing swaps"):

# run for 5 to test logic
#from itertools import islice
#for main_sid, helper_sid in islice(swapping_pairs.items(), 2): 
    #print('main <--> helper', main_sid, helper_sid) # but looping is slow, mapping might be better...

    # (1) isolate the swapping pair from main df
    # get tid_subid for both main and helper
    main_tid = point_to_tid_dict[main_sid]
    #print('tid of main', main_tid)
    helper_tid = point_to_tid_dict[helper_sid] # BUT TID OF POINT WILL CHANGE - build dict at the beginning of each loop?
    #print('tid of helper', helper_tid)

    # subset by tid and reset index
    main = t_forSwapping_r[t_forSwapping_r['new_tid_subid'] == main_tid].reset_index(drop=True)
    #print('len of main', len(main))
    #print('max index of main', main.index.max())
    helper = t_forSwapping_r[t_forSwapping_r['new_tid_subid'] == helper_tid].reset_index(drop=True)
    #print('len of helper', len(helper))
    #print('max index of helper ', helper.index.max())
    # must ensure that new_tid_subid is updated after every swap for this to work
    # --> t_forSwapping_r must be updated at the end of each loop

    #################################################################
    # ATTENTION
    #################################################################
    # swapping_pairs can become invalid due to previous swap
    # (a) for example when main_tid and helper_tid have the same new_tid_subid
    # (b) tail has no points based on split assignment
    # if a swapping_pair is invalid: try and swap it again later or skip
    # if ultimately skipped: take note of swapping pair so that the cloaking gap can be fileld synthetically
    # though the original cloaking gap destination would have been assigned a differnt pair



    # (2) split main and helper into heads and tail
    m_cut_index = main.index[main["row_uid"] == main_sid][0]
    #print('m_cut_index', m_cut_index)
    h_cut_index = helper.index[helper["row_uid"] == helper_sid][0]
    #print('h_cut_index', h_cut_index)

    # general split
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
    
    # split to track swapps
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

    # record origin destination for these swaps!
    main_origin_i = m_cut_index
    main_destintaion_i = h_cut_index+1
    helper_origin_i = h_cut_index
    helper_destination_i = m_cut_index+1
    # but this is the index, the index will change
    # so update df now when index is still correct
    # LOC ADS ROWS IF THERE IS NO ROW WITH THAT INDEX
    main.loc[main_origin_i, "swap_origin"] = f'main_{main_sid}_origin'
    main.loc[helper_destination_i, "swap_destination"] = f'helper_{helper_sid}_destination'
    helper.loc[helper_origin_i, "swap_origin"] = f'helper_{helper_sid}_origin'
    helper.loc[main_destintaion_i, "swap_destination"] = f'main_{main_sid}_destination'

    # need to record row_uid of these instead 
    # - only if I wanted to store these pairs as a dictonary rather than flags in the df
    main_origin_id =  main.at[m_cut_index, "row_uid"] 
    main_destintaion_id = helper.at[(h_cut_index+1), "row_uid"] 
    helper_origin_id = helper.at[h_cut_index, "row_uid"]
    helper_destination_id = main.at[(m_cut_index+1), "row_uid"]  
    #print('point ids of origin and destinations')  
    #print('main origin', main_origin_id, 'to destination (helper): ', main_destintaion_id)
    #print('helper origin', helper_origin_id, 'to destination (helper): ', helper_destination_id)
    # update origin destination dict
    #od_dict.update({
    #    main_origin_id: main_destintaion_id, # key already exists in dict and value will  be overwritten
        # helper_origin_id: helper_destination_id # key should not exist in dict unless helper origin pt is also a main, is added to the dict (unless a main hase the same id, then main gets overwritten)
        # save way to handle helpers potentially being a main: add _h, can remove this later
    #    helper_origin_id.astype(str)+"_h": helper_destination_id
        # could also store values as list to not overwrite key-value pair
    #})
    od_dict[main_origin_id].append(main_destintaion_id)
    od_dict[helper_origin_id].append(helper_destination_id)
    # can chain O-D when D is also an O: O-D-D or decide to drop intermediate D and have OD2 instead?
    # can record O-D-D for now and later decide to drop D




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

    # now I have an updated main and helper df
    # both should consist of two different orig_tid - that is if they were concated and split 
    # currently we have two sepereate df
    #print('main updated tid', main.new_tid_subid.nunique())
    #print('helper updated tid', helper.new_tid_subid.nunique())

    # (3b) update point_id (actually move points to new container, i.e., order by new point id)
    # hierarchy for ordering:
    # new_tid_subid after swap
    # head, then tail (h is before t in the alphabet)
    # row_uid
    
    # not ideal in terms of processing time, but only way I can help myself
    # concat helper and main to updated point id 
    swapped_df = pd.concat([main, helper])
    # is that sorting the same after the first swap?
    # yes because new_tid_subid applies to the full head and tail
    # this headtail column is the generic one - applies to full group of new_tid_subid
    # point number... row_uid is correct if not swapped before
    # if swapped before this should be based on the new point_id
    swapped_df = swapped_df.sort_values(
        by=['new_tid_subid', 'swap_SwappingHeadTail', 'row_uid'],
        ascending=[True, True, True]  
    ).reset_index(drop=True)
    # now that points are sorted we can add point ids
    swapped_df['swap_point_id_t'] = swapped_df.groupby('new_tid_subid').cumcount() + 1

    # add swap count
    swapped_df['swap_n'] = swapped_df['swap_n'] +1

    # (3c) ideally add synthetic points now? how fill further swaps impact the synthetic points?
    # can I keep track of swaps and tid changes without adding the syn points here, and instead assigning them this tid once they have been created
    


    # (3d) MUST UPDATE TID IN RECORDS
    # i.e., DICTONAIRY and gdf - assigning the new tid to split points    # must update t_forSwapping_r[t_forSwapping_r['new_tid_subid']
    # find row_uids to update
    # swapped_df.row_uid.unique()
    # drop these from the master df
    t_forSwapping_r = t_forSwapping_r[~t_forSwapping_r['row_uid'].isin(swapped_df['row_uid'])]
    # concat updated attributes of these points
    t_forSwapping_r = pd.concat([t_forSwapping_r, swapped_df], ignore_index=True)

    # currently only to the used split points
    # point_to_tid_dict.update({
        # the used main and helper - but they stay the same, they are at the end of their respective heads
        # all points on the updated tid that act as a helper OR main have a new tid
    #    main_sid: NEW TID,
    #    helper_sid: NEW TID
    #})
    # BUT changing tids affects ALL SPLIT POINTS on the orig, not just the two active on
    # it takes some away and adds others
    # MUST UPDATE ALL KEY-VALUES in DICTONARY --> overwrite dictonary
    point_to_tid_dict = dict(zip(t_forSwapping_r['row_uid'],
                   t_forSwapping_r['new_tid_subid'])) # tid_subid assignments change after swapping!
    #print('updated all point to tid entries in dict')



    # (6) run swapping on the next pair

#%%  11549/11549 [17:03:17<00:00,  5.76s/it]
import pickle
with open(r"D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\locBug_addedDuplicates/point_to_tid_dict_duplicatesWhenIndexOUtOfBound.pkl", "wb") as f:
    pickle.dump(point_to_tid_dict, f)
with open(r"D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\locBug_addedDuplicates/od_dict_duplicatesWhenIndexOUtOfBound.pkl", "wb") as f:
    pickle.dump(od_dict, f)

#%%
od_dict
# some have two destination (1 by manual inspection)
# some have nan (479586: [nan], 3 or 4 by manual inspection)
# look at the keys that have no destination?

#%%
t_forSwapping_r['swap_SwappingHeadTail'] = t_forSwapping_r['swap_SwappingHeadTail'].astype(str)
t_forSwapping_r['SwappingHeadTail'] = t_forSwapping_r['SwappingHeadTail'].astype(str)

t_forSwapping_r.to_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\locBug_addedDuplicates/t_forSwapping_duplicatesWhenIndexOUtOfBound.parquet")

#%% last loop version of
print(main_sid) # 7315343
print(helper_sid) # 5243076

print(m_cut_index) # 808
print(h_cut_index) # 228

print(main_tid) # 20200306_5e61a24666c6e1162e17749370d1f52e0600d897_4899
print(helper_tid) # 20200714_5e61a24666c6e1162e17749370d1f52e0600d897_6324

exported_lastLoop = {
    "main_sid": main_sid,
    "helper_sid": helper_sid,
    "m_cut_index": m_cut_index,
    "h_cut_index": h_cut_index,
    "main_tid": main_tid,
    "helper_tid": helper_tid
}
import csv
with open(r"D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\locBug_addedDuplicates/last_helperAndMain.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["variable", "value"])  
    for k, v in exported_lastLoop.items():
        writer.writerow([k, v])
# main and helper, they are all dfs not gdfs
main.to_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\locBug_addedDuplicates/last_main.parquet")
helper.to_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\locBug_addedDuplicates/last_helper.parquet")
swapped_df.to_csv(
    r"D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\locBug_addedDuplicates\last_main_helper_swapped.csv",
    index=False
)

#%% directly to R
swapped_df.to_csv(
    r"\\tsclient\R\paper3\fromVM_201\CloakingBasedSwapping\last_main_helper_swapped.csv",
    index=False
)
#%%
#t_forSwapping_r is not a gdf anymore
print(len(t_forSwapping_r)) # 7332056 + 78 rows
print(len(t_forSwapping)) #7331578 
#%%
print(len(t_forSwapping) == t_forSwapping.row_uid.nunique()) # True
print(len(t_forSwapping_r) == t_forSwapping_r.row_uid.nunique()) # False

#%%
# I don't understand why they are duplicates, I would have expected nan based on the loc and non-existing index issue
print(t_forSwapping_r.row_uid.isna().any()) # they are! easy way to identify points that shouldn't exist
t_forSwapping_r[t_forSwapping_r.row_uid.isna()] # only one is nan?
# but t_forSwapping_r is 78 longer than t_forSwapping

#%%
t_forSwapping_r[t_forSwapping_r.tid_subid.isna()] # same as missing row_uid

#%% so look at the duplicate row_uid - incl the firt occurance
dsplitpts = t_forSwapping_r[t_forSwapping_r['row_uid'].duplicated(keep=False)]
dsplitpts
#%%
print(dsplitpts['row_uid'].nunique())   #477
print(len(dsplitpts))                   #954
print(dsplitpts.index.max())            #3317391
print(dsplitpts.index.min())            #3316438
print(dsplitpts.index.max()-dsplitpts.index.min()) # 953
print(t_forSwapping_r.index.max()) # 7332055 --> bunch of duplicates in the middle of the df

import numpy as np
index_array = dsplitpts.index.to_numpy()
index_gaps = np.diff(index_array)  # difference between consecutive indices
print("Gaps between indices:", index_gaps) # all 1, i.e., no index is skipped --> all duplicates are consecutive

print(dsplitpts.tid_subid.nunique()) # 3 original tids
print(dsplitpts.new_tid_subid.nunique()) # all from one new tid
print(dsplitpts.new_tid_subid.unique()) # 20200318_60645664b1ea087b6acaf3b6caa6a4cad3704637_5231


#%% does this new tid have other points
t_forSwapping_r[t_forSwapping_r['new_tid_subid']=='20200318_60645664b1ea087b6acaf3b6caa6a4cad3704637_5231']
# 954 rows, must be exact same as the ones above, when looking for duplicates

#%% this is a different new_tid_subid than the one with duplicates
i_newtid = t_forSwapping_r[t_forSwapping_r['row_uid'].isna()] # swap_destination main_4274941_destination and swap_point_id_t 525
print(i_newtid.new_tid_subid.unique()) # 20201120_8c3cc91959f9c95e673fcc2c4692d54614e56d6c_7325

#%%
#t_forSwapping_r.swap_destination.unique() # 23033
t_forSwapping_r.swap_origin.unique() #23082

#%%
# question is, how did they affect downstream processing
# do they have point ids before and after?

#%%
t_forSwapping_r.new_tid_subid.nunique() # 19189 new_tids - ONE is problmatic


#%% are the duplicates a problem? Can I fix this?


#%%
counts = t_forSwapping.groupby('tid_subid').size().reset_index(name='n')
counts.n.min() # there is trajectories with 1 point
#%%
trajectory_sizes = counts['n'].value_counts().sort_index()
trajectory_sizes 
# 168 trajectories have one point only <--- this cannot be split!
# 204 have 2 points
# 175 have 3 points 

# must remove those trajectories from the df, but also from being a helper or main...
# main problem is tails not having a point, i.e., non-extistent tail
#%% look at the duplicates - can I drop thm 




#%%
od_dict
# some have two destination (1 by manual inspection)
# some have nan (479586: [nan], 3 or 4 by manual inspection)
# look at the keys that have no destination?



#%% look at some swapped trajectories in Q
# don't look at 
# duplicates: 20200318_60645664b1ea087b6acaf3b6caa6a4cad3704637_5231
# nan row_uid: 20201120_8c3cc91959f9c95e673fcc2c4692d54614e56d6c_7325
t_forSwapping_r = pd.read_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping_PredefinedSwaps\locBug_addedDuplicates/t_forSwapping_duplicatesWhenIndexOUtOfBound.parquet")
t = t_forSwapping_r[t_forSwapping_r['new_tid_subid'] == '20201120_8c3cc91959f9c95e673fcc2c4692d54614e56d6c_7325']
print(t.swap_n.unique())
print(t.tid_subid.unique())
print(t.swap_SwappingHeadTail.unique())
t.sort_values(by="row_uid")

# "last point" is nan, last based on index
# head and tail etc is also nan
# this is why this tid has no tail, only main

#%%
t_forSwapping_r['swap_SwappingHeadTail'] = t_forSwapping_r['swap_SwappingHeadTail'].replace("nan", np.nan)
t_forSwapping_r[t_forSwapping_r['swap_SwappingHeadTail'].isna()]
#%%
t_forSwapping_r['swap_SwappingHeadTail'].value_counts(dropna=False)
#False          1825816 --> never swapped, False is the iniatl state

#tail_helper    1809530
#head_main      1752634

#head_helper    1176263
#tail_main       767812

#NaN                  1 --> index issue

# tail and head numbers not the same...

#%% look at one in Q
import pandas as pd

exclude = [
    "20201120_8c3cc91959f9c95e673fcc2c4692d54614e56d6c_7325",
    "20200318_60645664b1ea087b6acaf3b6caa6a4cad3704637_5231"
]

# Step 1: remove excluded new_tid_subid values
df_filtered = t_forSwapping_r[~t_forSwapping_r['new_tid_subid'].isin(exclude)]

# Step 2: find tid_subid groups with multiple unique new_tid_subid
group_counts = df_filtered.groupby('tid_subid')['new_tid_subid'].nunique()
valid_tid_subid = group_counts[group_counts > 1].index

# Step 3: filter to only these valid tid_subid groups
df_valid = df_filtered[df_filtered['tid_subid'].isin(valid_tid_subid)]

# Step 4: sample a single new_tid_subid
sampled_new_tid_subid = df_valid['new_tid_subid'].sample(1).iloc[0]

sample_swapped_df = df_valid[df_valid['new_tid_subid']==sampled_new_tid_subid]
print(sample_swapped_df.new_tid_subid.nunique())
print(sample_swapped_df.tid_subid.nunique())
sample_swapped_df

#%% attach geometry back
print(len(sample_swapped_df))
sample_swapped_gdf = t_forSwapping[['row_uid', 'match_geometry']].merge(sample_swapped_df, on="row_uid", how="inner")
print(len(sample_swapped_gdf))
print(type(sample_swapped_gdf))
#%%
sample_swapped_gdf = sample_swapped_gdf.sort_values(by="swap_point_id_t")
sample_swapped_gdf
#%% export to look at in Q
sample_swapped_gdf.to_parquet(r"D:\paper3\debugging/sample_Swapped_indexbugcode.parquet")






#%% NEW APPROACH: CONNECT SWAPPING PAIRS BEFORE SWAP? i.e., move synthetic points with swap
# we know that head and tail is split so that the swapping point remains as the last point of the head
# ...
# hence all synthetic points will be part of the tail
import geopandas as gpd
import pandas as pd
t_forSwapping = gpd.read_parquet(r"d:\paper3\Data\output\CloakingBasedSwapping\t_forSwapping.parquet")
t_helper_random_assigned = pd.read_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping/CloakingGaps_swappingPairs_PointLevel.parquet")
t_helper_random_assigned

#%%
import numpy as np
t_forSwapping_r = t_forSwapping[['row_uid', 'tid_subid']].copy()
t_forSwapping_r['orig_tid_subid'] = t_forSwapping_r['tid_subid'].copy()
t_forSwapping_r['new_tid_subid'] = t_forSwapping_r['tid_subid'].copy()
t_forSwapping_r['swap_SwappingHeadTail'] = False
t_forSwapping_r['SwappingHeadTail'] = False
t_forSwapping_r['swap_n'] = 0
t_forSwapping_r['swap_origin'] = pd.Series(dtype='string')
t_forSwapping_r['swap_destination'] = pd.Series(dtype='string')
t_forSwapping_r['swap_point_id_t'] = np.nan

# prep data lookup
swapping_pairs = dict(zip(t_helper_random_assigned['main_row_uid'],
                   t_helper_random_assigned['helper_row_uid'])) # dictonaires are unoarded

point_to_tid_dict = dict(zip(t_forSwapping_r['row_uid'],
                   t_forSwapping_r['new_tid_subid'])) # tid_subid assignments change after swapping!
print(len(point_to_tid_dict)==len(t_forSwapping_r))
point_to_tid_dict # point id (row_uid) and the tid it belongs to, one entry per df row/point

#%%
from tqdm.auto import tqdm
#for main_sid, helper_sid in tqdm(swapping_pairs.items(), desc="Processing swaps"):
# run for 5 to test logic
from itertools import islice
for main_sid, helper_sid in islice(swapping_pairs.items(), 2): 
    print('main <--> helper', main_sid, helper_sid) # but looping is slow, mapping might be better...

    # (1) isolate the swapping pair from main df
    # get tid_subid for both main and helper
    main_tid = point_to_tid_dict[main_sid]
    #print('tid of main', main_tid)
    helper_tid = point_to_tid_dict[helper_sid] # BUT TID OF POINT WILL CHANGE - build dict at the beginning of each loop?
    #print('tid of helper', helper_tid)

    # subset by tid and reset index
    main = t_forSwapping_r[t_forSwapping_r['new_tid_subid'] == main_tid].reset_index(drop=True)
    #print('len of main', len(main))
    #print('max index of main', main.index.max())
    helper = t_forSwapping_r[t_forSwapping_r['new_tid_subid'] == helper_tid].reset_index(drop=True)

     # (2) split main and helper into heads and tail
    m_cut_index = main.index[main["row_uid"] == main_sid][0]
    #print('m_cut_index', m_cut_index)
    h_cut_index = helper.index[helper["row_uid"] == helper_sid][0]
    #print('h_cut_index', h_cut_index)

    # general split
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
    
    # split to track swapps
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

    # record origin destination for these swaps!
    main_origin_i = m_cut_index
    main_destintaion_i = h_cut_index+1
    helper_origin_i = h_cut_index
    helper_destination_i = m_cut_index+1
    # but this is the index, the index will change
    # so update df now when index is still correct
    # LOC ADS ROWS IF THERE IS NO ROW WITH THAT INDEX
    main.loc[main_origin_i, "swap_origin"] = f'main_{main_sid}_origin'
    main.loc[helper_destination_i, "swap_destination"] = f'helper_{helper_sid}_destination'
    helper.loc[helper_origin_i, "swap_origin"] = f'helper_{helper_sid}_origin'
    helper.loc[main_destintaion_i, "swap_destination"] = f'main_{main_sid}_destination'

    # need to record row_uid of these instead 
    # - only if I wanted to store these pairs as a dictonary rather than flags in the df
    main_origin_id =  main.at[m_cut_index, "row_uid"] 
    main_destintaion_id = helper.at[(h_cut_index+1), "row_uid"] 
    helper_origin_id = helper.at[h_cut_index, "row_uid"]
    helper_destination_id = main.at[(m_cut_index+1), "row_uid"]  
    #print('point ids of origin and destinations')  
    #print('main origin', main_origin_id, 'to destination (helper): ', main_destintaion_id)
    #print('helper origin', helper_origin_id, 'to destination (helper): ', helper_destination_id)
    # update origin destination dict
    #od_dict.update({
    #    main_origin_id: main_destintaion_id, # key already exists in dict and value will  be overwritten
        # helper_origin_id: helper_destination_id # key should not exist in dict unless helper origin pt is also a main, is added to the dict (unless a main hase the same id, then main gets overwritten)
        # save way to handle helpers potentially being a main: add _h, can remove this later
    #    helper_origin_id.astype(str)+"_h": helper_destination_id
        # could also store values as list to not overwrite key-value pair
    #})
    od_dict[main_origin_id].append(main_destintaion_id)
    od_dict[helper_origin_id].append(helper_destination_id)
    # can chain O-D when D is also an O: O-D-D or decide to drop intermediate D and have OD2 instead?
    # can record O-D-D for now and later decide to drop D




