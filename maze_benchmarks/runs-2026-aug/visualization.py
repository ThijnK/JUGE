from post_analysis import getRawData, toNumber
import matplotlib.pyplot as plt
import numpy as np

toolsDatafiles_60s = [
    "./t3_60_5runs_avrg.csv",
    "results_evosuite_60_5runs/evosuite_60_avrg.csv",
    "results_kex_60_5runs/kex_60_avrg.csv",
    #"results_mazebfs_60/mazebfs_60_5runs_avrg.csv",
    #"results_mazebfsbrmin_60/mazebfsbrmin_60_5runs_avrg.csv",
    #"results_mazepcsk3a0_60/mazepcsk3a0_60_5runs_avrg.csv"
    "results_mazefoscosbrmin_10/mazefoscosbrmin_10_5runs_avrg.csv"
    #"results_mazefoscosbrmin_10/mazefoscosbrmin_10_5runs_avrg.csv"
     ]

mazeStartegies_Datafiles_10s = [
    #"./t3_60_5runs_avrg.csv",
    "results_mazedfsbrmin_10/mazedfsbrmin_10_5runs_avrg.csv",
    "results_mazebfsbrmin_10/mazebfsbrmin_10_5runs_avrg.csv",
    "results_mazesgsbrmin_10/mazesgsbrmin_10_5runs_avrg.csv",
    "results_mazefoscosbrmin_10/mazefoscosbrmin_10_5runs_avrg.csv"
#    "results_mazepcsk3a0_10/mazepcsk3a0_10_5runs_avrg.csv"
     ]

mazeStartegies_Datafiles_60s = [
    #"./t3_60_5runs_avrg.csv",
    "results_mazedfsbrmin_60/mazedfsbrmin_60_5runs_avrg.csv",
    "results_mazebfsbrmin_60/mazebfsbrmin_60_5runs_avrg.csv",
    "results_mazesgsbrmin_60/mazesgsbrmin_60_5runs_avrg.csv",
    "results_mazefoscosbrmin_60/mazefoscosbrmin_60_5runs_avrg.csv"
#    "results_mazepcsk3a0_60/mazepcsk3a0_60_5runs_avrg.csv"
     ]


def dropAuxRows(data):
    return [r for r in data
                  if not r["benchmark"].startswith("OVERALL-mean") and
                     not r["benchmark"].startswith("TOTAL") ]



