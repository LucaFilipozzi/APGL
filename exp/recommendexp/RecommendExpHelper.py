
"""
Some common functions used for the recommendation experiments 
"""
import logging
import numpy
import argparse
import scipy.sparse
from copy import copy
from apgl.util.PathDefaults import PathDefaults
from apgl.util import Util
from exp.util.MCEvaluator import MCEvaluator 
from exp.sandbox.recommendation.IterativeSoftImpute import IterativeSoftImpute 
from exp.sandbox.recommendation.IterativeMeanRating import IterativeMeanRating 
from exp.util.SparseUtils import SparseUtils 
from apgl.util.Sampling import Sampling 

class RecommendExpHelper(object):
    defaultAlgoArgs = argparse.Namespace()
    defaultAlgoArgs.runSoftImpute = False
    defaultAlgoArgs.runMean = False
    defaultAlgoArgs.rhos = numpy.linspace(0.01, 0.0, 10)     
    defaultAlgoArgs.folds = 3
    defaultAlgoArgs.k = 200
    defaultAlgoArgs.kmax = None 
    defaultAlgoArgs.svdAlg = "propack"
    defaultAlgoArgs.modelSelect = False
    defaultAlgoArgs.postProcess = False 
    
    def __init__(self, trainXIteratorFunc, testXIteratorFunc, cmdLine=None, defaultAlgoArgs = None, dirName=""):
        """ priority for default args
         - best priority: command-line value
         - middle priority: set-by-function value
         - lower priority: class value
        """
        # Parameters to choose which methods to run
        # Obtained merging default parameters from the class with those from the user
        self.algoArgs = RecommendExpHelper.newAlgoParams(defaultAlgoArgs)
        
        #Function to return iterators to the training and test matrices  
        self.trainXIteratorFunc = trainXIteratorFunc
        self.testXIteratorFunc = testXIteratorFunc
        
        #How often to print output 
        self.logStep = 10

        # basic resultsDir
        self.resultsDir = PathDefaults.getOutputDir() + "recommend/" + dirName + "/"

        # update algoParams from command line
        self.readAlgoParams(cmdLine)

    @staticmethod
    # update parameters with those from the user
    def updateParams(params, update=None):
        if update:
            for key, val in vars(update).items():
                params.__setattr__(key, val) 
    
    @staticmethod
    # merge default algoParameters from the class with those from the user
    def newAlgoParams(algoArgs=None):
        algoArgs_ = copy(RecommendExpHelper.defaultAlgoArgs)
        RecommendExpHelper.updateParams(algoArgs_, algoArgs)
        return(algoArgs_)
    
    @staticmethod
    def newAlgoParser(defaultAlgoArgs=None, add_help=False):
        # default algorithm args
        defaultAlgoArgs = RecommendExpHelper.newAlgoParams(defaultAlgoArgs)
        
        # define parser
        algoParser = argparse.ArgumentParser(description="", add_help=add_help)
        for method in ["runSoftImpute", "runMean"]:
            algoParser.add_argument("--" + method, action="store_true", default=defaultAlgoArgs.__getattribute__(method))
        algoParser.add_argument("--rhos", type=float, nargs="+", help="Regularisation parameter (default: %(default)s)", default=defaultAlgoArgs.rhos)
        algoParser.add_argument("--k", type=int, help="Max number of singular values/vectors (default: %(default)s)", default=defaultAlgoArgs.k)
        algoParser.add_argument("--kmax", type=int, help="Max number of Krylov/Lanczos vectors for PROPACK/ARPACK (default: %(default)s)", default=defaultAlgoArgs.kmax)
        algoParser.add_argument("--svdAlg", type=str, help="Algorithm to compute SVD for each iteration of soft impute (default: %(default)s)", default=defaultAlgoArgs.svdAlg)
        algoParser.add_argument("--modelSelect", action="store_true", help="Weather to do model selection on the 1st iteration (default: %(default)s)", default=defaultAlgoArgs.modelSelect)
        algoParser.add_argument("--postProcess", action="store_true", help="Weather to do model selection on the 1st iteration (default: %(default)s)", default=defaultAlgoArgs.postProcess)
        return(algoParser)
    
    # update current algoArgs with values from user and then from command line
    def readAlgoParams(self, cmdLine=None, defaultAlgoArgs=None):
        # update current algoArgs with values from the user
        self.__class__.updateParams(defaultAlgoArgs)
        
        # define parser, current values of algoArgs are used as default
        algoParser = self.__class__.newAlgoParser(self.algoArgs, True)

        # parse
        algoParser.parse_args(cmdLine, namespace=self.algoArgs)
            
    def printAlgoArgs(self):
        logging.info("Algo params")
        keys = list(vars(self.algoArgs).keys())
        keys.sort()
        for key in keys:
            logging.info("    " + str(key) + ": " + str(self.algoArgs.__getattribute__(key)))
    
    def getIterator(self):
        return self.getIteratorFunc()

    def recordResults(self, ZIter, learner, fileName):
        """
        Save results for a particular recommendation 
        """
        trainIterator = self.trainXIteratorFunc()
        testIterator = self.testXIteratorFunc()
        measures = []
        logging.debug("Computing recommendation errors")

        for Z in ZIter:
            trainX = next(trainIterator)
            testX = next(testIterator)
            
            predTrainX = learner.predictOne(Z, trainX.nonzero())
            predTestX = learner.predictOne(Z, testX.nonzero())
            
            currentMeasures = [MCEvaluator.rootMeanSqError(trainX, predTrainX)]
            currentMeasures.extend([MCEvaluator.rootMeanSqError(testX, predTestX)])
            logging.debug("Error measures: " + str(currentMeasures))
            measures.append(currentMeasures)

        measures = numpy.array(measures)
        
        logging.debug(measures)
        numpy.savez(fileName, measures)
        logging.debug("Saved file as " + fileName)

    def runExperiment(self):
        """
        Run the selected clustering experiments and save results
        """
        if self.algoArgs.runSoftImpute:
            logging.debug("Running soft impute")
            learner = IterativeSoftImpute(k=self.algoArgs.k, svdAlg=self.algoArgs.svdAlg, logStep=self.logStep, kmax=self.algoArgs.kmax, postProcess=self.algoArgs.postProcess)
            trainIterator = self.trainXIteratorFunc()
            
            #First find the largest singular value to compute lambdas 
            X = trainIterator.next() 
            X = scipy.sparse.csc_matrix(X, dtype=numpy.float)
            U, s, V = SparseUtils.svdArpack(X, 1, kmax=20)
            self.lmbdas = s[0]*self.algoArgs.rhos
            logging.debug("Largest singular value : " + str(s[0]))
            
            
            if self.algoArgs.modelSelect: 
                #Let's find the optimal lambda using the first matrix 
                logging.debug("Performing model selection")
                cvInds = Sampling.randCrossValidation(self.algoArgs.folds, X.nnz)
                errors = learner.modelSelect(X, self.lmbdas, cvInds)
                
                logging.debug("Errors = " + str(errors))
                lmbda = self.lmbdas[numpy.argmin(errors)]
            else: 
                lmbda = self.algoArgs.rhos[0]*s[0]
                
            learner.setLambda(lmbda)            
            logging.debug("Training with lambda = " + str(lmbda))
            trainIterator = self.trainXIteratorFunc()
            ZIter = learner.learnModel(trainIterator)
            
            resultsFileName = self.resultsDir + "ResultsSoftImpute_k=" + str(self.algoArgs.k) + ".npz"
            self.recordResults(ZIter, learner, resultsFileName)
            
        if self.algoArgs.runMean: 
            logging.debug("Running mean recommendation")
            
            learner = IterativeMeanRating()
            trainIterator = self.trainXIteratorFunc()
            ZIter = learner.learnModel(trainIterator)
            
            resultsFileName = self.resultsDir + "ResultsMeanRating.npz"
            self.recordResults(ZIter, learner, resultsFileName)
            
        logging.info("All done: see you around!")
