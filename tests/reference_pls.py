"""Implémentation de référence du PLS, écrite indépendamment lors de l'audit externe de la v0.4.
N'importe rien d'openpls : sert à vérifier l'algorithme (schémas path/factorial/centroid, modes A/B)."""
import numpy as np, pandas as pd
def z(a): return (a-a.mean(0))/a.std(0,ddof=1)
def mypls(data, meas, paths, modes=None, scheme="path", it=5000):
    modes = modes or {}
    lvs=list(meas); k=len(lvs); idx={l:i for i,l in enumerate(lvs)}
    P=np.zeros((k,k))
    for s,d in paths: P[idx[s],idx[d]]=1
    X={l:z(data[meas[l]].to_numpy(float)) for l in lvs}
    W={l:np.ones(len(meas[l])) for l in lvs}
    def sc(W):
        Y=np.column_stack([X[l]@W[l] for l in lvs]); return z(Y)
    for _ in range(it):
        Y=sc(W); R=np.corrcoef(Y,rowvar=False); E=np.zeros((k,k))
        adj=(P+P.T)>0
        for j in range(k):
            for i in range(k):
                if not adj[i,j]: continue
                if scheme=="centroid": E[i,j]=np.sign(R[i,j])
                elif scheme=="factorial": E[i,j]=R[i,j]
                else:
                    if P[j,i]: E[i,j]=R[i,j]   # i successor of j
            if scheme=="path":
                pred=np.flatnonzero(P[:,j])
                if len(pred): E[pred,j]=np.linalg.lstsq(Y[:,pred],Y[:,j],rcond=None)[0]
        Z=Y@E
        Wn={}
        for j,l in enumerate(lvs):
            if modes.get(l,"A")=="A": Wn[l]=X[l].T@Z[:,j]
            else: Wn[l]=np.linalg.lstsq(X[l],Z[:,j],rcond=None)[0]
            s=(X[l]@Wn[l]).std(ddof=1); Wn[l]=Wn[l]/s
        d=max(np.abs(Wn[l]-W[l]).max() for l in lvs); W=Wn
        if d<1e-14: break
    Y=sc(W)
    load={l:np.array([np.corrcoef(X[l][:,q],Y[:,idx[l]])[0,1] for q in range(X[l].shape[1])]) for l in lvs}
    B=np.zeros((k,k))
    for j in range(k):
        pred=np.flatnonzero(P[:,j])
        if len(pred): B[pred,j]=np.linalg.lstsq(Y[:,pred],Y[:,j],rcond=None)[0]
    return dict(W=W,Y=pd.DataFrame(Y,columns=lvs),load=load,B=pd.DataFrame(B,index=lvs,columns=lvs),X=X)