def mkSimpleGraph(tools_data,
    propertyToDraw,  # property to plot at the y-axis
    propertyLabel,   # legend of the y-axis
    selector,        # predicate to select which benchmark-subjects to show
    diffThreshold,   # if not None will mark data with large diff between min and max
    sortinIncrComplexity # if true the BMs will be sorted in increasing number of branches
    ):

    BMs   = [ r["benchmark"] for r in tools_data[0] if selector(r["benchmark"])]
    tools = [ D[0]["tool"]for D in tools_data ]

    # drop the MZ/SVC-prefix from BMs names:
    def shortName(B):
        if B.startswith("SVC"): return B[4:]
        if B.startswith("MZ") :  return B[3:]
        return B

    SVCs  = [ shortName(B) for B in BMs if B.startswith("SVC")]
    MZBMs = [ shortName(B) for B in BMs if B.startswith("MZ")]
    BMs2  = [ shortName(B) for B in BMs ]

    def find_(s,f):
        for x in s:
            if f(x): return x
        return None

    # mapping every Tools T in the dataset to a mapping
    # BM-name --> prop-value
    tools_data_asDict = {}
    for T in tools :
        DT = find_(tools_data, lambda D: D[0]["tool"] == T)
        mapping = {}
        for r in DT:
            B = r["benchmark"]
            v = r[propertyToDraw]
            mapping[shortName(B)] = toNumber(v)
        tools_data_asDict[T] = mapping

    # BMs complexity, measured in number of branches
    BMcomplexity = {}
    T0 = tools_data[0]
    for B in BMs:
        r_ = find_(T0, lambda r: r["benchmark"] == B)
        c = r_["conditionsTotal"]
        BMcomplexity[shortName(B)] = toNumber(c)

    # Dictionary mapping every benchmark-subject B to a mapping
    # tool -> value
    asDict = {}
    for B in BMs:
        B_ = shortName(B)
        vals = {}
        for T in tools:
            vals[T] = tools_data_asDict[T][B_]
        asDict[B_] = vals

    NumericBMs = ["FLOAT", "HEAPSORT", "TRIANGLE",
            "EULER", "CONFLICT", "BESSEL", "OPTIMIZATION" ]

    BMsWithLargeDiff = [ B for B in BMs2
        if diffThreshold != None
           and max(asDict[B].values()) - min(asDict[B].values())
               >= diffThreshold
        ]

    #print(BMsWithLargeDiff)

    # sort MBs2 in increasing complexity:
    if sortinIncrComplexity:
        BMs2.sort(key = lambda B : BMcomplexity[B])

    fig, ax = plt.subplots(layout="constrained")
    toolcolors = {
        "t3": "#F89763",
        "kex": "#8FB4FA",
        "evosuite" : "#F4320B",
        "mazebfs" : "#000099",
        "mazepcsk3a0" : "#0B5DF4",
        "mazebfs" : "#000099",
        "mazedfsbrmin" : "#6BEFEB",
        "mazebfsbrmin" : "#14BDB8",
        "mazesgsbrmin" : "#6BA5EF",
        "mazefoscosbrmin" : "#104994"
        }

    x = np.arange(len(BMs2))
    width = 4  # the width of the bars
    K = 20
    print(x)
    x = K*x

    multiplier = 0

    def customFormatNumber(x):
        if x>=100: return ""
        return round(x,1)

    def shortToolName(tn):
        if (tn.endswith("brmin")):
            n = len(tn)
            k = len("brmin")
            return tn[:n-k]
        return tn

    for toolName in tools:
        offset = width * (multiplier - 1.5)
        y = [ tools_data_asDict[toolName][B] for B in BMs2 ]
        mycolor = toolcolors[toolName]
        rects = ax.bar(x + offset, y, width, label=shortToolName(toolName), color=mycolor)
        #ax.bar_label(rects, fmt="%.0f", padding=1, size=6)
        ax.bar_label(rects, fmt=lambda x:f"{customFormatNumber(x)}", padding=1, size=5, rotation=90)
        multiplier += 1

    ax.set_ylabel(propertyLabel)
    ax.set_xlim(left=-15)
    ax.set_ylim(bottom=20)
    ax.set_xticks(x, BMs2)
    ax.tick_params("x", rotation=30)

    ax.legend(loc="lower left", ncols=4, bbox_to_anchor=(0.0, 1.01))

    #ax.axhline(y=20,ls="--",lw=0.5,color="black")
    ax.axhline(y=40,ls="--",lw=0.5,color="black")
    ax.axhline(y=60,ls="--",lw=0.5,color="black")
    ax.axhline(y=80,ls="--",lw=0.5,color="black")


    for label in ax.get_xticklabels():
        lab = label.get_text()
        if lab in SVCs:
            #label.set_fontsize(16)
            label.set_color("#0000ff")
        else:
            label.set_text("hahaha")
        if lab in BMsWithLargeDiff:
            label.set_color("#ff0000")

    plt.show()



#propertyToDraw_ = "conditionsCoverageRatio"
propertyToDraw_ = "mutantsKillRatio"
# 'generationTime'
# 'testcaseNumber'
diffThreshold_ = 10 # 10%
#propertyLabel_ = "branch coverage (%)"
propertyLabel_ = "mutation kill ratio (%)"

select_MZBMsOnly = lambda B : B.startswith("MZ")
selectall = lambda B : B.startswith("MZ") or B.startswith("SVC")

#toolsData = [ getRawData(df)[1] for df in mazeStartegies_Datafiles_60s]
toolsData = [ getRawData(df)[1] for df in toolsDatafiles_60s]


mkSimpleGraph(toolsData,
    propertyToDraw_,
    propertyLabel_,
    select_MZBMsOnly,
    #selectall,
    diffThreshold_,
    True
    )
