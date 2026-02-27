#%% CLOAKING GEOMETRIES - by user
import geopandas as gpd
import pandas as pd
from pathlib import Path

folder = Path(r"D:\paper3\Data\cloaking_geom")
parquet_files = list(folder.glob("*.parquet"))

gdfs = []

for f in parquet_files:
    gdf = gpd.read_parquet(f)

    # Identify the geometry column
    geom_col = 'cloaking_geometry'
    if geom_col not in gdf.columns:
        raise ValueError(f"{geom_col} not found in {f}")

    # If GeoDataFrame has no CRS, try to guess based on coordinate ranges
    gdf = gpd.GeoDataFrame(gdf, geometry=geom_col)
    coords = gdf.geometry.apply(lambda g: g.exterior.coords[0])
    # simple check: if |x|<180 -> likely WGS84, else NZTM
    if gdf.crs is None:
        if all(abs(x) <= 180 and abs(y) <= 90 for x, y in coords):
            gdf.set_crs(epsg=4326, inplace=True)
        else:
            gdf.set_crs(epsg=2193, inplace=True)

    # Convert to common CRS
    gdf = gdf.to_crs(epsg=2193)

    # Optional: remove invalid geometries
    gdf = gdf[gdf.is_valid]

    gdfs.append(gdf)

# Concatenate
cloakinggeom = pd.concat(gdfs, ignore_index=True)
cloakinggeom = gpd.GeoDataFrame(cloakinggeom, geometry='cloaking_geometry', crs=2193)

print(cloakinggeom.crs)
cloakinggeom.head()

#%% cloakinggeom has cluster_id and RANK and uid
# --> can get rank per uid
cloakinggeom["uid"] = cloakinggeom["cluster_id"].str.split("_").str[0]
cloakinggeom["cloakingArea_id"] = cloakinggeom["rank"].astype("Int64").astype(str) + "_" + cloakinggeom["uid"] 
cloakinggeom.head()

#%%
cloakinggeom.to_parquet(r"d:\paper3\Data\trajectories\cloakingGeom_2sigLoc_100150m.parquet")



# TRAJECTORY POINTS, NOT CLOAKED, SENSITIVE POINTS, BOTH MAP-MATCHED AND RAW GEOMETRY (and MCP)
#%% look at my trajectories: ideally before sensitive vs nan, but raw vs synthetic also works
import geopandas as gpd
t = gpd.read_parquet(r"d:\paper3\Data\trajectories\mapmatched_150kmh_onOsmid.parquet")
t.head()

# I think this might not be clipped to Akl council - doesn't matter, only assigning gap-labels to cloaking geometries


#%%
# t.cloaking_sigloc.unique() --> indicates sensitivy level of point!
# --> can get rank per uid
t["sensitivity_rank"] = (
    t["cloaking_sigloc"]
    .str.extract(r'(\d+)')      # get 1 or 2 from the string
    .astype("Int64")            # nullable integer (keeps None as <NA>)
)
print(t.sensitivity_rank.unique())

import pandas as pd
t["rank_uid"] = pd.NA
mask = t["sensitivity_rank"].notna()
t.loc[mask, "rank_uid"] = (
    t.loc[mask, "sensitivity_rank"].astype(int).astype(str)
    + "_" +
    t.loc[mask, "uid"].astype(str)
)



#%% (1) check cloaking geometry: do they somehow align
# now I have sensitive points linked to their uid and rank - same id should align points and cloaking geometeries!
#points = t[t["rank_uid"].notna()].copy()
#polys  = cloakinggeom[cloakinggeom["rank_uid"].notna()].copy()

# Reproject to WGS84 for Folium
#points = points.set_geometry("match_geometry").to_crs(4326)
#polys  = polys.set_geometry("cloaking_geometry").to_crs(4326)
# look at these in Q
#points.to_parquet(r'D:\paper3\Data\tetsing/points.parquet')
#polys.to_parquet(r"D:\paper3\Data\tetsing/polys.parquet")

# looking good, the ones outside the cloaking area are becuase of map-matching but

#%% correct gap_label
# only look at valid gp_Labels though
# i.e., there MUST be sensitive poinst between first and last
import pandas as pd
import numpy as np

t = t.sort_values(['tid','tid_subid', 'point_id_t'])
t['cloaking'] = t['cloaking'].replace({None: np.nan})



def compute_gap_label_valid(group):

    group = group.copy()
    group['gap_label_valid'] = np.nan
    group['gap_label_valid'] = group['gap_label_valid'].astype(object)

    # sensitive mask
    is_sensitive = group['cloaking'] == 'sensitive'
    non_sensitive = ~is_sensitive

    # trajectory structure
    cloaking_prev = is_sensitive.shift(1, fill_value=False)
    cloaking_next = is_sensitive.shift(-1, fill_value=False)

    # -------------------------
    # 1. STRUCTURE-BASED LABELS
    # -------------------------

    # start of a gap
    mask_first = non_sensitive & cloaking_prev
    group.loc[mask_first, 'gap_label_valid'] = 'first'

    # end of a gap
    mask_last = non_sensitive & cloaking_next
    group.loc[mask_last, 'gap_label_valid'] = 'last'

    # single-point gap
    mask_first_last = non_sensitive & cloaking_prev & cloaking_next
    group.loc[mask_first_last, 'gap_label_valid'] = 'first, last'

    # -------------------------
    # 2. ONLY USE gap_label
    #    WHERE STRUCTURE IS
    #    AMBIGUOUS
    # -------------------------

    no_structure = non_sensitive & ~cloaking_prev & ~cloaking_next

    group.loc[no_structure & (group['gap_label'] == 'first'), 'gap_label_valid'] = 'first'
    group.loc[no_structure & (group['gap_label'] == 'last'),  'gap_label_valid'] = 'last'

    # -------------------------
    # 3. ENSURE SENSITIVE
    #    NEVER GET LABELLED
    # -------------------------

    group.loc[is_sensitive, 'gap_label_valid'] = np.nan

    return group

