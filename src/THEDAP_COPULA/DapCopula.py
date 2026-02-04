import numpy as np
import pandas as pd
from scipy.stats import multivariate_normal, norm
from scipy.optimize import minimize_scalar
from scipy.stats.qmc import Sobol

import itertools

class DapCopula:
    
    def __init__(self, marginal_probs, union_obs):
        self.marginal_obs = marginal_probs
        self.union_obs = union_obs
    
    def get_copula_union(self, p_list, rho):
        d = len(p_list)
        Sigma = np.full((d, d), rho)
        np.fill_diagonal(Sigma, 1.0)

        epsilon = 1e-6
        u = np.clip(1 - np.array(p_list), epsilon, 1 - epsilon)
        z = np.array([norm.ppf(ui) for ui in u])


        mvn = multivariate_normal(mean=np.zeros(d), cov=Sigma, allow_singular=True)
        prob_none = mvn.cdf(z)
        return 1 - prob_none
    
    def estimate_rho(self, marginal_probs, union_obs):
        p_list = list(marginal_probs.values())

        # 관측값 보정
        if np.max(p_list) > union_obs:
            union_obs = np.max(p_list)

        d = len(p_list)
        lower = -1.0 / (d - 1) + 1e-6
        upper = 0.99

        def objective(rho):
            union_hat = self.get_copula_union(p_list, rho)
            eps = 1e-6
            logit_hat = np.log((union_hat + eps)/(1 - union_hat + eps))
            logit_obs = np.log((union_obs + eps)/(1 - union_obs + eps))
            return (logit_hat - logit_obs)**2

        res = minimize_scalar(
            objective,
            bounds=(lower, upper),
            method="bounded",
            options={"xatol": 1e-6, "maxiter": 500}
        )

        rho_hat = res.x
        union_hat = self.get_copula_union(p_list, rho_hat)
        return np.round(rho_hat, 4), np.round(union_hat, 4)
    
    def get_copula_probs(self, marginal_probs, union_obs):
        
        rho, _ = self.estimate_rho(marginal_probs, union_obs)

        keys = list(marginal_probs.keys())
        p_list = list(marginal_probs.values())
        d = len(p_list)

        Sigma = np.full((d, d), rho)
        np.fill_diagonal(Sigma, 1.0)

        epsilon = 1e-6
        p = np.clip(np.array(p_list), epsilon, 1 - epsilon)
        t = norm.ppf(1 - p)

        results_union = {}
        results_inter = {}

        for r in range(1, d + 1):
            for subset in itertools.combinations(range(d), r):
                name = [keys[i] for i in subset]
                keyU = " \u22C3 ".join(name)
                keyI = " \u22C2 ".join(name)
                
                if r == 1:
                    # 단일 매체는 Copula 없이 marginal 그대로 사용
                    p_val = marginal_probs[name[0]]
                    results_union[keyU] = np.round(p_val, 6)
                    results_inter[keyI] = np.round(p_val, 6)
                    continue
                
                t_sub = t[list(subset)]
                Sigma_sub = Sigma[np.ix_(subset, subset)]

                # 합집합: 1 - CDF(t)
                probU = 1 - multivariate_normal.cdf(t_sub, mean=np.zeros(r), cov=Sigma_sub)
                # 교집합: CDF(-t)
                probI = multivariate_normal.cdf(-t_sub, mean=np.zeros(r), cov=Sigma_sub)

                results_union[keyU] = np.round(probU, 6)
                results_inter[keyI] = np.round(probI, 6)
                
        keys = list(marginal_probs.keys())
        df_union = self.dict_to_df(results_union, keys)
        df_inter = self.dict_to_df(results_inter, keys)
        
        inter_dict = {row['comb']: row['reach'] for _, row in df_inter.iterrows()}
        for k in keys:
            p_only = 0.0
            for comb, val in inter_dict.items():
                subset = comb.split(' ⋂ ')
                if k not in subset:
                    continue
                r = len(subset)
                sign = (-1) ** (r - 1)  
                p_only += sign * val

            p_only = max(round(p_only, 6), 0.0)
            df_inter.loc[df_inter['comb'] == k, ['comb', 'reach']] = [f"{k}_ONLY", p_only]

        full_union_key = " ⋃ ".join(keys)
        union_hat = self.get_copula_union(p_list, rho)
        df_union.loc[df_union['comb'] == full_union_key, 'reach'] = np.round(union_hat, 6)

        return df_union.filter(['comb', 'reach']).to_dict(orient='records'), \
            df_inter.filter(['comb', 'reach']).to_dict(orient='records')


    def dict_to_df(self, results, keys):
        rows = []
        for comb, val in results.items():
            row = {'comb': comb, 'reach': val}
            for k in keys:
                row[k] = k in comb
            rows.append(row)
        return pd.DataFrame(rows)[['comb'] + keys + ['reach']]