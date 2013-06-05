from cython.operator cimport dereference as deref, preincrement as inc 
import cython
import struct
import numpy 
cimport numpy
import scipy.sparse 
numpy.import_array()

cdef extern from "SparseUtilsCython.cpp": 
    void partialReconstructValsPQCpp(int*, int*, double*, double*, double*, int, int) 

class SparseUtilsCython(object): 
    """
    Some Cythonised functions for sparse matrices. 
    """
    
    @staticmethod 
    def partialReconstructVals(numpy.ndarray[numpy.long_t, ndim=1] rowInds, numpy.ndarray[numpy.long_t, ndim=1] colInds, numpy.ndarray[numpy.float_t, ndim=2] U, numpy.ndarray[numpy.float_t, ndim=1] s, numpy.ndarray[numpy.float_t, ndim=2] V): 
        """
        Given an array of unique indices omega, partially reconstruct a matrix 
        using its SVD. 
        """ 
        cdef unsigned int i
        cdef unsigned int j 
        cdef unsigned int k
        cdef numpy.ndarray[numpy.float_t, ndim=1, mode="c"] values = numpy.zeros(rowInds.shape[0], numpy.float)
        
        for i in range(rowInds.shape[0]):
            j = rowInds[i]
            k = colInds[i]
            
            values[i] = (U[j, :]*s).dot(V[k,:])            
            
        return values
        
    @staticmethod 
    @cython.boundscheck(False)
    def partialReconstructValsPQ(numpy.ndarray[numpy.long_t, ndim=1] rowInds, numpy.ndarray[numpy.long_t, ndim=1] colInds, numpy.ndarray[numpy.float_t, ndim=2, mode="c"] P, numpy.ndarray[numpy.float_t, ndim=2, mode="c"] Q): 
        """
        Given an array of unique indices inds, partially reconstruct $P*Q^T$.
        """ 
        cdef unsigned int i
        cdef unsigned int j 
        cdef unsigned int k
        cdef numpy.ndarray[numpy.float_t, ndim=1, mode="c"] values = numpy.zeros(rowInds.shape[0], numpy.float)
        
        for i in range(rowInds.shape[0]):
            j = rowInds[i]
            k = colInds[i]

            values[i] = numpy.inner(P[j, :], Q[k, :])            
            
        return values
        
    @staticmethod 
    def partialReconstructValsPQ2(numpy.ndarray[int, ndim=1] rowInds, numpy.ndarray[int, ndim=1] colInds, numpy.ndarray[double, ndim=2, mode="c"] P, numpy.ndarray[double, ndim=2, mode="c"] Q): 
        """
        Given an array of unique indices inds, partially reconstruct $P*Q^T$.
        """ 
        cdef numpy.ndarray[double, ndim=1, mode="c"] values = numpy.zeros(rowInds.shape[0])
        partialReconstructValsPQCpp(&rowInds[0], &colInds[0], &P[0,0], &Q[0,0], &values[0], rowInds.shape[0], P.shape[0])          
            
        return values        
        
        
    @staticmethod
    def partialOuterProduct(numpy.ndarray[numpy.long_t, ndim=1] rowInds, numpy.ndarray[numpy.long_t, ndim=1] colInds, numpy.ndarray[numpy.float_t, ndim=1] u, numpy.ndarray[numpy.float_t, ndim=1] v):
        """
        Given an array of unique indices omega, partially reconstruct a matrix 
        using two vectors u and v 
        """ 
        cdef unsigned int i
        cdef unsigned int j 
        cdef unsigned int k
        cdef numpy.ndarray[numpy.float_t, ndim=1, mode="c"] values = numpy.zeros(rowInds.shape[0], numpy.float)
        
        for i in range(rowInds.shape[0]):
            j = rowInds[i]
            k = colInds[i]
            
            values[i] = u[j]*v[k]            
            
        return values    
        
    @staticmethod 
    def partialReconstruct(omega, U, s, V): 
        """
        Given an array of unique indices omega, partially reconstruct a matrix 
        using its SVD. The returned matrix is a scipy csc_matrix. 
        """ 
        from sppy import csarray 
        
        X = csarray((U.shape[0], V.shape[0]), storageType="colMajor")
        X.reserve(omega[0].shape[0])
        for i in range(omega[0].shape[0]):
            j = omega[0][i]
            k = omega[1][i]
            
            X[j, k] = (U[j, :]*s).dot(V[k,:])            
            
        X.compress()
        return X.toScipyCsc()
        
    @staticmethod 
    def partialReconstruct2(omega, U, s, V): 
        """
        Given an array of unique indices omega, partially reconstruct a matrix 
        using its SVD. The returned matrix is a scipy csc_matrix. Uses Cython 
        to speed up the reconstruction. 
        """ 
        
        vals = SparseUtilsCython.partialReconstructVals(omega[0], omega[1], U, s, V)
        inds = numpy.c_[omega[0], omega[1]].T
        X = scipy.sparse.csc_matrix((vals, inds), shape=(U.shape[0], V.shape[0]))
        
        return X 
    
    @staticmethod 
    def partialReconstructPQ(omega, P, Q): 
        """
        Given an array of unique indices inds, partially reconstruct $P*Q^T$.
        The returned matrix is a scipy csc_matrix.
        """ 
        
        vals = SparseUtilsCython.partialReconstructValsPQ(omega[0], omega[1], P, Q)
        inds = numpy.c_[omega[0], omega[1]].T
        X = scipy.sparse.csc_matrix((vals, inds), shape=(P.shape[0], Q.shape[0]))
        
        return X 
        