# apply by tid
t = t.groupby('tid', group_keys=False).apply(compute_gap_label_valid)
print(t.gap_label_valid.unique()) 


#%% lok at this tid 20190104_47304939bf6162effb1f812959fb20398a098145_13
pd.set_option('display.max_rows', None)
tid_t = t[t['tid_subid'] == '20190104_47304939bf6162effb1f812959fb20398a098145_13'].copy()
tid_t[['tid_subid','point_id_t','gap_label','cloaking','gap_label_valid']]

#pd.reset_option('display.max_rows')


#%% there can be consecutive gap labels, i.e., one point after leaving a cloaing area,
# next point is the last one before re-enetering the cloaking area
def assign_gap_label_pair(df):
    df = df.copy()
    
    def pair_within_group(group):
        group = group.copy()
        pair_labels = [np.nan] * len(group)
        counter = 1

        for i, val in enumerate(group['gap_label_valid']):
            if pd.isna(val):
                continue

            # single 'last'
            if val == 'last':
                pair_labels[i] = f'last_{counter}'

            # single 'first'
            elif val == 'first':
                pair_labels[i] = f'first_{counter}'
                counter += 1  # increment counter after closing the pair

            # 'first, last' → assign first to current counter, last to next counter
            elif val in ['first, last', 'first,last', 'first / last']:
                first_num = f'first_{counter}'
                counter += 1
                last_num = f'last_{counter}'
                pair_labels[i] = f'{first_num}, {last_num}'

            else:
                raise ValueError(f"Unexpected gap_label_valid: {val}")

        group['gap_label_pair'] = pair_labels
        return group

    return df.groupby('tid_subid', group_keys=False).apply(pair_within_group)

t = assign_gap_label_pair(t)

#%%
print(t.gap_label_pair.unique())
print(t.gap_label_valid.unique())

pd.set_option('display.max_rows', None)
tid_t = t[t['tid_subid'] == '20190104_47304939bf6162effb1f812959fb20398a098145_13'].copy()
tid_t[['tid_subid','point_id_t','gap_label','cloaking','gap_label_valid', 'gap_label_pair']]



#%% adding cloaking geom id to gap_label
# extend the values of rank_uid to one row above and one below aka last and first
# staying within same tid
# sort first
t = t.sort_values(['tid', 'tid_subid', 'point_id_t'])

# group
g = t.groupby('tid')

# prev / next rank_uid within tid
prev = g['rank_uid'].shift(1)
next_ = g['rank_uid'].shift(-1)

# start fresh
t['rank_uid_firstLast_tid'] = np.nan

# masks
mask_first = t['gap_label_valid'] == 'first'
mask_last  = t['gap_label_valid'] == 'last'
mask_both  = t['gap_label_valid'] == 'first, last'

# assign values
t.loc[mask_first, 'rank_uid_firstLast_tid'] = prev[mask_first]
t.loc[mask_last,  'rank_uid_firstLast_tid'] = next_[mask_last]

# for 'first, last' assign a tuple (prev, next_)
both_values = pd.Series(
    list(zip(prev[mask_both], next_[mask_both])),
    index=t.index[mask_both]
)
t.loc[mask_both, 'rank_uid_firstLast_tid'] = both_values

#%% simplify tuples
mask_both = t['gap_label_valid'] == 'first, last'

def simplify_tuple(x):
    if isinstance(x, tuple):
        return x[0] if x[0] == x[1] else x
    return x

t.loc[mask_both, 'rank_uid_firstLast_tid'] = t.loc[mask_both, 'rank_uid_firstLast_tid'].apply(simplify_tuple)
#%%
pd.set_option('display.max_rows', None)
tid_t = t[t['tid_subid'] == '20190104_47304939bf6162effb1f812959fb20398a098145_13'].copy()
tid_t[['point_id_t','cloaking', 'gap_label_pair', 'rank_uid', 'rank_uid_firstLast_tid']]

#%% save to parquet
# Convert all tuple/object columns to strings if necessary
for col in t.columns:
    if t[col].dtype == 'object':
        # Only convert if there is a tuple inside
        if t[col].apply(lambda x: isinstance(x, tuple)).any():
            t[col] = t[col].apply(lambda x: str(x) if x is not None else None)

#%% 
t.to_parquet(r"d:\paper3\Data\trajectories\mapmatched_150kmh_onOsmid_CloakingGeomIDPairs.parquet")

#%%
import geopandas as gpd
t = gpd.read_parquet(r"d:\paper3\Data\trajectories\mapmatched_150kmh_onOsmid_CloakingGeomIDPairs.parquet")

#%% nan must be np nan and not strings
import numpy as np
import pandas as pd

def fix_missing(x):
    # Keep tuples as is
    if isinstance(x, tuple):
        return x
    # Convert anything that is None, pd.NA, or a placeholder string to np.nan
    if x is pd.NA or x is None:
        return np.nan
    if isinstance(x, str) and x.lower() in ['<NA>', 'nan', 'none', '']:
        return np.nan
    return x

t['rank_uid_firstLast_tid'] = t['rank_uid_firstLast_tid'].apply(fix_missing)

print(t['rank_uid_firstLast_tid'].isna().sum())
t['rank_uid_firstLast_tid'].head()


