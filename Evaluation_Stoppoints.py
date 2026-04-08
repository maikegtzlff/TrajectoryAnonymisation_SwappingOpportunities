#%% load libaries
import geopandas as gpd
import pandas as pd

#%% load stop points

stpts_i = gpd.read_parquet(r"d:\paper3\Data\output\Evaluation_HomeDetection\nodesSwapped_split_StopPoints.parquet")
stpts_e = gpd.read_parquet(r"D:\paper3\Data\output\Evaluation_HomeDetection/edgeSwapped_split_StopPoints.parquet")
stpts_c = gpd.read_parquet(r"d:\paper3\Data\output\Evaluation_HomeDetection\cloakedSwapped_StopPoints.parquet") 

# baseline: not swapped, cloaked and filled
stpts_cf = gpd.read_parquet(r"D:\paper3\Data\output\Evaluation_HomeDetection/cloakedFilledReleaseP3_final_StopPoints.parquet")
stpts_cf.head()

#%% explore stop points
stpts_e.head()
#%% intersection stops
stpts_i.head()
#%%
stpts_c.head()

#%% number of stay points - same as table in doc?
print('stpts_cf')
print(len(stpts_cf))                # 117,124
print(stpts_cf.stop_id.nunique())   # same

print('\nstpts_i')
print(len(stpts_i))                 # 7,907,536
print(stpts_i.stop_id.nunique())    # 104,173

print('\nstpts_e')
print(len(stpts_e))                 # 26,549,114
print(stpts_e.stop_id.nunique())    # 114,895

print('\nstpts_c')
print(len(stpts_c))                 # 79,694,465
print(stpts_c.stop_id.nunique())    # 115,002

# nunique are the values reported in the doc

#%% are those duplicate rows?
print(stpts_i.duplicated().sum())   # 7,803,363
print(stpts_e.duplicated().sum())   # 26,434,219
print(stpts_c.duplicated().sum())   # 79,579,463

#%% drop duplicate rows
stpts_i = stpts_i.drop_duplicates()
stpts_e = stpts_e.drop_duplicates()
stpts_c = stpts_c.drop_duplicates()

#%% export these
stpts_i.to_parquet(r"d:\paper3\Data\output\Evaluation_HomeDetection\nodesSwapped_split_StopPoints_nodupl.parquet")
stpts_e.to_parquet(r"D:\paper3\Data\output\Evaluation_HomeDetection/edgeSwapped_split_StopPoints_nodupl.parquet")
stpts_c.to_parquet(r"d:\paper3\Data\output\Evaluation_HomeDetection\cloakedSwapped_StopPoints_nodupl.parquet") 





#%% 
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 4, figsize=(16, 4))

axes[0].hist(stpts_cf['duration_s'], bins=30)
axes[0].set_title('Baseline')

axes[1].hist(stpts_i['duration_s'], bins=30)
axes[1].set_title('Intersection-swapped')

axes[2].hist(stpts_e['duration_s'], bins=30)
axes[2].set_title('Edge-swapped')

axes[3].hist(stpts_c['duration_s'], bins=30)
axes[3].set_title('Cloaking area-swapped')

plt.tight_layout()
plt.show()



#%% KDE overlayed
import seaborn as sns

fig, axes = plt.subplots(1, 4, figsize=(16, 4))

sns.histplot(stpts_cf['duration_s'], kde=True, ax=axes[0])
axes[0].set_title('Baseline')

sns.histplot(stpts_i['duration_s'], kde=True, ax=axes[1])
axes[1].set_title('Intersection-swapped')

sns.histplot(stpts_e['duration_s'], kde=True, ax=axes[2])
axes[2].set_title('Edge-swapped')

sns.histplot(stpts_c['duration_s'], kde=True, ax=axes[3])
axes[3].set_title('Cloaking area-swapped')

plt.tight_layout()
plt.show()

#%%
import scipy
from scipy.stats import shapiro

stat, p = shapiro(stpts_cf['duration_s'])
print(p) # 4.28493513583346e-167

stat, p = shapiro(stpts_i['duration_s'])
print(p) # 1.2500370313712664e-173


stat, p = shapiro(stpts_e['duration_s'])
print(p) # 1.689404838970995e-165


stat, p = shapiro(stpts_c['duration_s'])
print(p) # 5.978919005282425e-167


