#%% load libaries
import geopandas as gpd
import pandas as pd

#%% load stop points
# baseline: not swapped, cloaked and filled
stpts_cf = gpd.read_parquet(r"D:\paper3\Data\output\Evaluation_HomeDetection/cloakedFilledReleaseP3_final_StopPoints.parquet")
#stpts_cf.head()

#%% export as geopackage - for Arc
stpts_cf.to_file(r"D:\paper3\Data\output\Evaluation_HomeDetection\cloakedFilledReleaseP3_final_StopPoints.gpkg", layer="cf_stp", driver="GPKG")

#%%
#stpts_i = gpd.read_parquet(r"d:\paper3\Data\output\Evaluation_HomeDetection\nodesSwapped_split_StopPoints.parquet")
#stpts_e = gpd.read_parquet(r"D:\paper3\Data\output\Evaluation_HomeDetection/edgeSwapped_split_StopPoints.parquet")
#stpts_c = gpd.read_parquet(r"d:\paper3\Data\output\Evaluation_HomeDetection\cloakedSwapped_StopPoints.parquet") 


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

#%% to geopackage
stpts_i = gpd.read_parquet(r"d:\paper3\Data\output\Evaluation_HomeDetection\nodesSwapped_split_StopPoints_nodupl.parquet")
stpts_i = stpts_i.set_crs(2193)
stpts_i.to_file(r"D:\paper3\Data\output\Evaluation_HomeDetection\stpts_i.gpkg", layer="stpts_i", driver="GPKG")

#%%
stpts_e = gpd.read_parquet(r"D:\paper3\Data\output\Evaluation_HomeDetection/edgeSwapped_split_StopPoints_nodupl.parquet")
stpts_e = stpts_e.set_crs(2193)
stpts_e.to_file(r"D:\paper3\Data\output\Evaluation_HomeDetection\stpts_e.gpkg", layer="stpts_e", driver="GPKG")


stpts_c = gpd.read_parquet(r"d:\paper3\Data\output\Evaluation_HomeDetection\cloakedSwapped_StopPoints_nodupl.parquet") 
stpts_c = stpts_c.set_crs(2193)
stpts_c.to_file(r"D:\paper3\Data\output\Evaluation_HomeDetection\stpts_c.gpkg", layer="stpts_c", driver="GPKG")


#%% road network to look at intersections
edges = gpd.read_parquet(r"d:\Paper2\data\Output\cloaking_2sig_100150\traj_cloaked_anotated_mapmatched\OriginDestination_CloakingAreas\NetworkShortestPath\edges.parquet")
nodes = gpd.read_parquet(r"d:\Paper2\data\Output\cloaking_2sig_100150\traj_cloaked_anotated_mapmatched\OriginDestination_CloakingAreas\NetworkShortestPath\nodes.parquet")

edges.to_file(r"D:\paper3\Data\output\Evaluation_HomeDetection\edges.gpkg", layer="edges", driver="GPKG")
nodes.to_file(r"D:\paper3\Data\output\Evaluation_HomeDetection\nodes.gpkg", layer="nodes", driver="GPKG")


#%%get intersections
from joblib import load
G = load(r"D:\paper2\Data\Output\cloaking_2sig_100150\traj_cloaked_anotated_mapmatched\OriginDestination_CloakingAreas\NetworkShortestPath\graph.joblib")


import networkx as nx
import pandas as pd

# Get degree of all nodes
degrees = dict(G.degree()) # total degree of each node (in and out)
# directed count
#in_deg = dict(G.in_degree())
#out_deg = dict(G.out_degree())


# Convert to DataFrame
df_degree = pd.DataFrame.from_dict(degrees, orient='index', columns=['street_count'])
df_degree.reset_index(inplace=True)
df_degree.rename(columns={'index': 'node_id'}, inplace=True)
df_degree

#%% label intersections
import numpy as np
df_degree['intersection'] = np.where(df_degree['street_count'] > 2, True, False)
df_degree.head()

#%% add this back to nodes
print(len(nodes))
nodes_intersection = nodes.merge(df_degree, left_on = 'id', right_on ='node_id', how='right')
print(len(nodes_intersection))
nodes_intersection.head()

