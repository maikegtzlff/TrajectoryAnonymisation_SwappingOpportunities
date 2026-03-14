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
# ran for 40 mins
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
    },
    geometry=all_points,
    crs=sp_headtail_speed.crs
)

syn_points_gdf_1sec['syn_point_id_t'] = syn_points_gdf_1sec['time_sec_sinceOrigin']
syn_points_gdf_1sec

#%%
syn_points_gdf_1sec.to_parquet(r"D:\paper3\Data\synPointsForHeadTailConnection/synPoints_for_headtailOD_shortestPath_origTimebins_medianSpeed.parquet")

#%% look at one shortest path
import random
from shapely.geometry import Point

#random_odid = random.choice(sp_headtail_speed.odid.unique())
print(random_odid) # 15359_orig_4349461_dest_4349462
# syn points sownt overlap OD: 9916_orig_2880259_dest_2880260

random_odid_sp = sp_headtail_speed[sp_headtail_speed['odid']==random_odid]

# get origin and destination points
#sp_t_cswappingl_origsynf_OD_odid_final = gpd.read_parquet(r"d:\paper3\Data\synPointsForHeadTailConnection\headtailOD_shortestPath.parquet")

random_odid_sp_od = sp_t_cswappingl_origsynf_OD_odid_final[sp_t_cswappingl_origsynf_OD_odid_final['odid'] == random_odid]
random_odid_sp_od['orig_geometry'] = random_odid_sp_od.apply(lambda r: Point(r['orig_x'], r['orig_y']), axis=1)
random_odid_sp_od['dest_geometry'] = random_odid_sp_od.apply(lambda r: Point(r['dest_x'], r['dest_y']), axis=1)

random_odid_sp_orig = random_odid_sp_od.set_geometry('orig_geometry')
random_odid_sp_dest = random_odid_sp_od.set_geometry('dest_geometry')

random_odid_sp_orig = random_odid_sp_orig.set_crs(4326)
random_odid_sp_dest = random_odid_sp_dest.set_crs(4326)

random_odid_sp_orig = random_odid_sp_orig[['odid', 'orig_geometry']].head(1).copy()
random_odid_sp_dest = random_odid_sp_dest[['odid', 'dest_geometry']].head(1).copy()

#  get syn points for this odid
radnom_syn_points_1sec = syn_points_gdf_1sec[syn_points_gdf_1sec['odid'] == random_odid]

#%%
import matplotlib.pyplot as plt
import contextily as ctx  
import matplotlib.patheffects as path_effects

gdf1 = random_odid_sp.to_crs(epsg=3857)

gdf2 = random_odid_sp_orig.to_crs(epsg=3857)
gdf3 = random_odid_sp_dest.to_crs(epsg=3857)

gdf4 = radnom_syn_points_1sec.to_crs(epsg=3857)

import matplotlib.patheffects as path_effects

def annotate_with_halo(ax, point, label, 
                       text_color="black", arrow_color="black", 
                       xytext=(-60, 20), text_fontsize=12, 
                       text_halo_width=3, arrow_halo_width=5, arrow_width=1.5,
                       va="center", ha="center"):
   
    # arrow halo
    ax.annotate(
        "",
        xy=(point.x, point.y),
        xytext=xytext,
        textcoords="offset points",
        arrowprops=dict(
            arrowstyle="->",
            color="white",
            linewidth=arrow_halo_width
        ),
        zorder=2
    )
    
    # actual arrow
    ax.annotate(
        "",
        xy=(point.x, point.y),
        xytext=xytext,
        textcoords="offset points",
        arrowprops=dict(
            arrowstyle="->",
            color=arrow_color,
            linewidth=arrow_width
        ),
        zorder=3
    )
    
    # text with halo
    txt = ax.annotate(
        label,
        xy=(point.x, point.y),
        xytext=xytext,
        textcoords="offset points",
        fontsize=text_fontsize,
        color=text_color,
        va=va,
        ha=ha,
        zorder=4
    )
    
    txt.set_path_effects([
        path_effects.Stroke(linewidth=text_halo_width, foreground="white"),
        path_effects.Normal()
    ])
    
    return txt

