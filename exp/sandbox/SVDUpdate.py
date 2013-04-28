"""
Some code to test the SVD updating procedure
"""

import scipy
import scipy.sparse.linalg
from scipy.sparse.linalg import LinearOperator
import numpy
from apgl.util.Util import Util

numpy.set_printoptions(suppress=True, precision=3, linewidth=300)
numpy.random.seed(21)

class SVDUpdate:
    """
    A class to peform certain types of svd-decomposition updates.
    """
    def __init__(self):
        pass

    @staticmethod
    def addCols(U, s, V, B):
        """
        Find the SVD of a matrix [A, B] where  A = U diag(s) V.T. 
        """
        if U.shape[0] != B.shape[0]:
            raise ValueError("U must have same number of rows as B")
        if s.shape[0] != U.shape[1]:
            raise ValueError("Number of cols of U must be the same size as s")
        if s.shape[0] != V.shape[1]:
            raise ValueError("Number of cols of V must be the same size as s")

        m = U.shape[0]
        k = U.shape[1]
        r = B.shape[1]
        n = V.shape[0]

        C = numpy.dot(numpy.eye(m) - numpy.dot(U, U.T), B)
        Q, R = numpy.linalg.qr(C)

        rPrime = Util.rank(C)
        Q = Q[:, 0:rPrime]
        R = R[0:rPrime, :]

        D = numpy.r_[numpy.diag(s), numpy.zeros((rPrime, k))]
        E = numpy.r_[numpy.dot(U.T, B), R]

        D = numpy.c_[D, E]

        Uhat, sHat, Vhat = numpy.linalg.svd(D, full_matrices=False)
        inds = numpy.flipud(numpy.argsort(sHat))
        Uhat = Uhat[:, inds[0:k]]
        sHat = sHat[inds[0:k]]
        Vhat = Vhat[inds[0:k], :].T

        #The best rank k approximation of [A, B]
        Utilde = numpy.dot(numpy.c_[U, Q], Uhat)
        Stilde = numpy.diag(sHat)

        G1 = numpy.r_[V, numpy.zeros((r, k))]
        G2 = numpy.r_[numpy.zeros((n ,r)), numpy.eye(r)]
        Vtilde = numpy.dot(numpy.c_[G1, G2], Vhat)

        return Utilde, Stilde, Vtilde
      
    @staticmethod
    def addCols2(U, s, V, B):
        """
        Find the SVD of a matrix [A, B] where  A = U diag(s) V.T. 
        """
        if U.shape[0] != B.shape[0]:
            raise ValueError("U must have same number of rows as B")
        if s.shape[0] != U.shape[1]:
            raise ValueError("Number of cols of U must be the same size as s")
        if s.shape[0] != V.shape[1]:
            raise ValueError("Number of cols of V must be the same size as s")

        m = U.shape[0]
        k = U.shape[1]
        r = B.shape[1]
        n = V.shape[0]

        C = numpy.dot(numpy.eye(m) - numpy.dot(U, U.T), B)
        Ubar, sBar, Vbar = numpy.linalg.svd(C, full_matrices=False)
        inds = numpy.flipud(numpy.argsort(sBar))
        Ubar = Ubar[:, inds[0:k]]
        sBar = sBar[inds[0:k]]
        Vbar = Vbar[inds[0:k], :].T

        rPrime = Ubar.shape[1]

        D = numpy.r_[numpy.diag(s), numpy.zeros((rPrime, k))]
        E = numpy.r_[numpy.dot(U.T, B), numpy.diag(sBar).dot(Vbar.T)]

        D = numpy.c_[D, E]

        Uhat, sHat, Vhat = numpy.linalg.svd(D, full_matrices=False)
        inds = numpy.flipud(numpy.argsort(sHat))
        Uhat = Uhat[:, inds[0:k]]
        sHat = sHat[inds[0:k]]
        Vhat = Vhat[inds[0:k], :].T

        #The best rank k approximation of [A, B]
        Utilde = numpy.dot(numpy.c_[U, Ubar], Uhat)
        Stilde = numpy.diag(sHat)

        G1 = numpy.r_[V, numpy.zeros((r, k))]
        G2 = numpy.r_[numpy.zeros((n ,r)), numpy.eye(r)]
        Vtilde = numpy.dot(numpy.c_[G1, G2], Vhat)

        return Utilde, Stilde, Vtilde
    
    
    @staticmethod
    def _addSparseWrapp(f, U, s, V, X, k=10):
        m,n = X.shape
        if m > n:
            return f(U, s, V, X, k)
        else:
            U2, s2, V2 = f(V, s, U, X.T, k)
            return V2, s2, U2
            
    
    @staticmethod
    def addSparse(U, s, V, X, k=10):
        """
        Find the rank-k best SVD-decomposition of a matrix A = U s V.T + X in
        which X is sparse and C = U s V.T is a low rank matrix.
        
        Explicitly compute C.    
        """
        return SVDUpdate._addSparseWrapp(SVDUpdate._addSparse, U, s, V, X, k)

        
    @staticmethod
    def _addSparse(U, s, V, X, k=10):
        A = (U*s).dot(V.T) + X.todense()
        A = scipy.sparse.csc_matrix(A)
        U2, s2, V2T = scipy.sparse.linalg.svds(A, k=k)
        return U2, s2, V2T.T

    @staticmethod
    def addSparseArpack(U, s, V, X, k=10):
        """
        Find the rank-k best SVD-decomposition of a matrix A = U s V.T + X in
        which X is sparse and C = U s V.T is a low rank matrix.
        
        Use Arpack facilities to quickly obtain the decomposition when the
        matrix vector product A x can be computed in less than O(mn).    
        """
        return SVDUpdate._addSparseWrapp(SVDUpdate._addSparseArpack, U, s, V, X, k)

        
    @staticmethod
    def _addSparseArpack(U, s, V, X, k=10):
        # based on scipy.sparse.linalg.svds source code (abcebd5913c323b796379ea7815edc6a1f004d6a)
        m, n = X.shape
        Us = U*s

        def matvec_AH_A(x):
            Ax = Us.dot(V.T.dot(x)) + X.dot(x)
            return V.dot(Us.T.dot(Ax)) + X.T.dot(Ax)

        AH_A = LinearOperator(matvec=matvec_AH_A, shape=(n, n), dtype=X.dtype)

        eigvals, eigvec = scipy.sparse.linalg.eigsh(AH_A, k=k)
        s2 = scipy.sqrt(eigvals)
        V2 = eigvec
        U2 = (Us.dot(V.T.dot(V2)) + X.dot(V2)) / s2
        return U2, s2, V2

    @staticmethod
    def addSparseProjected(U, s, V, X, k=10):
        """
        Find the rank-k best SVD-decomposition of a matrix A = U s V.T + X in
        which X is sparse and C = U s V.T is a low rank matrix.
        
        Use the same idea as for clustering updata    
        """
        return SVDUpdate._addSparseWrapp(SVDUpdate._addSparseProjected, U, s, V, X, k)
    
    @staticmethod
    def _addSparseProjected(U, s, V, X, k=10):
        kk = len(s)
        m, n = X.shape
        
        # decompose X as X1 X2.T   
        colSums = numpy.array(abs(X).sum(1)).ravel()
        inds = scipy.unique(X.nonzero()[1])
        if len(inds) > 0:
            X1 = numpy.array(X[:,inds].todense())
            X2 = numpy.zeros((n, len(inds)))
            X2[(inds, numpy.arange(len(inds)))] = 1
        
        # svd decomposition of projections of X1 and X2
        UTX1 = U.T.dot(X1)
        Q1, R1 = numpy.linalg.qr(X1-U.dot(UTX1))
        k1 = Q1.shape[1]
        VTX2 = V.T.dot(X2)
        Q2, R2 = numpy.linalg.qr(X2-V.dot(VTX2))
        k2 = Q2.shape[1]
        
        # construct W
        W = scipy.zeros((kk+k1, kk+k2))
        W[(numpy.arange(k), numpy.arange(k))] = s
        W[:kk,:kk] += UTX1.dot(VTX2.T)
        W[:kk,kk:] = UTX1.dot(R2.T)
        W[kk:,:kk] = R1.dot(VTX2.T)
        W[kk:,kk:] = R1.dot(R2.T)
        
        # svd of W
        W = scipy.sparse.csc_matrix(W)
        UW, sW, VWT = scipy.sparse.linalg.svds(W, k)
        
        # reconstruct the correct decomposition
        Ures = numpy.c_[U, Q1].dot(UW)
        sres = sW
        Vres = numpy.c_[V, Q2].dot(VWT.T)
        
        return Ures, sres, Vres 
        
    @staticmethod
    def addSparseRSVD(U, s, V, X, k=10, kX=None, kRand=None, q=None):
        """
        Find *an approximation* of the rank-k best SVD-decomposition of a matrix
        A = U s V.T + X in which X is sparse and C = U s V.T is a low rank
        matrix.
        
        Take inspiration from Random SVD strategy.
        kX: number of directions to take in X. 
        kRand: number of random projections. 
        """
        def f(U, s, V, X, k):
            return SVDUpdate._addSparseRSVD(U, s, V, X, k, kX, kRand, q)
        return SVDUpdate._addSparseWrapp(f, U, s, V, X, k)

    @staticmethod
    def _addSparseRSVD(U, s, V, X, k=10, kX=None, kRand=None, q=None):
        if kX==None:
            kX=k
        if kRand==None:
            kRand=k
        if q==None:
            q=1

        m, n = X.shape
        Us = U*s

        UX, sX, VXT = scipy.sparse.linalg.svds(X, kX)
        omega = numpy.c_[V, VXT.T, numpy.random.randn(n, kRand)]
        
        def rMultA(x):
            return Us.dot(V.T.dot(x)) + X.dot(x)
        def rMultAT(x):
            return V.dot(Us.T.dot(x)) + X.T.dot(x)
        
        Y = rMultA(omega)
        for i in range(q): 
            Y = rMultAT(Y)
            Y = rMultA(Y)
        
        Q, R = numpy.linalg.qr(Y)
        B = rMultAT(Q).T   
        U, s, VT = numpy.linalg.svd(B, full_matrices=False)
        U, s, V = Util.indSvd(U, s, VT, numpy.flipud(numpy.argsort(s))[:k])
        U = Q.dot(U)
        
        return U, s, V 