#%% only keep intersection = True
len(nodes_intersection[nodes_intersection['intersection']==True])
#%%
nodes_intersection[nodes_intersection['intersection']==True].to_file(r"D:\paper3\Data\output\Evaluation_HomeDetection\nodes_intersections.gpkg", layer="nodes_intersections", driver="GPKG")



##########################################################################################
#%% differences in stop duration 
import geopandas as gpd

stpts_cf = gpd.read_parquet(r"D:\paper3\Data\output\Evaluation_HomeDetection/cloakedFilledReleaseP3_final_StopPoints.parquet")
stpts_i = gpd.read_parquet(r"d:\paper3\Data\output\Evaluation_HomeDetection\nodesSwapped_split_StopPoints_nodupl.parquet")
stpts_e = gpd.read_parquet(r"D:\paper3\Data\output\Evaluation_HomeDetection/edgeSwapped_split_StopPoints_nodupl.parquet")
stpts_c = gpd.read_parquet(r"d:\paper3\Data\output\Evaluation_HomeDetection\cloakedSwapped_StopPoints_nodupl.parquet") 


#%%
for df in [stpts_cf, stpts_i, stpts_e, stpts_c]:
    df["duration_min"] = df["duration_s"] / 60

baseline = stpts_cf["duration_min"]

dfs = {
    "baseline": stpts_cf,
    "stpts_i": stpts_i,
    "stpts_e": stpts_e,
    "stpts_c": stpts_c
}

summary = {}

for name, df in dfs.items():
    s = df["duration_min"]
    summary[name] = {
        "mean": s.mean(),
        "median": s.median(),
        "std": s.std(),
        "min": s.min(),
        "max": s.max()
    }

import pandas as pd
summary_df = pd.DataFrame(summary).T
print(summary_df)

#               mean     median         std  min          max
#baseline  49.133042  12.083333  103.679263  3.0  1421.066667
#stpts_i   33.195946  10.250000   91.465285  3.0  1847.233333
#stpts_e   76.902802  12.283333  168.071408  3.0  1838.216667
#stpts_c   70.207244  11.650000  159.248012  3.0  1840.500000

#%% relative change to baseline
#baseline_mean = stpts_cf["duration_min"].mean()
baseline_median = stpts_cf["duration_min"].median()

for name, df in dfs.items():
    if name == "baseline":
        continue
    median_val = df["duration_min"].median()
    change_pct = (median_val - baseline_median) / baseline_median * 100
    print(f"{name}: {change_pct:.2f}% change vs baseline")

# median
#stpts_i: -15.17% change vs baseline
#stpts_e: 1.66% change vs baseline
#stpts_c: -3.59% change vs baseline

# mean
#stpts_i: -32.44% change vs baseline
#stpts_e: 56.52% change vs baseline
#stpts_c: 42.89% change vs baseline

# increase/drease in mean

#%% look at IQR and 90th percentile
import pandas as pd
import numpy as np

dfs = {
    "baseline": stpts_cf,
    "stpts_i": stpts_i,
    "stpts_e": stpts_e,
    "stpts_c": stpts_c
}

results = {}

for name, df in dfs.items():
    data = df["duration_min"]

    q1 = np.percentile(data, 25)
    q3 = np.percentile(data, 75)
    iqr = q3 - q1
    p90 = np.percentile(data, 90)

    results[name] = {
        "Q1 (25%)": round(q1,2 ),
        "Median": round(np.median(data), 2),
        "Q3 (75%)": round(q3, 2),
        "IQR": round(iqr,2),
        "P90": round(p90,2)
    }

results_df = pd.DataFrame(results).T
print(results_df)

#          Q1 (25%)  Median  Q3 (75%)    IQR     P90
#baseline      5.58   12.08     38.23  32.65  124.15
#stpts_i       5.25   10.25     26.62  21.37   67.68
#stpts_e       5.65   12.28     42.78  37.13  276.69
#stpts_c       5.47   11.65     39.22  33.75  199.47


#%%

import numpy as np
import pandas as pd

dfs = {
    "baseline": stpts_cf,
    "stpts_i": stpts_i,
    "stpts_e": stpts_e,
    "stpts_c": stpts_c
}

