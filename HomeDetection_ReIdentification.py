#%% Home detection debugging
#%% Home detection debugging
import geopandas as gpd

gdf_edges_swppd = gpd.read_parquet(r"D:\paper3\Data\output/final_points_edgeSwap_FINAL_ContainerDatetime.parquet")
#gdf_nodess_swppd = gpd.read_parquet(r"d:\paper3\Data\filled_trajectories_list\trajectories_swapped_nodes_FINAL_ContainerDatetime.parquet")


#%% attributes used to detect stops:
# sub_container_id: sub_container_id = the split container

# see:
#edges_traj_collection = mpd.TrajectoryCollection(
#    gdf_edges_swppd,
#    traj_id_col='sub_container_id',
#    t='container_datetime'
#)

#%%
print(gdf_edges_swppd.columns)
gdf_edges_swppd[['container_id', 'sub_container_id']] # definitley the new id

#%% have these users, the one with stop points inside the sig loc, been swapped at all?
# i.e. is there only one container_id of these users?

# ranks:
#['1_0d105d8c884c653542c76c25aee0bcf4dd040e7e'
# '2_30e2f6772f3b37ed8cb82a984e5c1cdba86d26ab'
# '2_39cefe17d9a11d21fd520cbd981ad1aa6c06073c'
# '1_a0ac0ba30aa04f38f0dfa6bc8f289fa924f6f543']

# users
#['0d105d8c884c653542c76c25aee0bcf4dd040e7e', '30e2f6772f3b37ed8cb82a984e5c1cdba86d26ab', '39cefe17d9a11d21fd520cbd981ad1aa6c06073c', 'a0ac0ba30aa04f38f0dfa6bc8f289fa924f6f543']


u_sigLoc_same = gdf_edges_swppd[gdf_edges_swppd['container_uid'].isin(['0d105d8c884c653542c76c25aee0bcf4dd040e7e', '30e2f6772f3b37ed8cb82a984e5c1cdba86d26ab', '39cefe17d9a11d21fd520cbd981ad1aa6c06073c', 'a0ac0ba30aa04f38f0dfa6bc8f289fa924f6f543'])]
u_sigLoc_same.groupby(['sub_container_id'])['orig_uid'].nunique() # more than one user, so they have been swapped! (for edges)

#%%
u_sigLoc_same_nodes = gdf_nodess_swppd[gdf_nodess_swppd['container_uid'].isin(['0d105d8c884c653542c76c25aee0bcf4dd040e7e', '30e2f6772f3b37ed8cb82a984e5c1cdba86d26ab', '39cefe17d9a11d21fd520cbd981ad1aa6c06073c', 'a0ac0ba30aa04f38f0dfa6bc8f289fa924f6f543'])]
u_sigLoc_same_nodes.groupby(['sub_container_id'])['orig_uid'].nunique() # more than one user, so they have been swapped! (for edges)


#%% stop points
stop_points_edges = gpd.read_parquet(r"D:\paper3\Data\output\Evaluation_HomeDetection/edgeSwapped_split_StopPoints.parquet")
print(stop_points_edges.stop_id.nunique()) # 115,002, but 79,694,465 points total...
stop_points_edges.head() # traj_id, container_uid (I added those back)

# stop points by trajecorty (container)





#%% ############################################################
import geopandas as gpd
gdf_edges_swppd = gpd.read_parquet(r"D:\paper3\Data\output/final_points_edgeSwap_FINAL_ContainerDatetime.parquet")

#%% actually one final user has more than 2 original significant locations.
# ONE FINAL USERS NEW SIGNIFICANT LOCATION SHOULD NOT BE IN ANY OF IT'S "SUB-USERS" 
sorted(gdf_edges_swppd.columns)
# look at one user. must know all orig users

#%%
n_origU_by_newU = gdf_edges_swppd.groupby(['container_uid'])['orig_uid'].nunique().reset_index()
print(n_origU_by_newU['orig_uid'].median()) # 93
print(n_origU_by_newU['orig_uid'].min()) # 67
print(n_origU_by_newU['orig_uid'].max()) # 97

