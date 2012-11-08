"""
Output some statistics for the citation iterator 

"""


import os
import sys
import logging
import numpy
from exp.clusterexp.CitationIterGenerator import CitationIterGenerator 
from apgl.graph import GraphStatistics 
from apgl.graph import SparseGraph, GeneralVertexList 
import matplotlib.pyplot as plt 

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

generator = CitationIterGenerator()
iterator = generator.getIterator()

subgraphIndicesList = []
for W in iterator: 
    subgraphIndicesList.append(range(W.shape[0])) 
    
graph = SparseGraph(GeneralVertexList(W.shape[0]))

graphStats = GraphStatistics()
statsMatrix = graphStats.sequenceScalarStats(graph, subgraphIndicesList, slowStats=False)


plt.figure(0)
plt.plot(numpy.arange(statsMatrix.shape[0]), statsMatrix[:, graphStats.numVerticesIndex])

plt.figure(1)
plt.plot(numpy.arange(statsMatrix.shape[0]), statsMatrix[:, graphStats.maxComponentSizeIndex])

plt.figure(2)
plt.plot(numpy.arange(statsMatrix.shape[0]), statsMatrix[:, graphStats.numComponentsIndex])

plt.show()