#%%
#%% quality control: have all gap_labels been assigned a cloaking_id (YES, because gap_label has been corrected)
total_gap = t['gap_label_valid'].notna().sum()
missing_rank_uid = t.loc[t['gap_label_valid'].notna() & t['rank_uid_firstLast_tid'].isna()].shape[0]
percent_missing = missing_rank_uid / total_gap * 100
print(f"{missing_rank_uid} rows out of {total_gap} ({percent_missing:.2f}%) have a valid gap_label but no rank_uid_firstLast_tid")
# 354 rows out of 114273 (0.31%) have a valid gap_label but no rank_uid_firstLast_tid

#%%
# Only keep the columns we need for this check
cols = ['tid', 'tid_subid', 'point_id_t', 'gap_label_valid', 'rank_uid_firstLast_tid']
t_small = t[cols].copy()
t_small = t_small.sort_values(['tid_subid', 'point_id_t']).reset_index()

# mask for missing rank_uid_firstLast_tid
mask_missing = t_small['gap_label_valid'].notna() & t_small['rank_uid_firstLast_tid'].isna()

# indices of missing rows
missing_idx = t_small.index[mask_missing].to_numpy()


# indices of previous rows
prev_idx = missing_idx - 1
# indices of next rows
next_idx = missing_idx + 1

# filter out-of-bounds indices
prev_idx = prev_idx[prev_idx >= 0]
next_idx = next_idx[next_idx < len(t_small)]

# only keep neighbors with same tid_subid
prev_idx = prev_idx[t_small.loc[prev_idx, 'tid'].values == t_small.loc[prev_idx + 1, 'tid'].values]
next_idx = next_idx[t_small.loc[next_idx, 'tid'].values == t_small.loc[next_idx - 1, 'tid'].values]

import pandas as pd
all_idx = pd.Index(missing_idx).union(prev_idx).union(next_idx)
inspect_mask = t.index.isin(t_small.loc[all_idx, 'index'])
t.loc[inspect_mask, :].head(50)

#%%
t.loc[inspect_mask, :].sensitivity_rank.unique() # all nan, no matter whetehr looking at tid or tid_subid

#%% 354 rows out of 114273 (0.31%) have a valid gap_label but no rank_uid_firstLast_tid
# I suspect that all of these gap labels have been assigned incorrectly - so ignore them

t['gap_label_valid_final'] = t['gap_label_valid'].where(t['rank_uid_firstLast_tid'].notna(), np.nan)
t['gap_label_pair_final']  = t['gap_label_pair'].where(t['rank_uid_firstLast_tid'].notna(), np.nan)


total_gap = t['gap_label_valid_final'].notna().sum()
missing_rank_uid = t.loc[t['gap_label_valid_final'].notna() & t['rank_uid_firstLast_tid'].isna()].shape[0]
percent_missing = missing_rank_uid / total_gap * 100
print(f"{missing_rank_uid} rows out of {total_gap} ({percent_missing:.2f}%) have a valid gap_label_final but no rank_uid_firstLast_tid")
#0 rows out of 113919 (0.00%) have a valid gap_label_final but no rank_uid_firstLast_tid

#%%
t.to_parquet(r"d:\paper3\Data\trajectories\mapmatched_150kmh_onOsmid_CloakingGeomIDPairs_GapLabelsFinal.parquet")



#%% (2) # add cloaking geom id to trajectory gdf used for swapping (must seperate synthetic points before swapping)
import geopandas as gpd
gdf = gpd.read_parquet(r"d:\paper3\Data\trajectories\traj_filled_baseline_ShiftedTimestamps_gapAware.parquet")

#%% differentiate between synthetic and raw points
# based on syn point id
print(gdf['syn_point_id_t'].isna().equals(
    gdf['synpoint_id'].isna()
))

import numpy as np
gdf['point_type'] = np.where(
    gdf['synpoint_id'].isna(),
    'raw',
    'synthetic'
)

print(gdf['point_type'].unique())

# this is where synpoint_id comes from
# # assign sequential index per odid
# #d_syn_points_gdf["synpoint_id"] = d_syn_points_gdf.groupby("odid").cumcount() + 1 
# so this is a point id for synthetic points only (in theory)

# syn_point_id_t should also only be for synthetic points though
# syn_points_gdf_1sec['syn_point_id_t'] = syn_points_gdf_1sec['time_sec_sinceOrigin']

# classification could also be based on these columns
# only synthetic poinst should have a dest_point_id_t value
#print(gdf.dest_point_id_t.notna().sum()) #523739
#gdf.point_type.value_counts() 
# same numver as point_type synthetic
#point_type
#raw          6811202
#synthetic     523739

# or odid (origin destination id used to calculate shortest path on which synthetic trajecory points are placed)
#print(gdf.odid.notna().sum()) # also the same 523739
#gdf.loc[gdf.odid.notna(), 'odid'].unique()

#%% must upadte gap_label for gdf to include one-point sequences inbetween cloaking gaps
print(gdf.gap_label.unique())


import pandas as pd
import numpy as np

gdf = gdf.sort_values(['tid','tid_subid', 'point_id_t'])

gdf['cloaking'] = np.where(
    gdf['point_type'] == 'synthetic',
    'sensitive', 
    np.nan         
)

print(gdf['cloaking'].unique())

#%%
import numpy as np

