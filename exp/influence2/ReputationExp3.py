

"""
Use the new dataset from Pierre to perform expert recommendation. 
"""

import numpy 
try:  
    ctypes.cdll.LoadLibrary("/usr/local/lib/libigraph.so")
except: 
    pass 
import igraph 
from apgl.util.PathDefaults import PathDefaults 
from exp.util.IdIndexer import IdIndexer 
import xml.etree.ElementTree as ET
import array 
import logging 
import sys 
from exp.influence2.GraphRanker import GraphRanker 
from exp.influence2.RankAggregator import RankAggregator

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

coauthorFilename = PathDefaults.getDataDir() + "reputation/intelligent_agents.csv"
coauthorFile = open(coauthorFilename)

authorIndexer = IdIndexer("i")
articleIndexer = IdIndexer("i")

for line in coauthorFile: 
    vals = line.split(";")
    
    authorId = vals[0].strip()
    if "_" in authorId: 
        authorId = authorId[0:authorId.find("_")]
    
    articleId = vals[1].strip()
    
    print(authorId, articleId)
    
    authorIndexer.append(authorId)
    articleIndexer.append(articleId)

authorInds = authorIndexer.getArray()
articleInds = articleIndexer.getArray()
edges = numpy.c_[authorInds, articleInds]

print(numpy.max(authorInds), numpy.max(articleInds))

#Coauthor graph is undirected 
graph = igraph.Graph()
graph.add_vertices(numpy.max(authorInds) + numpy.max(articleInds))
graph.add_edges(edges)

print(graph.summary())

print(len(graph.components()))
compSizes = [len(x) for x in graph.components()]
print(numpy.max(compSizes))

outputLists = GraphRanker.rankedLists(graph)

itemList = RankAggregator.generateItemList(outputLists)
outputList, scores = RankAggregator.MC2(outputLists, itemList)

print(outputList[0:10])

#Now load list of experts - we get 31/35 
expertsFilename = PathDefaults.getDataDir() + "reputation/IntelligentAgentsExperts.txt"
expertsFile = open(expertsFilename)

expertsList = [] 
for line in expertsFile: 
    vals = line.split() 
    key = vals[1][0].lower() + "/" + vals[1] + ":" + vals[0]
    
    if key in authorIndexer.getIdDict(): 
        print(key)

#Now we just measure the error between true and fake errors 