#%%
fig, ax = plt.subplots(figsize=(12, 10))

# plot each GeoDataFrame with different color/marker
gdf1.plot(ax=ax, color='black', alpha=0.6, label='shortest path', linewidth=1.5, zorder =1)

gdf4.plot(ax=ax, color='black', alpha=0.6, label='synthetic points', markersize=16, zorder=2)

gdf2.plot(ax=ax, color='#fcc72d', alpha=1, markersize=60, zorder=3)
gdf3.plot(ax=ax, color='#fcc72d', alpha=1, markersize=60, zorder=4)

# annotate head and tail
# origin
row = gdf2.iloc[0]
annotate_with_halo(
    ax, 
    row.orig_geometry, 
    "origin:\nhead end",
    text_color="black",
    arrow_color="black",
    xytext=(-0, 100),   
    text_fontsize=18,
    va="bottom",      
    ha="center"    
)
# destination
row = gdf3.iloc[0]
annotate_with_halo(
    ax, 
    row.dest_geometry, 
    "destination:\ntail start",
    text_color="black",
    arrow_color="black",
    xytext=(0, -60),
    text_fontsize=18,
    va="top",
    ha="center"
)

# add basemap and legend
xlim = ax.get_xlim()
ylim = ax.get_ylim()
xpad = (xlim[1] - xlim[0]) * 0.05
ypad = (ylim[1] - ylim[0]) * 0.05
ax.set_xlim(xlim[0] - xpad, xlim[1] + xpad)
ax.set_ylim(ylim[0] - ypad, ylim[1] + ypad)

ctx.add_basemap(ax, source=ctx.providers.CartoDB.PositronNoLabels, attribution=False)
ax.legend(
    loc='lower left',
    fontsize=14,
    frameon=True,
    framealpha=0.6
)
ax.set_axis_off()

fig.savefig(r"\\tsclient\R\paper3\Figures/HeadTail_SynPoints_1Sec.svg", format="svg", bbox_inches="tight", dpi=300)

plt.show()






#%% (2) downsample  to show randomness
import random
import pandas as pd

# set your fraction limits
frac_min = 0.1
frac_max = 0.2

# --- downsample per odid ---
def downsample_group(group):
    random_frac = random.uniform(frac_min, frac_max)
    return group.sample(frac=random_frac, random_state=None)

print(len(syn_points_gdf_1sec)) # 2955095
d_syn_points_gdf = (
    syn_points_gdf_1sec
    .groupby("odid", group_keys=False)
    .apply(downsample_group)
    .reset_index(drop=True)
)
print(len(d_syn_points_gdf))


# --- add point index per trajectory ---
# sort by odid and unix first
d_syn_points_gdf = d_syn_points_gdf.sort_values(by=["odid", "unix"])
d_syn_points_gdf.reset_index(inplace=True, drop=True)
# assign sequential index per odid
d_syn_points_gdf["synpoint_id"] = d_syn_points_gdf.groupby("odid").cumcount() + 1
d_syn_points_gdf.head()

#%% 
d_syn_points_gdf.to_parquet(r"D:\paper3\Data\synPointsForHeadTailConnection/synPoints_DOWNSAMPLED1020_for_headtailOD_shortestPath_origTimebins_medianSpeed.parquet")


#%% final figure
radnom_syn_points_downsampled = d_syn_points_gdf[d_syn_points_gdf['odid'] == random_odid]
gdf5 = radnom_syn_points_downsampled.to_crs(epsg=3857)

#%%
import matplotlib.pyplot as plt
import contextily as ctx

# -----------------------------
# Compute unified extent for all GeoDataFrames
# -----------------------------
all_gdfs = [gdf1, gdf2, gdf3, gdf4, gdf5]  
xmin = min(gdf.total_bounds[0] for gdf in all_gdfs)
ymin = min(gdf.total_bounds[1] for gdf in all_gdfs)
xmax = max(gdf.total_bounds[2] for gdf in all_gdfs)
ymax = max(gdf.total_bounds[3] for gdf in all_gdfs)

