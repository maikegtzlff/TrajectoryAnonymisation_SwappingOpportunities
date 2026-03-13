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

#%% must downsample

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
gdf1.plot(ax=ax, color='black', alpha=0.6, linewidth=1.5, zorder=1)
gdf5.plot(ax=ax, color='black', alpha=0.6, markersize=16, zorder=2)  # new data
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
ax.set_title("(C) Downsampled synthetic trajectory points", fontsize=16)

# -----------------------------
# Save figure as SVG
# -----------------------------
fig.tight_layout()
fig.savefig(r"\\tsclient\R\paper3\Figures/HeadTail_SynPoints_3Panel.svg", format="svg", bbox_inches="tight", dpi=300)

plt.show()


#%% include some points of head and tail?



#%% "fill" swapped df




#%% harmonise timestamps and trajectory length