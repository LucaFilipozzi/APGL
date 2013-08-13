"""
Use the DBLP dataset to recommend experts. 
"""
import numpy 
import logging 
import sys 
import sklearn.metrics 
from exp.influence2.GraphRanker import GraphRanker 
from exp.influence2.RankAggregator import RankAggregator
from exp.influence2.ArnetMinerDataset import ArnetMinerDataset
from apgl.util.Latex import Latex 

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
numpy.random.seed(21)

#field = "Boosting" 
#field = "Intelligent Agents"
field = "Machine Learning"
#field = "Ontology Alignment"

k = 100
maxRelevantAuthors = 1000
similarityCutoff = 0.4
            
dataset = ArnetMinerDataset(field)
dataset.overwriteRelevantExperts = True
dataset.overwriteCoauthors = True
dataset.maxRelevantAuthors = maxRelevantAuthors
dataset.similarityCutoff = similarityCutoff
dataset.k = k
dataset.vectoriseDocuments()
dataset.findSimilarDocuments()

graph, authorIndexer, relevantExperts = dataset.coauthorsGraph()
expertMatches, expertsSet = dataset.matchExperts()

logging.debug(expertMatches)
logging.debug(graph.summary())

expertMatchesInds = authorIndexer.translate(expertMatches) 
logging.debug(expertMatchesInds)   

relevantAuthorInds = authorIndexer.translate(relevantExperts) 

assert (numpy.array(relevantAuthorInds) < len(relevantAuthorInds)).all()

#First compute graph properties 
computeInfluence = False
outputLists = GraphRanker.rankedLists(graph, numRuns=100, computeInfluence=computeInfluence, p=0.05, trainExpertsIdList=expertMatchesInds)
itemList = RankAggregator.generateItemList(outputLists)
methodNames = GraphRanker.getNames(computeInfluence=computeInfluence)

#Then use MC2 rank aggregation 
outputList, scores = RankAggregator.MC2(outputLists, itemList)
outputLists.append(outputList)
methodNames.append("MC2")
print("outputList="+str(outputList))

#The supervised MC2
#outputList2, scores2 = RankAggregator.supervisedMC22(outputLists, itemList, expertsIdList)
#outputLists.append(outputList2)
#methodNames.append("SMC2")

#Process outputLists to only include people from the relevant field  
newOutputLists = []
for lst in outputLists: 
    lst = lst[lst < len(relevantAuthorInds)]  
    newOutputLists.append(lst)

print("\n")
"""
r = 20 
logging.debug("Top " + str(r) + " authors:")
for ind in outputLists[-1][0:r]: 
    key = (key for key,value in reader.authorIndexer.getIdDict().items() if value==ind).next()
    logging.debug(key)
"""

print("\n")

ns = numpy.arange(5, 105, 5)
numMethods = len(newOutputLists)

precisions = numpy.zeros((len(ns), numMethods))
averagePrecisions = numpy.zeros(numMethods)

for i, n in enumerate(ns):     
    for j in range(len(outputLists)): 
        predY = -numpy.ones(len(relevantAuthorInds))
        predY[expertMatchesInds] = 1
        
        testY = -numpy.ones(len(relevantAuthorInds))
        testY[newOutputLists[j][0:n]] = 1
        
        precisions[i, j] = sklearn.metrics.precision_score(testY, predY) 
        #precisions[i, j] = sklearn.metrics.precision_score(testY, predY, labels=numpy.array([-1, 1, numpy.int]), average="micro")

n = 50 

for j in range(len(outputLists)): 
    predY = -numpy.ones(len(relevantAuthorInds))
    predY[expertMatchesInds] = 1
    
    testY = -numpy.ones(len(relevantAuthorInds))
    testY[newOutputLists[j][0:n]] = 1
    
    averagePrecisions[j] = sklearn.metrics.average_precision_score(testY, predY)

precisions = numpy.c_[numpy.array(ns), precisions]

print(Latex.latexTable(Latex.array2DToRows(precisions), colNames=methodNames))
print(Latex.array1DToRow(averagePrecisions))