#%% as boxplots instead
#%% compare distributions statistically
# Mann-Whitny U
from scipy.stats import mannwhitneyu

baseline = stpts_cf['duration_s'] / 60
comparisons = {
    'Intersection-swapping': stpts_i['duration_s'] / 60,
    'Edge-swapping': stpts_e['duration_s'] / 60,
    'Cloaking area-swapping': stpts_c['duration_s'] / 60
}

for name, data in comparisons.items():
    stat, p = mannwhitneyu(baseline, data, alternative='two-sided')
    print(f'{name} vs Baseline: U={stat:.2f}, p={p:.3e}')

#Intersection-swapping vs Baseline: U=6612096394.00, p=7.220e-255   - p < 0.001 = highly significant difference
#Edge-swapping vs Baseline: U=6554096210.50, p=3.055e-27            - p < 0.001 = significant difference
#Cloaking area-swapping vs Baseline: U=6711221661.00, p=1.450e-01   - p > 0.05 = NOT STATITICALLY DIFFERENT

#%%
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
import numpy as np

plt.style.use('ggplot')

# --- Data in minutes ---
data = [
    stpts_cf['duration_s'] / 60,
    stpts_e['duration_s'] / 60,
    stpts_i['duration_s'] / 60,
    stpts_c['duration_s'] / 60
]

labels = [r'Baseline t$_{f}$', r't$_{se} split$', r't$_{si} split$', r't$_{sc}$']
colors = ['#383a6b', '#FDD45F', '#F3B503', '#C09003']

fig, ax = plt.subplots(figsize=(10, 5))

# --- Boxplot without outliers ---
box = ax.boxplot(
    data,
    showfliers=False,
    patch_artist=True,
    medianprops=dict(color='black', linewidth=2)
)

# Set box colors
for patch, color in zip(box['boxes'], colors):
    patch.set_facecolor(color)

# --- Label medians with white halo ---
whisker_max = max([whisker.get_ydata()[1] for whisker in box['whiskers']])
line_gap_frac = 0.05
line_gap = whisker_max * line_gap_frac

for i, median in enumerate(box['medians']):
    median_value = median.get_ydata()[0]
    txt = ax.text(
        i + 1,
        median_value + line_gap,
        f'{int(round(median_value))} min',
        ha='center',
        va='bottom',
        fontsize=12,
        color='black',
        alpha=0.7
    )
    txt.set_path_effects([
        path_effects.Stroke(linewidth=3, foreground='white'),
        path_effects.Normal()
    ])

# --- Automatic stacked significance lines with fixed small offset ---
def add_stat_lines_auto(ax, box, comparisons, line_gap_frac=0.05, star_offset=0.5):
    """
    Add multiple significance lines automatically stacked above boxes.
    
    comparisons: list of tuples (x1, x2, text)
    star_offset: fixed offset above the line in data units
    """
    whisker_maxes = [whisker.get_ydata()[1] for whisker in box['whiskers']]
    global_max = max(whisker_maxes)
    line_gap = global_max * line_gap_frac
    
    line_positions = []
    
    for x1, x2, text in comparisons:
        y_base = max(box['whiskers'][2*(x1-1)+1].get_ydata()[1],
                     box['whiskers'][2*(x2-1)+1].get_ydata()[1])
        
        if line_positions:
            y = max(y_base + line_gap, max(line_positions) + line_gap)
        else:
            y = y_base + line_gap
        line_positions.append(y)
        
        # Draw horizontal and vertical lines
        ax.plot([x1, x2], [y, y], color='black', linewidth=1.5)
        ax.plot([x1, x1], [y, y - line_gap], color='black', linewidth=1.5)
        ax.plot([x2, x2], [y, y - line_gap], color='black', linewidth=1.5)
        
        # Draw significance text very close to line using fixed offset
        txt = ax.text(
            (x1 + x2) / 2,
            y + star_offset,  # small fixed offset
            text,
            ha='center',
            va='bottom',
            fontsize=12,
            color='#333333'
        )
        txt.set_path_effects([
            path_effects.Stroke(linewidth=3, foreground='white'),
            path_effects.Normal()
        ])
    
    # Adjust ylim to fit topmost line + star
    ax.set_ylim(0, max(line_positions) + star_offset*2)

