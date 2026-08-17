import csv
import statistics
#
# Contain the following post-analyses:
#   * Make csv-tables of averages of mutliple runs (of the same tool)
#   * just that for now :D
#


def getRawData(datafile):
    data = []
    with open(datafile, mode='r', encoding='utf-8') as file:
       # Create a CSV reader
       reader = csv.reader(file)
       header = next(reader)
       # Iterate over each row in the CSV file
       for row in reader:
           # Each row is a list of values
           D = {}
           for(name,v) in zip(header,row):
               D[name] = v
           data.append(D)
    return (header,data)

# these attribs do not change across different runs:
constantAttribs  = ['tool', 'benchmark', 'class', 'linesTotal', 'conditionsTotal', 'mutantsTotal', 'timeBudget', 'totalTestClasses']
# attribs that change over different runs, so we may  be interested
# in e.g. average:
variableAttribs = ['preparationTime', 'generationTime', 'executionTime', 'testcaseNumber', 'uncompilableNumber', 'brokenTests', 'failTests', 'linesCovered', 'linesCoverageRatio', 'conditionsCovered', 'conditionsCoverageRatio', 'mutantsCovered', 'mutantsCoverageRatio', 'mutantsKilled', 'mutantsKillRatio', 'mutantsAlive']
#
otherAttribs = ['run']
allAttribs = ['tool', 'benchmark', 'class', 'run', 'preparationTime', 'generationTime', 'executionTime', 'testcaseNumber', 'uncompilableNumber', 'brokenTests', 'failTests', 'linesTotal', 'linesCovered', 'linesCoverageRatio', 'conditionsTotal', 'conditionsCovered', 'conditionsCoverageRatio', 'mutantsTotal', 'mutantsCovered', 'mutantsCoverageRatio', 'mutantsKilled', 'mutantsKillRatio', 'mutantsAlive', 'timeBudget', 'totalTestClasses']

def toNumber(str):
    if '.' in str : return float(str)
    return int(str)

def mkTableOfMeans(rawData,outFile):
    bmnames = { r["benchmark"] for r in rawData }
    bmnames = [ r for r in bmnames ]
    bmnames.sort()
    T = []
    for BM in bmnames:
        group = [ r for r in rawData if r["benchmark"]==BM]
        g0 = group[0]
        N = len(group)
        D = {}
        for attrib in allAttribs:
            if attrib in constantAttribs:
                D[attrib] = g0[attrib]
            elif attrib in variableAttribs:
                m = statistics.mean([toNumber(r[attrib]) for r in group])
                D[attrib] = m
        T.append(D)
    #export T to a csv file

    # add some aggregate states
    extra1 = { "benchmark" : "OVERALL-mean"}
    for attrib in variableAttribs:
        m = statistics.mean([ r[attrib] for r in T ])
        extra1[attrib] = m

    extra2 = { "benchmark" : "TOTAL"}
    attribsToSum = ['linesTotal', 'conditionsTotal', 'mutantsTotal'] + variableAttribs
    for attrib in attribsToSum:
        m = sum([ toNumber(str(r[attrib])) for r in T ])
        extra2[attrib] = m
    extra2['linesCoverageRatio'] = extra2['linesCovered']/extra2['linesTotal']
    extra2['conditionsCoverageRatio'] = extra2['conditionsCovered']/extra2['conditionsTotal']
    extra2['mutantsCoverageRatio'] = extra2['mutantsCovered']/extra2['mutantsTotal']
    extra2['mutantsKillRatio'] = extra2['mutantsKilled']/extra2['mutantsTotal']
    T.append(extra1)
    T.append(extra2)

    allAttribs_ = [a for a in allAttribs if a != 'run']
    with open(outFile, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=allAttribs_)
        writer.writeheader()  # Write header row
        writer.writerows(T)
    return T

def mkTableOfMeans2(datafile) :
    if not datafile.endswith("_collected.csv") :
        raise Exception("expecting a ..._collected.csv file")
    n = len(datafile) - len("_collected.csv")
    outfname = datafile[:n]
    outfname += "_avrg.csv"
    (h,data) = getRawData(datafile)
    mkTableOfMeans(data,outfname)

datafiles = [
        "results_kex_10_5runs/kex_10_collected.csv",
        "results_kex_60_5runs/kex_60_collected.csv",
        "results_mazebfsbrmin_10/mazebfsbrmin_10_5runs_collected.csv",
        "results_mazedfsbrmin_10/mazedfsbrmin_10_5runs_collected.csv",
        "results_mazedfsbrmin_60/mazedfsbrmin_60_5runs_collected.csv",
        "results_mazesgsbrmin_10/mazesgsbrmin_10_5runs_collected.csv",
        "results_mazesgsbrmin_60/mazesgsbrmin_60_5runs_collected.csv",
        "results_mazefoscosbrmin_10/mazefoscosbrmin_10_5runs_collected.csv",
        "results_mazefoscosbrmin_60/mazefoscosbrmin_60_5runs_collected.csv",
        ]
for f in datafiles:
    mkTableOfMeans2(f)

#
# for testing:
#
#datafile = "results_mazebfsbrmin_60/mazebfsbrmin_60_5runs_collected.csv"
#outfile = "mazebfsbrmin_60_5runs_avrg.csv"
#
#
#(h,data) = getRawData(datafile)
#mkTableOfMeans(data,outfile)
