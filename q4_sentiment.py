#!/usr/bin/env python

import argparse
import numpy as np
import matplotlib

matplotlib.use('agg')
import matplotlib.pyplot as plt
import itertools

from utils.treebank import StanfordSentiment
import utils.glove as glove

from q3_sgd import load_saved_params,sgd

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix

def getArguments():
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--pretrained",dest="pretrained",action="store_true",
                       help="Use pretrained GloVe vectors.")
    group.add_argument("--yourvectors",dest="yourvectors",action="store_true",
                       help="Use your vectors from q3.")
    return parser.parse_args()

def getSentenceFeatures(tokens,wordVectors,sentence):
    """
    obtain the sentence feature for sentiment analysis by averaging its word vectors.
    :param tokens: a dictionary that maps words to their indices in the word vector list
    :param wordVectors: word vectors (each row) for all tokens
    :param sentence: a list of words in the sentence of interest
    :return: sentVector: feature vector for the sentence
    """
    sentVector=np.zeros((wordVectors.shape[1],))

    ### YOUR CODE HERE
    for s in sentence:
        sentVector+=wordVectors[tokens[s],:]
    sentVector*=1.0/len(sentence)
    ### END YOUR CODE

    assert sentVector.shape==(wordVectors.shape[1],)
    return sentVector

def getRegularizationValues():
    """Try different regularizations
    :return: sorted: a sorted list of values to try
    """
    values=None # Assign a list of floats in the block below
    ### YOUR CODE HERE
    values=np.logspace(-4,2,num=100,base=10)
    ### END YOUR CODE
    return sorted(values)

def chooseBestModel(results):
    """
    Choose the best model based on parameter tuning on the dev set
    :param results: A list of python dictionaries of the following format
        {
            "reg": regularization,
            "clf": classifier,
            "train": trainAccuracy,
            "dev": devAccuracy,
            "test": testAccuracy
        }
    :return: Your chosen result dictionary.
    """
    bestResult=None

    ### YOUR CODE HERE
    bestResult=max(results,key=lambda x: x["dev"])
    ### END YOUR CODE

    return bestResult

def accuracy(y,yhat):
    assert (y.shape==yhat.shape)
    return np.sum(y==yhat)*100.0/y.size

def plotRegVsAccuracy(regValues,results,filename):
    """Make a plot of regularization vs accuracy"""
    plt.plot(regValues,[x["train"] for x in results])
    plt.plot(regValues,[x["dev"] for x in results])
    plt.xscale('log')
    plt.xlabel("regularization")
    plt.ylabel("accuracy")
    plt.legend(['train','dev'],loc='upper left')
    plt.savefig(filename)

def outputConfusionMatrix(features,labels,clf,filename):
    """Generate a confusion matrix"""
    pred=clf.predict(features)
    cm=confusion_matrix(labels,pred,labels=range(5))
    plt.figure()
    plt.imshow(cm,interpolation='nearest',cmap=plt.cm.Reds)
    plt.colorbar()
    classes=["- -","-","neut","+","+ +"]
    tick_marks=np.arange(len(classes))
    plt.xticks(tick_marks,classes)
    plt.yticks(tick_marks,classes)
    thresh=cm.max()/2.
    for i,j in itertools.product(range(cm.shape[0]),range(cm.shape[1])):
        plt.text(j,i,cm[i,j],
                 horizontalalignment="center",
                 color="white" if cm[i,j]>thresh else "black")
    plt.tight_layout()
    plt.ylabel('True label')
    plt.xlabel('Predicted label')
    plt.savefig(filename)

def outputPredictions(dataset, features, labels, clf, filename):
    """Write the prediction to file"""
    pred=clf.predict(features)
    with open(filename,"w") as f:
        print >>f,"True\tPredicted\tText"
        for i in range(len(dataset)):
            print >>f,"%d\t%d\t%s" %(
                labels[i],pred[i]," ".join(dataset[i][0]))