#%%
#%% how many points do I have by the orginal user
gdf_edges_swppd.groupby(['container_uid'])['orig_uid'].value_counts()

#%%
gdf_edges_swppd.groupby('container_uid')['orig_uid'] \
    .value_counts(normalize=True) \
    .mul(100) \
    .unstack(fill_value=0)

#%%
import pandas as pd

counts = gdf_edges_swppd.groupby('container_uid')['orig_uid'].value_counts()
perc = gdf_edges_swppd.groupby('container_uid')['orig_uid'].value_counts(normalize=True).mul(100)

result = pd.concat([counts, perc], axis=1)
result.columns = ['count', 'percent']
result

#%%
print(result['percent'].max()) #76
print(result['percent'].median()) #0.6
print(result['percent'].min())

#%%
print(result['count'].max()) # 50647
print(result['count'].median()) # 427
print(result['count'].min()) # 1

#%%
result['count'].hist(bins=30)

#%% outliers removed
import matplotlib.pyplot as plt

# Apply ggplot style
plt.style.use('ggplot')

# IQR filtering
Q1 = result['count'].quantile(0.25)
Q3 = result['count'].quantile(0.75)
IQR = Q3 - Q1

filtered = result[
    (result['count'] >= Q1 - 1.5 * IQR) &
    (result['count'] <= Q3 + 1.5 * IQR)
]

# Plot
plt.figure()
plt.hist(filtered['count'], bins=30)
plt.xlabel('Number of points by original users contributing to new user')
plt.ylabel('Frequency')
plt.title('Swapped along edges - split, outliers removed')
plt.show()

#%%
max_contributionOfOrigtoNewUser = gdf_edges_swppd.groupby('container_uid')['orig_uid'].value_counts(normalize=True).groupby(level=0).max().mul(100).reset_index()
max_contributionOfOrigtoNewUser

#%%
print(max_contributionOfOrigtoNewUser.proportion.max())         # 76%
print(max_contributionOfOrigtoNewUser.proportion.median())      # 8%
print(max_contributionOfOrigtoNewUser.proportion.min())         # 3%















#%%##################################
# need the orid sig loc plus uid: cloaking_geom
# need the sig loc after swapping:
#%% need the contributing orig uid to each new user, i.e. container_uid
EcontainerUID_to_contributorUID_dict = gdf_edges_swppd.groupby('container_uid')['orig_uid'].unique().to_dict()
EcontainerUID_to_contributorUID_dict

#%%
e_nContributors = {k: len(v) for k, v in EcontainerUID_to_contributorUID_dict.items()}
e_nContributors_sorted = dict(sorted(e_nContributors.items(), key=lambda x: x[1]))
e_nContributors_sorted # minimum 67 users contributing to one final container_uid 
# --> each user thas participated in edge swapping
#%% median number of contributing users to new swapped user
import numpy as np
e_nContributors_values = list(e_nContributors.values())
median_e_nContributors_values = np.median(e_nContributors_values)
median_e_nContributors_values

#%% need the sig loc after swapping: on VM131
import pandas as pd

#ranked_clusters_nodes_top2.to_parquet(r"\\tsclient\R\paper3\Data\swappedtrajs\StopPoints\clusteringStopPointsPostSwapping/NodesSwappingStopPointsClusters_rankedTop2.parquet")

StpPntsClstered_edges = gpd.read_parquet(r"\\tsclient\R\paper3\Data\swappedtrajs\StopPoints\clusteringStopPointsPostSwapping/StpPntsClstered_edges_top2.parquet")
StpPntsClstered_edges.head()
# uid is container_uid, aka new uid
# point geometry 

#%% # need the orid sig loc plus uid: cloaking_geom
cloaking_geom = gpd.read_file(r"\\tsclient\R\paper3\Data\swappedtrajs\StopPoints\clusteringStopPointsPostSwapping\polys.gpkg")
cloaking_geom.head()
#uid_ is the orig uid
# polygon geometry

#%% prep data
# ensure crs is the same for both
print(StpPntsClstered_edges.crs)
print(cloaking_geom.crs)
cloaking_geom = cloaking_geom.to_crs(2193)
print(StpPntsClstered_edges.crs)
print(cloaking_geom.crs)