results = {}

for name, df in dfs.items():
    data = df["duration_min"]

    p95 = np.percentile(data, 95)
    p90 = np.percentile(data, 90)
    max_val = np.max(data)

    prop_30 = np.mean(data > 30) * 100
    prop_60 = np.mean(data > 60) * 100

    results[name] = {
        "P90 (min)": round(p90, 2),
        "P95 (min)": round(p95, 2),
        "Max (min)": round(max_val, 2),
        ">%30 min (%)": round(prop_30, 2),
        ">%60 min (%)": round(prop_60, 2)
    }

results_df = pd.DataFrame(results).T
print(results_df)

#          P90 (min)  P95 (min)  Max (min)  >%30 min (%)  >%60 min (%)
#baseline     124.15     242.23    1421.07         29.31         18.00
#stpts_i       67.68     117.23    1847.23         22.79         11.57
#stpts_e      276.69     464.40    1838.22         30.78         20.78
#stpts_c      199.47     441.90    1840.50         29.30         19.35


#%% tail ration (95th precentile /median)
import numpy as np
import pandas as pd

dfs = {
    "baseline": stpts_cf,
    "stpts_i": stpts_i,
    "stpts_e": stpts_e,
    "stpts_c": stpts_c
}

results = {}

for name, df in dfs.items():
    data = df["duration_min"]

    median = np.median(data)
    p95 = np.percentile(data, 95)

    tail_ratio = p95 / median

    results[name] = {
        "Median (min)": round(median, 2),
        "P95 (min)": round(p95, 2),
        "Tail ratio (P95/median)": round(tail_ratio, 2)
    }

tail_ratio_df = pd.DataFrame(results).T
print(tail_ratio_df)

#          Median (min)  P95 (min)  Tail ratio (P95/median)
#baseline         12.08     242.23                    20.05
#stpts_i          10.25     117.23                    11.44
#stpts_e          12.28     464.40                    37.81
#stpts_c          11.65     441.90                    37.93

#%% outliers
results = {}

for name, df in dfs.items():
    data = df["duration_min"]

    p90 = np.percentile(data, 90)
    max_val = np.max(data)

    inflation = max_val / p90 if p90 != 0 else np.nan

    results[name] = {
        "P90 (min)": round(p90, 2),
        "Max (min)": round(max_val, 2),
        "Max/P90 inflation": round(inflation, 2)
    }

inflation_df = pd.DataFrame(results).T
print(inflation_df)

#          P90 (min)  Max (min)  Max/P90 inflation
#baseline     124.15    1421.07              11.45
#stpts_i       67.68    1847.23              27.29
#stpts_e      276.69    1838.22               6.64
#stpts_c      199.47    1840.50               9.23

#%% tail historgam
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MultipleLocator, FuncFormatter

# -------------------------
# Data
# -------------------------
dfs = {
    "Baseline": stpts_cf,
    "Edge-swapping": stpts_e,
    "Intersection-swapping": stpts_i,
    "Cloaking": stpts_c
}

names = list(dfs.keys())
data_list = [df["duration_min"] for df in dfs.values()]

colors = ["#383a6b", "#FDD45F", "#F3B503", "#C09003"]

# -------------------------
# P90 values
# -------------------------
p90_list = [np.percentile(data, 95) for data in data_list]
baseline_p90 = p90_list[0]
p90_C = p90_list[2]

# -------------------------
# TAIL RANGE (minutes)
# -------------------------
xmin = 115
xmax = max([data.max() for data in data_list])

# FIX: upper limit = 24 hours
xmax_plot = 24 * 60

# -------------------------
# Figure
# -------------------------
fig, axes = plt.subplots(1, 4, figsize=(16, 5), sharey=True)

titles = [
    "(A) Baseline\nt$_{f}$",
    "(B) Edge-swapping\nt$_{se} split$",
    "(C) Intersection-swapping\nt$_{si} split$",
    "(D) Cloaking Area-swapping\nt$_{sc}$"
]

