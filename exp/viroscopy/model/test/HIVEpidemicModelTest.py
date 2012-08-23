
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

def runModel(theta, endDate=100.0, M=1000): 
    numpy.random.seed(21)
    undirected= True
    recordStep = 10 
    printStep = 10 
    startDate = 0
    alpha = 2
    zeroVal = 0.9
    p = Util.powerLawProbs(alpha, zeroVal)
    graph = HIVGraph(M, undirected)
    hiddenDegSeq = Util.randomChoice(p, graph.getNumVertices())
    logging.debug("MeanTheta=" + str(theta))
    
    rates = HIVRates(graph, hiddenDegSeq)
    model = HIVEpidemicModel(graph, rates, endDate, startDate)
    model.setRecordStep(recordStep)
    model.setPrintStep(printStep)
    model.setParams(theta)
    
    times, infectedIndices, removedIndices, graph = model.simulate(True)            
    
    return times, infectedIndices, removedIndices, graph, model  

@apgl.skipIf(not apgl.checkImport('pysparse'), 'No module pysparse')
class  HIVEpidemicModelTest(unittest.TestCase):
    def setUp(self):
        numpy.random.seed(21)
        numpy.set_printoptions(suppress=True, precision=4)
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

        M = 100
        undirected = True
        self.graph = HIVGraph(M, undirected)
        s = 3
        self.gen = scipy.stats.zipf(s)
        hiddenDegSeq = self.gen.rvs(size=self.graph.getNumVertices())
        rates = HIVRates(self.graph, hiddenDegSeq)
        self.model = HIVEpidemicModel(self.graph, rates)
     
    @unittest.skip("")
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
        
    @unittest.skip("")
    def testSimulate2(self):    
        startDate = 0.0 
        endDate = 100.0 
        M = 1000 
        meanTheta, sigmaTheta = HIVModelUtils.estimatedRealTheta()
        
        undirected = True
        graph = HIVGraph(M, undirected)
        
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
        
        times, infectedIndices, removedIndices, graph, model = runModel(meanTheta)

        self.assertEquals(len(graph.getInfectedSet()), 100)
        self.assertEquals(len(graph.getRemovedSet()), 0)
        self.assertEquals(graph.getNumEdges(), 0)
        
        heteroContactRate = 0.1
        meanTheta = numpy.array([100, 1, 1, 0, 0, heteroContactRate, 0, 0, 0, 0], numpy.float)
        times, infectedIndices, removedIndices, graph, model = runModel(meanTheta)
        
        self.assertEquals(len(graph.getInfectedSet()), 100)
        self.assertEquals(len(graph.getRemovedSet()), 0)
        
        edges = graph.getAllEdges()
        
        for i, j in edges:
            self.assertNotEqual(graph.vlist.V[i, HIVVertices.genderIndex], graph.vlist.V[j, HIVVertices.genderIndex]) 
            
        #Number of conacts = rate*people*time
        infectedSet = graph.getInfectedSet()
        numHetero = (graph.vlist.V[list(infectedSet), HIVVertices.orientationIndex] == HIVVertices.hetero).sum()
        self.assertTrue(abs(numHetero*endDate*heteroContactRate- model.getNumContacts()) < 100)
        
        heteroContactRate = 0.01
        meanTheta = numpy.array([100, 1, 1, 0, 0, heteroContactRate, 0, 0, 0, 0], numpy.float)
        times, infectedIndices, removedIndices, graph, model = runModel(meanTheta)
        infectedSet = graph.getInfectedSet()
        numHetero = (graph.vlist.V[list(infectedSet), HIVVertices.orientationIndex] == HIVVertices.hetero).sum()
        self.assertAlmostEqual(numHetero*endDate*heteroContactRate/100, model.getNumContacts()/100.0, 0)      
        
    @unittest.skip("")
    def testSimulateBis(self): 
        #Play with bi rate 
        biContactRate = 0.1
        endDate = 100.0
        meanTheta = numpy.array([200, 1, 1, 0, 0, 0, biContactRate, 0, 0, 0], numpy.float)
        times, infectedIndices, removedIndices, graph, model = runModel(meanTheta, endDate=endDate)
        infectedSet = graph.getInfectedSet()
        numBi = (graph.vlist.V[list(infectedSet), HIVVertices.orientationIndex] == HIVVertices.bi).sum()
        susceptibleSet = graph.getSusceptibleSet()
        self.assertTrue(abs(numBi*endDate*biContactRate- model.getNumContacts()) < 10)
        
        numContacts = model.getNumContacts()
        edges = graph.getAllEdges()        
        numMSM = 0         
        
        for i, j in edges:
            self.assertTrue(graph.vlist.V[i, HIVVertices.orientationIndex]==HIVVertices.bi or graph.vlist.V[j, HIVVertices.orientationIndex]==HIVVertices.bi) 
            
            if graph.vlist.V[i, HIVVertices.genderIndex] == graph.vlist.V[j, HIVVertices.genderIndex] and graph.vlist.V[i, HIVVertices.genderIndex]==HIVVertices.male: 
                numMSM += 1 
            
        biContactRate = 0.2
        meanTheta = numpy.array([200, 1, 1, 0, 0, 0, biContactRate, 0, 0, 0], numpy.float)
        times, infectedIndices, removedIndices, graph, model = runModel(meanTheta)
        
        infectedSet = graph.getInfectedSet()
        numBi = (graph.vlist.V[list(infectedSet), HIVVertices.orientationIndex] == HIVVertices.bi).sum()
        
        numContacts2 = model.getNumContacts()
        self.assertTrue(abs(numContacts*2-numContacts2) < 10)
        
        #Try infection between men only 
        biContactRate = 0.2
        manBiInfectProb = 1.0 
        meanTheta = numpy.array([300, 1, 1, 0, 0, 0, biContactRate, 0, 0, manBiInfectProb], numpy.float)
        
        times, infectedIndices, removedIndices, graph, model = runModel(meanTheta)
        #print(numpy.logical_and(graph.vlist.V[:, HIVVertices.orientationIndex] == HIVVertices.bi, graph.vlist.V[:, HIVVertices.genderIndex] == HIVVertices.male).sum())
        
        newInfects = numpy.setdiff1d(graph.getInfectedSet(), numpy.array(infectedIndices[0]))
        
        self.assertTrue((graph.vlist.V[newInfects, HIVVertices.orientationIndex] == HIVVertices.bi).all())
        self.assertTrue((graph.vlist.V[newInfects, HIVVertices.genderIndex] == HIVVertices.male).all())


    @unittest.skip("")
    def testSimulateInfects(self): 
        #Test varying infection probabilities 
        
        heteroContactRate = 0.1
        manWomanInfectProb = 1.0 
        meanTheta = numpy.array([100, 1, 1, 0, 0, heteroContactRate, 0, 0, manWomanInfectProb, 0], numpy.float)
        times, infectedIndices, removedIndices, graph, model = runModel(meanTheta)
        
        newInfects = numpy.setdiff1d(graph.getInfectedSet(), numpy.array(infectedIndices[0]))
        
        self.assertTrue((graph.vlist.V[newInfects, HIVVertices.genderIndex] == HIVVertices.female).all())
        
        manWomanInfectProb = 0.1
        meanTheta = numpy.array([100, 1, 1, 0, 0, heteroContactRate, 0, 0, manWomanInfectProb, 0], numpy.float)
        times, infectedIndices, removedIndices, graph, model = runModel(meanTheta)
        newInfects2 = numpy.setdiff1d(graph.getInfectedSet(), numpy.array(infectedIndices[0]))
        
        self.assertTrue((graph.vlist.V[newInfects2, HIVVertices.genderIndex] == HIVVertices.female).all())
        self.assertTrue(newInfects.shape[0] > newInfects2.shape[0])
        
        
        #Now only women infect 
        heteroContactRate = 0.1
        womanManInfectProb = 1.0 
        meanTheta = numpy.array([100, 1, 1, 0, 0, heteroContactRate, 0, womanManInfectProb, 0, 0], numpy.float)
        times, infectedIndices, removedIndices, graph, model = runModel(meanTheta)
        
        newInfects = numpy.setdiff1d(graph.getInfectedSet(), numpy.array(infectedIndices[0]))
        
        self.assertTrue((graph.vlist.V[newInfects, HIVVertices.genderIndex] == HIVVertices.male).all())
        
        womanManInfectProb = 0.1
        meanTheta = numpy.array([100, 1, 1, 0, 0, heteroContactRate, 0, womanManInfectProb, 0, 0], numpy.float)
        times, infectedIndices, removedIndices, graph, model = runModel(meanTheta)
        newInfects2 = numpy.setdiff1d(graph.getInfectedSet(), numpy.array(infectedIndices[0]))
        
        self.assertTrue((graph.vlist.V[newInfects2, HIVVertices.genderIndex] == HIVVertices.male).all())
        self.assertTrue(newInfects.shape[0] > newInfects2.shape[0])
  

    def testSimulateDetects(self): 
        heteroContactRate = 0.05
        endDate = 100
        
        randDetectRate = 0
        meanTheta = numpy.array([100, 1, 1, randDetectRate, 0, heteroContactRate, 0, 0, 0, 0], numpy.float)
        times, infectedIndices, removedIndices, graph, model = runModel(meanTheta)
        detectedSet = graph.getRemovedSet()    
        self.assertEquals(len(detectedSet), 0)
        
        randDetectRate = 0.01
        meanTheta = numpy.array([100, 1, 1, randDetectRate, 0, heteroContactRate, 0, 0, 0, 0], numpy.float)
        times, infectedIndices, removedIndices, graph, model = runModel(meanTheta)
        detectedSet = graph.getRemovedSet()
        
        self.assertTrue(len(detectedSet) < 100*randDetectRate*endDate)
        
        randDetectRate = 0.001
        meanTheta = numpy.array([100, 1, 1, randDetectRate, 0, heteroContactRate, 0, 0, 0, 0], numpy.float)
        times, infectedIndices, removedIndices, graph, model = runModel(meanTheta)
        detectedSet2 = graph.getRemovedSet()
    
        self.assertTrue(abs(len(detectedSet) - len(detectedSet2)*10)<10)   
        
        #Test contact tracing 
        randDetectRate = 0
        setCtRatePerPerson = 0.1
        meanTheta = numpy.array([100, 1, 1, randDetectRate, setCtRatePerPerson, heteroContactRate, 0, 0, 0, 0], numpy.float)
        times, infectedIndices, removedIndices, graph, model = runModel(meanTheta)
        detectedSet = graph.getRemovedSet()   
        self.assertEquals(len(detectedSet), 0)
        
        randDetectRate = 0.001
        setCtRatePerPerson = 0.5
        meanTheta = numpy.array([100, 1, 1, randDetectRate, setCtRatePerPerson, heteroContactRate, 0, 0, 0, 0], numpy.float)
        times, infectedIndices, removedIndices, graph, model = runModel(meanTheta)
        detectedSet = graph.getRemovedSet()   
        self.assertTrue(len(detectedSet) > len(detectedSet2))
        
    
    @unittest.skip("")
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