# add 10% padding so that labels stay witing map extent
xpad = (xmax - xmin) * 0.1
ypad = (ymax - ymin) * 0.1
xlim = (xmin - xpad, xmax + xpad)
ylim = (ymin - ypad, ymax + ypad)

# -----------------------------
# Create figure with 3 panels
# -----------------------------
fig, axes = plt.subplots(1, 3, figsize=(24, 10))
axs = axes.flatten()

# -----------------------------
# Panel A: Only head/tail points
# -----------------------------
ax = axs[0]
gdf2.plot(ax=ax, color='#fcc72d', alpha=1, markersize=60, zorder=3)
gdf3.plot(ax=ax, color='#fcc72d', alpha=1, markersize=60, zorder=4)

# annotate
annotate_with_halo(ax, gdf2.iloc[0].orig_geometry, "origin:\nhead end",
                   xytext=(-0, 100), va="bottom", ha="center", text_fontsize=18)
annotate_with_halo(ax, gdf3.iloc[0].dest_geometry, "destination:\ntail start",
                   xytext=(0, -60), va="top", ha="center", text_fontsize=18)

# set unified extent
ax.set_xlim(xlim)
ax.set_ylim(ylim)

ctx.add_basemap(ax, source=ctx.providers.CartoDB.PositronNoLabels, attribution=False)
ax.set_axis_off()
ax.set_title("(A) Head and tail points", fontsize=16)

# -----------------------------
# Panel B: Original plot
# -----------------------------
ax = axs[1]
gdf1.plot(ax=ax, color='black', alpha=0.6, linewidth=1.5, zorder=1)
gdf4.plot(ax=ax, color='black', alpha=0.6, markersize=16, zorder=2)
gdf2.plot(ax=ax, color='#fcc72d', alpha=1, markersize=60, zorder=3)
gdf3.plot(ax=ax, color='#fcc72d', alpha=1, markersize=60, zorder=4)

# annotate
annotate_with_halo(ax, gdf2.iloc[0].orig_geometry, "origin:\nhead end",
                   xytext=(-0, 100), va="bottom", ha="center", text_fontsize=18)
annotate_with_halo(ax, gdf3.iloc[0].dest_geometry, "destination:\ntail start",
                   xytext=(0, -60), va="top", ha="center", text_fontsize=18)

# set unified extent
ax.set_xlim(xlim)
ax.set_ylim(ylim)

ctx.add_basemap(ax, source=ctx.providers.CartoDB.PositronNoLabels, attribution=False)
ax.set_axis_off()
ax.set_title("(B) Synthetic trajectory points", fontsize=16)

# add legend only on B
ax.legend(loc='lower left', fontsize=14, frameon=True, framealpha=0.6)

# -----------------------------
# Panel C: show downsampled synthetic points
# -----------------------------
ax = axs[2]
gdf1.plot(ax=ax, color='black', alpha=0.6, linewidth=1.5, zorder=1) # shortest path
gdf5.plot(ax=ax, color='black', alpha=0.6, markersize=16, zorder=2)  # downsampled syn trajectory points
gdf2.plot(ax=ax, color='#fcc72d', alpha=1, markersize=60, zorder=3) # origin
gdf3.plot(ax=ax, color='#fcc72d', alpha=1, markersize=60, zorder=4) # destination

# annotate
annotate_with_halo(ax, gdf2.iloc[0].orig_geometry, "origin:\nhead end",
                   xytext=(-0, 100), va="bottom", ha="center", text_fontsize=18)
annotate_with_halo(ax, gdf3.iloc[0].dest_geometry, "destination:\ntail start",
                   xytext=(0, -60), va="top", ha="center", text_fontsize=18)

# set unified extent
ax.set_xlim(xlim)
ax.set_ylim(ylim)

ctx.add_basemap(ax, source=ctx.providers.CartoDB.PositronNoLabels, attribution=False)
ax.set_axis_off()
ax.set_title("(C) Downsampled synthetic trajectory points", fontsize=16)