def compute_gap_label_valid(group):
    """
    Compute gap_label_valid for a single trajectory (group by tid).
    Only assigns the new column; does not touch any existing columns.
    """
    group = group.copy(deep=False)  # shallow copy; avoids overwriting other columns

    # Initialize new column as object type
    group['gap_label_valid'] = np.nan
    group['gap_label_valid'] = group['gap_label_valid'].astype(object)

    # sensitive mask (do not modify original column!)
    is_sensitive = group['cloaking'] == 'sensitive'
    non_sensitive = ~is_sensitive

    # trajectory structure
    cloaking_prev = is_sensitive.shift(1, fill_value=False)
    cloaking_next = is_sensitive.shift(-1, fill_value=False)

    # -------------------------
    # 1. STRUCTURE-BASED LABELS
    # -------------------------

    # single-point gaps first
    mask_first_last = non_sensitive & cloaking_prev & cloaking_next
    group.loc[mask_first_last, 'gap_label_valid'] = 'first, last'

    # start of a multi-point gap
    mask_first = non_sensitive & cloaking_prev & ~cloaking_next
    group.loc[mask_first, 'gap_label_valid'] = 'first'

    # end of a multi-point gap
    mask_last = non_sensitive & ~cloaking_prev & cloaking_next
    group.loc[mask_last, 'gap_label_valid'] = 'last'

    # -------------------------
    # 2. STRUCTURE-AMBIGUOUS POINTS
    # -------------------------
    no_structure = non_sensitive & ~cloaking_prev & ~cloaking_next
    group.loc[no_structure & (group['gap_label'] == 'first'), 'gap_label_valid'] = 'first'
    group.loc[no_structure & (group['gap_label'] == 'last'), 'gap_label_valid']  = 'last'

    # -------------------------
    # 3. ENSURE SENSITIVE POINTS ARE NEVER LABELED
    # -------------------------
    group.loc[is_sensitive, 'gap_label_valid'] = np.nan

    return group[['gap_label_valid']]  # return only the new column


# apply by tid
gdf['gap_label_valid'] = gdf.groupby('tid', group_keys=False).apply(
    lambda group: compute_gap_label_valid(group)
)

print(gdf['cloaking'].unique()) 
print(gdf['gap_label_valid'].unique()) # no 'first, last" in  [nan 'last' 'first'] 

#%% no single non-sensitive point sandwhiched between two sensitive points
is_sensitive = gdf['cloaking'] == 'sensitive'
non_sensitive = ~is_sensitive

cloaking_prev = is_sensitive.shift(1, fill_value=False)
cloaking_next = is_sensitive.shift(-1, fill_value=False)

mask_first_last = non_sensitive & cloaking_prev & cloaking_next
print(mask_first_last.sum())  # 0 

# whereas t has 13565 of those sandwhiched points
is_sensitive = t['cloaking'] == 'sensitive'
non_sensitive = ~is_sensitive

cloaking_prev = is_sensitive.shift(1, fill_value=False)
cloaking_next = is_sensitive.shift(-1, fill_value=False)

mask_first_last = non_sensitive & cloaking_prev & cloaking_next
print(mask_first_last.sum())  # 13,565



#%% comparing number of non-sensitive points in the two df
num_missing_t = t['cloaking'].isna().sum() + (t['cloaking'] == 'nan').sum()
num_missing_gdf = gdf['cloaking'].isna().sum() + (gdf['cloaking'] == 'nan').sum()

print(f"t: {num_missing_t} points with cloaking NaN or 'nan'")      # 6,787,408 
print(f"gdf: {num_missing_gdf} points with cloaking NaN or 'nan'")  # 6,811,202  - more points...



#%% what about the 0.31% ones that I droped for gap_label final? will get dropped autonatically because of merge key

#%% add cloaking geometry ids for valid gap labels
gdf.rename(columns={'gap_label':'gap_label_invalid'}, inplace=True)
gdf_enriched = gdf.merge(t[['uid', 'point_id', 'point_id_t', 'gap_label_valid_final', 'gap_label_pair_final' ,'rank_uid_firstLast_tid']], left_on =['uid', 'point_id', 'point_id_t', 'gap_label_invalid'], right_on =['uid', 'point_id', 'point_id_t', 'gap_label_valid_final'], how='left')
gdf_enriched.head()

#%%
print(t.gap_label_valid_final.unique())
print(gdf_enriched.gap_label_valid_final.unique()) 
# gdf doesn't have first last either 
print(gdf.gap_label_invalid.unique())

gdf_enriched['rank_uid_firstLast_tid'].nunique()



#%% look at gap labels after mereg
# if gap_label_valid has a label but gap_label (coming from t) does not, then gap labels and point_ids do not align
# total number of valid gap_label rows
total_gap = gdf_enriched['gap_label_valid_final'].notna().sum()

# number of valid gap_label rows where rank_uid_firstLast_tid is missing
missing_rank_uid = gdf_enriched.loc[gdf_enriched['gap_label_valid_final'].notna() & gdf_enriched['rank_uid_firstLast_tid'].isna()].shape[0]

# percentage
percent_missing = missing_rank_uid / total_gap * 100

print(f"{missing_rank_uid} rows out of {total_gap} ({percent_missing:.2f}%) "
      "have a valid gap_label but no rank_uid_firstLast_tid")
#0 rows out of 65956 (0.00%) have a valid gap_label but no rank_uid_firstLast_tid



#%% why include gap_labels in merge key??
gdf_enriched2 = gdf.merge(t[['uid', 'point_id', 'point_id_t', 'gap_label_valid_final', 'gap_label_pair_final' ,'rank_uid_firstLast_tid']], left_on =['uid', 'point_id', 'point_id_t'], right_on =['uid', 'point_id', 'point_id_t'], how='left')
gdf_enriched2.head()