# rename columns for clarity
cloaking_geom = cloaking_geom.drop(columns=['uid'])
cloaking_geom = cloaking_geom.rename(columns={'uid_': 'contributor_uid', 'rank_uid': 'contributor_rank_uid'})
StpPntsClstered_edges = StpPntsClstered_edges.rename(columns={'uid': 'container_uid', 'rank_uid': 'container_rank_uid'})

#%% group geometryies by uid (becuase we have 2 sig per user)
e_container_points = StpPntsClstered_edges.groupby('container_uid').apply(lambda df: df[['container_rank_uid', 'geometry']].to_dict('records'))
contributor_polys = cloaking_geom.groupby('contributor_uid').apply(lambda df: df[['contributor_rank_uid', 'geometry']].to_dict('records'))

# compute intersections
rows = []

for container_uid, contributor_list in EcontainerUID_to_contributorUID_dict.items():
    
    points = e_container_points.get(container_uid, [])
    
    for contributor_uid in contributor_list:
        polys = contributor_polys.get(contributor_uid, [])
        
        for p in points:
            for poly in polys:
                
                rows.append({
                    'container_uid': container_uid,
                    'contributor_uid': contributor_uid,
                    'container_rank_uid': p['container_rank_uid'],
                    'contributor_rank_uid': poly['contributor_rank_uid'],
                    'intersects': p['geometry'].intersects(poly['geometry'])
                })

eSwppd_intersections = pd.DataFrame(rows)
print(eSwppd_intersections.intersects.value_counts())
#intersects
#False    34943
#True        45 # not too bad
eSwppd_intersections


#%% look at the True intersect one - how many different container_uid are involved?
print(eSwppd_intersections[eSwppd_intersections['intersects']==True]['container_uid'].nunique()) # 35
# 35 out of 97 users have at least one significant location intersecting with one of their contributor's significant locations
# less than half..
eSwppd_intersections[eSwppd_intersections['intersects']==True]

eSwppd_reidentified = eSwppd_intersections[eSwppd_intersections['intersects']==True]
print(len(eSwppd_reidentified))

print(eSwppd_reidentified.contributor_rank_uid.nunique()) # THIS IS THE IMPORTANT ONE: number of significant locations "re-identified"
print(eSwppd_reidentified.contributor_rank_uid.nunique()) # how many new frequent locations "expose" these signfiicant locations? i.e., how often is a sig loc epxosed?






#%% how often are specific original significant locations re-identified?
eSwppd_reidentified.groupby(['contributor_rank_uid']).size().sort_values(ascending=False)

# shows the 11 significant locations
#contributor_rank_uid

# re-identified by more than one new users "signficant locatoin"
#1_0d105d8c884c653542c76c25aee0bcf4dd040e7e    12
#1_a0ac0ba30aa04f38f0dfa6bc8f289fa924f6f543     9
#2_d8e1b548c25df0c24d8d8d493d4e6db0ad25c792     7
#2_39cefe17d9a11d21fd520cbd981ad1aa6c06073c     6
#1_0d5010abd3d6f0bcd8cee8c66cb58784af4357a1     5

# re-identified by one "new frequently visited location"
#1_233fcca62bd9fd22213e17f78eaee17c55b742f0     1
#1_6de38e429e314e246d7914531e45f7e32864a863     1
#1_8f49e010015deb70a880d8e11d62d48fcd7c1490     1
#2_30e2f6772f3b37ed8cb82a984e5c1cdba86d26ab     1
#2_488e488998d387ccd0ca374eb8c9cdd1be93ebae     1
#2_81f5ef2a49ed456cfbd0fb819af4ff019d09ed4d     1

# sum is 45

#%% look at these manually
e_freq = eSwppd_reidentified['contributor_rank_uid'].value_counts()
e_reidentified_sorted = eSwppd_reidentified.set_index('contributor_rank_uid').loc[e_freq.index].reset_index()
e_reidentified_sorted[['contributor_rank_uid', 'container_rank_uid', 'container_uid']] 
# same user, both new sig loc reidentiy the SAME ONE ORIG location (not always, but one scenario)
# --> "significant locations" of "new" user must be close together, if they both "re-identify" the same original signficant location