# -----------------------------
# Save figure as SVG
# -----------------------------
fig.tight_layout()
fig.savefig(r"\\tsclient\R\paper3\Figures/HeadTail_SynPoints_3Panel.svg", format="svg", bbox_inches="tight", dpi=300)

plt.show()







#%% "fill" swapped df
#%% haven't looked at point id of syn points yet
print((syn_points_gdf_1sec['time_sec_sinceOrigin'] == syn_points_gdf_1sec['syn_point_id_t']).any()) # True
syn_points_gdf_1sec.head() 
# time_sec_sinceOrigin, don't need unix column
# syn_point_id_t is the same as time_sec

#%%
d_syn_points_gdf.head() # point id: synpoint_id is correct, syn_point_id_t mst be from before downsampling!
# ['odid', 'uid', 'time_sec_sinceOrigin', 'unix', 'speed_mps', 'geometry', 'syn_point_id_t', 'synpoint_id']

# odid is also fake orig_tid
# must add final_tid
# final_tid is based on odid

#%% odid to final_tid dict
# from VM 131
#t_cswappingl_origsynf.to_parquet(r"E:\paper3\FinalCloakedBasedSwapping\shortestPath_CloakedBasedSwapping/t_cswappingl_origsynf_crs4326.parquet")
t_cswappingl_origsynf_OD_odid_final_sp = pd.read_parquet(r"d:\paper3\Data\synPointsForHeadTailConnection\t_cswappingl_origsynf_OD_odid_final_crs4326.parquet")
print(len(t_cswappingl_origsynf_OD_odid_final_sp)) # 33558 --> only od
t_cswappingl_origsynf_OD_odid_final_sp.head() # has odid, point_id_global of origin AND destination, true_pair_id, origin_label, destination_label
#%%
odid_to_finalTid_dict = dict(zip(
    t_cswappingl_origsynf_OD_odid_final_sp['odid'],
    zip(
        t_cswappingl_origsynf_OD_odid_final_sp['final_tid'], 
        t_cswappingl_origsynf_OD_odid_final_sp['true_pair_id'],
        t_cswappingl_origsynf_OD_odid_final_sp['point_id_global']
    )
))

d_syn_points_gdf[['final_tid', 'true_pair_id', 'point_id_global']] = d_syn_points_gdf['odid'].map(odid_to_finalTid_dict).apply(pd.Series)
d_syn_points_gdf.head()

#%% claen up d_syn_points_gdf
d_syn_points_gdf[['orig_point_id_global', 'dest_point_id_global']] = d_syn_points_gdf['point_id_global'].apply(pd.Series)
d_syn_points_gdf = d_syn_points_gdf.drop(['unix', 'syn_point_id_t'], axis=1)

d_syn_points_gdf.head()

#%% update syn_point_id to be within orig and dest global point id
d_syn_points_gdf = d_syn_points_gdf.sort_values(['final_tid', 'synpoint_id'])

# assign a value between the tuple range as syn point id global
def assign_within_range(group):
    start = group['point_id_global'].iloc[0][0]
    end = group['point_id_global'].iloc[0][1]
    n = len(group)
    # add offset to exclude tuple values
    group = group.copy()
    group['syn_point_id_global'] = np.linspace(start + 1e-6, end - 1e-6, n)
    return group

d_syn_points_gdf = d_syn_points_gdf.groupby('odid', group_keys=False).apply(assign_within_range)
d_syn_points_gdf[['odid', 'synpoint_id', 'point_id_global', 'syn_point_id_global']].head()

#%% clean d_syn_points_gdf
d_syn_points_gdf = d_syn_points_gdf.drop('synpoint_id', axis=1)
d_syn_points_gdf.head()


#%% the df to be filled
#from VM 131
#t_cswappingl_origsynf_OD_odid_final_sp.to_parquet(r"D:\paper3\FinalCloakedBasedSwapping\shortestPath_CloakedBasedSwapping/t_cswappingl_origsynf_OD_odid_final_sp.parquet")
# now on VM 201