# -------------------------
# Plot
# -------------------------
for i, (ax, data, name, color, p90) in enumerate(
    zip(axes, data_list, names, colors, p90_list)
):

    # -------------------------
    # FILTER TO TAIL ONLY
    # -------------------------
    tail_data = data[data >= xmin]

    # -------------------------
    # bins (clipped to 24h)
    # -------------------------
    bins = np.arange(0, xmax_plot + 30, 30)  # 30 minute bins

    ax.hist(
        tail_data,
        bins=bins,
        color=color,
        edgecolor="white",
        alpha=0.9,
        linewidth=0.6
    )

    # -------------------------
    # P90 lines
    # -------------------------
    ax.axvline(
        baseline_p90,
        color="red",
        linestyle="-",
        linewidth=2,
        label="Baseline\n95$^{\\mathrm{th}}$ percentile" if i == 3 else None
    )

    ax.axvline(
        p90,
        color="red",
        linestyle="--",
        linewidth=2,
        label="95$^{\\mathrm{th}}$ percentile\nafter swapping" if i == 3 else None
    )

    # label p95
    # convert to hours + minutes
    p95_hours = int(p90 // 60)
    p95_mins = int(p90 % 60)

    label_text = f"{p95_hours}h {p95_mins}m"

    ax.text(
        p90 + 35,  # small offset to the right of the line
        ax.get_ylim()[1] * 0.9,  # near top of plot
        label_text,
        rotation=90,
        color="red",
        fontsize=14,
        va="top"
    )

    

    # -------------------------
    # X LIMITS (FIXED TO 24 HOURS)
    # -------------------------
    ax.set_xlim(xmin, xmax_plot)

    # -------------------------
    # CLEAN HOUR AXIS
    # -------------------------
    ax.xaxis.set_major_locator(MultipleLocator(120))  # every 2 hours
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"{x/60:.0f}"))
    ax.tick_params(axis='both', labelsize=14, colors="#333333")



    # -------------------------
    # Y formatting
    # -------------------------
    ax.set_ylim(0, None)

    if i == 0:
        ax.set_ylabel("Frequency", fontsize=16, color="#555555")
    else:
        ax.tick_params(axis="y", left=False, labelleft=False)
        ax.spines["left"].set_visible(False)

    # -------------------------
    # GRID
    # -------------------------
    ax.set_axisbelow(True)
    ax.grid(True, axis="y", linestyle=":", alpha=0.5)

    # -------------------------
    # Titles
    # -------------------------
    ax.set_title(titles[i], fontsize=18, color="#333333")

for ax in axes:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)



# -------------------------
# Shared x-label (hours)
# -------------------------
fig.supxlabel("Stop duration in hours", fontsize=16, color="#555555")

# -------------------------
# Legend only in last plot
# -------------------------
axes[-1].legend(frameon=False)

plt.savefig(
    r"\\tsclient\R\paper3\Figures\hist_duration_tails.svg",
    format="svg",
    bbox_inches="tight",
    dpi=300
)


plt.tight_layout()
plt.show()








#%% histogram: four separate plots (duration)
import matplotlib.pyplot as plt
import numpy as np

# Data
data_list = [
    stpts_cf["duration_min"],
    stpts_e["duration_min"],
    stpts_i["duration_min"],
    stpts_c["duration_min"]
]

colors = ["#383a6b", "#FDD45F", "#F3B503", "#C09003"]

# Create 4 side-by-side plots
fig, axes = plt.subplots(1, 4, figsize=(16,5), sharey=True)

# Define bins 
bins = np.arange(0, 121, 5)  # e.g. 0–120 minutes in 5-min bins
bins = np.arange(0, 31, 1)  # more precise bins

# Precompute counts for consistent y-axis
counts_list = []
for data in data_list:
    counts, _ = np.histogram(data, bins=bins)
    counts_list.append(counts)

global_max = max([c.max() for c in counts_list])

