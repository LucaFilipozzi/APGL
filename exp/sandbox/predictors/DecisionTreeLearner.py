import numpy 
from apgl.predictors.AbstractPredictor import AbstractPredictor
from apgl.graph.DictTree import DictTree


class DecisionNode(): 
    def __init__(self, trainInds, value): 
        #All nodes 
        self.value = value 
        self.trainInds = trainInds
        #Internal nodes 
        self.featureInd = None 
        self.threshold = None 
        self.error = None 
        #Used for sorting predictions 
        self.testInds = None 
        
    def getTrainInds(self): 
        return self.trainInds
        
    def getValue(self): 
        return self.value 
        
    def setError(self, error): 
        self.error = error 
        
    def setFeatureInd(self, featureInd): 
        self.featureInd = featureInd 
        
    def getFeatureInd(self): 
        return self.featureInd 
        
    def setThreshold(self, threshold): 
        self.threshold = threshold 
        
    def getThreshold(self): 
        return self.threshold
        
    def setValue(self, value): 
        self.value = value 
          
    def setTestInds(self, testInds): 
        self.testInds = testInds
        
    def getTestInds(self): 
        return self.testInds
    
    def isLeaf(self): 
        return self.error == None
        
    def __str__(self): 
        outputStr = "Size: " + str(self.trainInds.shape[0]) + ", " 
        outputStr += "featureInd: " + str(self.featureInd) + ", " 
        outputStr += "threshold: " + str(self.threshold) + ", "
        outputStr += "error: " + str(self.error) + ", "
        outputStr += "value: " + str(self.value) + " "
        return outputStr 
    

class DecisionTreeLearner(AbstractPredictor): 
    def __init__(self, criterion="mse", maxDepth=10, minSplit=30, type="class"):
        super(DecisionTreeLearner, self).__init__()
        self.maxDepth = maxDepth
        self.minSplit = minSplit
        self.criterion = criterion
        self.type = type
        
        self.maxDepths = numpy.arange(1, 10)
        self.minSplits = numpy.arange(10, 51, 10)
        
    def meanSqError(self, y1, y2): 
        """
        Given a split that results in the labels y1 \in \mathbb^n1, y2 \in \mathbb{R}^n2, 
        compute the impurity using the mean squared error. This is just computed 
        as ||y1 - 1/n1 y1^T 1 1^T||^2 + ||y2 - 1/n2 y2^T 1 1^T||^2. 
        """
        error = y1.shape[0]*y1.var() + y2.shape[0]*y2.var()  
        return error 
        
    def findBestSplit(self, X, y): 
        """
        Give a set of examples and a particular feature, find the best split 
        of the data. 
        """
        if X.shape[0] == 0: 
            raise ValueError("Cannot split on 0 examples")
        
        bestError = float("inf")   
        
        for featureInd in range(X.shape[1]): 
            x = X[:, featureInd] 
            vals = numpy.unique(x)

            for val in vals: 
                inds1 = x<val
                inds2 = x>=val
                
                error = self.meanSqError(y[inds1], y[inds2])

                if error < bestError: 
                    bestError = error 
                    bestFeatureInd = featureInd
                    bestThreshold = val 
                    bestSplitInds = (inds1, inds2)
                        
        return bestError, bestFeatureInd, bestThreshold, bestSplitInds 

    def learnModel(self, X, y):
        #Let's create a tree 

        nodeId = (0, )         
        self.tree = DictTree()
        rootNode = DecisionNode(numpy.arange(X.shape[0]), y.mean())
        self.tree.setVertex(nodeId, rootNode)
        self.recursiveSplit(X, y, nodeId)
     
    def getLeftChildId(self, nodeId): 
        leftChildId = list(nodeId)
        leftChildId.append(0)
        leftChildId = tuple(leftChildId)
        return leftChildId

    def getRightChildId(self, nodeId): 
        rightChildId = list(nodeId)
        rightChildId.append(1)
        rightChildId = tuple(rightChildId) 
        return rightChildId
   
    def recursiveSplit(self, X, y, nodeId): 
        """
        Give a sample of data and a node index, we find the best split and 
        add children to the tree accordingly. 
        """
        if len(nodeId)-1 >= self.maxDepth: 
            return 
        
        node = self.tree.getVertex(nodeId)
        tempX = X[node.getTrainInds(), :]
        tempY = y[node.getTrainInds()]

        bestError, bestFeatureInd, bestThreshold, bestSplitInds = self.findBestSplit(tempX, tempY)
    
        #The split may have 0 items in one set, so don't split 
        if bestSplitInds[0].sum() != 0 and bestSplitInds[1].sum() != 0: 
            node.setError(bestError)
            node.setFeatureInd(bestFeatureInd)
            node.setThreshold(bestThreshold)
            
            leftChildId = self.getLeftChildId(nodeId)
            rightChildId = self.getRightChildId(nodeId)

            leftChild = DecisionNode(node.getTrainInds()[bestSplitInds[0]], tempY[bestSplitInds[0]].mean())
            self.tree.addChild(nodeId, leftChildId, leftChild)
            
            rightChild = DecisionNode(node.getTrainInds()[bestSplitInds[1]], tempY[bestSplitInds[1]].mean())
            self.tree.addChild(nodeId, rightChildId, rightChild)
            
            if leftChild.getTrainInds().shape[0] >= self.minSplit: 
                self.recursiveSplit(X, y, leftChildId)
                
            if rightChild.getTrainInds().shape[0] >= self.minSplit: 
                self.recursiveSplit(X, y, rightChildId)
        
    def predict(self, X): 
        """
        Make a prediction for the set of examples given in the matrix X. 
        """
        rootId = (0,)
        y = numpy.zeros(X.shape[0])
        self.tree.getVertex(rootId).setTestInds(numpy.arange(X.shape[0]))
        self.recursivePredict(X, y, rootId)
        
        return y 
        
        
        
    def recursivePredict(self, X, y, nodeId): 
        node = self.tree.getVertex(nodeId)
        testInds = node.getTestInds()
        
        if node.isLeaf(): 
            y[testInds] == node.getValue()
        else: 
             
            leftChildId = self.getLeftChildId(nodeId)
            if self.tree.vertexExists(leftChildId):
                leftChild = self.tree.getVertex(leftChildId)
                leftChildInds = X[testInds, node.getFeatureInd()] < node.getThreshold() 
                leftChild.setTestInds(testInds[leftChildInds])
                self.recursivePredict(X, y, leftChildId)
                
            rightChildId = self.getRightChildId(nodeId)
            if self.tree.vertexExists(rightChildId): 
                rightChild = self.tree.getVertex(rightChildId)
                rightChildInds = X[testInds, node.getFeatureInd()] >= node.getThreshold()
                rightChild.setTestInds(testInds[rightChildInds])
                self.recursivePredict(X, y, rightChildId)
        
        
        
        
        
        