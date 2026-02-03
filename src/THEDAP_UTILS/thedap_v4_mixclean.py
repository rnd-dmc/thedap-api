import pandas as pd
import numpy as np
import json
from collections import OrderedDict
from THEDAP_UTILS.thedap_v4_utils import getUTIL_v4

class getMixClean_v4(getUTIL_v4):
    
    def __init__(self):
        super().__init__()

    ### 믹스안 정제 & 기대 노출량
    def mix_clean(self, input_mix):
        pop_sum = self.population_DB['population'].sum()

        mix_df = pd.read_json(input_mix)
        for i in range(0, mix_df.shape[0]):
            for j in range(0, mix_df.shape[1]):
                if (mix_df.iloc[i, j] == ''):
                    mix_df.iloc[i, j] = None

        mix = mix_df.astype(
            {'platform': 'str', 'product': 'str', 'gender': 'str', 'min': 'float', 'max': 'float', 'impact': 'float',
            'budget': 'float',
            'bid_type': 'str', 'bid_cost': 'float', 'bid_rate': 'float', 'e_imp': 'float', 'e_grp': 'float'})

        mix['platform'] = np.where((mix['bid_type'] == 'E.IMP 직접입력') & ((mix['e_imp'].isnull()) | (mix['e_imp'] == 0)),
                                None, mix['platform'])
        mix['platform'] = np.where((mix['bid_type'] == 'E.GRP 직접입력') & ((mix['e_grp'].isnull()) | (mix['e_grp'] == 0)),
                                None, mix['platform'])
        mix['platform'] = np.where(
            (mix.bid_type.isin(['CPM', 'CPRP'])) & ((mix['bid_cost'].isnull()) | (mix['bid_cost'] == 0)), None,
            mix['platform'])
        mix['platform'] = np.where((mix.bid_type.isin(['CPV', 'CPC'])) & (
                    (mix['bid_cost'].isnull()) | (mix['bid_rate'].isnull()) | (mix['bid_cost'] == 0) | (
                        mix['bid_rate'] == 0)), None, mix['platform'])
        mix['budget'] = np.where(mix['budget'] <= 0, None, mix['budget'])
        
        # IMPACT가 0 ~ 100 사이로 들어옴
        # mix['impact'] = mix['impact'].apply(lambda x: x/100 if isinstance(x, float) else x)
        
        mix['impact'] = np.where((mix['impact'].isnull()) | (mix['impact'] >= 1) | (mix['impact'] <= 0), 1, mix['impact'])
        mix['bid_cost'] = np.where(mix['bid_cost'] <= 0, None, mix['bid_cost'])
        mix['bid_rate'] = np.where(mix['bid_rate'] <= 0, None, mix['bid_rate'])
        mix['bid_rate'] = np.where(mix['bid_rate'] >= 1, 1, mix['bid_rate'])
        mix['e_imp'] = np.where(mix['e_imp'] < 0, None, mix['e_imp'])
        mix['e_grp'] = np.where(mix['e_grp'] < 0, None, mix['e_grp'])
        mix['bid_rate'] = np.where(((mix['bid_rate'] < 0) | (mix['bid_rate'] > 1)), None, mix['bid_rate'])

        mix_cleaned = mix[(~mix['platform'].isnull()) & (~mix['product'].isnull()) & (~mix['gender'].isnull()) &
                        (~mix['min'].isnull()) & (~mix['max'].isnull()) & (~mix['budget'].isnull()) & (
                            ~mix['bid_type'].isnull())]

        mix_cleaned = mix_cleaned[~(mix_cleaned['platform'].isnull()) | ~(mix_cleaned['product'].isnull()) |
                                ~(mix_cleaned['gender'].isnull()) | ~(mix_cleaned['min'].isnull()) |
                                ~(mix_cleaned['max'].isnull()) | ~(mix_cleaned['budget'].isnull()) | ~(
            mix_cleaned['bid_type'].isnull())]

        mix_cleaned['min'] = mix_cleaned['min'].apply(lambda x: self.trans_min_age(x))
        mix_cleaned['max'] = mix_cleaned['max'].apply(lambda x: self.trans_max_age(x))

        # 모든 float type에 대한 반올림 & infinity 처리
        mix_cleaned = self.round_float(mix_cleaned)

        return mix_cleaned


    # 기대노출량 계산
    def get_eimp(self, mix_cleaned):
        
        pop_sum = self.population_DB['population'].sum()

        pop = []
        for g, mn, mx in zip(mix_cleaned['gender'], mix_cleaned['min'], mix_cleaned['max']):
            pop.append(pd.read_json(self.get_population(g, mn, mx))['trans_pop'][0])

        mix_cleaned['pop_grps'] = pop

        mix_cleaned['e_imp'] = np.where(mix_cleaned['bid_type'].isin(['CPV', 'CPC']),
                                        (mix_cleaned['budget'] / (mix_cleaned['bid_cost'] * mix_cleaned['bid_rate'])),
                                        np.where(mix_cleaned['bid_type'] == 'CPM',
                                                (mix_cleaned['budget'] / mix_cleaned['bid_cost'] * 1000),
                                                np.where(mix_cleaned['bid_type'] == 'CPRP', (
                                                            (mix_cleaned['budget'] / mix_cleaned['bid_cost']) *
                                                            mix_cleaned['pop_grps'] / 100),
                                                        np.where(mix_cleaned['bid_type'] == "E.GRP 직접입력",
                                                                (mix_cleaned['e_grp'] / 100 * mix_cleaned['pop_grps']),
                                                                mix_cleaned['e_imp']))))

        mix_cleaned['grp'] = mix_cleaned['e_imp'] / mix_cleaned['pop_grps'] * 100
        mix_cleaned['eimp_weighted'] = np.where(mix_cleaned['e_imp'].isna(), None,
                                                mix_cleaned['e_imp'] * mix_cleaned['impact'])
        mix_cleaned['grp_weighted'] = np.where(mix_cleaned['grp'].isna(), None, mix_cleaned['grp'] * mix_cleaned['impact'])

        mix_cleaned['gender_org'] = mix_cleaned['gender']
        mix_cleaned['gender'] = np.where((mix_cleaned['platform'].isin(['SMR', 'TV'])), 'P', mix_cleaned['gender'])
        mix_cleaned['min_org'] = mix_cleaned['min']
        mix_cleaned['max_org'] = mix_cleaned['max']
        mix_cleaned['min'] = np.where((mix_cleaned['platform'].isin(['SMR', 'TV'])), min(self.population_DB['age_min']),
                                    mix_cleaned['min'])
        mix_cleaned['max'] = np.where((mix_cleaned['platform'].isin(['SMR', 'TV'])), max(self.population_DB['age_max']),
                                    mix_cleaned['max'])
        mix_cleaned.dropna(subset=['platform'], inplace=True)
        mix_cleaned.dropna(subset=['e_imp'], inplace=True)
        mix_cleaned = mix_cleaned.reset_index(drop=True)
        mix_cleaned['line'] = [f'{i+1:02}' for i in mix_cleaned.index.to_list()]
        mix_cleaned.fillna(0, inplace=True)

        mix_cleaned_tv = mix_cleaned.query('platform == "TV"')
        mix_cleaned_ntv = mix_cleaned.query('platform != "TV"')

        # TV매체 기대노출량
        tv_eimp = []
        tv_eimp_weighted = []

        for g in mix_cleaned_tv.index.tolist():
            df = self.get_age_range(mix_cleaned_tv['gender'][g], mix_cleaned_tv['min'][g], mix_cleaned_tv['max'][g]). \
                assign(platform=mix_cleaned_tv['platform'][g], product=mix_cleaned_tv['product'][g],
                    e_imp=mix_cleaned_tv['e_imp'][g], impact=mix_cleaned_tv['impact'][g],
                    eimp_weighted=mix_cleaned_tv['eimp_weighted'][g], gender_org=mix_cleaned_tv['gender_org'][g],
                    min_org=mix_cleaned_tv['min_org'][g], max_org=mix_cleaned_tv['max_org'][g]). \
                merge(self.distribution_DB)

            df['gender_org'] = np.where(df['gender_org'] == "P", df['gender'], df['gender_org'])
            df['isDemo'] = np.where(
                ((df['gender'] == df['gender_org']) & (df['age_min'] >= df['min_org']) & (df['age_max'] <= df['max_org'])),
                1, 0)
            df['dist_sum'] = np.dot(df['isDemo'], df['distribution'])
            df['dist_rat'] = df['distribution'] / df['dist_sum']
            df['e_imp'] = df['e_imp'] * df['dist_rat']
            df['eimp_weighted'] = df['eimp_weighted'] * df['dist_rat']

            tv_eimp.append(np.sum(df['e_imp']))
            tv_eimp_weighted.append(np.sum(df['eimp_weighted']))

        mix_cleaned_tv['e_imp'] = tv_eimp
        mix_cleaned_tv['eimp_weighted'] = tv_eimp_weighted

        mix_cleaned = pd.concat([mix_cleaned_tv, mix_cleaned_ntv], axis=0).sort_index()

        # 모든 float type에 대한 반올림 & infinity 처리
        mix_cleaned = self.round_float(mix_cleaned)

        return (mix_cleaned)


    # 예산 총합
    def sum_budget(self, input_mix):
        mix_cleaned = self.get_eimp(self.mix_clean(input_mix))
        sum_budget = pd.DataFrame({'sum_budget': [(mix_cleaned['budget'].sum())]}).to_json(force_ascii=False)

        return (sum_budget)