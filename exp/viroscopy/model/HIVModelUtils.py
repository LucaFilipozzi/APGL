

"""
Keep some default parameters for the epidemic model. 
"""
import numpy 
import logging 
from apgl.util import Util 
from apgl.util import PathDefaults 
from apgl.graph.GraphStatistics import GraphStatistics
from exp.viroscopy.model.HIVGraph import HIVGraph
from exp.viroscopy.model.HIVEpidemicModel import HIVEpidemicModel
from exp.viroscopy.model.HIVRates import HIVRates
from exp.viroscopy.model.HIVVertices import HIVVertices
from exp.viroscopy.HIVGraphReader import HIVGraphReader, CsvConverters

class HIVModelUtils(object):
    def __init__(self): 
        pass 
    
    @staticmethod
    def estimatedRealTheta():
        """
        This is taken from simulated runs using the real data 
        """
        theta = numpy.array([ 500,  0.5, 0.5, 0.5, 0.2, 0.2, 500, 0.5, 0.5, 0.1, 0.1, 0.1])
        sigmaTheta = theta*2
        return theta, sigmaTheta 
    
    @staticmethod
    def toyTheta(): 
        theta = numpy.array([100, 0.5, 1.0, 0.5, 1.0/800, 0.01, 200, 0.1, 0.2, 38.0/1000, 30.0/1000, 170.0/1000])
        sigmaTheta = theta/2
        return theta, sigmaTheta 
        
    @staticmethod 
    def toySimulationParams(loadTarget=True): 
        
        if loadTarget: 
            resultsDir = PathDefaults.getOutputDir() + "viroscopy/toy/" 
            graphFile = resultsDir + "ToyEpidemicGraph0"
            targetGraph = HIVGraph.load(graphFile)        
        
        startDate = 0.0        
        endDate = 1000.0
        recordStep = 100
        M = 5000
        
        if loadTarget: 
            return startDate, endDate, recordStep, M, targetGraph
        else: 
            return startDate, endDate, recordStep, M
        
    @staticmethod 
    def realSimulationParams(): 
        hivReader = HIVGraphReader()
        targetGraph = hivReader.readSimulationHIVGraph()
        
        numRecordSteps = 10 
        #Note that 5% of the population is bi 
        M = targetGraph.size * 4
        #This needs to be from 1986 to 2004 
        startDate = CsvConverters.dateConv("01/01/1986")
        endDates = [CsvConverters.dateConv("01/01/1987"), CsvConverters.dateConv("01/01/1990"), CsvConverters.dateConv("01/01/1993"), CsvConverters.dateConv("01/01/1996"), CsvConverters.dateConv("01/01/1999")]
        endDates = [float(i) for i in endDates]
        
        return float(startDate), endDates, numRecordSteps, M, targetGraph
    
    @staticmethod     
    def simulate(theta, startDate, endDate, recordStep, M, graphMetrics=None): 
        undirected = True
        graph = HIVGraph(M, undirected)
        logging.debug("Created graph: " + str(graph))
    
        alpha = 2
        zeroVal = 0.9
        p = Util.powerLawProbs(alpha, zeroVal)
        hiddenDegSeq = Util.randomChoice(p, graph.getNumVertices())
    
        rates = HIVRates(graph, hiddenDegSeq)
        model = HIVEpidemicModel(graph, rates, endDate, startDate, metrics=graphMetrics)
        model.setRecordStep(recordStep)
        model.setParams(theta)
        
        logging.debug("Theta = " + str(theta))
        
        return model.simulate(True)
        
    @staticmethod 
    def generateStatistics(graph, startDate, endDate, recordStep): 
        """
        For a given theta, simulate the epidemic, and then return a number of 
        relevant statistics. 
        """
        times = [] 
        removedIndices = []
        
        for t in numpy.arange(startDate, endDate+1, recordStep): 
            times.append(t)
            removedIndices.append(graph.removedIndsAt(t))

        V = graph.getVertexList().getVertices()
        
        removedArray  = numpy.array([len(x) for x in removedIndices])
        maleArray  = numpy.array([numpy.sum(V[x, HIVVertices.genderIndex]==HIVVertices.male) for x in removedIndices])
        femaleArray = numpy.array([numpy.sum(V[x, HIVVertices.genderIndex]==HIVVertices.female) for x in removedIndices])
        heteroArray = numpy.array([numpy.sum(V[x, HIVVertices.orientationIndex]==HIVVertices.hetero) for x in removedIndices])
        biArray = numpy.array([numpy.sum(V[x, HIVVertices.orientationIndex]==HIVVertices.bi) for x in removedIndices])
        randDetectArray = numpy.array([numpy.sum(V[x, HIVVertices.detectionTypeIndex]==HIVVertices.randomDetect) for x in removedIndices])
        conDetectArray = numpy.array([numpy.sum(V[x, HIVVertices.detectionTypeIndex]==HIVVertices.contactTrace) for x in removedIndices])
        
        vertexArray = numpy.c_[removedArray, maleArray, femaleArray, heteroArray, biArray, randDetectArray, conDetectArray]
        
        graphStats = GraphStatistics()
        removedGraphStats = graphStats.sequenceScalarStats(graph, removedIndices, slowStats=False)
        
        return times, vertexArray, removedGraphStats
    
    toyTestPeriod = 500 
    realTestPeriod = 365