# --- Define comparisons ---
comparisons = [
    (1, 2, '***'),  # Edge-swapping vs Baseline
    (1, 3, '***'),  # Intersection-swapping vs Baseline
    (1, 4, 'ns')    # Cloaking vs Baseline
]

add_stat_lines_auto(ax, box, comparisons, line_gap_frac=0.05, star_offset=0.5)

# --- White background and spines ---
ax.set_facecolor('white')
ax.grid(False)
ax.yaxis.grid(True, linestyle=':', color='gray', alpha=0.7, zorder=0)
ax.spines['left'].set_visible(True)
ax.spines['left'].set_color('black')
ax.spines['left'].set_linewidth(0.8)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# --- Axis labels and legend ---
ax.set_xticks([1,2,3,4])
ax.set_xticklabels(labels, fontsize=14)
ax.set_ylabel('Stop duration in minutes', fontsize=16, color='#555555')
ax.set_xlabel("Trajectory swapping approach", fontsize=16, color='#555555')

handles = [plt.Line2D([0], [0], color=c, lw=8) for c in colors]
custom_labels = [r'Baseline (t$_{f}$)', r'Edge-swapping (t$_{se} split$)', 
                 r'Intersection-swapping (t$_{si} split$)', r'Cloaking area-swapping (t$_{sc}$)']
ax.legend(handles, custom_labels, loc='upper center', bbox_to_anchor=(0.5, -0.15),
          ncol=2, frameon=False, fontsize=14)

plt.tight_layout()
plt.savefig(r"\\tsclient\R\paper3\Figures/StopDuration_boxplot.svg", format="svg", bbox_inches="tight", dpi=300)

plt.show()



#%% by time bin
# Assume start_time is a datetime column
import pandas as pd

# Example: ensure start_time is datetime
stpts_cf['start_time'] = pd.to_datetime(stpts_cf['start_time'])
stpts_i['start_time'] = pd.to_datetime(stpts_i['start_time'])
stpts_e['start_time'] = pd.to_datetime(stpts_e['start_time'])
stpts_c['start_time'] = pd.to_datetime(stpts_c['start_time'])

# Define a function to categorize time bins
def time_bin(hour):
    if 7 <= hour < 9:
        return 'Morning Peak'
    elif 9 <= hour < 16:
        return 'Flat Peak'
    elif 16 <= hour < 20:
        return 'Evening Peak'
    else:  # 20:00 - 7:00
        return 'Nighttime'

# Add a new column for the time bin
for df in [stpts_cf, stpts_i, stpts_e, stpts_c]:
    df['time_bin'] = df['start_time'].dt.hour.apply(time_bin)

#%%
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
import numpy as np
import pandas as pd

plt.style.use('ggplot')

# --- Colors and labels ---
colors = ['#383a6b', '#FDD45F', '#F3B503', '#C09003']
labels = [r'Baseline t$_{f}$', r't$_{se} split$', r't$_{si} split$', r't$_{sc}$']

# --- Ensure datetime and add time bins ---
for df in [stpts_cf, stpts_i, stpts_e, stpts_c]:
    df['start_time'] = pd.to_datetime(df['start_time'])

def time_bin(hour):
    if 7 <= hour < 9:
        return 'Morning (7–9)'
    elif 9 <= hour < 16:
        return 'Flat Peak (9–16)'
    elif 16 <= hour < 20:
        return 'Evening (16–20)'
    else:
        return 'Night (20–7)'

for df in [stpts_cf, stpts_i, stpts_e, stpts_c]:
    df['time_bin'] = df['start_time'].dt.hour.apply(time_bin)

time_bins = ['Morning (7–9)','Flat Peak (9–16)','Evening (16–20)','Night (20–7)']

# --- Figure ---
fig, axes = plt.subplots(nrows=2, ncols=1, figsize=(12, 10))
plt.tight_layout(pad=4)

