import numpy 
import scipy.sparse 
import gc 
from exp.util.GeneralLinearOperator import GeneralLinearOperator
from apgl.util.Parameter import Parameter 

class RandomisedSVD(object): 
    """
    Compute the randomised SVD using the algorithm on page 9 of Halko et al., 
    Finding Structure with randomness: stochastic algorithms for constructing 
    approximate matrix decompositions, 2009. 
    """
    def ___init__(self): 
        pass
    
    @staticmethod
    def svd(X, k, p=10, q=2, omega=None): 
        """
        Compute the SVD of a sparse or dense matrix X, finding the first k 
        singular vectors/values, using exponent q. Returns the left and right singular 
        vectors, and the singular values. The resulting matrix can be approximated 
        using X ~ U s V.T. 
        
        :param X: A matrix or GeneralLinearOperator 
        
        :param k: The number of singular values and random projections
        
        :param p: The oversampling parameter 
        
        :param q: The exponent for the projections.
        
        :param omega: An initial matrix to perform random projections onto with at least k columns 
        """
        Parameter.checkInt(k, 1, float("inf"))
        Parameter.checkInt(p, 0, float("inf"))
        Parameter.checkInt(q, 0, float("inf"))        

        if scipy.sparse.isspmatrix(X) or type(X) == numpy.ndarray: 
            L = GeneralLinearOperator.asLinearOperator(X) 
        else: 
            L = X
        
        n = L.shape[1]
        if omega == None: 
            omega = numpy.random.randn(n, k+p)
        else: 
            omega = numpy.c_[omega, numpy.random.randn(n, p+k - omega.shape[1])]
        
        Y = L.matmat(omega)
        del omega 

        for i in range(q):
            Y = L.rmatmat(Y)
            gc.collect() 
            Y = L.matmat(Y)
            gc.collect() 
        
        Q, R = numpy.linalg.qr(Y)
        
        del Y 
        del R 
        gc.collect() 
        
        B = L.rmatmat(Q).T
        U, s, V = numpy.linalg.svd(B, full_matrices=False)
        del B 
        V = V.T
        U = Q.dot(U)

        U = U[:, 0:k]
        s = s[0:k]
        V = V[:, 0:k]        
        
        return U, s, V 
        
    def svd2(A, lmbda): 
        """
        Compute the randomised SVD with error estimate up to a tolerance of 
        lmbda, i.e. ||A - QQ^TA||_2 <= lmbda. 
        """ 
        Parameter.checkFloat(lmbda, 0.0, float("inf"))
        r = 10 

        m, n = A.shape        
        Omega = numpy.random.randn(n, k)
        Y = A.dot(Omega)
        
        Q = numpy.zeros((m, 0))
        
        i = 0 

        while numpy.max((Y**2).sum(0)) > eps/(10*numpy.sqrt(2/numpy.pi)): 
            Y[:, i] = Y[:, i] - Q.dot(Q.T).dot(Y[:, i])
            q = Y[:, i]
            Q = numpy.c_[Q, q]
            
            omega = numpy.random.randn(n) 
        
        