#%% len 7328560 --> all points not just od
t_cswappingl_origsynf = gpd.read_parquet(r"d:\paper3\Data\synPointsForHeadTailConnection\t_cswappingl_origsynf_crs4326.parquet") 
t_cswappingl_origsynf.head()
# does not have an odid 

#%% look for common columns
#set(t_cswappingl_origsynf_OD_odid_final_sp.columns) & set(t_cswappingl_origsynf.columns)
# {'final_tid', 'point_id_global', 'true_pair_id'}
# pointd_id_gloobal is unique, can add odid to traj based on this

# don't need to do this, syn points have final_tid and would only be concated
# would only need odid in main df for plot

print(d_syn_points_gdf.columns) 
#['odid', 'uid', 'time_sec_sinceOrigin', 'speed_mps', 'geometry', 'synpoint_id', 'final_tid', 'true_pair_id']

print(t_cswappingl_origsynf.columns)
#['point_id_global', 'point_id_unique', 'main_clkgp_wHelper_id',
#       'main_headEND_pointid', 'main_tailStart_pointid', 'match_geometry',
#       'final_tid', 'order_in_traj', 'swap_id', 'original_tid',
#       'main_clkgp_id_tuple', 'valid_helpers', 'active_swap',
#      'main_involved_in_split', 'valid_swap', 'order_in_traj_tuple',
#       'point_type', 'order_in_traj_filled', 'order_in_traj_filled_valid',
#       'final_tid_origsynfilled', 'final_tid_origsynfilled_valid',
#       'true_pair_id']

#%% will pd.concat, then sorting by global point id to get syn points at the correct positon
# rename tid column/add

# final_tid of d_syn_points_gdf == final_tid_origsynfilled of t_cswappingl_origsynf
d_syn_points_gdf['final_tid_origsynfilled'] = d_syn_points_gdf['final_tid']

# add orig_tid akak odid
d_syn_points_gdf['original_tid'] = d_syn_points_gdf['odid']
d_syn_points_gdf['point_type'] = "swapping_synthetic"

# rename global point id column
d_syn_points_gdf = d_syn_points_gdf.rename(columns={'point_id_global': 'point_id_global_OD_tuple'})
d_syn_points_gdf = d_syn_points_gdf.rename(columns={'syn_point_id_global': 'point_id_global'})

d_syn_points_gdf.head()

#%%
d_syn_points_gdf.to_parquet(r"D:\paper3\Data\synPointsForHeadTailConnection/synPoints_DOWNSAMPLED1020_GLOBALPOINTID_for_headtailOD_shortestPath_origTimebins_medianSpeed.parquet")

#%% clean up both df before merge
print(sorted(t_cswappingl_origsynf.columns)) # doesn't have geometry! will add match_geometry back, can then fill with geometry column
print(sorted(d_syn_points_gdf.columns))


print(t_cswappingl_origsynf[t_cswappingl_origsynf['main_clkgp_id_tuple'].notna()][[
 'main_clkgp_id_tuple',
 'main_clkgp_wHelper_id',
 'main_headEND_pointid',
 'main_involved_in_split',
 'main_tailStart_pointid']].head())

print(t_cswappingl_origsynf.final_tid_origsynfilled_valid.unique())

print(t_cswappingl_origsynf[[
 'order_in_traj',
 'order_in_traj_filled',
 'order_in_traj_filled_valid',
 'order_in_traj_tuple']].head())

# print(t_cswappingl_origsynf.apply(lambda r: np.array_equal(r['main_clkgp_id_tuple'], r['order_in_traj_tuple']), axis=1).any())
# true --> can drop one

#%%
# columns to drop from syn points
d_syn_points_gdf = d_syn_points_gdf.drop('uid', axis=1)

# rename columns
# point_id_global_OD_tuple to  'main_clkgp_id_tuple'
# MUST RENAME GEOMETRY TO MATCH GEOMETRY (and set active geometry column)
d_syn_points_gdf = d_syn_points_gdf.rename(columns={'geometry': 'match_geometry', 'point_id_global_OD_tuple': 'main_clkgp_id_tuple'})
d_syn_points_gdf = d_syn_points_gdf.set_geometry('match_geometry')

