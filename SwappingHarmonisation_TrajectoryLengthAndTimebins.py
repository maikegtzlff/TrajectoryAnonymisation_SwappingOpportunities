
#%% harmonise timestamps and trajectory length
# and uid (depends on final_tid)
# would be interesting to see the distribution...
# do I still have 97 users? or have "main" heads from one user been favored? ie bias? 
# and number of tid: becore swapping: 19,189
import geopandas as gpd
t_cswappingl_origsynf_headtailsynf = gpd.read_parquet(r"D:\paper3\Data\ClkSwpSynFilled_backup.parquet")

print(t_cswappingl_origsynf_headtailsynf.final_tid_origsynfilled.nunique()) # same as before, 19,189

#%% get final uid column
t_cswappingl_origsynf_headtailsynf['final_uid'] = t_cswappingl_origsynf_headtailsynf['final_tid_origsynfilled'].str.split('_').str[1]
t_cswappingl_origsynf_headtailsynf['final_uid'].nunique() 

#%% calculate to base
t_p2 = gpd.read_parquet(r'\\tsclient\R\paper3\filledtrajectories_gdfenriched2\traj_filled_baseline_ShiftedTimestamps_gapAware_CloakingGeomID_AllCloakingAreas_clean.parquet')


#%% trajectory points by user
# 97 users, same as before, didnt loose any user
# has the distribution of number of trajectory points by user changed?

#counts1 = t_cswappingl_origsynf_headtailsynf.groupby('final_uid').size()
counts2 = t_p2.groupby('uid').size()

#print(counts1.describe()) # t_cswappingl_origsynf_headtailsynf
#count        97
#mean      80,109
#std       53,102 # is lower
#min        2,518 # is higher
#25%       38,580 # litttle higher
#50%       71,446 # median is higher
#75%      111,535 # higher
#max      217,971 # lower --> less extreme outliers

print(counts2.describe()) # t_p2
#count        97
#mean      75,618
#std       63,413
#min        1,995
#25%       31,696
#50%       57,225
#75%       99,526
#max      370,379

#%% trajectory length
# what is the median, mean and std before swapping? max/min

# these lengths are not based on the road network
#%% must calculate trajectory lengths first
if t_p2.crs.to_epsg() != 2193:  
    print("ransforming to EPSG:2193")
    t_p2 = t_p2.to_crs(epsg=2193)

t_p2 = t_p2.sort_values(['tid_subid', 'row_uid'])

t_p2['prev_geom'] = t_p2.groupby('tid_subid')['match_geometry'].shift(1)

t_p2['segment_length_m'] = t_p2.geometry.distance(t_p2['prev_geom'])
t_p2['segment_length_m'] = t_p2['segment_length_m'].fillna(0)
t_p2_length = t_p2.groupby('tid_subid')['segment_length_m'].sum().reset_index()
t_p2_length.rename(columns={'segment_length_m':'total_length_m'}, inplace=True)

t_p2_length.head()

#%% same for swapped trajectories
if t_cswappingl_origsynf_headtailsynf.crs.to_epsg() != 2193:  
    print("ransforming to EPSG:2193")
    t_cswappingl_origsynf_headtailsynf = t_cswappingl_origsynf_headtailsynf.to_crs(epsg=2193)

t_cswappingl_origsynf_headtailsynf = t_cswappingl_origsynf_headtailsynf.sort_values(['final_tid_origsynfilled', 'point_id_global_synfilled'])

t_cswappingl_origsynf_headtailsynf['prev_geom'] = t_cswappingl_origsynf_headtailsynf.groupby('final_tid_origsynfilled')['match_geometry'].shift(1)

t_cswappingl_origsynf_headtailsynf['segment_length_m'] = t_cswappingl_origsynf_headtailsynf.geometry.distance(t_cswappingl_origsynf_headtailsynf['prev_geom'])
t_cswappingl_origsynf_headtailsynf['segment_length_m'] = t_cswappingl_origsynf_headtailsynf['segment_length_m'].fillna(0)
t_cswappingl_origsynf_headtailsynf_length = t_cswappingl_origsynf_headtailsynf.groupby('final_tid_origsynfilled')['segment_length_m'].sum().reset_index()
t_cswappingl_origsynf_headtailsynf_length.rename(columns={'segment_length_m':'total_length_m'}, inplace=True)

t_cswappingl_origsynf_headtailsynf_length.head()

#%% compare distributions
from scipy.stats import ks_2samp

stat, p_value = ks_2samp(t_p2_length['total_length_m'], t_cswappingl_origsynf_headtailsynf_length['total_length_m'])
print(f"Kolmogorov-Smirnov: {stat:.3f}, p-value: {p_value:.3e}")
# Kolmogorov-Smirnov: 0.019, p-value: 2.137e-03
# Kolmogorov-Smirnov very small, maximum difference between the cumulative distributions of the two is small (expected)
# p-value = 0.002137, < 0.05, rejects null hypothesis --> the two distributions are NOT identical (expected)


#%%
print("Cloaked and filled (km):")
print((t_p2_length['total_length_m'] / 1000).describe())

print("\nSwapped within cloaking geometry (km):")
print((t_cswappingl_origsynf_headtailsynf_length['total_length_m'] / 1000).describe())

#Cloaked and filled (km):
#count    19189.000000
#mean        66.500298
#std         69.839029
#min          0.000000
#25%         13.950139
#50%         43.837043
#75%         95.354925
#max        554.174061
#Name: total_length_m, dtype: float64

#Swapped within cloaking geometry (km):
#count    19189.000000
#mean        67.768108
#std         70.615634
#min          0.000000
#25%         14.607343
#50%         46.466780
#75%         97.152168
#max        694.096202

# --> not too different for swapping at cloaking geometries, must be more of an issue at edge and node swapping as a result of more atcive swapping
#%% histogram of trajectory length
# must also look at trajectory length for node and edge swapping
import matplotlib.pyplot as plt

plt.figure(figsize=(10,6))
plt.hist(
    t_p2_length['total_length_m'],
    bins=50,
    alpha=0.5,
    label='Cloaked and filled',
    color='#383a6b'  # dark blue
)
plt.hist(
    t_cswappingl_origsynf_headtailsynf_length['total_length_m'],
    bins=50,
    alpha=0.5,
    label='Swapped within cloaking geometry',
    color='#fcc72d'  # yellow
)
plt.xlabel("Trajectory length (m)")
plt.ylabel("Number of trajectories")
plt.legend()
plt.title("Distribution of Trajectory Lengths")
plt.show()

#%% split the tid of the swapped df by artificially adding tids
# make sure that both segments of the split tid have reasonable lengths




#%% timestamps: fix after splitting trajectories