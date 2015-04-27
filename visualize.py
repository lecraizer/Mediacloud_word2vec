# -*- coding:utf-8 -*-
u"""
Created on 24/04/15
by fccoelho
license: GPL V3 or Later
"""

__docformat__ = 'restructuredtext en'

from gensim.models.word2vec import Word2Vec
from nltk.tokenize import sent_tokenize, wordpunct_tokenize
from sklearn.manifold import TSNE
from sklearn.cluster import AffinityPropagation, DBSCAN, AgglomerativeClustering, MiniBatchKMeans
import numpy as np
import pymongo
import re
import time


pattern = re.compile(r"[^-a-zA-Z\s]")

def text_gen(limit=2000000):
    """
    Generator to return a document per turn
    :param limit: number of documents to return
    """
    con = pymongo.MongoClient('localhost', port=27017)
    col = con.word2vec.frases
    for doc in col.find({'cleaned_text': {'$exists': True}}, {'cleaned_text': 1}, limit=limit):
        text = pattern.sub("", doc['cleaned_text'])
        yield doc['_id'], wordpunct_tokenize(text.lower())



def build_document_vector(model, text):
    """
    Build a scaled vector for the document
    :param text: document to be vectorized (tokenized)
    :param model: word2vec model
    :return:
    """
    feature_count = model.syn0.shape[1]
    vec = np.zeros(feature_count).reshape((1, feature_count))
    count = 0.
    for word in text:
        try:
            vec += model[word].reshape((1, feature_count))
            count += 1.
        except KeyError:
            continue
    if count != 0:
        vec /= count
    return vec


def cluster_vectors(model, method='KM'):
    """
    Cluster the word vectors using one of a few possible models
    :param model: Word2vec model
    :param method: cluster model used. Default is minibatch K-means
    """

    print("Calculating Clusters.")
    X = model.syn0
    if method == 'AP':
        af = AffinityPropagation(copy=False).fit(X)
        cluster_centers_indices = af.cluster_centers_indices_
        labels = af.labels_
        n_clusters_ = len(set(labels))
    elif method == 'DBS':
        print("Computing DBSCAN")
        db = DBSCAN(eps=0.03, min_samples=5, algorithm='brute', metric='cosine').fit(X)
        labels = db.labels_
        n_clusters_ = len(set(labels))
    elif method == 'AC':
        print("Computing Agglomerative Clustering")
        ac = AgglomerativeClustering(10).fit(X)
        labels = ac.labels_
        n_clusters_ = ac.n_clusters
    elif method == 'KM':
        print("Computing MiniBatchKmeans clustering")
        km = MiniBatchKMeans(n_clusters=X.shape[1], batch_size=200).fit(X)
        labels = km.labels_
        n_clusters_ = len(km.cluster_centers_)
    print('Estimated number of clusters: %d' % n_clusters_)
    return X, labels


def cluster_documents(model, ndocs):
    """
    Cluster the documents based on their vectors
    :param model:
    :param ndocs:
    :return:
    """
    X = np.zeros((ndocs, model.syn0.shape[1]), dtype=float)
    ids = []
    for n, d in enumerate(text_gen(ndocs)):
        ids.append(d[0])
        X[n, :] = build_document_vector(model, d[1])
    km = MiniBatchKMeans(n_clusters=X.shape[1], batch_size=200).fit(X)
    labels = km.labels_
    return X, ids, labels


def extract_cluster(model, labels, label=1):
    """
    Extract a cluster from the
    :param model: Word2vec model
    :param labels: list with cluster labels attributed to each word in the model
    :param label: label if the cluster to extract
    :return:
    """
    indices = [i for i in range(len(labels)) if labels[i] == label]
    palavras = [model.index2word[i] for i in indices]
    return palavras

def extract_clustered_docs(ids, labels, cluster_label):
    con = pymongo.MongoClient('localhost', port=27017)
    col = con.word2vec.frases
    docs = []
    for i, l in zip(ids, labels):
        if l !=cluster_label:
            continue
        d = col.find_one({'_id': i}, {'cleaned_text': 1, '_id': 0})
        if d is not None:
            docs.append(d["cleaned_text"])
    return docs




def load_model(model_name):
    m = Word2Vec.load(model_name)
    return m

if __name__ == "__main__":
    model = load_model("MediaCloud_w2v")
    t0 = time.time()
    x, ids,  l = cluster_documents(model, 100000)
    print("clustered documents in {} seconds".format(time.time()-t0))
    docs = extract_clustered_docs(ids, l, 9)
    for i in range(5):
        print(docs[i])
        print("<<==================>>")

