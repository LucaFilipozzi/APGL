
import logging
import sys
import numpy
from apgl.graph import *
from apgl.util import *
from exp.viroscopy.model.HIVGraph import HIVGraph
from exp.viroscopy.model.HIVEpidemicModel import HIVEpidemicModel
from exp.viroscopy.model.HIVRates import HIVRates
from exp.viroscopy.model.HIVABCParameters import HIVABCParameters
from exp.viroscopy.model.HIVVertices import HIVVertices
from exp.viroscopy.model.HIVModelUtils import HIVModelUtils
from exp.viroscopy.model.HIVGraphMetrics2 import HIVGraphMetrics2

"""
This is the epidemic model for the HIV spread in cuba. We repeat the simulation a number
of times and average the results. 
"""

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
numpy.seterr(all='raise')
numpy.random.seed(24)
numpy.set_printoptions(suppress=True, precision=4)

T = 1000.0
recordStep = 90
printStep = 10
M = 2000
numRepetitions = 10
undirected = True

outputDir = PathDefaults.getOutputDir() + "viroscopy/"

#Default Params based on real data
theta1 = [50, 1.0, 0.5, 1.0/800, 0.01, 0.05, 0.1, 38.0/1000, 30.0/1000, 170.0/1000]
theta2 = [50, 1.0, 0.5, 0.00001, 0.01, 0.05, 0.1, 38.0/1000, 30.0/1000, 170.0/1000]
theta3 = [50, 1.0, 1.0, 1.0/800, 0.01, 0.05, 0.1, 38.0/1000, 30.0/1000, 170.0/1000]
theta4 = [50, 1.0, 0.5, 1.0/800, 0.0001, 0.05, 0.1, 38.0/1000, 30.0/1000, 170.0/1000]
theta1 = [50, 1.0, 0.5, 1.0/800, 0.01, 0.05, 0.5, 38.0/1000, 30.0/1000, 170.0/1000]

theta = theta4

thetaFileName = outputDir + "thetaReal.pkl"
Util.savePickle(theta, thetaFileName)

for j in range(numRepetitions):
    graph = HIVGraph(M, undirected)
    logging.info("Created graph: " + str(graph))

    alpha = 2
    zeroVal = 0.9
    p = Util.powerLawProbs(alpha, zeroVal)
    hiddenDegSeq = Util.randomChoice(p, graph.getNumVertices())

    rates = HIVRates(graph, hiddenDegSeq)
    model = HIVEpidemicModel(graph, rates)
    model.setT(T)
    model.setRecordStep(recordStep)
    model.setPrintStep(printStep)

    params = HIVABCParameters(theta)
    paramFuncs = params.getParamFuncs()

    for i in range(len(theta)):
        paramFuncs[i](theta[i])

    times, infectedIndices, removedIndices, graph = model.simulate(True)
    graphFileName = outputDir + "epidemicGraph" + str(j)
    graph.save(graphFileName)

    evolutionFileName = outputDir + "epidemicEvolution"  + str(j) + ".pkl"
    Util.savePickle((infectedIndices, removedIndices, times), evolutionFileName)

