"""
Output some statistics for the real graph datasets.  

"""
import os
import sys
import logging
import numpy
import itertools 
from exp.clusterexp.CitationIterGenerator import CitationIterGenerator 
from exp.clusterexp.HIVIterGenerator import HIVIterGenerator 
from apgl.graph import GraphStatistics 
from apgl.graph import SparseGraph, GraphUtils  
from apgl.util.PathDefaults import PathDefaults
from exp.clusterexp.BemolData import BemolData
import matplotlib.pyplot as plt 
import scipy.sparse.linalg 

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

plotHIV = False 
plotCitation = False
plotBemol = True 

if plotHIV: 
    generator = HIVIterGenerator()
    iterator = generator.getIterator()
if plotCitation: 
    maxGraphSize = 3000 
    generator = CitationIterGenerator(maxGraphSize=maxGraphSize)
    iterator = generator.getIterator()
if plotBemol: 
    dataDir = PathDefaults.getDataDir() + "cluster/"
    nbUser = 10000 # set to 'None' to have all users
    nbPurchasesPerIt = 50 # set to 'None' to take all the purchases
                                          # per date
    startingIteration = 20
    endingIteration = None # set to 'None' to have all iterations
    stepSize = 10    
    
    iterator = itertools.islice(BemolData.getGraphIterator(dataDir, nbUser, nbPurchasesPerIt), startingIteration, endingIteration, stepSize)
    
    #Appears to be 10 components 

subgraphIndicesList = []
for W in iterator: 
    subgraphIndicesList.append(range(W.shape[0])) 

#Try to find number of clusters at end of sequence by looking at eigengap 
k = 2000
L = GraphUtils.normalisedLaplacianSym(W)
logging.debug("Computing eigenvalues")
omega, Q = scipy.sparse.linalg.eigsh(L, min(k, L.shape[0]-1), which="SM", ncv = min(10*k, L.shape[0]))

omegaDiff = numpy.diff(omega)

plotInd = 0 
plt.figure(plotInd)
plt.plot(numpy.arange(omega.shape[0]), omega)
plt.xlabel("Eigenvalue index")
plt.ylabel("Eigenvalue")
plotInd+=1 

plt.figure(plotInd)
plt.plot(numpy.arange(omegaDiff.shape[0]), omegaDiff)
plt.xlabel("Eigenvalue index")
plt.ylabel("Eigenvalue diff")
plotInd +=1 

#No obvious number of clusters and there are many edges 
graph = SparseGraph(W.shape[0], W=W)

logging.debug("Computing graph statistics")
graphStats = GraphStatistics()
statsMatrix = graphStats.sequenceScalarStats(graph, subgraphIndicesList, slowStats=False)

plt.figure(plotInd)
plt.plot(numpy.arange(statsMatrix.shape[0]), statsMatrix[:, graphStats.numVerticesIndex])
plt.xlabel("Graph index")
plt.ylabel("Num vertices")
plotInd+=1 

plt.figure(plotInd)
plt.plot(numpy.arange(statsMatrix.shape[0]), statsMatrix[:, graphStats.maxComponentSizeIndex])
plt.xlabel("Graph index")
plt.ylabel("Max component size")
plotInd+=1 

plt.figure(plotInd)
plt.plot(numpy.arange(statsMatrix.shape[0]), statsMatrix[:, graphStats.numComponentsIndex])
plt.xlabel("Graph index")
plt.ylabel("Num components")
plotInd+=1 

plt.show()
