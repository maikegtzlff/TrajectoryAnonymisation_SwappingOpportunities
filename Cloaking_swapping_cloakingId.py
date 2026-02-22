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

import numpy as np

import numpy as np

import numpy as np

def compute_gap_label_valid(group):
    group = group.copy()
    group['gap_label_valid'] = np.nan
    group['gap_label_valid'] = group['gap_label_valid'].astype(object)

    is_sensitive = group['cloaking'] == 'sensitive'

    # previous and next cloaking
    cloaking_prev = is_sensitive.shift(1, fill_value=False)
    cloaking_next = is_sensitive.shift(-1, fill_value=False)

    non_sensitive = ~is_sensitive

    # assign 'last' if next row is sensitive
    mask_last = non_sensitive & cloaking_next
    group.loc[mask_last, 'gap_label_valid'] = 'last'

    # assign 'first' if previous row is sensitive
    mask_first = non_sensitive & cloaking_prev
    group.loc[mask_first, 'gap_label_valid'] = 'first'

    # explicit gap_label overrides
    group.loc[group['gap_label'] == 'last', 'gap_label_valid'] = 'last'
    group.loc[group['gap_label'] == 'first', 'gap_label_valid'] = 'first'

    # assign 'first, last' if both prev and next are sensitive
    mask_first_last = non_sensitive & cloaking_prev & cloaking_next
    group.loc[mask_first_last, 'gap_label_valid'] = 'first, last'

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
t = t.sort_values(['tid', 'tid_subid', 'point_id_t']) 
g = t.groupby('tid')

prev = g['rank_uid'].shift(1)
next_ = g['rank_uid'].shift(-1)

t['rank_uid_firstLast_tid'] = t['rank_uid']
t.loc[(t['gap_label_valid'] == 'first') & t['rank_uid_firstLast_tid'].isna(), 'rank_uid_firstLast_tid'] = prev
t.loc[(t['gap_label_valid'] == 'last') & t['rank_uid_firstLast_tid'].isna(),'rank_uid_firstLast_tid'] = next_


#%% look at gap_label_pairs
# Extract the gap number from gap_label_pair
t['gap_num'] = t['gap_label_pair'].str.extract(r'_(\d+)$').astype(float)

# Count how many unique gap numbers per tid_subid
gap_counts = t.groupby('tid_subid')['gap_num'].nunique()

# Select tid_subid with more than 1 gap
tids_multi_gap = gap_counts[gap_counts > 1].index

# Pick the first one
tid = tids_multi_gap[0]

df_tid = t[t['tid_subid'] == tid].sort_values('point_id_t')
pd.set_option('display.max_rows', None)
df_tid[['tid_subid','point_id_t','cloaking','gap_label_valid','gap_label_pair']]
#%%
pd.reset_option('display.max_rows')



#%% quality control: have all gap_labels been assigned a cloaking_id (YES, because gap_label has been corrected)
total_gap = t['gap_label_valid'].notna().sum()
missing_rank_uid = t.loc[t['gap_label_valid'].notna() & t['rank_uid_firstLast_tid'].isna()].shape[0]
percent_missing = missing_rank_uid / total_gap * 100
print(f"{missing_rank_uid} rows out of {total_gap} ({percent_missing:.2f}%) have a valid gap_label but no rank_uid_firstLast_tid")


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



#%% add cloaking geometry ids for valid gap labels
gdf.rename(columns={'gap_label':'gap_label_invalid'}, inplace=True)
gdf_enriched = gdf.merge(t[['uid', 'point_id', 'point_id_t', 'gap_label_valid', 'rank_uid_firstLast_tid', 'sensitivity_rank']], left_on =['uid', 'point_id', 'point_id_t', 'gap_label_invalid'], right_on =['uid', 'point_id', 'point_id_t', 'gap_label_valid'], how='left')
gdf_enriched.head()

#%% look at gap labels after mereg
# if gap_label_valid has a label but gap_label (coming from t) does not, then gap labels and point_ids do not align
# total number of valid gap_label rows
total_gap = gdf_enriched['gap_label_valid'].notna().sum()

# number of valid gap_label rows where rank_uid_firstLast_tid is missing
missing_rank_uid = gdf_enriched.loc[gdf_enriched['gap_label_valid'].notna() & gdf_enriched['rank_uid_firstLast_tid'].isna()].shape[0]

# percentage
percent_missing = missing_rank_uid / total_gap * 100

print(f"{missing_rank_uid} rows out of {total_gap} ({percent_missing:.2f}%) "
      "have a valid gap_label but no rank_uid_firstLast_tid")

#%%
gdf_enriched.rename(columns={'rank_uid_firstLast_tid':'cloakingArea_id'}, inplace=True)

#%% 
gdf_enriched.to_parquet(r"d:\paper3\Data\trajectories\traj_filled_baseline_ShiftedTimestamps_gapAware_CloakingGeomID.parquet")
