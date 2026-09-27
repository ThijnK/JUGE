"""Rebuild CSV/statistics from verified records; never modify raw runs."""
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
import csv
import math
import statistics

import numpy as np
from scipy import stats

from common import BASE, SUBJECTS, TREATMENTS, atomic, read, selection, scoreable, scored, valid_record, write_csv


def describe(values):
    return dict(n=len(values), mean=statistics.mean(values), median=statistics.median(values),
                sd=statistics.stdev(values) if len(values) > 1 else None, min=min(values), max=max(values))


def compare(x, y):
    test = stats.mannwhitneyu(x, y, alternative='two-sided', method='asymptotic', use_continuity=True)
    return dict(u=float(test.statistic), p=float(test.pvalue), a12=float(test.statistic / (len(x) * len(y))),
                n_best=len(x), n_other=len(y))


def analyze(root):
    spec = read(root / 'manifest.json')
    out = root / 'stats'
    out.mkdir(exist_ok=True)
    with (root / 'env/subject-characteristics.csv').open() as f:
        characteristics = list(csv.DictReader(f))
    tags = read(root / 'suite/feature-tags.json')
    write_csv(out / 'subject_characteristics.csv', [dict(r, feature_tags=tags[r['subject']]) for r in characteristics])
    valid, outcomes, flat, missing, excluded = [], [], [], [], []
    for row in spec['runs']:
        rec = valid_record(root, row, spec['id'])
        if rec is None:
            missing.append(row['id'])
            flat.append(dict(**row, status='pending_or_unverifiable'))
            continue
        flat.append(dict(**row, **{k: v for k, v in rec.items() if k not in ('run', 'evidence', 'manifest_id')}))
        if scoreable(rec):
            outcomes.append(rec)
        if rec['status'] == 'ok':
            valid.append(rec)
        elif rec['status'] == 'excluded':
            excluded.append(dict(id=row['id'], reason=rec['reason']))
    write_csv(root / 'runs.csv', flat)
    atomic(out / 'availability.json', dict(manifest_id=spec['id'], valid=len(valid), excluded=excluded, missing=missing,
                                         policy=spec['statistics_policy'], outcome_policy=spec.get('outcome_policy'),
                                         scored=len(outcomes), tool_timeout=sum(r['status']=='tool_timeout' for r in outcomes),
                                         empty=sum(r['status']=='empty' for r in outcomes), units='coverage and kill fractions [0,1]; spread fraction; threshold .10'))
    # Main exports include confirmed tool deadlines/empty outputs as zero outcomes.
    analyze_view([scored(r) for r in outcomes], out)
    secondary = out / 'successful-only'
    secondary.mkdir(exist_ok=True)
    analyze_view(valid, secondary)
    chosen = selection(root, spec)
    if chosen:
        atomic(root / 'selection.json', chosen)
    else:
        (root / 'selection.json').unlink(missing_ok=True)
    grouped = defaultdict(Counter)
    for row in flat:
        key = (row['experiment'], row['subject'], row['budget'], row['treatment'])
        grouped[key][row['status']] += 1
    write_csv(out / 'outcomes.csv', [dict(experiment=k[0], subject=k[1], budget=k[2], treatment=k[3],
        planned=sum(v.values()), measured=v['ok'], tool_timeout=v['tool_timeout'], empty=v['empty'],
        unresolved=v['excluded'], pending_or_unverifiable=v['pending_or_unverifiable'],
        scored=v['ok']+v['tool_timeout']+v['empty']) for k, v in sorted(grouped.items())])
    print(f'Wrote {len(flat)} manifest rows to runs.csv; valid={len(valid)}, excluded={len(excluded)}, pending/unverifiable={len(missing)}')


