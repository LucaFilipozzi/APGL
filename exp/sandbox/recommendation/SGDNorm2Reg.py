
"""
An implementation of the matrix completion algorithm based on stochastic gradient descent minimizing the objective function:
||M-PQ||_{F on known values}^2 + \lambda (||P||_F^2 + ||Q||_F^2)
"""

import numpy
import numpy.random
import scipy.sparse
import scipy.sparse.linalg 
import scipy.linalg
from exp.util.MCEvaluator import MCEvaluator 
from apgl.util.Util import Util 
import exp.util.SparseUtils as ExpSU
import logging
import copy

class SGDNorm2Reg(object): 
    def __init__(self, k, lmbda, eps, tmax, gamma = 1):
        """
        Initialise imputing algorithm with given parameters. lambda is the 
        regularisation parameter, eps is the convergence threshold, tmax is
        the maximum number of allowed iterations, and k is the rank of the
        decomposition.
        """
        self.k = k
        self.lmbda = lmbda  
        self.eps = eps
        self.tmax = tmax
        self.gamma = gamma
        
        # other parameters
        self.t0 = 1
        
        
    def learnModel(self, X, P=None, Q=None, Z=None, storeAll=True): 
        """
        Learn the matrix completion using a sparse matrix X.
        
        :param storeAll: Store and return a list of intermediate solutions P, Q
        
        When no initial point is given, expect the matrix to be centered
        in rows and columns. 
        """
        
        if Z == None:
            if P == None and Q == None:
                sX = X.data.std()
                sP = sQ = numpy.sqrt(sX / numpy.sqrt(self.k))
                P = numpy.random.randn(X.shape[0], self.k) * sP 
                Q = numpy.random.randn(X.shape[1], self.k) * sQ
            else:
                if P == None:
                    sX = X.data.std()
                    sQ = Q.std()
                    sP = sX / sQ / numpy.sqrt(self.k)
                    P = numpy.random.randn(X.shape[0], self.k) * sP 
                if Q == None:
                    sX = X.data.std()
                    sP = P.std()
                    sQ = sX / sP / numpy.sqrt(self.k)
                    Q = numpy.random.randn(X.shape[1], self.k) * sQ
        else:
            P,Q = Z[-1]
                    
        omega = X.nonzero()
#        tol = 10**-6
        t = 1
        
        ZList = []
        oldProw = scipy.zeros(self.k)
        
        while True: 
            oldP = P.copy()
            oldQ = Q.copy()
            
            # do one pass on known values
            logging.debug("one pass on the training matrix")
            for u,i in zip(omega[0], omega[1]):
                error = X[u,i] - P[u,:].dot(Q[i,:])
                #if error > self.eps:
                #    logging.debug(str(u) + " " + str(i) + ": " + str(error))
                grad_weight = 1.*self.gamma/(t+self.t0)
#                grad_weight = 1.self.gamma/scipy.sqrt(t+self.t0)
                oldProw[:] = P[u,:]
                P[u,:] += grad_weight * (error*Q[i,:]-self.lmbda*P[u,:])
                Q[i,:] += grad_weight * (error*oldProw-self.lmbda*Q[i,:])
                
                t += 1
                # stop due to limited time budget
                if t > self.tmax:
                    break;
                    
#            ZList.append(scipy.sparse.csr_matrix(P).dot(scipy.sparse.csr_matrix(Q).T))
            if storeAll: 
                ZList.append((P, Q))
            else: 
                Z = P, Q
            
            # stop due to no change after a bunch of gradient steps
            logging.debug("norm of DeltaP: " + str(scipy.linalg.norm(P - oldP)))
            logging.debug("norm of DeltaQ: " + str(scipy.linalg.norm(Q - oldQ)))
            if scipy.linalg.norm(P - oldP) < self.eps and scipy.linalg.norm(Q - oldQ) < self.eps:
                break;
            
            # stop due to limited time budget
            if t > self.tmax:
                break;
                
        if __debug__:
            logging.info("nb grad: " + str(t-1))

        if storeAll: 
            return ZList 
        else: 
            return [Z] 

    def predict(self, ZList, inds, i=-1):
        """
        From i-th matrix returned by learnModel, predict the values of indices
        contained in inds.
        """
        U, V = ZList[i]
        Xhat = ExpSU.SparseUtils.reconstructLowRankPQ(U, V, inds)
        return Xhat

    def predictAll(self, ZList, inds):
        """
        Make a set of predictions for a given iterator of completed matrices and
        an index list.
        """
        predXList = []
        
        for i in range(len(ZList)): 
            predXList.append(self.predict(ZList, inds, i))
            
        return predXList 

    def getMetricMethod(self): 
        return MCEvaluator.meanSqError

    def copy(self): 
        """
        Return a new copied version of this object. 
        """

        return copy.copy(self) 
        
        