for i, (ax, data, color, counts) in enumerate(zip(axes, data_list, colors, counts_list)):

    bin_edges = bins
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    bin_width = bin_edges[1] - bin_edges[0]

    ax.bar(
        bin_centers,
        counts,
        width=bin_width * 0.9,
        color=color,
        edgecolor="white",
        alpha=0.9,
        linewidth=0.6
    )

    # same y-scale
    ax.set_ylim(0, global_max * 1.15)

    # Median line
    median_val = np.median(data)

    # Convert to minutes + seconds
    minutes = int(median_val)
    seconds = int((median_val - minutes) * 60)

    label = f"{minutes}m {seconds}s"

    ax.axvline(median_val, color=color, linestyle="--", linewidth=1.5)

    ax.text(
        #median_val + 6,
        median_val + 2,
        global_max * 0.9,
        label,
        color=color,
        fontsize=11,
        ha='center',
        rotation=90
    )

    # Remove y-axis for all but first
    if i > 0:
        ax.spines['left'].set_visible(False)
        ax.tick_params(axis='y', left=False, labelleft=False)

    # Style
    ax.set_facecolor("white")
    ax.grid(False)
    ax.yaxis.grid(True, linestyle=":", color="#d3d3d3", alpha=0.7, zorder=0)

    ax.spines['bottom'].set_visible(True)
    ax.spines['bottom'].set_color('black')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    #ax.set_xlim(0, 120)
    ax.set_xlim(2, 30)


# Axis labels
axes[0].set_ylabel("Number of stay points", fontsize=14, color="#555555")
fig.supxlabel("Stop duration in minutes", fontsize=14, color="#555555")

# Titles
titles = [
    "(A) Baseline (t$_{cf}$)",
    "(B) Edge-swapping (t$_{se} split$)",
    "(C) Intersection-swapping (t$_{si} split$)",
    "(D) Cloaking (t$_{sc}$)"
]

for ax, title in zip(axes, titles):
    ax.set_title(title, fontsize=16, color="#333333")

#plt.tight_layout(rect=[0,0.08,1,1])
#plt.tight_layout(rect=[0,0.1,1,1])
plt.tight_layout(rect=[0,0.005,1,1])

plt.savefig(
    r"\\tsclient\R\paper3\Figures\hist_duration_fourPanels.svg",
    format="svg",
    bbox_inches="tight",
    dpi=300
)

plt.show()

#%% Kolmogorov-Smirnov test
from scipy.stats import ks_2samp

for name, df in dfs.items():
    if name == "baseline":
        continue
    stat, p = ks_2samp(stpts_cf["duration_s"], df["duration_s"])
    print(f"{name}: KS p-value = {p}")

#stpts_i: KS p-value = 4.37905737183253e-214
#stpts_e: KS p-value = 8.397494470389594e-179
#stpts_c: KS p-value = 8.98417630204851e-112
# all extremely small --> distributions are significanlty differnetly from the baseline


###########################################################################################
#%% CLIP DATA TO CENTRAL AUCKLAND FOR VIS


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















##############################################################################
##############################################################################
#%% spatially exploring stop points
##############################################################################
##############################################################################
import geopandas as gpd

import rioxarray as rxr

raster = rxr.open_rasterio(r"d:\paper3\StopsKDE_Arc\KDE_weighted\KernelD_cf_central_weighted.tif", masked=True)

print(raster)


#%%
print(raster.rio.crs)
raster_3857 = raster.rio.reproject("EPSG:3857")
print(raster_3857.rio.crs)

#%%
#import contextily as ctx

fig, ax = plt.subplots(figsize=(10, 10))

raster_3857.plot(ax=ax, 
    cmap="inferno",
    alpha=0.8,
    robust=True) # to exlcude outliers from the colour ramp - 98th percentile only

ctx.add_basemap(
    ax, 
    crs="EPSG:3857",
    source=ctx.providers.CartoDB.PositronNoLabels,
    attribution=False  
)
ax.set_aspect("equal")  

ax.set_xticks([])
ax.set_yticks([])
ax.set_xlabel("")
ax.set_ylabel("")
for spine in ax.spines.values():
    spine.set_visible(True)
    spine.set_linewidth(1.2)
    spine.set_color("black")
ax.set_title("")

plt.show()






#%% data for panel figure
wKDE_baseline = rxr.open_rasterio(r"d:\paper3\StopsKDE_Arc\KDE_weighted\KernelD_cf_central_weighted.tif", masked=True)
wKDE_baseline = wKDE_baseline.rio.reproject(3857)
print(wKDE_baseline.rio.crs)

