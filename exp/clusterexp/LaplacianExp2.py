"""
Compare eigen-updating, exact eigenvalues and the Nystrom method. 
"""

import sys 
import logging
import numpy
import scipy 
import itertools 
import copy
import matplotlib.pyplot as plt 
from apgl.graph import *
from apgl.util.PathDefaults import PathDefaults
from apgl.graph.GraphUtils import GraphUtils
from apgl.util.Util import Util 
from exp.clusterexp.BoundGraphIterator import BoundGraphIterator 
from exp.sandbox.Nystrom import Nystrom 
from exp.sandbox.EigenUpdater import EigenUpdater 

numpy.random.seed(21)
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
numpy.set_printoptions(suppress=True, linewidth=200, precision=3)
       

numGraphs = 10 
k = 3
nystromN = 250
i = 0 

iterator = BoundGraphIterator(changeEdges=1, numGraphs=numGraphs, numClusterVertices=100, p=0.1)

def eigenUpdate(L1, L2, omega, Q, k): 
    """
    Find the eigen-update between two matrices L1 (with eigenvalues omega, and 
    eigenvectors Q), and L2.  
    """
    deltaL = L2 - L1 
    deltaL.prune()
    inds = numpy.unique(deltaL.nonzero()[0]) 
    #print(inds)
    
    if len(inds) > 0:
        Y1 = deltaL[:, inds]
        Y1 = numpy.array(Y1.todense())
        Y1[inds, :] = Y1[inds, :]/2
        
        Y2 = numpy.zeros((L1.shape[0], inds.shape[0]))
        Y2[(inds, numpy.arange(inds.shape[0]))] = 1
        
        omega, Q = EigenUpdater.eigenAdd2(omega, Q, Y1, Y2, min(k, L1.shape[0]))
    
    return omega, Q


def computeBound(A, omega, Q, omega2, Q2, k):
    """
    Compute the perturbation bound on L using exact eigenvalues/vectors omega and 
    Q and approximate ones omega2, Q. 
    """
    A = A.todense()
    M = Q2.T.dot(A).dot(Q2)
    R = A.dot(Q2) - Q2.dot(M)
    
    normR = numpy.linalg.norm(R)
    #print("normR=" + str(normR))    
    
    lmbda, U = numpy.linalg.eig(M)
    
    L2 = omega[k:]
    
    delta = float("inf")
    
    print(lmbda)
    print(L2)
    
    for i in lmbda: 
        for j in L2: 
            
            if abs(i-j) < delta: 
                delta = abs(i-j)
                
    #print("delta="+str(delta))
    
    return normR/delta 

numMethods = 2 
errors = numpy.zeros((numGraphs, numMethods)) 

for W in iterator: 
    L = GraphUtils.shiftLaplacian(W)
    
    if i == 0: 
        lastL = L
        lastOmega, lastQ = numpy.linalg.eig(L.todense())
        inds = numpy.flipud(numpy.argsort(lastOmega))
        lastOmega, lastQ = lastOmega[inds], lastQ[:, inds]
    
    #Compute exact eigenvalues 
    omega, Q = numpy.linalg.eig(L.todense())
    inds = numpy.flipud(numpy.argsort(omega))    
    omega, Q = omega[inds], Q[:, inds]
    print("omega=" + str(omega))
    omegak, Qk = omega[inds[0:k]], Q[:, inds[0:k]]
    
    
    #Nystrom method 
    print("Running Nystrom")
    omega2, Q2 = Nystrom.eigpsd(L, nystromN)
    inds = numpy.flipud(numpy.argsort(omega2))
    omega2, Q2 = omega2[inds], Q2[:, inds]
    print("omega2=" + str(omega2))
    omega2k, Q2k = omega2[inds[0:k]], Q2[:, inds[0:k]]
    
    errors[i, 0] = computeBound(L, omega, Q, omega2k, Q2k, k)
    
    #Incremental updates 
    omega3, Q3 = eigenUpdate(lastL, L, lastOmega, lastQ, k)
    inds = numpy.flipud(numpy.argsort(omega3))
    omega3, Q3 = omega3[inds], Q3[:, inds]
    omega3k, Q3k = omega3[inds[0:k]], Q3[:, inds[0:k]]
    
    errors[i, 1] = computeBound(L, omega, Q, omega3k, Q3k, k)
    
    i += 1 
    
print(errors)