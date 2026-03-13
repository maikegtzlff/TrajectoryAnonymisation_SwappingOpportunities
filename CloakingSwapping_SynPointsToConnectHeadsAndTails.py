#%% 
import geopandas as gpd
import pandas as pd
import numpy as np
#%% shortest path connecting head and tails
#sp_t_cswappingl_origsynf_OD_odid_final.to_parquet(r"E:\paper3\FinalCloakedBasedSwapping\shortestPath_CloakedBasedSwapping/headtailOD_shortestPath.parquet")
sp_headtail = gpd.read_parquet("d:\paper3\Data\synPointsForHeadTailConnection\headtailOD_shortestPath_origTimebins.parquet")
wayids = sp_headtail.id.unique() 


#%% get speed data
tid_osmid_speed = gpd.read_parquet(r"d:\paper3\Data\synPointsForHeadTailConnection\traj_osmid_shortestpath_speed_allColumns_speedkmh_5to150kmh_4Dec.parquet")
tid_osmid_speed.head()

#%% get median speed by user (and updated time bins) on each road segment, ignoring seasons
tid_osmid_speed["time_bin"] = np.where(
    (tid_osmid_speed["hour"] >= 7) & (tid_osmid_speed["hour"] < 9),
    "morning peak",
    np.where(
        (tid_osmid_speed["hour"] >= 9) & (tid_osmid_speed["hour"] < 16),
        "flat peak",
        np.where(
            (tid_osmid_speed["hour"] >= 16) & (tid_osmid_speed["hour"] < 20),
            "evening peak",
            "night time"
        )
    )
)

tid_osmid_speed.head()

#%% get median speed for all users by time_bin
median_speed_alluid = tid_osmid_speed.groupby(['id', 'time_bin'])['speed_kmh'].median().reset_index() # median speed by time bin for each osmid, based on all users
median_speed_alluid

#%% only keep the speed data for the osmid of interest
print(len(median_speed_alluid))
median_speed_alluid_wayids = median_speed_alluid[median_speed_alluid['id'].isin(wayids)]
print(len(median_speed_alluid_wayids))
median_speed_alluid_wayids

#%% time bin must also match
median_speed_alluid_wayids = median_speed_alluid_wayids.rename(columns={'time_bin': 'time_bin_label'})
sp_headtail_speed = sp_headtail.merge(median_speed_alluid_wayids, on =['id', 'time_bin_label'], how='left')
if sp_headtail_speed.speed_kmh.isna().any():
    print(sp_headtail_speed.speed_kmh.isna().sum(), ' out of ', len(sp_headtail_speed), 'do not have median speed (for this time of day)') # 55430
sp_headtail_speed
#%% add overall time, not time bin
median_speed_alluid_allday = tid_osmid_speed.groupby(['id'])['speed_kmh'].median().reset_index()
#%%
median_speed_alluid_allday = median_speed_alluid_allday.rename(columns={'speed_kmh': 'speed_kmh_noHour'})
sp_headtail_speed = sp_headtail_speed.merge(median_speed_alluid_allday, on =['id'], how='left')
sp_headtail_speed.head()

#%% fill na of speed_kmh
sp_headtail_speed['speed_kmh'] = sp_headtail_speed['speed_kmh'].fillna(
    sp_headtail_speed['speed_kmh_noHour']
)
if sp_headtail_speed.speed_kmh.isna().any():
    print(sp_headtail_speed.speed_kmh.isna().sum(), ' out of ', len(sp_headtail_speed), 'do not have median speed (for this time of day)') # 38955, before55430

#%% fill the remaining na with maxspeed
edges = gpd.read_parquet(r"d:\paper3\Data\synPointsForHeadTailConnection\edges.parquet")
edges = edges[['id', 'maxspeed']]
edges = edges.drop_duplicates(subset=['id'])
edges = edges.dropna(subset=['maxspeed'])
edges.head()

#%% add maxspeed to shortest path
sp_headtail_speed = sp_headtail_speed.merge(edges, on =['id'], how='left')

sp_headtail_speed['speed_kmh'] = sp_headtail_speed['speed_kmh'].fillna(
    sp_headtail_speed['maxspeed']
)

if sp_headtail_speed.speed_kmh.isna().any():
    print(sp_headtail_speed.speed_kmh.isna().sum(), ' out of ', len(sp_headtail_speed), 'do not have median speed (for this time of day)') # 23989 (1.9%), before 38955, before 55430


#%% fill nan speeds with speed from previous segment
sp_headtail_speed['speed_kmh'] = sp_headtail_speed.groupby('odid')['speed_kmh'].ffill()
if sp_headtail_speed.speed_kmh.isna().any():
    print(sp_headtail_speed.speed_kmh.isna().sum(), ' out of ', len(sp_headtail_speed), 'do not have median speed (for this time of day)') 
    # 23989 (1.9%), before 38955, before 55430
    # now 4426  
#%% backfill the remaining ones
#%% now to a backwards fill
sp_headtail_speed['speed_kmh'] = sp_headtail_speed.groupby('odid')['speed_kmh'].ffill().bfill()
if sp_headtail_speed.speed_kmh.isna().any():
    print(sp_headtail_speed.speed_kmh.isna().sum()) # no nan left

