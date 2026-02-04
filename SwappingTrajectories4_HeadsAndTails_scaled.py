#%%


#%% list of trajectories
current = t1
others = [t2, t3, t4, t5, t6]

updated_others = []

for df in others:
    current, df_swapped = swap_tails_auto(current, df, n=3)
    updated_others.append(df_swapped)

#%%
print(len(updated_others)) # same length as before
print(current.source_tid_subid.nunique()) # 3 different tids
for i in range(len(updated_others)):
    print(updated_others[i].source_tid_subid.nunique()) # most "others" have more than one tid now




#%% ok so now, do I exclude t1 from swapping or do I keep going?
trajectories = [t1, t2, t3, t4, t5, t6]
num_trajectories = len(trajectories)

# You can repeat this for multiple passes if needed
num_passes = 5  # change to higher if you want several rounds

for _ in range(num_passes):
    for i in range(num_trajectories):
        current = trajectories[i]
        others_indices = [j for j in range(num_trajectories) if j != i]
        
        updated_others = []
        for j in others_indices:
            current, df_swapped = swap_tails_auto(current, trajectories[j], n=3)
            updated_others.append(df_swapped)
        
        # Save updated current
        trajectories[i] = current
        
        # Save updated others back to their positions
        for idx, j in enumerate(others_indices):
            trajectories[j] = updated_others[idx]

#%%
for i in range(len(trajectories)):
    print(trajectories[i].source_tid_subid.nunique()) # most "others" have more than one tid now

# number of unique source_tid by updated trajectory 
# after setting num_pass to 2 - there are some "cannot wsap overlapping user" and no matching uv messages
#4
#5
#2
#2
#2
#5

# setting num_pass to 20 - actually reduced number of source-Tid-subid
#2
#5
#2
#3
#3
#3

# setting it to 200
#2
#5
#2
#3
#3
#3

# might depend more on number of input trajectories than num_pass

#%% look at output in q
for i in range(len(trajectories)):
    trajectories[i].to_parquet(fr"E:\paper3\data\SampleTids\SwappingAtNodes\MoreManual\trajectoryByTrajectory\HeadsAndTails_scaledUP/tswapped_{i}.parquet")

