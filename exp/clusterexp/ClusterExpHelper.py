"""
Some common functions used for the clustering experiments 
"""
import logging
import numpy
from apgl.graph.GraphUtils import GraphUtils 
from apgl.util.PathDefaults import PathDefaults
from exp.sandbox.IterativeSpectralClustering import IterativeSpectralClustering
from exp.sandbox.NingSpectralClustering import NingSpectralClustering
from exp.sandbox.IterativeModularityClustering import IterativeModularityClustering
from exp.sandbox.GraphIterators import toDenseGraphListIterator


class ClusterExpHelper(object):
    def __init__(self, iteratorFunc, datasetName, numGraphs):
        #Variables to choose which methods to run
        self.runIASC = True
        self.runExact = True
        self.runNystrom = True
        self.runNing = True
        self.runModularity = True

        self.getIteratorFunc = iteratorFunc
        self.datasetName = datasetName 

        self.numGraphs = numGraphs
        self.resultsDir = PathDefaults.getOutputDir() + "cluster/"

        self.k1 = 10
        self.k2 = 10 
        self.k3 = 500

    def getIterator(self):
        return self.getIteratorFunc()

    def recordResults(self, clusterList, timeList, fileName):
        """
        Save results for a particular clustering
        """
        iterator = self.getIterator()
        numMeasures = 2
        measures = numpy.zeros((self.numGraphs, numMeasures))

        for i in range(self.numGraphs):
            W = iterator.next()
            measures[i, 0] = GraphUtils.modularity(W, clusterList[i])
            measures[i, 1] = GraphUtils.kwayNormalisedCut(W, clusterList[i])

        file = open(fileName, 'w')
        numpy.savez(file, measures, timeList)
        logging.info("Saved file as " + fileName)

    def runExperiment(self):
        """
        Run the selected clustering experiments and save results
        """
        if self.runIASC or self.runExact:
            clusterer = IterativeSpectralClustering(self.k1, self.k2)
            clusterer.nb_iter_kmeans = 20

        if self.runIASC:
            logging.info("Running approximate method")
            iterator = self.getIterator()
            clusterList, timeList = clusterer.clusterFromIterator(iterator, timeIter=True)

            resultsFileName = self.resultsDir + self.datasetName + "ResultsIASC.npz"
            self.recordResults(clusterList, timeList, resultsFileName)

        if self.runExact:
            logging.info("Running exact method")
            iterator = self.getIterator()
            clusterList, timeList = clusterer.clusterFromIterator(iterator, False, timeIter=True)

            resultsFileName = self.resultsDir + self.datasetName + "ResultsExact.npz"
            self.recordResults(clusterList, timeList, resultsFileName)

        if self.runNystrom:
            logging.info("Running nystrom method without updates")
            clusterer = IterativeSpectralClustering(self.k1, self.k2, k3=self.k3, nystromEigs=True)
            clusterer.nb_iter_kmeans = 20
            iterator = self.getIterator()
            clusterList, timeList = clusterer.clusterFromIterator(iterator, False, timeIter=True)

            resultsFileName = self.resultsDir + self.datasetName + "ResultsNystrom.npz"
            self.recordResults(clusterList, timeList, resultsFileName)

        if self.runModularity: 
            logging.info("Running modularity clustering")
            clusterer = IterativeModularityClustering(self.k1)
            iterator = self.getIterator()

            clusterList, timeList = clusterer.clusterFromIterator(iterator, timeIter=True)

            resultsFileName = self.resultsDir + self.datasetName + "ResultsModularity.npz"
            self.recordResults(clusterList, timeList, resultsFileName)

        if self.runNing:
            logging.info("Running Nings method")
            iterator = self.getIterator()
            clusterer = NingSpectralClustering(self.k1)
            clusterList, timeList = clusterer.cluster(toDenseGraphListIterator(iterator), timeIter=True)

            resultsFileName = self.resultsDir + self.datasetName + "ResultsNing.npz"
            self.recordResults(clusterList, timeList, resultsFileName)

        logging.info("All done: see you around!")