# columns to drop from t_cswappingl_origsynf
t_cswappingl_origsynf = t_cswappingl_origsynf.drop([
 'final_tid_origsynfilled_valid', 
 'order_in_traj',
 'order_in_traj_filled',
 'order_in_traj_filled_valid',
 'order_in_traj_tuple'], axis=1)

# compare crs
print(d_syn_points_gdf.crs)
print(t_cswappingl_origsynf.crs)
#%%
t_cswappingl_origsynf = t_cswappingl_origsynf.to_crs(d_syn_points_gdf.crs)
print(t_cswappingl_origsynf.crs)

#%% can now safely concat and sort to "fill"
t_cswappingl_origsynf_headtailsynf = gpd.GeoDataFrame(pd.concat([t_cswappingl_origsynf, d_syn_points_gdf], ignore_index=True))
t_cswappingl_origsynf_headtailsynf = t_cswappingl_origsynf_headtailsynf.sort_values('point_id_global')
t_cswappingl_origsynf_headtailsynf = t_cswappingl_origsynf_headtailsynf.reset_index(drop=True)

print(t_cswappingl_origsynf_headtailsynf.columns)
t_cswappingl_origsynf_headtailsynf.head() # no temporal information at all at the moment, otther than time_sec_sinceOrigin for new syn points

#%%
t_cswappingl_origsynf_headtailsynf = t_cswappingl_origsynf_headtailsynf.reset_index().rename(columns={'index': 'point_id_global_synfilled'})
t_cswappingl_origsynf_headtailsynf.head()


#%% export 
t_cswappingl_origsynf_headtailsynf.to_parquet(r"D:\paper3\Data\ClkSwpSynFilled.parquet")


#%% include some points of head and tail in the plot?
# get tid of the odid plotted in figure
tid_of_random_odid = t_cswappingl_origsynf_headtailsynf[t_cswappingl_origsynf_headtailsynf['odid']==random_odid]['final_tid_origsynfilled'].unique()[0]
# 20200303_5e61a24666c6e1162e17749370d1f52e0600d897_4814

#%%
clk_t_sample = t_cswappingl_origsynf[t_cswappingl_origsynf['final_tid_origsynfilled']==tid_of_random_odid]
clk_t_connected_sample = t_cswappingl_origsynf_headtailsynf[t_cswappingl_origsynf_headtailsynf['final_tid_origsynfilled']==tid_of_random_odid]

clk_t_sample.head()

# both of them should be classified by orig tid


#%% add these to the figure
gdf_c = clk_t_sample.to_crs(epsg=3857)
gdf_f = clk_t_connected_sample.to_crs(epsg=3857)

#%% showing the full gdf for that tid does not work well visualisation wise, only look at a few points before and after the head end and satil start
print(gdf_c.true_pair_id.unique()) # has multiple cloaking gaps
# [  nan, 9911., 9912., 9913., 9914., 9915., 9916., 9917., 9918.,
#       9919., 9920., 9921., 9922., 9923., 9924., 9925., 9926., 9927.,
#       9928., 9929., 9930., 9931., 9932.]

# which one is the one in the figure?
print(random_odid) #9916_orig_2880259_dest_2880260
true_pair_id, orig_id, dest_id = int(random_odid.split('_')[0]), int(random_odid.split('_')[2]), int(random_odid.split('_')[4])
print(true_pair_id, orig_id, dest_id )

# true_pair is 9916
# point id of origin is 2880259
# point id of destination is 2880260

#%% how many points before/after this clk gap are continous, i.e., not broken by another clk gap
# look at a few columns before and after
n_pts = 65
gdf_c = gdf_c.sort_values(by='point_id_global').reset_index(drop=True)
# points before origin
gdf_c_clkgp_origin = gdf_c[(gdf_c['point_id_global'] >= orig_id - 5) & 
                            (gdf_c['point_id_global'] < orig_id)]
print('points before', orig_id-n_pts)
print('orig_id', orig_id)
print(gdf_c_clkgp_origin.point_id_global.min())
print(gdf_c_clkgp_origin.point_id_global.max())
print(gdf_c_clkgp_origin.true_pair_id.unique())

