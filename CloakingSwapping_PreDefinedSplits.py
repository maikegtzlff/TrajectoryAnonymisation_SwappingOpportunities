#%%
import geopandas as gpd
import pandas as pd
t_forSwapping = gpd.read_parquet(r"d:\paper3\Data\output\CloakingBasedSwapping\t_forSwapping.parquet")
valid_assigned_helpers_df = pd.read_parquet(r"d:\paper3\Data\output\CloakingBasedSwapping\valid_assigned_helpers_df.parquet")

#%% have found the matching helper trajectory segment 
# but must actually identify a splitting point outside the swapping loop

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

#%% how many potential helpers do we have per clk gap?
print(len(t_helper))
print(t_helper.main_row_uid.nunique())

t_helper_count = t_helper.groupby('main_row_uid')['helper_row_uid'].nunique().reset_index(name="n_helper")
print(t_helper_count.n_helper.min())
print(t_helper_count.n_helper.median()) # 2
print(t_helper_count.n_helper.max()) # 1818 <-- one cloaking gap has a lot of possible swapping partners 

Q1 = t_helper_count['n_helper'].quantile(0.25)
Q3 = t_helper_count['n_helper'].quantile(0.75)
IQR = Q3 - Q1

lower = Q1 - 1.5 * IQR
upper = Q3 + 1.5 * IQR

t_no_outliers = t_helper_count[(t_helper_count['n_helper'] >= lower) & (t_helper_count['n_helper'] <= upper)]
t_no_outliers.n_helper.hist()


#%% a main_row_uid can't be a helper
print(t_helper['helper_row_uid'].isin(t_helper.main_row_uid.unique()).any()) # True, can't be true!
#t_helper[t_helper['helper_row_uid'].isin(t_helper['main_row_uid'])].sort_values(['helper_row_uid']).to_csv(r"\\tsclient\R\paper3\fromVM_201\debugging/helperPointAssignment.csv")
t_helper[t_helper['helper_row_uid'].isin(t_helper['main_row_uid'])].sort_values(['helper_row_uid'])
# not all potential helpers for that main_row though
# shows the helpers where the helper is a main_row, does not chow the main_row_uid istels

# must figure out if these main_row_uids, the ones that would be served by a helper that IS a main row have alternative points 
# realsitically they won't as helper tid and cloaking area have been pre-filtered already...

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

#%% look at helper ckl and main clk area
print(valid_assigned_helpers_df.head(1)) 
# main_row_uid 5365117 will get a helper from tid_subid 20191108_7cf738514ffcb46516c2982ca9abf6b221c17...
# at the cloaking area 2_6ceae7098142cdba6ebd5c5927c31066f1505482 for any point with time_bin 0
# look at the potential helpers
ph_t = t_helper[t_helper['main_row_uid']==5365117].copy()
print('number of potential split points', ph_t.helper_row_uid.nunique())
print('ensuring it is the same clk area (2_6ceae7098142cdba6ebd5c5927c31066f1505482)', ph_t.helper_clkpassed.unique())
print(ph_t.time_bin.unique(), 'should be 0')
print(ph_t.helper_tid_subid.unique(), 'expected 20191108_7cf738514ffcb46516c2982ca9abf6b221c17...')

ph_t # all valid helper points, could pick any of these at random

#%% now do the same for a helper that has a main_row_uid as their helper
print(mah_id_df.head(1))
# helper 124095 - which must also be a main
# helps main 5306703
# time bin 3
# helper_tid_subid 20190905_7cf738514ffcb46516c2982ca9abf6b221c17...
# helper_clkpassed 1_6ceae7098142cdba6ebd5c5927c31066f1505482
ph_tm = t_helper[t_helper['main_row_uid']==5306703].copy()
print('number of potential split points', ph_tm.helper_row_uid.nunique())
print('ensuring it is the same clk area (1_6ceae7098142cdba6ebd5c5927c31066f1505482)', ph_tm.helper_clkpassed.unique())
print(ph_tm.time_bin.unique(), 'should be 0')
print(ph_tm.helper_tid_subid.unique(), 'expected 20190905_7cf738514ffcb46516c2982ca9abf6b221c17...')