#%% must have speed in m per second
sp_headtail_speed['speed_kmh'] = sp_headtail_speed['speed_kmh'].astype(int)
sp_headtail_speed['median_speed_m_s'] = sp_headtail_speed['speed_kmh'] * 1000 / 3600
sp_headtail_speed.head()



#%% calculate synthetic points
#%% FILL GAPS IN TRAJECTORIES (introduced by cloaking)
# (1) add points on shortest path - distance based on speed
# add synthetic points based on shortest path geometry and speed info

#%% geometry checks 
from shapely.geometry import LineString
if ~sp_headtail_speed.geometry.apply(lambda g: isinstance(g, LineString)).any():
    print("MUST check geometry, not every edge is a  LineString") # good, all shortest paths are lines

# direction of edge travelled along shortest path is different to direction of edge recorded in geometry of edges df
sp_headtail_speed['edge_u_v'] = (
    sp_headtail_speed['id'].astype(str) + '_' +
    sp_headtail_speed['u'].astype(str) + '_' +
    sp_headtail_speed['v'].astype(str)
)

#%%
edges_gdf_uv = gpd.read_parquet(r"d:\paper3\Data\synPointsForHeadTailConnection\edges.parquet")
edges_gdf_uv['edge_u_v'] = (
    edges_gdf_uv['id'].astype(str) + '_' +
    edges_gdf_uv['u'].astype(str) + '_' +
    edges_gdf_uv['v'].astype(str)
)
edges_gdf_uv = edges_gdf_uv[['edge_u_v']].copy()
edges_gdf_uv['edge_orientation'] = True

sp_headtail_speed = sp_headtail_speed.merge(edges_gdf_uv, on='edge_u_v', how='left')
print(sp_headtail_speed['edge_orientation'].unique()) # True when True, Nan when reversing is required
sp_headtail_speed.head()


#%% now reverse edge orientation if needed, i.e., if edge_orientation is nan
sp_headtail_speed['geometry'] = sp_headtail_speed['geometry'].where(
    sp_headtail_speed['edge_orientation'].notna(),  # keep original if not NaN
    sp_headtail_speed['geometry'].apply(lambda geom: LineString(geom.coords[::-1]))  # reverse if NaN
)


#%% export 
sp_headtail_speed.to_parquet(r'd:\paper3\Data\synPointsForHeadTailConnection\headtailOD_shortestPath_origTimebins_medianSpeed.parquet')

#%% do speeds look reasonable
sp_headtail_speed['median_speed_m_s'].describe() # mean is 34 km/h, median 32


#%% sp_headtail_speed.datetime_loc_tz.dtype - datetime64[ns, Pacific/Auckland]
sp_headtail_speed['unix_timestamp'] = sp_headtail_speed['datetime_loc_tz'].astype('int64') // 10**9
sp_headtail_speed[['datetime_loc_tz', 'unix_timestamp']].head()

#%%
sp_headtail_speed = sp_headtail_speed.to_crs(epsg=2193) 
sp_headtail_speed['length_m'] = sp_headtail_speed.geometry.length

#%% time driven approach to syn point generation
syn_sinterval = 1

all_points = []
all_time = []
all_unix = []

all_odid = []
all_speed_mps = []
all_speed_source = []

all_u = []
all_v = []
all_edge_id = []

all_uid = []
all_unix_dest = []

# would be good to keep info on unix_timestamp_destination
for odid, segs in sp_headtail_speed.groupby('odid'):
    segs = segs.reset_index(drop=True)

    # cumulative segment positions
    segs['cum_start'] = segs.length_m.cumsum().shift(fill_value=0)
    segs['cum_end']   = segs.cum_start + segs.length_m

    cum_dist = 0.0
    t = 1
    #unix = segs.loc[0, 'unix_timestamp'] + 1
    #don't have meaningful timestamp
    unix = 0 # record time since origin    

    while cum_dist < segs.cum_end.iloc[-1]:

        # segment used for this second
        row = segs.loc[
            (segs.cum_start <= cum_dist) & (cum_dist < segs.cum_end)
        ].iloc[0]

        speed = row.median_speed_m_s

        # advance distance
        cum_dist += speed * syn_sinterval

        # project onto segment
        dist_on_seg = cum_dist - row.cum_start
        frac = dist_on_seg / row.length_m
        frac = min(max(frac, 0.0), 1.0)

        # record spatial + attributes
        all_points.append(row.geometry.interpolate(frac, normalized=True))
        all_time.append(t)
        all_unix.append(unix)

        all_odid.append(odid)
        all_speed_mps.append(speed)

        all_uid.append(row.uid)  

        # tick time
        t += 1
        unix += 1

#%%
#%% turn into a gdf
import geopandas as gpd

syn_points_gdf_1sec = gpd.GeoDataFrame(
    {
        "odid": all_odid,
        "uid": all_uid,
        "time_sec_sinceOrigin": all_time,
        "unix": all_unix,
        "speed_mps": all_speed_mps,
        "speed_source": all_speed_source,
        "unix_timestamp_destination": all_unix_dest,
        #"edge_id" : all_edge_id,
        #"u": all_u,
        #"v": all_v,
    },
    geometry=all_points,
    crs=sp_headtail_speed.crs
)

syn_points_gdf_1sec['syn_point_id_t'] = syn_points_gdf_1sec['time_sec_sinceOrigin']
syn_points_gdf_1sec



#%% must downsample

