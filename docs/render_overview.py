"""Render the portfolio overview from saved audit evidence (no model rerun)."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = Path(__file__).resolve().parents[1]
audit = json.loads((ROOT / 'results/audit.json').read_text())
fresh = json.loads((ROOT / 'results/fresh_download.json').read_text())
BG, PANEL, INK, MUTED = '#18221f', '#233029', '#eee8dc', '#b5bdae'
COPPER, BLUE = '#d69170', '#96bac8'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'svg.fonttype': 'none'})
fig = plt.figure(figsize=(15, 9), dpi=160, facecolor=BG)
base = fig.add_axes([0, 0, 1, 1]); base.set_axis_off()
fig.text(.055, .925, 'From race archive to an inspectable result', color=INK, fontsize=25, weight='bold')
fig.text(.055, .879, 'TRACK ALTITUDE  /  DATA PIPELINE & EVALUATION AUDIT', color=MUTED, fontsize=11)

outdoor = fresh['derived_datasets']['dataset_all.csv']['rebuilt_outdoor_rows']
enriched = fresh['derived_datasets']['dataset_v3.csv']['rebuilt_outdoor_rows']
held = sum(f['n_test'] for f in audit['temporal_base']['folds'])
stages = [
    ('01  INGEST', f'{outdoor:,}', 'outdoor race records', '16 source CSVs'),
    ('02  ENRICH', f'{enriched:,}', 'enriched outdoor records', 'Venues + athlete proxies'),
    ('03  BUILD FEATURES', f"{audit['sample']['n']:,}", 'eligible performances', 'Past-only race history'),
    ('04  EVALUATE', f'{held:,}', 'held-out race predictions', 'Five future-date blocks'),
]
for i, (label, value, caption, detail) in enumerate(stages):
    x = .055 + i * .235
    base.add_patch(FancyBboxPatch((x, .636), .21, .185, boxstyle='round,pad=0.008,rounding_size=0.01',
                                 facecolor=PANEL, edgecolor='#46554a', linewidth=.9))
    fig.text(x+.014, .786, label, color=COPPER if i<3 else BLUE, fontsize=10, weight='bold')
    fig.text(x+.014, .730, value, color=INK, fontsize=25)
    fig.text(x+.014, .696, caption, color=INK, fontsize=10)
    fig.text(x+.014, .661, detail, color=MUTED, fontsize=9)
    if i<3:
        base.add_patch(FancyArrowPatch((x+.214,.729),(x+.228,.729),arrowstyle='-|>',mutation_scale=12,color=MUTED))
fig.text(.055, .593, 'Shared dates stay together. Preprocessing fits on training rows only.', color=MUTED, fontsize=11)

fig.text(.055, .524, 'Does altitude improve future-race prediction?', color=INK, fontsize=17, weight='bold')
fig.text(.055, .488, 'Reduction in log-time squared error vs. personal-best + race-context baseline', color=MUTED, fontsize=10)
ax=fig.add_axes([.15, .188, .44, .265], facecolor=BG)
folds=audit['temporal_base']['folds']
values=[100*f['relative_sse_improvement'] for f in folds]
labels=[f"{f['test_start'][:4]}–{f['test_end'][:4]}" for f in folds]
ax.barh(range(5), values, height=.53, color=[COPPER if v<0 else BLUE for v in values])
ax.set_yticks(range(5)); ax.set_yticklabels(labels, color=INK, fontsize=10)
ax.invert_yaxis(); ax.set_xlim(-1.4,1.65); ax.set_xticks([-1,0,1]); ax.set_xticklabels(['−1%','0','+1%'],color=MUTED,fontsize=10)
ax.axvline(0, color='#738376', linewidth=1)
ax.tick_params(axis='both',length=0,pad=9)
for spine in ax.spines.values(): spine.set_visible(False)
for i,v in enumerate(values):
    ax.text(v + (.045 if v >= 0 else -.045), i, f'{v:+.2f}%',
            va='center', ha='left' if v >= 0 else 'right', color=INK, fontsize=10)
fig.text(.15,.14,'← Worse prediction',color=COPPER,fontsize=10)
fig.text(.46,.14,'Better prediction →',color=BLUE,fontsize=10)

pooled=100*audit['temporal_base']['pooled_prediction']['relative_sse_improvement']
fig.text(.68,.401,f'{pooled:.2f}%',color=BLUE,fontsize=45)
fig.text(.682,.350,'lower pooled held-out squared error',color=INK,fontsize=12)
fig.text(.682,.303,'Four of five folds improve.',color=MUTED,fontsize=11)
fig.text(.682,.271,'The earliest fold worsens.',color=MUTED,fontsize=11)
matched=sum(v['matches_recorded_snapshot'] for v in fresh['archive_members'].values())
fig.text(.682,.214,f'{matched}/{len(fresh["archive_members"])} source files matched on rebuild.',color=INK,fontsize=11)
fig.text(.682,.182,'Saved audit results reproduced exactly.*',color=MUTED,fontsize=10)
fig.text(.055,.078,'Prediction-error reduction, not a change in race time or a causal effect. Exploratory; no confidence interval.',color=INK,fontsize=10)
fig.text(.055,.043,'*Reuses the existing venue table, retrospective mass cache and software environment. Source: saved audit and rebuild reports.',color=MUTED,fontsize=9)
for ext in ('png','svg'):
    fig.savefig(str(ROOT/'docs'/('overview.'+ext)), facecolor=BG)
print('Wrote docs/overview.png and docs/overview.svg')