#%%
print(t.gap_label_valid_final.unique())
print(gdf_enriched2.gap_label_valid_final.unique()) # now includes first, last
# gdf doesn't have first last either 
print(gdf_enriched2.gap_label_invalid.unique()) 

print(gdf_enriched2['rank_uid_firstLast_tid'].nunique()) # now a few more (228, instad of 186)

#%%
#%% look at gap labels after mereg
# if gap_label_valid has a label but gap_label (coming from t) does not, then gap labels and point_ids do not align
# total number of valid gap_label rows
total_gap = gdf_enriched2['gap_label_valid_final'].notna().sum()

# number of valid gap_label rows where rank_uid_firstLast_tid is missing
missing_rank_uid = gdf_enriched2.loc[gdf_enriched2['gap_label_valid_final'].notna() & gdf_enriched2['rank_uid_firstLast_tid'].isna()].shape[0]

# percentage
percent_missing = missing_rank_uid / total_gap * 100

print(f"{missing_rank_uid} rows out of {total_gap} ({percent_missing:.2f}%) "
      "have a valid gap_label but no rank_uid_firstLast_tid")
# now 0 rows out of 113919 (0.00%) have a valid gap_label but no rank_uid_firstLast_tid
# instead of #0 rows out of 65956 (0.00%) have a valid gap_label but no rank_uid_firstLast_tid




#%%
gdf_enriched2.rename(columns={'rank_uid_firstLast_tid':'cloakingArea_id'}, inplace=True)

#%% 
gdf_enriched2.to_parquet(r"d:\paper3\Data\trajectories\traj_filled_baseline_ShiftedTimestamps_gapAware_CloakingGeomID.parquet")

#%%
import geopandas as gpd
gdf_enriched2 = gpd.read_parquet(r"d:\paper3\Data\trajectories\traj_filled_baseline_ShiftedTimestamps_gapAware_CloakingGeomID.parquet")

#%% sort by tid_subid and point_id_t, then reset index
gdf_enriched2 = gdf_enriched2.sort_values(by=['tid_subid', 'point_id_t']).reset_index(drop=True)
gdf_enriched2.to_parquet(r"d:\paper3\Data\trajectories\traj_filled_baseline_ShiftedTimestamps_gapAware_CloakingGeomID.parquet")

#%% look at gap labels
import pandas as pd
import numpy as np

# Filter tid_subid groups that have at least one non-NaN cloakingArea_id
valid_tid_subid = gdf_enriched2.groupby('tid_subid')['cloakingArea_id'].apply(lambda x: x.notna().any())
valid_tid_subid = valid_tid_subid[valid_tid_subid].index  # keep only True ones

# Pick one random tid_subid
random_tid_subid = np.random.choice(valid_tid_subid)
print("Random tid_subid with at least one cloakingArea_id:", random_tid_subid)

subset = gdf_enriched2[gdf_enriched2['tid_subid'] == random_tid_subid][
    ['point_id_t', 'point_type', 'cloaking', 'gap_label_valid_final', 'gap_label_pair_final', 'cloakingArea_id']
]

pd.set_option('display.max_rows', None)  
subset

# 20200128_ead4f86080d9d0e94db07eba45c54933495c92b5_3960
# the first one is often still labeled first, last
# there is labels for points with no synthetic points inbetwene them (but I can see points are missing based on point_id_t)
# this must (might?) be becuase of the one point inbetweeen sensitive points problem
# short answer: gap_labels are not valid and must be updated - overlabeled

#%% look at synpointid insted
gdf_enriched2[['point_id_t', 'point_type', 'syn_point_id_t', 'synpoint_id']].head(150)
# point id of synthetic points bery easily identifable as they have decimals - raw point ids are integers
#%%THERE IS POINT_ID_T with NaN?!
gdf_enriched2.point_id_t.isna().any() # True

#%%
gdf_enriched2.point_id.isna().any() # True
#%%
gdf_enriched2[['point_id', 'point_id_t', 'point_type', 'syn_point_id_t', 'synpoint_id']].head(150)

# the nan point_id_t (raw) do have a point_id
# the nan point_id are for synthetic points

#%% are point_id_t nan for gdf (i.e. before enrichmen of cloaking areas)
import geopandas as gpd
gdf = gpd.read_parquet(r"d:\paper3\Data\trajectories\traj_filled_baseline_ShiftedTimestamps_gapAware.parquet")

# based on syn point id
print(gdf['syn_point_id_t'].isna().equals(
    gdf['synpoint_id'].isna()
))

import numpy as np
gdf['point_type'] = np.where(
    gdf['synpoint_id'].isna(),
    'raw',
    'synthetic'
)

print(gdf['point_type'].unique())

gdf.point_id_t.isna().any() # True

#%% what a bout map-matched ones
import geopandas as gpd
t = gpd.read_parquet(r"d:\paper3\Data\trajectories\mapmatched_150kmh_onOsmid.parquet")
t.head()

t.point_id_t.isna().any() # True

#%%
t[t.point_id_t.isna()][['point_id', 'point_id_t', 'tid', 'tid_subid']].head() # they do have a tid and tid_subid

#%%
nan_count = t.point_id_t.isna().sum()
nan_pct = t.point_id_t.isna().mean() * 100

nan_count, nan_pct

# %%
gdf_enriched2[gdf_enriched2.point_id_t.isna()][['point_id', 'point_id_t', 'tid', 'tid_subid']].head() # they do have a tid and tid_subid

#%%% do I drop those points? no, order byt timestamp and add final point id
gdf_enriched2[gdf_enriched2.point_id_t.isna()][['point_id', 'point_id_t', 'tid', 'tid_subid', 'unix_timestamp']].head() # they do have a tid and tid_subid

