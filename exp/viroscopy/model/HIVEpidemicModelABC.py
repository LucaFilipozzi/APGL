"""
A script to estimate the HIV epidemic model parameters using ABC.
"""

from apgl.util import *
from exp.viroscopy.model.HIVGraph import HIVGraph
from exp.viroscopy.model.HIVABCParameters import HIVABCParameters
from exp.viroscopy.model.HIVEpidemicModel import HIVEpidemicModel
from exp.viroscopy.model.HIVRates import HIVRates
from exp.viroscopy.model.HIVModelUtils import HIVModelUtils
from exp.viroscopy.model.HIVGraphMetrics2 import HIVGraphMetrics2
from exp.viroscopy.model.HIVVertices import HIVVertices
from exp.sandbox.GraphMatch import GraphMatch
from apgl.predictors.ABCSMC import ABCSMC

import logging
import sys
import numpy
import multiprocessing

assert False, "Must run with -O flag"

FORMAT = "%(levelname)s:root:%(process)d:%(message)s"
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format=FORMAT)
numpy.set_printoptions(suppress=True, precision=4, linewidth=100)
numpy.seterr(invalid='raise')

resultsDir = PathDefaults.getOutputDir() + "viroscopy/toy/" 
graphFile = resultsDir + "ToyEpidemicGraph0"
targetGraph = HIVGraph.load(graphFile)

numTimeSteps = 10 
T, recordStep, printStep, M = HIVModelUtils.defaultSimulationParams()
startDate = 0
endDate = T

times = numpy.linspace(0, T, numTimeSteps)
epsilonArray = numpy.array([0.6, 0.5, 0.3])

def createModel(t):
    """
    The parameter t is the particle index. 
    """
    undirected = True
    graph = HIVGraph(M, undirected)
    
    alpha = 2
    zeroVal = 0.9
    p = Util.powerLawProbs(alpha, zeroVal)
    hiddenDegSeq = Util.randomChoice(p, graph.getNumVertices())
    
    featureInds= numpy.ones(graph.vlist.getNumFeatures(), numpy.bool)
    featureInds[HIVVertices.infectionTimeIndex] = False 
    featureInds[HIVVertices.hiddenDegreeIndex] = False 
    featureInds = numpy.arange(featureInds.shape[0])[featureInds]
    matcher = GraphMatch("U", featureInds=featureInds)
    graphMetrics = HIVGraphMetrics2(targetGraph, epsilonArray[t], matcher)

    rates = HIVRates(graph, hiddenDegSeq)
    model = HIVEpidemicModel(graph, rates, T=float(endDate), T0=float(startDate), metrics=graphMetrics)
    model.setRecordStep(recordStep)
    model.setPrintStep(printStep)

    return model

if len(sys.argv) > 1:
    numProcesses = int(sys.argv[1])
else: 
    numProcesses = multiprocessing.cpu_count()

posteriorSampleSize = 20
thetaLen = 10

logging.debug("Posterior sample size " + str(posteriorSampleSize))

meanTheta = HIVModelUtils.defaultTheta()
abcParams = HIVABCParameters(meanTheta, 0.5, 0.2)

abcSMC = ABCSMC(epsilonArray, createModel, abcParams)
abcSMC.setPosteriorSampleSize(posteriorSampleSize)
thetasArray = abcSMC.run()

meanTheta = numpy.mean(thetasArray, 0)
stdTheta = numpy.std(thetasArray, 0)
logging.debug(thetasArray)
logging.debug("meanTheta=" + str(meanTheta))
logging.debug("stdTheta=" + str(stdTheta))
logging.debug("realTheta=" + str(HIVModelUtils.defaultTheta()))

thetaFileName =  resultsDir + "ThetaDistSimulated.pkl"
Util.savePickle(thetasArray, thetaFileName)