#%%
e_counts = (
    eSwppd_reidentified.groupby('contributor_rank_uid')
    .size()
    .value_counts()
    .reset_index(name='frequency')
    .rename(columns={'index': 'NrOfReidentifications'})
    .sort_values('NrOfReidentifications')
)
e_counts

#%% a histogram of "re-identification risk of specific significant locations"
plt.style.use('ggplot')
fig, ax = plt.subplots(figsize=(4, 3))

# remove grey background
fig.patch.set_facecolor('white')
ax.set_facecolor('white')

# bar plot with label for legend
ax.bar(
    e_counts['NrOfReidentifications'],
    e_counts['frequency'],
    color='#FDD45F',
    label='Edge-swapping'
)

# labels
ax.set_xlabel('Significant location:\nnumber of times "re-identified"', color='#555555')
ax.set_ylabel('Frequency', color='#555555')

# ticks
ax.set_xticks(e_counts['NrOfReidentifications'])
ax.tick_params(axis='x', colors='#555555')
ax.tick_params(axis='y', colors='#555555')

# spines
ax.spines['bottom'].set_color('#555555')
ax.spines['left'].set_color('#555555')

# grid
ax.grid(axis='y', linestyle='--', alpha=0.4, color='#cccccc')

# legend
ax.legend(frameon=False)

# remove top/right spines
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout()
plt.show()








#%% MAPS
#%% plot them all at once?
get_E_newsigloc_geom = eSwppd_reidentified['container_rank_uid'].unique()
get_E_origsigloc_geom = eSwppd_reidentified['contributor_rank_uid'].unique()

#%% plot these significant locations
print(StpPntsClstered_edges.crs)
print(cloaking_geom.crs)
StpPntsClstered_edges = StpPntsClstered_edges.to_crs(cloaking_geom.crs)
print(StpPntsClstered_edges.crs)

#%%
#StpPntsClstered_edges
print(len(StpPntsClstered_edges))
StpPntsClstered_edges_ri = StpPntsClstered_edges[StpPntsClstered_edges['container_rank_uid'].isin(get_E_newsigloc_geom)]
print(len(StpPntsClstered_edges_ri))

#cloaking_geom
print(len(cloaking_geom))
cloaking_geom_riE = cloaking_geom[cloaking_geom['contributor_rank_uid'].isin(get_E_origsigloc_geom)]
print(len(cloaking_geom_riE))



#%% interactive map of TRUE intersections
import folium

StpPntsClstered_edges_ri_4326 = StpPntsClstered_edges_ri.to_crs(epsg=4326)
cloaking_geom_ri_4326 = cloaking_geom_riE.to_crs(epsg=4326)

# get center of your data
center = [
    StpPntsClstered_edges_ri_4326.geometry.centroid.y.mean(),
    StpPntsClstered_edges_ri_4326.geometry.centroid.x.mean()
]

m = folium.Map(location=center, zoom_start=13)

# add first layer
folium.GeoJson(
    StpPntsClstered_edges_ri_4326,
    name="after swapping",
    style_function=lambda x: {"color": "blue", "weight": 3}
).add_to(m)

# add second layer
folium.GeoJson(
    cloaking_geom_riE,
    name="sensitive location",
    style_function=lambda x: {"color": "red", "weight": 3}
).add_to(m)

# layer control toggle
folium.LayerControl().add_to(m)

# save + open in browser
m.save("map.html")

import webbrowser
webbrowser.open("map.html")





# ADD NODE SWAPPING AND EDGE SWAPPING TO MAP, SELECT ONE CLOAKING GEOM TO REPRESENT AS FIGURE
#%% figure should be static
import matplotlib.pyplot as plt

fig, ax = plt.subplots()

StpPntsClstered_edges_ri.plot(ax=ax, color='blue', label='after swapping')
cloaking_geom_riE.plot(ax=ax, color='red', label='sensitive location')

ax.legend()
plt.show()