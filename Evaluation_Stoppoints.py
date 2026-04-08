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
ax.set_ylabel('Stop Duration in minutes', fontsize=16, color='#555555')
ax.set_xlabel("Trajectory swapping approach", fontsize=16, color='#555555')

handles = [plt.Line2D([0], [0], color=c, lw=8) for c in colors]
custom_labels = [r'Baseline (t$_{f}$)', r'Edge-swapping (t$_{se} split$)', 
                 r'Intersection-swapping (t$_{si} split$)', r'Cloaking area-swapping (t$_{sc}$)']
ax.legend(handles, custom_labels, loc='upper center', bbox_to_anchor=(0.5, -0.15),
          ncol=2, frameon=False, fontsize=14)

plt.tight_layout()
plt.savefig(r"\\tsclient\R\paper3\Figures/StopDuration_boxplot.svg", format="svg", bbox_inches="tight", dpi=300)

plt.show()