ph_tm # only one point, that point is  helper 124095 - which must also be a main

#%% look at that main
t_forSwapping[t_forSwapping['row_uid'] == 124095][['row_uid', 'tid_subid', 'time_bin', 'Sensitive_CloakingAreaId', 'intersecting_cloaking_ids']]
# own clk area is 2_7cf738514ffcb46516c2982ca9abf6b221c17146
# but intersects with 1_6ceae7098142cdba6ebd5c5927c31066f1505482 - for which it becomes a helper!
# main is tid   20190905_7cf738514ffcb46516c2982ca9abf6b221c17

# what is the tid of the main it helps
#t_forSwapping[t_forSwapping['row_uid'] == 5306703][['row_uid', 'tid_subid']]#, 'time_bin', 'Sensitive_CloakingAreaId', 'intersecting_cloaking_ids']]
#               20200717_6ceae7098142cdba6ebd5c5927c31066f1505
# both come from different tids - good

#%% for those problematic "main helpers" look at the alternatives, do they also intersect with the main sensitive cloaking area? are there options that do not intersect with the main cloaking area
# mah_id_df mains (main_row_uid) with mains (helper_row_uid) as helpers

print(len(mah_id_df)) #1473
print(mah_id_df.helper_row_uid.nunique()) # 1473 potential helpers to mains where at least one helper is a main themselves
print(mah_id_df.main_row_uid.nunique()) # 61 mains have these main helper issues
# helper_clkpassed is the mains sensitive cloaking area
# must now if all helper options for that main have passed this cloaking area


#%% look at all options for mains that have a main as their helper
# from 'mains as helpers' get the 'problematic' mains to look for alterantives
# are all helpers mains?
mains_list = valid_assigned_helpers_df.main_row_uid.unique()
(set(mah_id_df.helper_row_uid.unique()).issubset(set(mains_list))) # False, not all the helpers are mains (good)

mah_id_df['helper_is_main'] = mah_id_df['helper_row_uid'].isin(mains_list)
# look at the alterantives per main_row_uid 
# must have passed the helper_clkpassed geometry, otherwise they wouldn't have been assigned
#%%I want to know which other clk they passed - i.e., did they pass the main clk area that has been assigned to be a helper
#mah_id_df'helper_main_clk_sen'
hm_list = mah_id_df[mah_id_df['helper_is_main'] == True]['helper_row_uid'].unique() #122 helpers are also mains
# for these main helpers, get their sensitive cloaking id
hm_clkid = t_forSwapping[t_forSwapping['row_uid'].isin(hm_list)][['row_uid', 'Sensitive_CloakingAreaId']]
hm_clkid = hm_clkid.rename(columns={'row_uid':'helper_row_uid'})
# add these back to df
mah_id_df = mah_id_df.merge(hm_clkid, on ="helper_row_uid", how='left')
#%% now, also add all intersecting clkPassed of helper point, to determine whether the point overlaps with the clk of main
mah_allcklpssd = t_forSwapping[t_forSwapping['row_uid'].isin(mah_id_df.helper_row_uid.unique())][['row_uid', 'intersecting_cloaking_ids']]
mah_allcklpssd = mah_allcklpssd.rename(columns={'row_uid':'helper_row_uid'})
mah_id_df = mah_id_df.merge(mah_allcklpssd, on ="helper_row_uid", how='left')
mah_id_df

#%%
agg_df = mah_id_df.groupby('helper_tid_subid')['Sensitive_CloakingAreaId'] \
           .apply(lambda x: list(x.dropna().unique())) \
           .reset_index() \
           .rename(columns={'Sensitive_CloakingAreaId': 'Sensitive_CloakingAreaId_OfHelperMain'})
#agg_df['num_values'] = agg_df['Sensitive_CloakingAreaId_OfHelperMain'].apply(len) # all 1
mah_id_df = mah_id_df.merge(agg_df, on='helper_tid_subid', how='left')
mah_id_df

#%%
mah_id_df['helper_intersectingMainhelperclk'] = mah_id_df.apply(
    lambda row: any(val in row['intersecting_cloaking_ids'] for val in row['Sensitive_CloakingAreaId_OfHelperMain']),
    axis=1
)
#%%
mah_id_df = mah_id_df.sort_values(['main_row_uid', 'helper_row_uid'])