#%%
nan_count = gdf_enriched2.point_id_t.isna().sum()
nan_pct = gdf_enriched2.point_id_t.isna().mean() * 100

nan_count, nan_pct

#%% make new point id
#gdf_enriched2.unix_timestamp_final.isna().any()

gdf_enriched2 = gdf_enriched2.sort_values(by=['tid_subid', 'unix_timestamp_final']).reset_index(drop=True)
gdf_enriched2['point_id_t_final'] = gdf_enriched2.groupby('tid_subid').cumcount() + 1
gdf_enriched2['point_id_t_final'].isna().any() # False
#%% export updated df
gdf_enriched2.to_parquet(r"d:\paper3\Data\trajectories\traj_filled_baseline_ShiftedTimestamps_gapAware_CloakingGeomID.parquet")

#%%
import geopandas as gpd
gdf_enriched2 = gpd.read_parquet(r"d:\paper3\Data\trajectories\traj_filled_baseline_ShiftedTimestamps_gapAware_CloakingGeomID.parquet")

#%% must ensure gap labels are valid
import pandas as pd
import numpy as np

# Filter tid_subid groups that have at least one non-NaN cloakingArea_id
valid_tid_subid = gdf_enriched2.groupby('tid_subid')['cloakingArea_id'].apply(lambda x: x.notna().any())
valid_tid_subid = valid_tid_subid[valid_tid_subid].index  # keep only True ones

# Pick one random tid_subid
random_tid_subid = np.random.choice(valid_tid_subid)
print("Random tid_subid with at least one cloakingArea_id:", random_tid_subid)

subset = gdf_enriched2[gdf_enriched2['tid_subid'] == random_tid_subid][
    ['point_id_t','point_id_t_final', 'point_type', 'cloaking', 'gap_label_valid_final', 'gap_label_pair_final', 'cloakingArea_id']
]

pd.set_option('display.max_rows', None)  
subset

#%%
import numpy as np

cols_to_copy = ['gap_label_pair_final', 'cloakingArea_id']

for col in cols_to_copy:
    gdf_enriched2[col + '_syn'] = gdf_enriched2.groupby('tid_subid', group_keys=False).apply(
        lambda g: g[col].where(
            (g['point_type'].shift(1) == 'synthetic') | (g['point_type'].shift(-1) == 'synthetic')
        )
    ).reset_index(level=0, drop=True)

print(gdf_enriched2.gap_label_pair_final_syn.unique())
print(gdf_enriched2.cloakingArea_id_syn.unique())

#%% explore one random tid_subid
random_tid_subid = np.random.choice(valid_tid_subid)
print("Random tid_subid with at least one cloakingArea_id:", random_tid_subid)

subset = gdf_enriched2[gdf_enriched2['tid_subid'] == random_tid_subid][
    ['point_id_t','point_id_t_final', 'point_type', 'cloaking', 'gap_label_valid_final', 'gap_label_pair_final', 'gap_label_pair_final_syn', 'cloakingArea_id', 'cloakingArea_id_syn']
]

pd.set_option('display.max_rows', None)  
subset
#%% 
subset.tail(2) # _syn columns work

#%% must update 'first, last' too
print(gdf_enriched2.cloakingArea_id_syn.nunique())
print(gdf_enriched2.gap_label_pair_final_syn.nunique())
      
mask_comma = gdf_enriched2['gap_label_pair_final'].str.contains(',', na=False)
num_comma = mask_comma.sum()
num_single = (~mask_comma).sum()
print(f"Single-word entries before fixing the gap labels: {num_single}")
print(f"Comma-separated entries before fixing the gap labels: {num_comma}")


mask_comma = gdf_enriched2['gap_label_pair_final_syn'].str.contains(',', na=False)
num_comma = mask_comma.sum()
num_single = (~mask_comma).sum()
print(f"Single-word entries: {num_single}")
print(f"Comma-separated entries: {num_comma}") # still some "first, last" - must check if these are valid
print(gdf_enriched2.cloakingArea_id_syn.nunique())
print(gdf_enriched2.gap_label_pair_final_syn.nunique())

#%%
subset[['point_id_t_final', 'point_type', 'gap_label_pair_final_syn', 'cloakingArea_id_syn']]

#%% look at the comma seperated labels - are they correct
mask_comma = gdf_enriched2['gap_label_pair_final_syn'].str.contains(',', na=False)
print(mask_comma.sum())

tid_with_commas = gdf_enriched2.loc[mask_comma, 'tid_subid'].unique() # 3,829 tids
print(len(tid_with_commas))

example_tid = tid_with_commas[0]
gdf_one_tid = gdf_enriched2.loc[gdf_enriched2['tid_subid'] == example_tid]
#%%
gdf_one_tid[['point_id_t_final', 'point_type', 'gap_label_pair_final_syn', 'cloakingArea_id_syn']]
# first entry is first, last - only last is valid
# last one is first, last - only first is valid


#%%
import numpy as np