# --- Helper functions ---
def add_medians(ax, box, line_gap_frac=0.05, offset=-3):
    """Add median value labels above each box horizontally."""
    whisker_max = max([w.get_ydata()[1] for w in box['whiskers']])
    line_gap = whisker_max * line_gap_frac
    for median in box['medians']:
        median_value = median.get_ydata()[0]
        x_pos = median.get_xdata().mean()
        txt = ax.text(
            x_pos,
            median_value + line_gap + offset,
            f'{int(round(median_value))}', 
            ha='center',
            va='bottom',
            fontsize=10,
            color='black',
            alpha=0.7,
            rotation=0 
        )
        txt.set_path_effects([
            path_effects.Stroke(linewidth=3, foreground='white'),
            path_effects.Normal()
        ])

def add_stat_lines(ax, box, comparisons, line_gap_frac=0.05, star_offset=0.3):
    whisker_maxes = [w.get_ydata()[1] for w in box['whiskers']]
    global_max = max(whisker_maxes)
    line_gap = global_max * line_gap_frac
    line_positions = []
    for x1, x2, text in comparisons:
        y_base = max(box['whiskers'][2*(x1-1)+1].get_ydata()[1],
                     box['whiskers'][2*(x2-1)+1].get_ydata()[1])
        y = max(y_base + line_gap, max(line_positions)+line_gap if line_positions else y_base + line_gap)
        line_positions.append(y)
        # Draw horizontal and vertical lines
        ax.plot([x1, x2], [y, y], color='black', lw=1.5)
        ax.plot([x1, x1], [y, y - line_gap], color='black', lw=1.5)
        ax.plot([x2, x2], [y, y - line_gap], color='black', lw=1.5)
        # Draw significance text close to line
        txt = ax.text(
            (x1 + x2)/2,
            y + star_offset,
            text,
            ha='center', va='bottom',
            fontsize=10,
            color='#333333'
        )
        txt.set_path_effects([
            path_effects.Stroke(linewidth=3, foreground='white'),
            path_effects.Normal()
        ])
    if line_positions:
        ax.set_ylim(0, max(line_positions) + star_offset*2)

# ---------------------------
# Row 1: Full dataset
# ---------------------------
ax = axes[0]
data_full = [
    stpts_cf['duration_s']/60,
    stpts_e['duration_s']/60,
    stpts_i['duration_s']/60,
    stpts_c['duration_s']/60
]
box = ax.boxplot(data_full, showfliers=False, patch_artist=True, medianprops=dict(color='black', linewidth=2))
for patch, color in zip(box['boxes'], colors):
    patch.set_facecolor(color)

add_medians(ax, box)
comparisons = [(1,2,'***'), (1,3,'***'), (1,4,'ns')]
add_stat_lines(ax, box, comparisons)

ax.set_title('(A) Full Day', fontsize=14, fontweight = 'bold', y=1.05)
ax.set_xticks([1,2,3,4])
ax.set_xticklabels(labels, fontsize=12)
ax.set_ylabel('Stop duration in minutes', fontsize=12)
ax.set_facecolor('white')
ax.grid(False)
ax.yaxis.grid(True, linestyle=':', color='gray', alpha=0.7)
ax.spines['left'].set_visible(True)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# ---------------------------
# Row 2: Grouped by time bins
# ---------------------------
ax = axes[1]

# Prepare grouped data: time bin × trajectory type
grouped_data = []
for tb in time_bins:
    for traj_df in [stpts_cf, stpts_e, stpts_i, stpts_c]:
        grouped_data.append(traj_df[traj_df['time_bin']==tb]['duration_s']/60)

# Box positions: stagger them
positions = []
for j in range(4):  # 4 time bins
    for i in range(4):  # 4 trajectory types
        positions.append(j*5 + i + 1)  # spacing 5 per time bin

# Flatten data
data_flat = grouped_data

# Boxplot
box = ax.boxplot(
    data_flat,
    positions=positions,
    widths=0.8,
    patch_artist=True,
    showfliers=False,
    medianprops=dict(color='black', linewidth=2)
)

# Color boxes correctly by trajectory type
for i, patch in enumerate(box['boxes']):
    traj_idx = i % 4
    patch.set_facecolor(colors[traj_idx])

# X-ticks in the middle of each time bin
xticks = [np.mean([j*5+1, j*5+4]) for j in range(4)]
ax.set_xticks(xticks)
ax.set_xticklabels(time_bins, fontsize=12)
ax.set_ylabel('Stop duration in minutes', fontsize=12)
ax.set_title('(B) By Time Bin', fontsize=14, fontweight='bold')