def analyze_view(valid, out):
    a = defaultdict(list)
    b = defaultdict(list)
    for rec in valid:
        r = rec['run']
        if r['experiment'] == 'A':
            a[r['subject'], r['budget'], r['treatment']].append(rec['coverage'])
        else:
            b[r['subject'], r['tool']].append(rec)
    for label, treatments in [('base', BASE), ('all', TREATMENTS)]:
        cells, winners, spreads, tests, ranks, posthoc, omnibus, distribution = [], [], [], [], [], [], [], []
        for budget in (10, 60):
            blocks = []
            for subject in SUBJECTS:
                data = {t: a[subject, budget, t] for t in treatments}
                for t, values in data.items():
                    if values:
                        cells.append(dict(subject=subject, budget=budget, treatment=t, kind='combinator' if t == 'FOS+COS' else 'base', **describe(values)))
                if not all(data.values()):
                    continue
                means = [statistics.mean(data[t]) for t in treatments]
                blocks.append(means)
                order = sorted(treatments, key=lambda t: (-statistics.mean(data[t]), treatments.index(t)))
                best, second = order[:2]
                co_winners = [t for t in treatments if statistics.mean(data[t]) == max(means)]
                winners.append(dict(subject=subject, budget=budget, winners=co_winners, minimum_n=min(map(len, data.values())), maximum_n=max(map(len, data.values()))))
                spreads.append(dict(subject=subject, budget=budget, spread=max(means)-min(means)))
                tests.append(dict(subject=subject, budget=budget, best=best, runner_up=second, tied_best=len(co_winners)>1, **compare(data[best], data[second])))
            selected = [v['spread'] for v in spreads if v['budget'] == budget]
            if selected:
                distribution.append(dict(budget=budget, subjects=len(selected), median=statistics.median(selected), q1=float(np.quantile(selected, .25)), q3=float(np.quantile(selected, .75)), max=max(selected), at_least_10_percentage_points=sum(s >= .10 for s in selected)))
            n, k = len(blocks), len(treatments)
            if n:
                rank_matrix = np.array([stats.rankdata(-np.array(block), method='average') for block in blocks])
                avg = np.mean(rank_matrix, axis=0)
                for t, rank in zip(treatments, avg):
                    ranks.append(dict(budget=budget, treatment=t, average_rank=float(rank), subjects=n))
                if n >= 2:
                    if all(len(set(block)) == 1 for block in blocks):
                        statistic, p = 0., 1.
                    else:
                        f = stats.friedmanchisquare(*np.array(blocks).T)
                        statistic, p = float(f.statistic), float(f.pvalue)
                    se = math.sqrt(k * (k + 1) / (6 * n))
                    cd = float(stats.studentized_range.ppf(.95, k, np.inf) / math.sqrt(2) * se)
                    omnibus.append(dict(budget=budget, subjects=n, statistic=statistic, p=p, critical_difference=cd, alpha=.05))
                    for i, j in combinations(range(k), 2):
                        diff = float(abs(avg[i] - avg[j]))
                        pvalue = float(stats.studentized_range.sf(diff / se * math.sqrt(2), k, np.inf))
                        posthoc.append(dict(budget=budget, first=treatments[i], second=treatments[j], rank_difference=diff, p=pvalue, critical_difference=cd, exceeds_cd=diff > cd))
        for name, rows in [('cells', cells), ('winners', winners), ('spreads', spreads), ('spread_distribution', distribution), ('best_vs_runner_up', tests), ('average_ranks', ranks), ('friedman', omnibus), ('nemenyi', posthoc)]:
            write_csv(out / f'A_{label}_{name}.csv', rows)
        atomic(out / f'A_{label}_distinct_winners.json', {str(budget): sorted({t for row in winners if row['budget'] == budget for t in row['winners']}) for budget in (10, 60)})
        write_csv(out / f'A_{label}_win_counts.csv', [dict(budget=budget, treatment=t,
            subjects_won=sum(t in row['winners'] for row in winners if row['budget'] == budget),
            distinct_winners=len({w for row in winners if row['budget'] == budget for w in row['winners']}))
            for budget in (10, 60) for t in treatments])
    composition = []
    for subject in SUBJECTS:
        for budget in (10, 60):
            names = ['FOS+COS', 'FOS', 'COS']
            values = [a[subject, budget, t] for t in names]
            if all(values):
                ranked = stats.rankdata([-statistics.mean(v) for v in values], method='average')
                for i, component in enumerate(names[1:], 1):
                    composition.append(dict(subject=subject, budget=budget, component=component, composed_rank_among_three=float(ranked[0]), component_rank_among_three=float(ranked[i]),
                                            mean_difference=statistics.mean(values[0])-statistics.mean(values[i]), **compare(values[0], values[i])))
    write_csv(out / 'A_composition.csv', composition)
    subjects, tools = [], []
    for (subject, tool), records in sorted(b.items()):
        subjects.append(dict(subject=subject, tool=tool, **describe([r['mutation_kill'] for r in records]),
                             mutant_counts=sorted(set(r['mutant_count'] for r in records if r['mutant_count'] is not None)),
                             generated_counts=sorted(set(r['mutants_generated'] for r in records if r['mutants_generated'] is not None)),
                             ignored_counts=sorted(set(r['mutants_ignored'] for r in records if r['mutants_ignored'] is not None))))
    for tool in ['MAZE', 'T3', 'EvoSuite', 'Kex']:
        cells = [r for r in subjects if r['tool'] == tool]
        wins = 0
        complete_subjects = 0
        for subject in SUBJECTS:
            entries = [r for r in subjects if r['subject'] == subject]
            if len(entries) == 4:
                complete_subjects += 1
                wins += any(r['tool'] == tool and r['mean'] == max(x['mean'] for x in entries) for r in entries)
        if cells:
            tools.append(dict(tool=tool, subjects=len(cells), mean_kill_across_available_subjects=statistics.mean(r['mean'] for r in cells), best_count=wins, subjects_with_all_tools=complete_subjects))
    write_csv(out / 'B_subjects.csv', subjects)
    write_csv(out / 'B_tools.csv', tools)


if __name__ == '__main__':
    analyze(Path('/results'))
