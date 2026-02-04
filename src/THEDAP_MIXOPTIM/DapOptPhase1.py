import warnings
import pandas as pd
from datetime import datetime, date
import numpy as np
warnings.filterwarnings(action='ignore')
from dateutil.relativedelta import relativedelta
from scipy.optimize import minimize
from THEDAP_SIMULATION.DapPhase5_v5 import DapPhase5_v5

class DapOptPhase1(DapPhase5_v5):
    
    def __init__(self, inputModelDate = datetime.strftime(date.today(), "%Y-%m-%d"), userName = ''):
        super().__init__(inputModelDate=inputModelDate, userName=userName)

    def opt_tidy(self, opt_mix, input_age, input_gender):
        age = pd.read_json(self.trans_age(input_age))
        trans_min = age['trans_min'][0]
        trans_max = age['trans_max'][0]

        opt_mix_cleaned = pd.read_json(opt_mix).assign(
            campaign='MIX_OPTIMIZE',
            date_start=datetime.today().strftime('%Y-%m-%d'),
            date_end=(datetime.today() + relativedelta(months=+1)).strftime('%Y-%m-%d'),
            gender=pd.read_json(self.get_gender(input_gender))['gender'][0],
            min=trans_min,
            max=trans_max,
            retargeting=.0,
            budget=1.,
            imp=.0,
            reach=.0,
        ).to_json(orient='records', force_ascii=False)

        opt_mix_cleaned = self.mix_clean(opt_mix_cleaned).assign(budget=.0)   
        opt_mix_cleaned = self.get_eimp(opt_mix_cleaned)

        opt_mix_cleaned['CPM'] = np.where(opt_mix_cleaned['bid_type'] == "CPM", opt_mix_cleaned['bid_cost'],
                                        np.where(opt_mix_cleaned['bid_type'] == "CPRP",
                                                opt_mix_cleaned['bid_cost'] / opt_mix_cleaned['pop_grps'] * 100 * 1000,
                                                opt_mix_cleaned['bid_cost'] * opt_mix_cleaned['bid_rate'] * 1000))
        opt_mix_cleaned = opt_mix_cleaned.drop_duplicates().dropna(subset=['platform', 'product', 'CPM']).query('CPM > .0')
        opt_mix_cleaned = opt_mix_cleaned.astype({'CPM': 'float'})

        # 최종 중복확인
        check_df_ = opt_mix_cleaned.groupby(['platform', 'product']).size().reset_index(name='n')
        filt_ = check_df_.query('n > 1').filter(['platform', 'product'])
        unfilt_ = check_df_.query('n == 1').filter(['platform', 'product'])

        line_list = []

        for i in range(unfilt_.shape[0]):
            line_list.extend(opt_mix_cleaned.loc[(opt_mix_cleaned['platform'] == unfilt_['platform'][i]) & (
                        opt_mix_cleaned['product'] == unfilt_['product'][i])]['line'].tolist())

        if filt_.shape[0] == 0:
            pass
        else:
            for d in range(filt_.shape[0]):
                line_list.extend(
                    opt_mix_cleaned.loc[(opt_mix_cleaned['platform'] == unfilt_['platform'][d]) & (
                                opt_mix_cleaned['product'] == unfilt_['product'][d])]. \
                        sort_values(['impact', 'min_rat', 'CPM'], ascending=[False, False, True])['line'].tolist()
                )

        opt_mix_cleaned = opt_mix_cleaned.loc[opt_mix_cleaned['line'].isin(line_list)].\
            sort_values('line', ascending=True).\
            drop(['gender', 'min', 'max'], axis=1).\
            rename(columns={'gender_org':'gender', 'min_org':'min', 'max_org':'max'})
        return opt_mix_cleaned
    
    def get_reach_max(self, opt_mix_cleaned, input_age, input_gender, input_weight, target_budget, ftol=1e-04):
        reach_epochs = [0]
        
        bounds = tuple((opt_mix_cleaned['min_rat'].values[i], 1.0) for i in range(len(opt_mix_cleaned)))
        
        def objective(ratios):
            try:
                lower_bounds = [b[0] for b in bounds]
                ratios = np.clip(ratios, lower_bounds, 1.0)
                if np.sum(ratios) > 0:
                    ratios = ratios / np.sum(ratios)
                    
                opt_mix_temp = opt_mix_cleaned.copy()
                opt_mix_temp['budget'] = ratios * (target_budget * 1e+06)
                input_mix_json = opt_mix_temp.assign(imp="", reach="").to_json(orient='records', force_ascii=False)   
            
                result = self.summary_total(
                    input_mix=input_mix_json,
                    input_age=input_age,
                    input_gender=input_gender,
                    input_weight=input_weight
                )
                val_ = result[1]['target_reach_p'].values[0]
                reach_epochs.append(val_)
                return -val_
            except Exception:
                return -(np.max(reach_epochs) * 0.8) if np.max(reach_epochs) > 0 else -1e-6
                
        initial_guess = opt_mix_cleaned['min_rat'].values
        if np.sum(initial_guess) == 0:
            initial_guess = np.ones(len(opt_mix_cleaned)) / len(opt_mix_cleaned)
        
        if (1 - np.sum(opt_mix_cleaned['min_rat'].values)) <= 0.05:
            eps = 1e-6
        else: 
            eps = 1e-2
            
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1.0})

        result = minimize(
            objective, initial_guess, method='SLSQP',
            bounds=bounds, constraints=constraints,
            options={'maxiter': 100, 'ftol': ftol, 'eps': eps}
        )
        return (np.round(result.x, 7) / np.sum(np.round(result.x, 7)))
        