def fix_comma_entries(group):
    # Copy the original columns to avoid modifying in place
    gap = group['gap_label_pair_final_syn'].copy()
    cloaking = group['cloakingArea_id_syn'].copy()

    # Prepare new columns
    gap_fixed = gap.copy()
    cloaking_fixed = cloaking.copy()

    for i in range(len(group)):
        val = gap.iloc[i]

        # Only process comma-separated values
        if isinstance(val, str) and ',' in val:
            above_synth = i > 0 and group['point_type'].iloc[i-1] == 'synthetic'
            below_synth = i < len(group)-1 and group['point_type'].iloc[i+1] == 'synthetic'

            parts = [p.strip() for p in val.split(',')]

            # Cloaking parts
            cloak_val = cloaking.iloc[i]
            if isinstance(cloak_val, str) and cloak_val.startswith('(') and ',' in cloak_val:
                cloak_parts = [p.strip().strip("()'\"") for p in cloak_val.strip('()').split(',')]
            else:
                cloak_parts = [cloak_val]

            if above_synth and below_synth:
                # Keep both parts
                gap_fixed.iloc[i] = ', '.join(parts)
                cloaking_fixed.iloc[i] = ', '.join(cloak_parts)
            elif above_synth and not below_synth:
                # Keep only first part
                gap_fixed.iloc[i] = parts[0]
                cloaking_fixed.iloc[i] = cloak_parts[0] if len(cloak_parts) > 0 else np.nan
            elif below_synth and not above_synth:
                # Keep only second part
                gap_fixed.iloc[i] = parts[1] if len(parts) > 1 else parts[0]
                cloaking_fixed.iloc[i] = cloak_parts[1] if len(cloak_parts) > 1 else (cloak_parts[0] if len(cloak_parts)>0 else np.nan)
            else:
                # Neither neighbor is synthetic → set NaN
                gap_fixed.iloc[i] = np.nan
                cloaking_fixed.iloc[i] = np.nan

    # Return a DataFrame with the new fixed columns
    return pd.DataFrame({
        'gap_label_pair_final_syn_fixed': gap_fixed,
        'cloakingArea_id_syn_fixed': cloaking_fixed
    }, index=group.index)


# Apply to each tid_subid separately
fixed_cols = gdf_enriched2.groupby('tid_subid', group_keys=False).apply(fix_comma_entries)

# Join the new columns back to the main GeoDataFrame
gdf_enriched2 = gdf_enriched2.join(fixed_cols)

#%%
mask_comma = gdf_enriched2['gap_label_pair_final_syn_fixed'].str.contains(',', na=False)
num_comma = mask_comma.sum()
num_single = (~mask_comma).sum()
print(f"gap_label_pair_final_syn_fixed single-word entries: {num_single}")
print(f"gap_label_pair_final_syn_fixed comma-separated entries: {num_comma}") # 15

mask_comma = gdf_enriched2['cloakingArea_id_syn_fixed'].str.contains(',', na=False)
num_comma = mask_comma.sum()
num_single = (~mask_comma).sum()
print(f"cloakingArea_id_syn_fixed single-word entries: {num_single}")
print(f"cloakingArea_id_syn_fixed comma-separated entries: {num_comma}") # 0



#%% ensure those 15 "sandwhich points" are valid
mask_comma = gdf_enriched2['gap_label_pair_final_syn_fixed'].str.contains(',', na=False)
tid_with_comma = gdf_enriched2.loc[mask_comma, 'tid_subid'].unique()
#%%example_tid = tid_with_comma[0] # legit first, last
#example_tid = tid_with_comma[1] # legit
example_tid = tid_with_comma[2] # legit
gdf_one_tid = gdf_enriched2.loc[gdf_enriched2['tid_subid'] == example_tid]

gdf_one_tid[['point_id_t_final', 'point_type', 'gap_label_pair_final_syn_fixed', 'cloakingArea_id_syn_fixed']]




#%% First step: add time bins
# timebins
gdf_enriched2["hour"] = (
    pd.to_datetime(gdf_enriched2["unix_timestamp"], unit="s", utc=True)
      .dt.tz_convert("Pacific/Auckland")
      .dt.hour
)

gdf_enriched2["time_bin"] = np.where(
    (gdf_enriched2["hour"] >= 7) & (gdf_enriched2["hour"] < 9),
    "morning peak",
    np.where(
        (gdf_enriched2["hour"] >= 9) & (gdf_enriched2["hour"] < 16),
        "flat peak",
        np.where(
            (gdf_enriched2["hour"] >= 16) & (gdf_enriched2["hour"] < 20),
            "evening peak",
            "night time"
        )
    )
)

gdf_enriched2.time_bin.unique()

#%%
import pandas as pd
mapping = {
    'night time': 0,
    'morning peak': 1,
    'flat peak': 2,
    'evening peak': 3,
}

gdf_enriched2['time_bin_label'] = gdf_enriched2['time_bin']
gdf_enriched2['time_bin'] = gdf_enriched2['time_bin'].map(mapping)

missing = gdf_enriched2['time_bin'].isna().any()
if missing:
    raise ValueError("Unexpected time_bin value found")

gdf_enriched2.time_bin.unique()

#%%
gdf_enriched2.to_parquet(r"d:\paper3\Data\trajectories\traj_filled_baseline_ShiftedTimestamps_gapAware_CloakingGeomID.parquet")
#%%
import geopandas as gpd
gdf_enriched2 = gpd.read_parquet(r"d:\paper3\Data\trajectories\traj_filled_baseline_ShiftedTimestamps_gapAware_CloakingGeomID.parquet")


#%% Second step: assign non-sensitive cloaking geometries to to points 
# if cloaking geometries overlap one point might be assigned multiple to them non-sensitive cloaking geom
cloakinggeom = gpd.read_parquet(r"d:\paper3\Data\trajectories\cloakingGeom_2sigLoc_100150m.parquet")
cloakinggeom.head()

#%% check geom is set to cloaking geometry
# 'cloaking_geometry'
# onliy interested in 
#'cloakingArea_id' # = rank + uid
# and cloaking range plus actual cloaking distance
#'og_cloaking_range'
#'cloaking_distance_m'