# points after destination
gdf_c_clkgp_dest = gdf_c[(gdf_c['point_id_global'] > dest_id) & 
                          (gdf_c['point_id_global'] <= dest_id + n_pts)]
print('\ndest_id', dest_id)
print('points after destination', dest_id+n_pts)
print(gdf_c_clkgp_dest.point_id_global.min())
print(gdf_c_clkgp_dest.point_id_global.max())                          
print(gdf_c_clkgp_dest.true_pair_id.unique()) #array([  nan, 9917.])

# points for true pair id of interest [2880259 2880260]
print(clk_t_sample[clk_t_sample['true_pair_id'] == true_pair_id].point_id_global.unique())
# how close is the next true pair_id?
print(clk_t_sample[clk_t_sample['true_pair_id'] == 9917].point_id_global.unique())
#[2880330 2880331]
# do not include points after 2880330 in gdf_c_clkgp_dest
#print(gdf_c_clkgp_dest.point_id_global.max()) was 2880335, 5 over     
# none include when looking at 65 points before/after               

#%%
fig, ax = plt.subplots(figsize=(12, 12))

# Origin points
gdf_c_clkgp_origin.plot(ax=ax, color='red', alpha=0.5, markersize=10, label='head')
# Destination points
gdf_c_clkgp_dest.plot(ax=ax, color='blue', alpha=0.5, markersize=10, label='tail')

# origin and destination points have the same matched geometry? (when looking at 50 points before and after)
# they are not the same, I called the same df and labelled it tail

# Other layers
gdf2.plot(ax=ax, color='red', alpha=1, markersize=60)
gdf3.plot(ax=ax, color='blue', alpha=1, markersize=60)

# Add basemap
ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron)
ax.legend()
ax.set_axis_off()

plt.show()

#%% explore in Q
gdf_c_clkgp_origin.to_parquet(r'D:\paper3\Data\debugging/gdf_c_clkgp_origin.parquet')
gdf_c_clkgp_dest.to_parquet(r'D:\paper3\Data\debugging/gdf_c_clkgp_dest.parquet')
gdf2.to_parquet(r'D:\paper3\Data\debugging/gdf2_orig.parquet')
gdf3.to_parquet(r'D:\paper3\Data\debugging/gdf3_dest.parquet')

#%% look at direction of syn points
gdf1.to_parquet(r"D:\paper3\Data\debugging/shortestPath.parquet")  # shortest path
gdf5.to_parquet(r"D:\paper3\Data\debugging/sample_synPoints_downsamples.parquet")  # downsampled syn trajectory points
#gdf2  # origin
#gdf3  # destination




#%% add these to figure

# -----------------------------
# Compute unified extent for all GeoDataFrames
# -----------------------------
all_gdfs = [gdf1, gdf2, gdf3, gdf4, gdf5, gdf_c_clkgp_origin, gdf_c_clkgp_dest]  
xmin = min(gdf.total_bounds[0] for gdf in all_gdfs)
ymin = min(gdf.total_bounds[1] for gdf in all_gdfs)
xmax = max(gdf.total_bounds[2] for gdf in all_gdfs)
ymax = max(gdf.total_bounds[3] for gdf in all_gdfs)

# add 10% padding so that labels stay witing map extent
xpad = (xmax - xmin) * 0.1
ypad = (ymax - ymin) * 0.1
xlim = (xmin - xpad, xmax + xpad)
ylim = (ymin - ypad, ymax + ypad)

# -----------------------------
# Create figure with 3 panels
# -----------------------------
fig, axes = plt.subplots(1, 3, figsize=(24, 10))
axs = axes.flatten()

# -----------------------------
# Panel A: Only head/tail points
# -----------------------------
ax = axs[0]
gdf_c_clkgp_origin.plot(ax=ax, color='#FDD45F', alpha=1, markersize=16)#, label='head')
gdf_c_clkgp_dest.plot(ax=ax, color='#C09003', alpha=1, markersize=16)#, label='tail')

