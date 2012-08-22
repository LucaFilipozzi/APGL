
import apgl
import unittest
import logging
import sys
import numpy
import scipy.stats 

from exp.viroscopy.model.HIVEpidemicModel import HIVEpidemicModel
from exp.viroscopy.model.HIVRates import HIVRates
from exp.viroscopy.model.HIVGraph import HIVGraph
from exp.viroscopy.model.HIVVertices import HIVVertices
from exp.viroscopy.model.HIVModelUtils import HIVModelUtils
from apgl.graph import * 
from apgl.util import Util 

@apgl.skipIf(not apgl.checkImport('pysparse'), 'No module pysparse')
class  HIVEpidemicModelTest(unittest.TestCase):
    def setUp(self):
        numpy.random.seed(21)
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

        M = 100
        undirected = True
        self.graph = HIVGraph(M, undirected)
        s = 3
        self.gen = scipy.stats.zipf(s)
        hiddenDegSeq = self.gen.rvs(size=self.graph.getNumVertices())
        rates = HIVRates(self.graph, hiddenDegSeq)
        self.model = HIVEpidemicModel(self.graph, rates)
        
    def testSimulate(self):
        T = 1.0

        self.graph.getVertexList().setInfected(0, 0.0)
        self.model.setT(T)

        times, infectedIndices, removedIndices, graph = self.model.simulate(verboseOut=True)

        numInfects = 0
        for i in range(graph.getNumVertices()):
            if graph.getVertex(i)[HIVVertices.stateIndex] == HIVVertices==infected:
                numInfects += 1

        self.assertTrue(numInfects == 0 or times[len(times)-1] >= T)

        #Test with a larger population as there seems to be an error when the
        #number of infectives becomes zero.
        M = 100
        undirected = True
        graph = HIVGraph(M, undirected)
        graph.setRandomInfected(10)

        self.graph.removeAllEdges()

        T = 21.0
        hiddenDegSeq = self.gen.rvs(size=self.graph.getNumVertices())
        rates = HIVRates(self.graph, hiddenDegSeq)
        model = HIVEpidemicModel(self.graph, rates)
        model.setRecordStep(10)
        model.setT(T)

        times, infectedIndices, removedIndices, graph = model.simulate(verboseOut=True)
        self.assertTrue((times == numpy.array([0, 10, 20], numpy.int)).all())
        self.assertEquals(len(infectedIndices), 3)
        self.assertEquals(len(removedIndices), 3)

        #TODO: Much better testing
        
    def testSimulate2(self):         
        startDate = 0.0 
        endDate = 100.0 
        recordStep = 10 
        printStep = 10 
        M = 1000 
        meanTheta, sigmaTheta = HIVModelUtils.estimatedRealTheta()
        
        undirected = True
        graph = HIVGraph(M, undirected)
        logging.info("Created graph: " + str(graph))
        
        alpha = 2
        zeroVal = 0.9
        p = Util.powerLawProbs(alpha, zeroVal)
        hiddenDegSeq = Util.randomChoice(p, graph.getNumVertices())
        
        rates = HIVRates(graph, hiddenDegSeq)
        model = HIVEpidemicModel(graph, rates, endDate, startDate)
        model.setRecordStep(recordStep)
        model.setPrintStep(printStep)
        model.setParams(meanTheta)
        
        initialInfected = graph.getInfectedSet()
        
        logging.debug("MeanTheta=" + str(meanTheta))
        
        times, infectedIndices, removedIndices, graph = model.simulate(True)
        
        #Now test the final graph 
        edges = graph.getAllEdges()
        
        for i, j in edges:
            if graph.vlist.V[i, HIVVertices.genderIndex] == graph.vlist.V[j, HIVVertices.genderIndex] and (graph.vlist.V[i, HIVVertices.orientationIndex] != HIVVertices.bi or graph.vlist.V[j, HIVVertices.orientationIndex] != HIVVertices.bi): 
                self.fail()
                      
        finalInfected = graph.getInfectedSet()
        finalRemoved = graph.getRemovedSet()
        
        self.assertEquals(numpy.intersect1d(initialInfected, finalRemoved).shape[0], len(initialInfected))
        
        #Test case where there is no contact  
        meanTheta = numpy.array([100, 1, 1, 0, 0, 0, 0, 0, 0, 0], numpy.float)
        graph = HIVGraph(M, undirected)
        rates = HIVRates(graph, hiddenDegSeq)
        model = HIVEpidemicModel(graph, rates, endDate, startDate)
        model.setParams(meanTheta)
        
        times, infectedIndices, removedIndices, graph = model.simulate(True)
        self.assertEquals(len(graph.getInfectedSet()), 100)
        self.assertEquals(len(graph.getRemovedSet()), 0)
        self.assertEquals(graph.getNumEdges(), 0)
        
        meanTheta = numpy.array([100, 1, 1, 0, 0, 0.1, 0, 0, 0, 0], numpy.float)
        graph = HIVGraph(M, undirected)
        rates = HIVRates(graph, hiddenDegSeq)
        model = HIVEpidemicModel(graph, rates, endDate, startDate)
        model.setPrintStep(printStep)
        model.setParams(meanTheta)
        
        times, infectedIndices, removedIndices, graph = model.simulate(True)
        self.assertEquals(len(graph.getInfectedSet()), 100)
        self.assertEquals(len(graph.getRemovedSet()), 0)
        
        
        edges = graph.getAllEdges()
        
        for i, j in edges:
            if graph.vlist.V[i, HIVVertices.genderIndex] == graph.vlist.V[j, HIVVertices.genderIndex]: 
                self.fail()
    
    def testFindStandardResults(self):
        times = [3, 12, 22, 25, 40, 50]
        infectedIndices = [[1], [1, 2], [1, 2], [1, 2], [1, 2], [1, 2]]
        removedIndices = [[1], [1, 2], [1, 2], [1, 2], [1, 2], [1, 2]]

        self.model.setT(51.0)
        self.model.setRecordStep(10)

        times, infectedIndices, removedIndices = self.model.findStandardResults(times, infectedIndices, removedIndices)

        self.assertTrue((numpy.array(times)==numpy.arange(0, 60, 10)).all())


        #Now try case where simulation is slightly longer than T and infections = 0
        numpy.random.seed(21)
        times = [3, 12, 22, 25, 40, 50]
        infectedIndices = [[1], [1, 2], [1, 2], [1, 2], [1, 2], [1, 2]]
        removedIndices = [[1], [1, 2], [1, 2], [1, 2], [1, 2], [1, 2]]

        self.model.setT(51.0)
        self.model.setRecordStep(10)

        times, infectedIndices, removedIndices = self.model.findStandardResults(times, infectedIndices, removedIndices)
        logging.debug(times)


if __name__ == '__main__':
    unittest.main()