cloakinggeom = cloakinggeom[['cloakingArea_id', 'uid','cloaking_geometry', 'og_cloaking_range', 'cloaking_distance_m']].copy()
print(cloakinggeom.crs)
cloakinggeom.geometry

#%%
cloakinggeom = cloakinggeom.rename(columns={"cloakingArea_id": "NonSensitive_CloakingAreaId"})
gdf_enriched2 = gdf_enriched2.rename(columns={"cloakingArea_id_syn_fixed": "Sensitive_CloakingAreaId"})




#%% must reset index,so sort first
gdf_enriched2 = gdf_enriched2.sort_values(['tid_subid', 'point_id_t_final']).reset_index(drop=True)
gdf_enriched2 = gdf_enriched2.reset_index(drop=False).rename(columns={'index': 'row_uid'})
gdf_enriched2.head()

#%% 
# (1) only assign raw points to cloaking geometries for swapping purposes
raw_pts = gdf_enriched2[gdf_enriched2['point_type'] != 'synthetic'].copy()
# (2) ensure same crs and spatial index
raw_pts = raw_pts.to_crs(cloakinggeom.crs)

#%% build spatial index using stree
from collections import defaultdict
hits = defaultdict(list)
for poly_idx, poly in cloakinggeom.iterrows():
    possible_idxs = raw_pts.sindex.query(poly['cloaking_geometry'], predicate='intersects')
    for idx in possible_idxs:
        hits[raw_pts.iloc[idx]['row_uid']].append(poly['NonSensitive_CloakingAreaId'])

# index-based mapping 
gdf_enriched2['intersecting_cloaking_ids'] = gdf_enriched2['row_uid'].map(lambda uid: hits.get(uid, []))
gdf_enriched2['intersects_cloaking'] = gdf_enriched2['intersecting_cloaking_ids'].apply(lambda x: len(x) > 0)




#%%
gdf_enriched2.head()



#%% have synthetic points been handled correctly?
gdf_enriched2.intersects_cloaking.value_counts()
#False    6,988,796
#True      346,145
# most points actually intersect with a cloaking geometry 
# synthetic points cannot intersect with a cloaking geometry

#%%
print(gdf_enriched2.point_type.unique()) #['raw' 'synthetic']
print(gdf_enriched2['intersects_cloaking'].unique()) # only [ True False]
print(gdf_enriched2['intersects_cloaking'].isna().any()) # False
gdf_enriched2[gdf_enriched2['intersects_cloaking'] == False].point_type.unique() # ['raw', 'synthetic']

#%%
print(gdf_enriched2[gdf_enriched2['point_type'] == 'synthetic'][['point_type', 'intersecting_cloaking_ids', 'intersects_cloaking']].head())
print(gdf_enriched2[gdf_enriched2['point_type'] == 'synthetic']['intersects_cloaking'].unique()) # [False] - good

#%% export file
gdf_enriched2.to_parquet(r"d:\paper3\Data\trajectories\traj_filled_baseline_ShiftedTimestamps_gapAware_CloakingGeomID_AllCloakingAreas.parquet")


#%% look at cloaking geom and point assignment in Q, do they align?
# select points with exactly 1 polygon in the list
single_poly_points = gdf_enriched2[gdf_enriched2['intersecting_cloaking_ids'].apply(len) == 1]
# inspect the first few in Q
single_poly_points.head().to_parquet(r'D:\paper3\Data\tetsing/t_assignedCloakingArea_test.parquet')
# points are assigned the correct cloaking geom (based on map-matched geometr)

#%% clean up df and export before swapping starts
# ensure these are what I want
# Sensitive_CloakingAreaId
# gap_label_pair_final_syn_fixed
import numpy as np

# 'HeadTail' column
gdf_enriched2['HeadTail'] = np.where(
    gdf_enriched2['gap_label_pair_final_syn_fixed'].str.startswith('last_'),
    'HeadEnd',
    np.nan
)

# 'HeadEndCloakingAreaId' column
gdf_enriched2['HeadEndCloakingAreaId'] = np.where(
    gdf_enriched2['HeadTail'] == 'HeadEnd',
    gdf_enriched2['Sensitive_CloakingAreaId'],  
    np.nan
)

gdf_enriched2[gdf_enriched2['HeadTail'] == 'HeadEnd'].head()


#%% reduce coloumns
cols_to_drop = ['unix_timestamp', 'gap_label_invalid', 'syn_point_id_t', 'syn_point_id_t', 'synpoint_id', 
                'timestamp_ok', 'block', 'overlap_time_gap_sec',
                'gap_label_valid', 'gap_label_valid_final', 'gap_label_pair_final', 'gap_label_pair_final_syn',
                'cloakingArea_id', 'cloakingArea_id_syn']  # replace with your column names
gdf_enriched2 = gdf_enriched2.drop(columns=cols_to_drop)
gdf_enriched2.head()

#%% replace empty lists with nan
# replace empty lists with np.nan
gdf_enriched2['intersecting_cloaking_ids'] = gdf_enriched2['intersecting_cloaking_ids'].apply(
    lambda x: np.nan if len(x) == 0 else x
)

gdf_enriched2.head()

#%%
gdf_enriched2.to_parquet(r"d:\paper3\Data\trajectories\traj_filled_baseline_ShiftedTimestamps_gapAware_CloakingGeomID_AllCloakingAreas_clean.parquet")
# columns for cloaking based swapping
# intersecting_cloaking_ids - cloaking areas passing only
# HeadEndCloakingAreaId - upcoming cloaking area
# HeadTail - point to split tid before cloaking area
# then delete all syntithic points until first raw point
# this is the first point of the tail