#%% look at one of them
th = mah_id_df[mah_id_df['main_row_uid']==143114] # 35 helper options, one of them is a main itself
print(len(th))
th
# none overlap with the sensitive clk area of the main helper, but that is probably because the area is cloaked...
# there are gaps in helper_row_uid
# the main helper is helper_row_uid 5164107
# but helper_row_uid "segments" based on continous row_uid are
# 586
# 755
# 101 to 107 <-- helper is last point of this "segment" of potential helpers
# 128 to 153
# when chosing a helper to split at, pick one from the segments that the "main" helper is not part of

#%% segment helpers
th['segment_helper_row_uid'] = th.groupby('main_row_uid')['helper_row_uid'] \
                                 .transform(lambda x: (x.diff() > 1).cumsum() + 1)
th

#%% class segment as main helper or not
th['segment_helper_is_main'] = th.groupby('segment_helper_row_uid')['helper_is_main'] \
                                  .transform('any')
th

#%%
def pick_helper(group):
    # 1st prioroity: segment is not part of main as helper
    candidates = group[group['segment_helper_is_main'] == False]
    if len(candidates) > 0:
        return candidates.sample(1)['helper_row_uid'].iloc[0]
    # 2nd priority: segment can be part of main as helper, but point itself isnt
    fallback = group[group['segment_helper_is_main'] == True]
    preferred = fallback[fallback['helper_is_main'] == False]
    if len(preferred) > 0:
        return preferred.sample(1)['helper_row_uid'].iloc[0]
    # final pick: only helper_is_main == True available
    return fallback.sample(1)['helper_row_uid'].iloc[0]


selected_helpers = (
    th.groupby('main_row_uid', group_keys=False)
      .apply(pick_helper)
      .reset_index(name='selected_helper_row_uid')
)
selected_helpers

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
      .apply(pick_helper)
      .reset_index(name='selected_helper_row_uid')
)
selected_mahelpers

#%% now pick a random point for the unproblematic helpers
# remove problematic helpers from sample
print(t_helper.main_row_uid.nunique())
#mah_id_df = t_helper[t_helper['main_row_uid'].isin(mah_id)] # helpers which are also mains, or as the name suggests mains as helpers
print(mah_id_df.main_row_uid.nunique())
random_t_helper_pool = t_helper[~t_helper['main_row_uid'].isin(mah_id)] # helpers which are unproblematic (aka not a main themselves)
print(random_t_helper_pool.main_row_uid.nunique())
print((random_t_helper_pool.main_row_uid.nunique()+mah_id_df.main_row_uid.nunique()) == t_helper.main_row_uid.nunique())

# randomly pick unproblematic helpers
t_helper_random = random_t_helper_pool.groupby('main_row_uid', group_keys=False).sample(n=1)
# only want a record of main_row_uid and helper_row_uid
t_helper_random = t_helper_random[['main_row_uid', 'helper_row_uid']]
print(len(t_helper_random))
t_helper_random
#%%  reunite helper selection
selected_mahelpers = selected_mahelpers.rename(columns={'selected_helper_row_uid': 'helper_row_uid'})
# append  these to t_helper_random because I want them to be swapped last, incase it is a main that is acting as a helper
t_helper_random_assigned = pd.concat([t_helper_random, selected_mahelpers]).reset_index()
t_helper_random_assigned # len 11549 
#%% export swapping pairs
t_helper_random_assigned.to_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping/CloakingGaps_swappingPairs_PointLevel.parquet")



#%% SWAPPING
import geopandas as gpd
import pandas as pd
t_forSwapping = gpd.read_parquet(r"d:\paper3\Data\output\CloakingBasedSwapping\t_forSwapping.parquet")
t_helper_random_assigned = pd.read_parquet(r"D:\paper3\Data\output\CloakingBasedSwapping/CloakingGaps_swappingPairs_PointLevel.parquet")


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



#%%
swapped_df.to_csv(r"\\tsclient\R\paper3\fromVM_201\debugging/swapped_df_sorted4.csv")