wKDE_e = rxr.open_rasterio(r"d:\paper3\StopsKDE_Arc\KDE_weighted\KernelD_e_central_weighted.tif", masked=True)
wKDE_e = wKDE_e.rio.reproject(3857)
print(wKDE_e.rio.crs)

wKDE_i = rxr.open_rasterio(r"d:\paper3\StopsKDE_Arc\KDE_weighted\KernelD_i_central_weighted.tif", masked=True)
wKDE_i = wKDE_i.rio.reproject(3857)
print(wKDE_i.rio.crs)

wKDE_c = rxr.open_rasterio(r"d:\paper3\StopsKDE_Arc\KDE_weighted\KernelD_cloaked_central_weighted.tif", masked=True)
wKDE_c = wKDE_c.rio.reproject(3857)
print(wKDE_c.rio.crs)







#%% panel figure
# %%
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.ticker as ticker
import contextily as ctx
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

rasters = [wKDE_baseline, wKDE_e, wKDE_i, wKDE_c]

# -----------------------
# shared scaling
# -----------------------
all_values = np.concatenate([r.values.flatten() for r in rasters])
vmin = np.nanpercentile(all_values, 2)
vmax = np.nanpercentile(all_values, 98)

labels = [
    '(A) Baseline\n(t$_{f}$)', 
    '(B) Edge-swapping\n(t$_{se}$ split)', 
    '(C) Intersection-swapping\n(t$_{si}$ split)', 
    '(D) Cloaking area-swapping\n(t$_{sc}$)'
]

# -----------------------
# figure (NO GridSpec)
# -----------------------
fig, axes = plt.subplots(1, 4, figsize=(20, 5), constrained_layout=True)

# -----------------------
# plotting
# -----------------------
for ax, r, lab in zip(axes, rasters, labels):

    r.plot(
        ax=ax,
        cmap="inferno",
        vmin=vmin,
        vmax=vmax,
        alpha=0.8,
        add_colorbar=False
    )

    ctx.add_basemap(
        ax,
        crs="EPSG:3857",
        source=ctx.providers.CartoDB.PositronNoLabels,
        attribution=False,
        reset_extent=False
    )

    # FIXED aspect (prevents D shrinking differently)
    ax.set_aspect("equal", adjustable="box")

    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_title(lab, fontsize=22, color="#333333")

    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(1.2)
        spine.set_color("black")

axes[0].set_ylabel("(1) Full day", fontsize=16, rotation=90, labelpad=15, color ="#333333")

# -----------------------
# COLORBAR (correct height binding)
# -----------------------
cax = inset_axes(
    axes[-1],
    width="5%",
    height="100%",
    loc="lower left",
    bbox_to_anchor=(1.05, 0., 1, 1),
    bbox_transform=axes[-1].transAxes,
    borderpad=0
)

norm = mpl.colors.Normalize(vmin=vmin, vmax=vmax)
sm = mpl.cm.ScalarMappable(cmap="inferno", norm=norm)
sm.set_array([])

cbar = fig.colorbar(sm, cax=cax)

cbar.ax.yaxis.set_major_formatter(
    ticker.FuncFormatter(lambda x, pos: f"{x:,.0f}")
)
cbar.ax.tick_params(labelsize=14, color="#333333")

cbar.set_label("Density of stay points per km²", fontsize=16, color="#333333")

plt.show()










##############################################################################
#%% counts by rgid
print(len(stpts_cf))
print(len(stpts_e))
print(len(stpts_i))
print(len(stpts_c))

#117124
#114895
#104173
#115002

#%%
stpts_c = stpts_c.set_crs(2193)
stpts_e = stpts_e.set_crs(2193)
stpts_i = stpts_i.set_crs(2193)

#%%
print(stpts_cf.crs)
print(stpts_e.crs)
print(stpts_i.crs)
print(stpts_c.crs)


#%%
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import box
from matplotlib.colors import BoundaryNorm
import contextily as ctx  # optional, only if you want a basemap