def main(args):
    """Train a model to do sentiment analysis"""
    # Load the dataset
    dataset=StanfordSentiment()
    tokens=dataset.tokens()
    nWords=len(tokens)

    if args.yourvectors:
        _,wordVecctors,_=load_saved_params()
        wordVecctors=np.concatenate(
            (wordVecctors[:nWords,:],wordVecctors[nWords:,:]),
            axis=1)
    elif args.pretrained:
        wordVecctors=glove.loadWordVectors(tokens)
    dimVectors=wordVecctors.shape[1]

    # Load the train set
    trainset=dataset.getRandomTrainSentence()
    nTrain=len(trainset)
    trainFeatures=np.zeros(nTrain,dimVectors)
    trainLabels=np.zeros((nTrain,),dtype=np.int32)
    for i in range(nTrain):
        words,trainLabels[i]=trainset[i]
        trainFeatures[i,:]=getSentenceFeatures(tokens,wordVecctors,words)

    # Prepare dev set features
    devset=dataset.getDevSentences()
    nDev=len(devset)
    devFeatures=np.zeros((nDev,dimVectors))
    devLabels=np.zeros((nDev,),dtype=np.int32)
    for i in range(nDev):
        words,devLabels[i]=devset[i]
        devFeatures[i,:]=getSentenceFeatures(tokens,wordVecctors,words)

    # Prepare test set features
    testset=dataset.getTestSentences()
    nTest=len(testset)
    testFeatures=np.zeros((nTest,dimVectors))
    testLabels=np.zeros((nTest,),dtype=np.int32)
    for i in range(nTest):
        words,testLabels[i]=testset[i]
        testFeatures[i,:]=getSentenceFeatures(tokens,wordVecctors,words)

    # We will save our results from each run
    results=[]
    regValues=getRegularizationValues()
    for reg in regValues:
        print("Training for reg=%f"%reg)
        # Note: add a very small number to regularization
        clf=LogisticRegression(C=1.0/(reg+1e-12))
        clf.fit(trainFeatures,trainLabels)

        # Test on train set
        pred=clf.predict(trainFeatures)
        trainAccuracy=accuracy(trainLabels,pred)
        print("Train accuracy (%%): %f"%trainAccuracy)

        # Test on dev set
        pred=clf.predict(devFeatures)
        devAccuracy=accuracy(devLabels,pred)
        print("Dev accuracy (%%): %f"%devAccuracy)

        # Test on test set
        # Note: always running on test is poor style.Typically, you should
        # do this only after validation.
        pred=clf.predict(testFeatures)
        testAccuracy=accuracy(testLabels,pred)
        print("Test accuracy (%%): %f"% testAccuracy)

        results.append({
            "reg":reg,
            "clf":clf,
            "train":trainAccuracy,
            "dev":devAccuracy,
            "test":testAccuracy})

        print("")
        print("===Recap===")
        print("Reg\t\tTrain\tDev\tTest")
        for result in results:
            print("%.2E\t%.3f\t%.3f"%(
                result["reg"],
                result["train"],
                result["dev"],
                result["test"]))
        print("")

        bestResult=chooseBestModel(results)
        print("Best regularization value: %0.2E"%bestResult["reg"])
        print("Test accuracy (%%): %f" %bestResult["test"])

        # do some error analysis
        if args.pretrained:
            plotRegVsAccuracy(regValues,results,"q4_reg_acc.png")
            outputConfusionMatrix(devFeatures,devLabels,bestResult["clf"],
                                  "q4_dev_pred.png")
            outputPredictions(devset,devFeatures,devLabels,bestResult["clf"],
                              "q4_dev_pred.txt")

if __name__ == '__main__':
    # Load the dataset
    dataset = StanfordSentiment()
    tokens = dataset.tokens()
    nWords = len(tokens)

    wordVecctors = glove.loadWordVectors(tokens)
    dimVectors = wordVecctors.shape[1]










