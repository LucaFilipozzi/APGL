
import numpy
import logging
from apgl.graph import *
from apgl.generator.ErdosRenyiGenerator import ErdosRenyiGenerator
from apgl.util.Util import Util 

class BoundGraphIterator(object): 
    """
    Take 3 clusters generated by Erdos Renyi processes and then add random edges 
    successively to model "noise". 
    """
    def __init__(self, changeEdges=10, numGraphs=100, numClusterVertices=50, numClusters=3, p=0.3): 
        self.changeEdges = changeEdges 
        self.numGraphs = numGraphs
        self.graphInd = 0
        self.numClusters = numClusters 
        self.realClustering = numpy.zeros(numClusterVertices*numClusters)
        generator = ErdosRenyiGenerator(p)
        
        clusterList = []
        for i in range(numClusters):  
            cluster = SparseGraph(GeneralVertexList(numClusterVertices))
            cluster = generator.generate(cluster)
            clusterList.append(cluster)
            
            self.realClustering[numClusterVertices*i:(i+1)*numClusterVertices] = i

        self.graph = clusterList[0]
        for i in range(1, len(clusterList)): 
            self.graph = self.graph.concat(clusterList[i])
        
        
    def __iter__(self):
        return self
        
    def next(self):
        if self.graphInd == self.numGraphs: 
            raise StopIteration
        
        i = 0
        while i < self.changeEdges: 
            inds = numpy.random.randint(0, self.graph.size, 2)
            if self.graph[inds[0], inds[1]] == 0: 
                self.graph[inds[0], inds[1]] = 1
                i += 1 
        
        logging.debug(self.graph)        
        
        W = self.graph.getSparseWeightMatrix().tocsr()
        self.graphInd += 1 
        return W 
            