# --- Load your dataset ---
gdf = stpts_cf.copy()  # replace with your GeoDataFrame
if gdf.crs is None:
    gdf = gdf.set_crs(epsg=4326)  # assume WGS84 if CRS unknown
gdf = gdf.to_crs(epsg=3857)  # projected CRS in meters

# --- Create 500 m grid ---
cell_size = 500
xmin, ymin, xmax, ymax = gdf.total_bounds

# Snap bounds to grid
xmin = np.floor(xmin / cell_size) * cell_size
ymin = np.floor(ymin / cell_size) * cell_size
xmax = np.ceil(xmax / cell_size) * cell_size
ymax = np.ceil(ymax / cell_size) * cell_size

grid_cells = [
    box(x, y, x + cell_size, y + cell_size)
    for x in np.arange(xmin, xmax, cell_size)
    for y in np.arange(ymin, ymax, cell_size)
]

grid = gpd.GeoDataFrame(geometry=grid_cells, crs="EPSG:3857")

# --- Count points per cell ---
joined = gpd.sjoin(grid, gdf, how='left', predicate='contains')
counts = joined.groupby(joined.index).size()
grid["count"] = counts
grid["count"] = grid["count"].fillna(0)

# --- Mask cells below threshold (e.g., counts < 3) ---
threshold = 3
grid["count_masked"] = grid["count"].where(grid["count"] >= threshold)

# --- Define bins starting at threshold ---
max_val = grid["count_masked"].max()
bins = [threshold, 5, 10, 20, 50, 100, max_val]
norm = BoundaryNorm(bins, ncolors=256, clip=False)

# --- Colormap: NaNs are transparent ---
cmap = plt.cm.Reds.copy()
cmap.set_bad(color='none')  # cells below threshold invisible

# --- Plot ---
fig, ax = plt.subplots(figsize=(10, 10))

grid.plot(
    column="count_masked",
    cmap=cmap,
    norm=norm,
    linewidth=0,
    legend=True,
    ax=ax
)

# --- Optional basemap ---
# ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron)

ax.set_title(f"Point Density (500 m grid, counts ≥ {threshold})")
ax.axis('off')
plt.tight_layout()
plt.show()

#%% jenks
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import box
from matplotlib.colors import BoundaryNorm
import mapclassify as mc
import contextily as ctx

# --- Load dataset ---
gdf = stpts_cf.copy()  # replace with your GeoDataFrame
if gdf.crs is None:
    gdf = gdf.set_crs(epsg=4326)
gdf = gdf.to_crs(epsg=3857)  # projected CRS in meters

# --- Create 500 m grid ---
cell_size = 500
xmin, ymin, xmax, ymax = gdf.total_bounds
xmin = np.floor(xmin / cell_size) * cell_size
ymin = np.floor(ymin / cell_size) * cell_size
xmax = np.ceil(xmax / cell_size) * cell_size
ymax = np.ceil(ymax / cell_size) * cell_size

grid_cells = [
    box(x, y, x + cell_size, y + cell_size)
    for x in np.arange(xmin, xmax, cell_size)
    for y in np.arange(ymin, ymax, cell_size)
]
grid = gpd.GeoDataFrame(geometry=grid_cells, crs="EPSG:3857")

# --- Count points per cell ---
joined = gpd.sjoin(grid, gdf, how='left', predicate='contains')
counts = joined.groupby(joined.index).size()
grid["count"] = counts.fillna(0)

# --- Mask counts below threshold ---
threshold = 3
grid["count_masked"] = grid["count"].where(grid["count"] >= threshold)

# --- Prepare data for classification ---
data = grid["count_masked"].dropna().values  # all counts ≥ threshold

# --- 1️⃣ Jenks Natural Breaks ---
jenks = mc.NaturalBreaks(y=data, k=6)
grid["jenks_class"] = np.nan
grid.loc[~grid["count_masked"].isna(), "jenks_class"] = jenks.yb

# --- 2️⃣ Quantiles ---
quantiles = mc.Quantiles(y=data, k=6)
grid["quantile_class"] = np.nan
grid.loc[~grid["count_masked"].isna(), "quantile_class"] = quantiles.yb