# origin shortest path
gdf2.plot(ax=ax, color='#FDD45F', alpha=1, markersize=60, zorder=3)
# destination shortest path
gdf3.plot(ax=ax, color='#C09003', alpha=1, markersize=60, zorder=4)

# annotate
annotate_with_halo(ax, gdf2.iloc[0].orig_geometry, "origin:\nhead end",
                   xytext=(-0, 100), va="bottom", ha="center", text_fontsize=18)
annotate_with_halo(ax, gdf3.iloc[0].dest_geometry, "destination:\ntail start",
                   xytext=(0, -60), va="top", ha="center", text_fontsize=18)

# set unified extent
ax.set_xlim(xlim)
ax.set_ylim(ylim)

ctx.add_basemap(ax, source=ctx.providers.CartoDB.PositronNoLabels, attribution=False)
ax.set_axis_off()
ax.set_title("(A) Head and tail", fontsize=24)

# -----------------------------
# Panel B: Original plot
# -----------------------------
ax = axs[1]
gdf1.plot(ax=ax, color='black', alpha=0.6, linewidth=1.5, zorder=1)
gdf4.plot(ax=ax, color='black', alpha=0.6, markersize=16, zorder=2)
gdf2.plot(ax=ax, color='#FDD45F', alpha=1, markersize=60, zorder=3)
gdf3.plot(ax=ax, color='#C09003', alpha=1, markersize=60, zorder=4)
gdf_c_clkgp_origin.plot(ax=ax, color='#FDD45F', alpha=1, markersize=16)#, label='head')
gdf_c_clkgp_dest.plot(ax=ax, color='#C09003', alpha=1, markersize=16)#, label='tail')

# annotate
annotate_with_halo(ax, gdf2.iloc[0].orig_geometry, "origin:\nhead end",
                   xytext=(-0, 100), va="bottom", ha="center", text_fontsize=18)
annotate_with_halo(ax, gdf3.iloc[0].dest_geometry, "destination:\ntail start",
                   xytext=(0, -60), va="top", ha="center", text_fontsize=18)

# set unified extent
ax.set_xlim(xlim)
ax.set_ylim(ylim)

ctx.add_basemap(ax, source=ctx.providers.CartoDB.PositronNoLabels, attribution=False)
ax.set_axis_off()
ax.set_title("(B) Connected head and tail", fontsize=24)


# -----------------------------
# Panel C: show downsampled synthetic points
# -----------------------------
ax = axs[2]
gdf1.plot(ax=ax, color='black', alpha=0.6, linewidth=1.5, zorder=1) # shortest path
gdf5.plot(ax=ax, color='black', alpha=0.6, markersize=16, zorder=2)  # downsampled syn trajectory points
gdf2.plot(ax=ax, color='#FDD45F', alpha=1, markersize=60, zorder=3) # origin
gdf3.plot(ax=ax, color='#C09003', alpha=1, markersize=60, zorder=4) # destination
gdf_c_clkgp_origin.plot(ax=ax, color='#FDD45F', alpha=1, markersize=16)#, label='head')
gdf_c_clkgp_dest.plot(ax=ax, color='#C09003', alpha=1, markersize=16)#, label='tail')

# annotate
annotate_with_halo(ax, gdf2.iloc[0].orig_geometry, "origin:\nhead end",
                   xytext=(-0, 100), va="bottom", ha="center", text_fontsize=18)
annotate_with_halo(ax, gdf3.iloc[0].dest_geometry, "destination:\ntail start",
                   xytext=(0, -60), va="top", ha="center", text_fontsize=18)

# set unified extent
ax.set_xlim(xlim)
ax.set_ylim(ylim)

ctx.add_basemap(ax, source=ctx.providers.CartoDB.PositronNoLabels, attribution=False)
ax.set_axis_off()
ax.set_title("(C) Downsampled synthetic trajectory points", fontsize=24)

# Save figure as SVG
# -----------------------------
fig.tight_layout()
fig.savefig(r"\\tsclient\R\paper3\Figures/HeadTail_SynPoints_3Panel_inclHeadTail.svg", format="svg", bbox_inches="tight", dpi=300)

plt.show()