# Background and grid
ax.set_facecolor('white')
ax.grid(False)
ax.yaxis.grid(True, linestyle=':', color='gray', alpha=0.7, zorder=0)
ax.spines['left'].set_visible(True)
ax.spines['left'].set_color('black')
ax.spines['left'].set_linewidth(0.8)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Median labels horizontal
add_medians(ax, box, offset=-16)

# Legend
handles = [plt.Line2D([0],[0], color=c, lw=8) for c in colors]

custom_labels = [r'Baseline (t$_{f}$)', r'Edge-swapping (t$_{se} split$)', 
                 r'Intersection-swapping (t$_{si} split$)', r'Cloaking area-swapping (t$_{sc}$)']
ax.legend(
    handles, 
    custom_labels,           
    loc='upper center',
    bbox_to_anchor=(0.5, -0.15), 
    ncol=2,
    frameon=False,
    fontsize=14,
    title="Trajectory swapping approach", 
    title_fontsize=16)

plt.tight_layout(pad=4)
plt.savefig(r"\\tsclient\R\paper3\Figures/StopDuration_boxplot_timebins.svg", format="svg", bbox_inches="tight", dpi=300)
plt.show()

#%% mann whitney by time bin
from scipy.stats import mannwhitneyu
import pandas as pd

# Trajectory dataframes
dfs = {
    'Baseline': stpts_cf,
    'Edge-swapping': stpts_e,
    'Intersection-swapping': stpts_i,
    'Cloaking area': stpts_c
}

# Automatically get exact time bins from baseline
time_bins = stpts_cf['time_bin'].unique()

# Helper to map p-values to stars
def p_to_star(p):
    if p <= 0.001:
        return '***'
    elif p <= 0.01:
        return '**'
    elif p <= 0.05:
        return '*'
    else:
        return 'ns'

results = []

for tb in time_bins:
    baseline_data = dfs['Baseline'][dfs['Baseline']['time_bin']==tb]['duration_s']/60
    if len(baseline_data) == 0:
        print(f"Skipping {tb} because baseline is empty")
        continue
    for name in ['Edge-swapping','Intersection-swapping','Cloaking area']:
        comp_data = dfs[name][dfs[name]['time_bin']==tb]['duration_s']/60
        if len(comp_data) == 0:
            print(f"Skipping {tb} {name} because data is empty")
            continue
        # Mann-Whitney U test
        U, p = mannwhitneyu(comp_data, baseline_data, alternative='two-sided')
        results.append({
            'Time bin': tb,
            'Comparison': f'{name} vs Baseline',
            'U': U,
            'p-value': p,
            'stars': p_to_star(p)
        })

# Convert to DataFrame
results_df = pd.DataFrame(results)
print(results_df)

#            Time bin                         Comparison             U  \
#0       Night (20–7)          Edge-swapping vs Baseline  1.610276e+09   
#1       Night (20–7)  Intersection-swapping vs Baseline  1.697793e+09   
#2       Night (20–7)          Cloaking area vs Baseline  1.511136e+09   

#3   Flat Peak (9–16)          Edge-swapping vs Baseline  2.021587e+08   
#4   Flat Peak (9–16)  Intersection-swapping vs Baseline  1.260755e+08   
#5   Flat Peak (9–16)          Cloaking area vs Baseline  2.015010e+08   

#6    Evening (16–20)          Edge-swapping vs Baseline  1.223631e+08   
#7    Evening (16–20)  Intersection-swapping vs Baseline  1.073695e+08   
#8    Evening (16–20)          Cloaking area vs Baseline  1.149376e+08   

#9      Morning (7–9)          Edge-swapping vs Baseline  4.366212e+07   
#10     Morning (7–9)  Intersection-swapping vs Baseline  3.256539e+07   
#11     Morning (7–9)          Cloaking area vs Baseline  4.741876e+07   


#         p-value stars  
#0   3.516962e-04   ***  
#1   6.604156e-96   ***  
#2   8.875451e-22   ***  

#3   2.646853e-05   ***  
#4   5.344012e-75   ***  
#5   8.035187e-07   ***  

#6   9.512079e-16   ***  
#7   5.153285e-94   ***  
#8   8.678455e-49   ***  

#9   7.553428e-84   ***  
#10  9.425320e-29   ***  
#11  1.199081e-89   ***  