# --- Plotting function with real count bins ---
def plot_grid(grid, column, classifier, title):
    # Use classifier bins for legend
    bins = classifier.bins
    boundaries = np.insert(bins, 0, threshold)  # add threshold as lower bound

    cmap = plt.cm.Reds.copy()
    cmap.set_bad(color='none')  # masked cells invisible
    norm = BoundaryNorm(boundaries=boundaries, ncolors=cmap.N)

    fig, ax = plt.subplots(figsize=(12, 12))
    grid.plot(
        column="count_masked",
        cmap=cmap,
        norm=norm,
        linewidth=0,
        legend=True,
        ax=ax
    )

    # Add basemap
    ctx.add_basemap(
        ax,
        source=ctx.providers.CartoDB.Positron,
        crs=grid.crs.to_string()
    )

    ax.set_title(title, fontsize=14)
    ax.axis('off')
    plt.tight_layout()
    plt.show()

# --- Plot Jenks ---
plot_grid(grid, "count_masked", jenks, f"Point Density (Jenks, counts ≥ {threshold})")

# --- Plot Quantiles ---
plot_grid(grid, "count_masked", quantiles, f"Point Density (Quantiles, counts ≥ {threshold})")



#%% panel figure






# %%
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import contextily as ctx
import matplotlib as mpl
import numpy as np

# --- Assuming your grid and gdfs are already defined ---

# Baseline and other columns
baseline_col = 'Baseline_count_masked'
other_cols = ['Edge-swapping_count_masked', 'Intersection-swapping_count_masked', 'Cloaking area_count_masked']

# --- Compute percentage change relative to baseline ---
for col in other_cols:
    pct_col = col.replace('_count_masked', '_pct_change')
    grid[pct_col] = ((grid[col] - grid[baseline_col]) / grid[baseline_col]) * 100
    grid[pct_col] = grid[pct_col].clip(-100, 100)  # cap at ±100%

pct_cols = [c.replace('_count_masked', '_pct_change') for c in other_cols]

# --- Color maps ---
baseline_cmap = plt.cm.Reds
div_cmap = plt.cm.RdBu_r  # diverging for percent change

# --- Plot setup ---
fig, axes = plt.subplots(1, 4, figsize=(18, 6))


titles = [
    '(A) Baseline\n(t$_{f}$)',
    '(B) Edge-swapping\n% change',
    '(C) Intersection-swapping\n% change',
    '(D) Cloaking area-swapping\n% change'
]

# --- Plot Baseline on first axis ---
grid.plot(column=baseline_col, cmap=baseline_cmap, linewidth=0, ax=axes[0])
ctx.add_basemap(axes[0], source=ctx.providers.CartoDB.Positron, crs=grid.crs.to_string(), attribution=False)
axes[0].set_title(titles[0], fontsize=12, fontweight='bold')
axes[0].axis('off')

# --- Colorbar for baseline on the left of A ---
sm_base = mpl.cm.ScalarMappable(cmap=baseline_cmap,
                                norm=Normalize(vmin=grid[baseline_col].min(),
                                               vmax=grid[baseline_col].max()))
sm_base.set_array([])

# attach colorbar to axes[0] and place it on the left
cbar_left = fig.colorbar(sm_base, ax=axes[0], fraction=0.046, pad=0.02, location='left')
cbar_left.set_label("Stay Point Count", fontsize=12)

# --- Plot percentage change maps (B–D) ---
for ax, col, title in zip(axes[1:], pct_cols, titles[1:]):
    plot_data = grid[col].fillna(0)
    
    grid.plot(column=col, cmap=div_cmap, linewidth=0, ax=ax, vmin=-100, vmax=100)
    ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron, crs=grid.crs.to_string(), attribution=False)
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.axis('off')

# --- Diverging colorbar on the right of the last map (D) ---
sm_div = mpl.cm.ScalarMappable(cmap=div_cmap, norm=Normalize(vmin=-100, vmax=100))
sm_div.set_array([])
cbar_right = fig.colorbar(sm_div, ax=axes[-1], fraction=0.046, pad=0.02)
cbar_right.set_label("% Change vs Baseline", fontsize=12)



plt.tight_layout()
plt.show()