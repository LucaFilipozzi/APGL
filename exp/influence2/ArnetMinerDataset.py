import os 
import numpy 
import logging 
import difflib 
import re 
import sklearn.feature_extraction.text as text 
import gc
import scipy.sparse
import igraph
import array
import itertools 
import gensim.matutils
import sys 
import scipy.io
import sklearn.preprocessing 
from gensim.models.ldamodel import LdaModel
from gensim.models.lsimodel import LsiModel
import gensim.similarities
from apgl.util.Util import Util 
from apgl.util.PathDefaults import PathDefaults 
from exp.sandbox.RandomisedSVD import RandomisedSVD
from exp.util.IdIndexer import IdIndexer
from collections import Counter, OrderedDict 
from exp.util.PorterTokeniser import PorterTokeniser
from exp.util.SparseUtils import SparseUtils


class ArnetMinerDataset(object): 
    """
    We process the ArnetMinerDataset into two graphs - a coauthor and an 
    abstract similarity. The output is two graphs - collaboration and 
    abstract similarity. 
    """    
    def __init__(self, k=50, additionalFields=[]):
        numpy.random.seed(21)
        self.dataDir = PathDefaults.getDataDir() + "dblpCitation/" 
        
        self.fields = ["Boosting", "Computer Vision", "Cryptography", "Data Mining"]
        self.fields.extend(["Information Extraction", "Intelligent Agents", "Machine Learning"])
        self.fields.extend(["Natural Language Processing", "Neural Networks", "Ontology Alignment"])
        self.fields.extend(["Planning", "Semantic Web", "Support Vector Machine"])    
        self.fields.extend(additionalFields)        
        
        #self.dataFilename = self.dataDir + "DBLP-citation-Feb21.txt" 
        #self.dataFilename = self.dataDir + "DBLP-citation-7000000.txt" 
        self.dataFilename = self.dataDir + "DBLP-citation-100000.txt"
        
        self.baseDir = PathDefaults.getDataDir() + "reputation/"
        self.docTermMatrixFilename = self.baseDir + "termDocMatrix"        
        self.authorListFilename = self.baseDir + "authorList.pkl"
        self.vectoriserFilename = self.baseDir + "vectoriser.pkl"   
        self.ldaModelFilename = self.baseDir + "ldaModel.pkl"
        self.lsiModelFilename = self.baseDir + "lsiModel.pkl"
        
        self.stepSize = 1000000    
        self.numLines = 15192085
        self.matchCutoff = 0.90   
        
        #Params for finding relevant authors
        self.similarityCutoff = 0.3
        self.maxRelevantAuthors = 500

        #Params for vectoriser 
        self.numFeatures = None
        self.binary = True 
        self.sublinearTf = False
        self.minDf = 2 
        self.ngram = 2
        
        #params for LSI        
        self.k = k
        self.q = 3
        self.p = 30 
        self.ks = [50, 100, 150, 200, 250]
        self.sampleDocs = 1000000
        
        self.overwrite = False
        self.overwriteVectoriser = False
        self.overwriteModel = False
        
        self.chunksize = 5000
        self.tfidf = True 
        
        #Load the complete set of experts 
        self.expertsDict = {} 
        for field in self.fields: 
            expertsFile = open(self.getResultsDir(field) + "experts.txt")
            self.expertsDict[field] = expertsFile.readlines()
            self.expertsDict[field] = set([x.strip() for x in self.expertsDict[field]])
            expertsFile.close()
            
        #Create a set of experts we use for training 
        self.trainExpertDict = {}
        self.testExpertDict = {}        
        
        for field in self.fields: 
            inds  = numpy.random.permutation(len(self.expertsDict[field]))            
            
            numTrainInds = int(0.5*len(self.expertsDict[field])) 
            trainInds = inds[0:numTrainInds]
            self.trainExpertDict[field] = list(numpy.array(list(self.expertsDict[field]))[trainInds]) 
            
            testInds = inds[numTrainInds:]
            self.testExpertDict[field] = list(numpy.array(list(self.expertsDict[field]))[testInds]) 
            
    def getResultsDir(self, field):
        return self.baseDir + field.replace(' ', '') + "/"
        
    def getRelevantExpertsFilename(self, field): 
        return self.getResultsDir(field) + "relevantExperts.pkl"
        
    def getCoauthorsFilename(self, field): 
        return self.getResultsDir(field) + "coauthors.pkl"
        
    def matchExperts(self, relevantExperts, expertsSet): 
        """
        Match experts in the set of relevant experts for the given field. It returns 
        expertMatches which is the name of the expert in the database, and expertSet 
        which is the complete set of experts. 
        """
        expertsSet = set(expertsSet)
        expertMatches = set([])
               
        for relevantExpert in relevantExperts: 
            possibleMatches = difflib.get_close_matches(relevantExpert, expertsSet, cutoff=self.matchCutoff)
            if len(possibleMatches) != 0: 
                expertMatches.add(relevantExpert)

        for author in expertsSet.difference(expertMatches):
            possibleMatches = difflib.get_close_matches(author, relevantExperts, cutoff=0.6)
            if len(possibleMatches) != 0: 
                logging.debug("Possible matches for " + author + " : " + str(possibleMatches))
                          
        expertMatches = sorted(list(expertMatches))
        logging.debug("Total number of matches " + str(len(expertMatches)) + " of " + str(len(expertsSet)))        
        
        return expertMatches 

    def coauthorsGraphFromAuthors(self, relevantExperts): 
        """
        Take a set of relevant authors and return the graph. 
        """
        dataFile = open(self.dataFilename)  
        authorIndexer = IdIndexer()
        author1Inds = array.array("i")
        author2Inds = array.array("i")
        
        for relevantExpert in relevantExperts: 
            authorIndexer.append(relevantExpert)
        
        for i, line in enumerate(dataFile):
            Util.printIteration(i, self.stepSize, self.numLines)
            authors = re.findall("#@(.*)", line)  
                            
            if len(authors) != 0: 
                authors = set([x.strip() for x in authors[0].split(",")]) 
                if len(authors.intersection(relevantExperts)) != 0: 
                    iterator = itertools.combinations(authors, 2)
                
                    for author1, author2 in iterator: 
                        author1Ind = authorIndexer.append(author1) 
                        author2Ind = authorIndexer.append(author2)
                        
                        author1Inds.append(author1Ind)
                        author2Inds.append(author2Ind)
        
        logging.debug("Found " + str(len(authorIndexer.getIdDict())) + " coauthors")
                               
        #Coauthor graph is undirected 
        author1Inds = numpy.array(author1Inds, numpy.int)
        author2Inds = numpy.array(author2Inds, numpy.int)
        edges = numpy.c_[author1Inds, author2Inds]            
        
        graph = igraph.Graph()
        graph.add_vertices(len(authorIndexer.getIdDict()))
        graph.add_edges(edges)
        graph.es["weight"] = numpy.ones(graph.ecount())
        graph.simplify(combine_edges=sum)   
        graph.es["invWeight"] = 1.0/(numpy.array(graph.es["weight"])) 
        
        return graph, authorIndexer
            
    def coauthorsGraph(self, field, relevantExperts): 
        """
        Using the relevant authors we find all coauthors. 
        """  
        if not os.path.exists(self.getCoauthorsFilename(field)) or self.overwrite: 
            logging.debug("Finding coauthors of relevant experts")
            graph, authorIndexer = self.coauthorsGraphFromAuthors(set(relevantExperts))
            logging.debug(graph.summary())
            Util.savePickle([graph, authorIndexer], self.getCoauthorsFilename(field), debug=True)
        else: 
            logging.debug("Files already generated: " + self.getCoauthorsFilename(field))  

        graph, authorIndexer = Util.loadPickle(self.getCoauthorsFilename(field))
        return graph, authorIndexer 

    def expertsFromDocSimilarities(self, similarities): 
        """
        Given a set of similarities work out which documents are relevent 
        and then return a list of ranked authors using these scores. 
        """
        relevantDocs = numpy.arange(similarities.shape[0])[similarities >= self.similarityCutoff]
        
        #Now find all authors corresponding to the documents 
        expertDict = {} 
        expertsSet = set([])
        for docInd in relevantDocs: 
            for author in self.authorList[docInd]: 
                if author not in expertsSet: 
                    expertsSet.add(author)
                    expertDict[author] = similarities[docInd]
                else: 
                    expertDict[author] += similarities[docInd]
        
        expertDict = OrderedDict(sorted(expertDict.items(), key=lambda t: t[1], reverse=True))
        experts = expertDict.keys()[0:self.maxRelevantAuthors]
        
        return experts 

    def readAuthorsAndDocuments(self): 
        logging.debug("About to read file " + self.dataFilename)
        inFile = open(self.dataFilename)  
        authorList = []
        documentList = []
                    
        lastAbstract = ""
        lastTitle = ""    
        lastAuthors = []                    
                    
        for i, line in enumerate(inFile):
            Util.printIteration(i, self.stepSize, self.numLines)
                
            #Match the fields in the file 
            emptyLine = line == "\n"
            title = re.findall("#\*(.*)", line)
            currentAuthors = re.findall("#@(.*)", line)  
            abstract = re.findall("#!(.*)", line)
            
            if emptyLine:
                document = lastTitle + " " + lastAbstract 
                documentList.append(document) 
                authorList.append(lastAuthors)

                lastAbstract = ""
                lastTitle = ""
                lastAuthors = []
 
            if len(title) != 0 and len(title[0]) != 0: 
                lastTitle = title[0]               
            
            if len(abstract) != 0 and len(abstract[0]) != 0: 
                lastAbstract = abstract[0]
                       
            if len(currentAuthors) != 0: 
                currentAuthors = currentAuthors[0].split(",")  
                currentAuthors = set([x.strip() for x in currentAuthors])
                lastAuthors = currentAuthors                     

        inFile.close() 
        logging.debug("Finished reading file")    

        return authorList, documentList

    def vectoriseDocuments(self):
        """
        We want to go through the dataset and vectorise all the title+abstracts.
        The results are saved in TDIDF format in a matrix X. 
        """
        if not os.path.exists(self.docTermMatrixFilename + ".mtx") or not os.path.exists(self.authorListFilename) or not os.path.exists(self.vectoriserFilename) or self.overwriteVectoriser:
            logging.debug("Vectorising documents")            
            
            authorList, documentList = self.readAuthorsAndDocuments()
            Util.savePickle(authorList, self.authorListFilename, debug=True)
            
            #vectoriser = text.HashingVectorizer(ngram_range=(1,2), binary=self.binary, norm="l2", stop_words="english", tokenizer=PorterTokeniser(), dtype=numpy.float)
            
            if self.tfidf:             
                vectoriser = text.TfidfVectorizer(min_df=self.minDf, ngram_range=(1,self.ngram), binary=self.binary, sublinear_tf=self.sublinearTf, norm="l2", max_df=0.95, stop_words="english", tokenizer=PorterTokeniser(), max_features=self.numFeatures, dtype=numpy.float)
            else: 
                vectoriser = text.CountVectorizer(min_df=self.minDf, ngram_range=(1,self.ngram), binary=self.binary, max_df=0.95, stop_words="english", max_features=self.numFeatures, dtype=numpy.float, tokenizer=PorterTokeniser())            
            
            X = vectoriser.fit_transform(documentList)
            del documentList
            scipy.io.mmwrite(self.docTermMatrixFilename, X)
            logging.debug("Wrote X to file " + self.docTermMatrixFilename + ".mtx")
            del X 
                
            #Save vectoriser - note that we can't pickle the tokeniser so it needs to be reset when loaded 
            vectoriser.tokenizer = None 
            Util.savePickle(vectoriser, self.vectoriserFilename, debug=True) 
            del vectoriser  
            gc.collect()
        else: 
            logging.debug("Author list, document-term matrix and vectoriser already generated: ")   
   
    def loadVectoriser(self): 
        self.vectoriser = Util.loadPickle(self.vectoriserFilename)
        self.vectoriser.tokenizer = PorterTokeniser() 
        self.authorList = Util.loadPickle(self.authorListFilename)     
        logging.debug("Loaded vectoriser and author list")
           
    def computeLDA(self):
        if not os.path.exists(self.ldaModelFilename) or self.overwriteModel:
            self.vectoriseDocuments()
            self.loadVectoriser()
            X = scipy.io.mmread(self.docTermMatrixFilename)
            #corpus = gensim.matutils.MmReader(self.docTermMatrixFilename + ".mtx", True)
            corpus = gensim.matutils.Sparse2Corpus(X, documents_columns=False)
            del X 
            id2WordDict = dict(zip(range(len(self.vectoriser.get_feature_names())), self.vectoriser.get_feature_names()))   
            
            logging.getLogger('gensim').setLevel(logging.INFO)
            lda = LdaModel(corpus, num_topics=self.k, id2word=id2WordDict, chunksize=self.chunksize, distributed=False) 
            index = gensim.similarities.docsim.SparseMatrixSimilarity(lda[corpus], num_features=self.k)             
            
            Util.savePickle([lda, index], self.ldaModelFilename, debug=True)
            gc.collect()
        else: 
            logging.debug("File already exists: " + self.ldaModelFilename)
   
    def findSimilarDocumentsLDA(self, field): 
        """ 
        We use LDA in this case 
        """
        if not os.path.exists(self.getRelevantExpertsFilename(field)) or self.overwrite: 
            self.computeLDA()
            self.loadVectoriser()
                                
            lda, index = Util.loadPickle(self.ldaModelFilename)
            
            newX = self.vectoriser.transform([field])
            #newX = self.vectoriser.transform(["database"])
            newX = [(i, newX[0, i])for i in newX.nonzero()[1]]
            result = lda[newX]    
            
            #Cosine similarity 
            similarities = index[result]
            experts = self.expertsFromDocSimilarities(similarities)
            
            logging.debug("Number of relevant authors : " + str(len(experts)))
            Util.savePickle(experts, self.getRelevantExpertsFilename(field), debug=True)
        else: 
            logging.debug("File already generated " + self.getRelevantExpertsFilename(field))

    def computeLSI(self):
        """
        Compute using the LSI version in gensim 
        """
        if not os.path.exists(self.lsiModelFilename) or self.overwriteModel:
            self.vectoriseDocuments()
            self.loadVectoriser()
            X = scipy.io.mmread(self.docTermMatrixFilename)
            #corpus = gensim.matutils.MmReader(self.docTermMatrixFilename + ".mtx", True)
            corpus = gensim.matutils.Sparse2Corpus(X, documents_columns=False)
            del X 
            id2WordDict = dict(zip(range(len(self.vectoriser.get_feature_names())), self.vectoriser.get_feature_names()))   
            
            logging.getLogger('gensim').setLevel(logging.ERROR)
            lsi = LsiModel(corpus, num_topics=self.k, id2word=id2WordDict, chunksize=self.chunksize, distributed=False) 
            index = gensim.similarities.docsim.SparseMatrixSimilarity(lsi[corpus], num_features=len(self.vectoriser.get_feature_names()))             
            
            Util.savePickle([lsi, index], self.lsiModelFilename, debug=True)
            gc.collect()
        else: 
            logging.debug("File already exists: " + self.lsiModelFilename)   


    def findSimilarDocumentsLSI(self, field): 
        """ 
        We use LSI from gensim in this case 
        """
        self.computeLSI()
        self.loadVectoriser()
                            
        lsi, index = Util.loadPickle(self.lsiModelFilename)
        
        newX = self.vectoriser.transform([field])
        #newX = self.vectoriser.transform(["database"])
        newX = [(i, newX[0, i])for i in newX.nonzero()[1]]
        result = lsi[newX]             
        similarities = index[result]
        relevantExperts = self.expertsFromDocSimilarities(similarities)
        
        return relevantExperts
             
            
    def modelSelectionLSI(self): 
        """
        Lets find the optimal parameters for LSI for all fields. We see the optimal 
        number of parameters for the training set of experts. 
        """
        self.computeLSI()
        self.loadVectoriser()
        X = scipy.io.mmread(self.docTermMatrixFilename)
        X = X.tocsr()
        
        #inds = numpy.random.permutation(X.shape[0])[0:self.sampleDocs]
        #X = X[inds, :]
        corpus = gensim.matutils.Sparse2Corpus(X, documents_columns=False)
        id2WordDict = dict(zip(range(len(self.vectoriser.get_feature_names())), self.vectoriser.get_feature_names()))
        
        errors = numpy.zeros((len(self.ks), len(self.fields)))
        logging.getLogger('gensim').setLevel(logging.ERROR) 
        
        logging.debug("Starting model selection")
        
        for i, k in enumerate(self.ks): 
            for j, field in enumerate(self.fields): 
                logging.debug("k="+str(k) + " and field=" + str(field))
                
                lsi = LsiModel(corpus, num_topics=k, id2word=id2WordDict, chunksize=self.chunksize, distributed=False) 
                index = gensim.similarities.docsim.SparseMatrixSimilarity(lsi[corpus], num_features=k)
                
                newX = self.vectoriser.transform([field])
                newX = [(s, newX[0, s])for s in newX.nonzero()[1]]
                result = lsi[newX]             
                similarities = index[result]
                relevantExperts = self.expertsFromDocSimilarities(similarities)
                
                expertMatches = self.matchExperts(relevantExperts, set(self.trainExpertDict[field]))
                errors[i, j] = float(len(expertMatches))/len(self.trainExpertDict[field])
        
        meanErrors = numpy.mean(errors, 1)
        logging.debug(meanErrors)
        
        self.k = self.ks[numpy.argmin(meanErrors)]
        logging.debug("Chosen k=" + str(self.k))
        
        