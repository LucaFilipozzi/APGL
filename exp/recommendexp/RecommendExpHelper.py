
"""
Some common functions used for the recommendation experiments 
"""
import logging
import numpy
import argparse
import scipy.sparse
import time 
from copy import copy
from apgl.util.PathDefaults import PathDefaults
from apgl.util import Util
from exp.util.MCEvaluator import MCEvaluator 
from exp.sandbox.recommendation.IterativeSoftImpute import IterativeSoftImpute 
from exp.sandbox.recommendation.IterativeMeanRating import IterativeMeanRating 
from exp.util.SparseUtils import SparseUtils 
from apgl.util.Sampling import Sampling 
from apgl.util.FileLock import FileLock 
from exp.recommendexp.CenterMatrixIterator import CenterMatrixIterator

class RecommendExpHelper(object):
    defaultAlgoArgs = argparse.Namespace()
    defaultAlgoArgs.runSoftImpute = False
    defaultAlgoArgs.runMean = False
    defaultAlgoArgs.rhos = numpy.linspace(0.5, 0.0, 10)     
    defaultAlgoArgs.folds = 3
    defaultAlgoArgs.ks = numpy.array(2**numpy.arange(3, 7, 0.5), numpy.int)
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
        algoParser.add_argument("--ks", type=int, nargs="+", help="Max number of singular values/vectors (default: %(default)s)", default=defaultAlgoArgs.ks)
        algoParser.add_argument("--kmax", type=int, help="Max number of Krylov/Lanczos vectors for PROPACK/ARPACK (default: %(default)s)", default=defaultAlgoArgs.kmax)
        algoParser.add_argument("--svdAlg", type=str, help="Algorithm to compute SVD for each iteration of soft impute (default: %(default)s)", default=defaultAlgoArgs.svdAlg)
        algoParser.add_argument("--modelSelect", action="store_true", help="Weather to do model selection on the 1st iteration (default: %(default)s)", default=defaultAlgoArgs.modelSelect)
        algoParser.add_argument("--postProcess", action="store_true", help="Weather to do post processing for soft impute (default: %(default)s)", default=defaultAlgoArgs.postProcess)
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
            
    def getTrainIterator(self): 
        """
        Return the training iterator wrapped in an iterator which centers the rows. 
        Note that the original iterator must generate *new* matrices on repeated 
        calls since the original ones are modified by centering. 
        """
        return CenterMatrixIterator(self.trainXIteratorFunc())            
            
    def recordResults(self, ZIter, learner, fileName):
        """
        Save results for a particular recommendation 
        """
        trainIterator = self.getTrainIterator()
        testIterator = self.testXIteratorFunc()
        measures = []
        metadata = []
        logging.debug("Computing recommendation errors")
        
        while True: 
            try: 
                start = time.time()
                Z = next(ZIter) 
                learnTime = time.time()-start 
            except StopIteration: 
                break 
            
            trainX = next(trainIterator)
            predTrainX = learner.predictOne(Z, trainX.nonzero())  
            predTrainX = trainIterator.uncenter(predTrainX)
            trainX = trainIterator.uncenter(trainX)
            
            testX = next(testIterator)
            predTestX = learner.predictOne(Z, testX.nonzero())
            predTestX = trainIterator.uncenter(predTestX)
            
            currentMeasures = [MCEvaluator.rootMeanSqError(trainX, predTrainX)]
            currentMeasures.extend([MCEvaluator.rootMeanSqError(testX, predTestX), MCEvaluator.meanAbsError(testX, predTestX)])
            logging.debug("Error measures: " + str(currentMeasures))
            logging.debug("Standard deviation of test set " + str(testX.data.std()))
            measures.append(currentMeasures)
            
            #Store some metadata about the learning process 
            metadata.append([Z[0].shape[1], learner.getRho(), learnTime])

        measures = numpy.array(measures)
        metadata = numpy.array(metadata)
        
        logging.debug(measures)
        numpy.savez(fileName, measures, metadata)
        logging.debug("Saved file as " + fileName)



    def runExperiment(self):
        """
        Run the selected clustering experiments and save results
        """
        if self.algoArgs.runSoftImpute:
            logging.debug("Running soft impute")
            
            resultsFileName = self.resultsDir + "ResultsSoftImpute_alg=" + self.algoArgs.svdAlg +  ".npz"
            fileLock = FileLock(resultsFileName)  
            
            if not fileLock.isLocked() and not fileLock.fileExists(): 
                fileLock.lock()
                
                learner = IterativeSoftImpute(svdAlg=self.algoArgs.svdAlg, logStep=self.logStep, kmax=self.algoArgs.kmax, postProcess=self.algoArgs.postProcess)
                
                if self.algoArgs.modelSelect: 
                    trainIterator = self.getTrainIterator()
                    #Let's find the optimal lambda using the first matrix 
                    X = trainIterator.next() 
                    X = scipy.sparse.csc_matrix(X, dtype=numpy.float)
                    logging.debug("Performing model selection")
                    cvInds = Sampling.randCrossValidation(self.algoArgs.folds, X.nnz)
                    meanErrors, stdErrors = learner.modelSelect(X, self.algoArgs.rhos, self.algoArgs.ks, cvInds)
                    
                    logging.debug("Mean errors = " + str(meanErrors))
                    logging.debug("Std errors = " + str(stdErrors))
                    rho = self.algoArgs.rhos[numpy.unravel_index(numpy.argmin(meanErrors), meanErrors.shape)[0]]
                    k = self.algoArgs.ks[numpy.unravel_index(numpy.argmin(meanErrors), meanErrors.shape)[1]]
                else: 
                    rho = self.algoArgs.rhos[0]
                    k = self.algoArgs.ks[0]
                    
                learner.setK(k)            
                logging.debug("Training with k = " + str(k))                    
                    
                learner.setRho(rho)            
                logging.debug("Training with rho = " + str(rho))
                trainIterator = self.getTrainIterator()
                ZIter = learner.learnModel(trainIterator)
                
                self.recordResults(ZIter, learner, resultsFileName)
                fileLock.unlock()
            else: 
                logging.debug("File is locked or already computed: " + resultsFileName)
            
        if self.algoArgs.runMean: 
            logging.debug("Running mean recommendation")
            
            learner = IterativeMeanRating()
            trainIterator = self.getTrainIterator()
            ZIter = learner.learnModel(trainIterator)
            
            resultsFileName = self.resultsDir + "ResultsMeanRating.npz"
            self.recordResults(ZIter, learner, resultsFileName)
            
        logging.info("All done: see you around!")
