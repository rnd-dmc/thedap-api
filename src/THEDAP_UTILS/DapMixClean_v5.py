import pandas as pd
import numpy as np
import json
from collections import OrderedDict
from datetime import datetime, date
from THEDAP_UTILS.DapUtils_v5 import DapUtils_v5

class DapMixClean_v5(DapUtils_v5):
    
    def __init__(self, inputModelDate = datetime.strftime(date.today(), "%Y-%m-%d"), userName = ''):
        super().__init__(inputModelDate=inputModelDate, userName=userName)
        self.tv_list = self.get_TV_list()

    ### 믹스안 정제 & 기대 노출량
    def mix_clean(self, input_mix):

        mix_df = pd.read_json(input_mix)
        for i in range(0, mix_df.shape[0]):
            for j in range(0, mix_df.shape[1]):
                if (mix_df.iloc[i, j] == ''):
                    mix_df.iloc[i, j] = None

        mix = mix_df.astype({'campaign': 'str', 'platform': 'str', 'product': 'str', 'date_start': 'str', 'date_end': 'str',
                            'gender': 'str', 'min': 'float', 'max': 'float', 'impact': 'float', 'budget': 'float',
                            'bid_type': 'str', 'bid_cost': 'float', 'bid_rate': 'float', 'imp': 'float', 'reach': 'float'})

        mix['platform'] = np.where(
            (mix.bid_type.isin(['E.IMP 직접입력', 'E.GRP 직접입력'])) & ((mix['imp'].isnull()) | (mix['imp'] == 0.)), None,
            mix['platform'])
        mix['platform'] = np.where(
            (mix.bid_type.isin(['CPM', 'CPRP'])) & ((mix['bid_cost'].isnull()) | (mix['bid_cost'] == 0.)), None,
            mix['platform'])
        mix['platform'] = np.where((mix.bid_type.isin(['CPV', 'CPC'])) & (
                    (mix['bid_cost'].isnull()) | (mix['bid_rate'].isnull()) | (mix['bid_cost'] == 0.) | (
                        mix['bid_rate'] == 0.)), None, mix['platform'])
        mix['budget'] = np.where(mix['budget'] <= 0., None, mix['budget'])
        mix['retargeting'] = np.where(mix['retargeting'] < 0., None, mix['retargeting'])
        mix['retargeting'] = np.where(mix['platform'].isin(self.tv_list), None, mix['retargeting'])
        mix['retargeting'] = np.where(mix['bid_type'].isin(['기집행 분석 (IMP)', '기집행 분석 (GRP)']), None, mix['retargeting'])
        
        # mix['impact'] = np.where((mix['impact'].isnull()) | (mix['impact'] <= 0.), 1.,
        #                         mix['impact'])
        mix['impact'] = np.where((mix['impact'].isnull()) | (mix['impact'] >= 1.) | (mix['impact'] <= 0.), 1.,
                                mix['impact'])
        mix['bid_cost'] = np.where(mix['bid_cost'] <= 0., None, mix['bid_cost'])
        mix['bid_rate'] = np.where((mix['bid_rate'] <= 0.) | (mix['bid_rate'] > 1.), None, mix['bid_rate'])
        mix['bid_rate'] = np.where(mix['bid_rate'] >= 1., 1., mix['bid_rate'])
        mix['imp'] = np.where(mix['imp'] < 0., None, mix['imp'])
        mix['reach'] = np.where(mix['reach'] < 0., None, mix['reach'])
        mix['reach'] = np.where(mix['bid_type'] == "기집행 분석 (GRP)", mix['reach'] / 100, mix['reach'])
            
        mix_cleaned = mix[(~mix['campaign'].isnull()) & (~mix['platform'].isnull()) & (~mix['product'].isnull()) & (
            ~mix['gender'].isnull()) &
                        (~mix['date_start'].isnull()) & (~mix['date_end'].isnull()) &
                        (~mix['min'].isnull()) & (~mix['max'].isnull()) & (~mix['budget'].isnull()) & (
                            ~mix['bid_type'].isnull())]

        mix_cleaned = mix_cleaned[
            ~(mix_cleaned['campaign'].isnull()) | ~(mix_cleaned['platform'].isnull()) | ~(mix_cleaned['product'].isnull()) |
            ~(mix_cleaned['date_start'].isnull()) | ~(mix_cleaned['date_end'].isnull()) |
            ~(mix_cleaned['gender'].isnull()) | ~(mix_cleaned['min'].isnull()) |
            ~(mix_cleaned['max'].isnull()) | ~(mix_cleaned['budget'].isnull()) | ~(mix_cleaned['bid_type'].isnull())]
        
        
        mix_cleaned['date_start'] = mix_cleaned['date_start'].replace('None', None)
        mix_cleaned['date_end'] = mix_cleaned['date_end'].replace('None', None)
        
        #### 
        mix_cleaned['date_start'] = mix_cleaned['date_start'].apply(lambda x: self.safe_date(x))
        mix_cleaned['date_end'] = mix_cleaned['date_end'].apply(lambda x: self.safe_date(x))
        
        # date_start 공백 & date_end 공백
        na_date = (mix_cleaned['date_start'].isna() & mix_cleaned['date_end'].isna())
        # date_start만 공백
        na_start = (mix_cleaned['date_start'].isna() & ~mix_cleaned['date_end'].isna())
        # date_end만 공백
        na_end = (~mix_cleaned['date_start'].isna() & mix_cleaned['date_end'].isna())
        
        # date_start 공백 & date_end 공백이면, 각각 (오늘, 오늘+29일) 로 대체
        if (na_date.sum() > 0) :
            mix_cleaned['date_start'] = np.where(na_date, datetime.strftime(datetime.today(), '%Y-%m-%d'), mix_cleaned['date_start'])
            mix_cleaned['date_end'] = np.where(na_date, datetime.strftime(datetime.today() + pd.Timedelta(days=29), '%Y-%m-%d'), mix_cleaned['date_end'])
        
        # date_start만 공백이면, 입력된 date_end에서 29일 전으로 대체
        if (na_start.sum() > 0) :
            mix_cleaned['date_start'] = np.where(
                na_start, 
                mix_cleaned['date_end'].apply(lambda x: datetime.strftime(datetime.strptime(x, '%Y-%m-%d')-pd.Timedelta(days=29), '%Y-%m-%d') if isinstance(x, str) else x),
                mix_cleaned['date_start'])
        
        # date_end만 공백이면, 입력된 date_start에서 29일 후로 대체
        if (na_end.sum() > 0) :
            mix_cleaned['date_end'] = np.where(
                na_end, 
                mix_cleaned['date_start'].apply(lambda x: datetime.strftime(datetime.strptime(x, '%Y-%m-%d')+pd.Timedelta(days=29), '%Y-%m-%d') if isinstance(x, str) else x),
                mix_cleaned['date_end'])    
        
        mix_cleaned['Eimp'] = np.where(mix_cleaned['bid_type'].str.contains('기집행'), 0., mix_cleaned['imp'])
        mix_cleaned['Aimp'] = np.where(mix_cleaned['bid_type'].str.contains('기집행'), mix_cleaned['imp'], 0.)
        mix_cleaned['Areach'] = np.where(mix_cleaned['bid_type'].str.contains('기집행'), mix_cleaned['reach'], 0.)
        mix_cleaned['min'] = mix_cleaned['min'].apply(lambda x: self.trans_min_age(x))
        mix_cleaned['max'] = mix_cleaned['max'].apply(lambda x: self.trans_max_age(x))
        mix_cleaned.drop(['imp', 'reach'], axis=1, inplace=True)

        if 'min_rat' in mix_cleaned.columns:
            mix_cleaned['min_rat'] = mix_cleaned['min_rat'].fillna(.0)
            mix_cleaned['min_rat'] = mix_cleaned['min_rat'].apply(lambda x: np.round(x, 2))
            mix_cleaned['min_rat'] = mix_cleaned['min_rat'].apply(lambda x: .05 if x == .0 else x)

        # 모든 float type에 대한 반올림 & infinity 처리
        mix_cleaned = self.round_float(mix_cleaned)
        
        return mix_cleaned


    # 기대노출량 계산
    def get_eimp(self, mix_cleaned):

        mix_cleaned['line'] = [f'{i+1:02}' for i in mix_cleaned.index.to_list()]
        pop = []
        for g, mn, mx in zip(mix_cleaned['gender'], mix_cleaned['min'], mix_cleaned['max']):
            pop.append(pd.read_json(self.get_population(g, mn, mx))['trans_pop'][0])

        mix_cleaned['pop_grps'] = pop
        mix_cleaned['Eimp'] = np.where(mix_cleaned['bid_type'].isin(['CPV', 'CPC']),
                                    (mix_cleaned['budget'] / (mix_cleaned['bid_cost'] * mix_cleaned['bid_rate'])),
                                    np.where(mix_cleaned['bid_type'] == 'CPM',
                                                (mix_cleaned['budget'] / mix_cleaned['bid_cost'] * 1000),
                                                np.where(mix_cleaned['bid_type'] == 'CPRP', (
                                                            (mix_cleaned['budget'] / mix_cleaned['bid_cost']) * mix_cleaned[
                                                        'pop_grps'] / 100),
                                                        np.where(mix_cleaned['bid_type'] == "E.GRP 직접입력",
                                                                (mix_cleaned['Eimp'] / 100 * mix_cleaned['pop_grps']),
                                                                np.where(mix_cleaned['bid_type'] == "E.IMP 직접입력",
                                                                        mix_cleaned['Eimp'], 0.)))))
        mix_cleaned['eimp_weighted'] = np.where(mix_cleaned['Eimp'].isna(), None,
                                                mix_cleaned['Eimp'] * mix_cleaned['impact'])

        mix_cleaned['gender_org'] = mix_cleaned['gender']
        mix_cleaned['gender'] = np.where((mix_cleaned['platform'].isin(['SMR'] + self.tv_list)), 'P', mix_cleaned['gender'])
        mix_cleaned['min_org'] = mix_cleaned['min']
        mix_cleaned['max_org'] = mix_cleaned['max']
        mix_cleaned['min'] = np.where((mix_cleaned['platform'].isin(['SMR'] + self.tv_list)), min(self.population_DB['age_min']),
                                    mix_cleaned['min'])
        mix_cleaned['max'] = np.where((mix_cleaned['platform'].isin(['SMR'] + self.tv_list)), max(self.population_DB['age_max']),
                                    mix_cleaned['max'])

        mix_cleaned['Aimp'] = np.where(mix_cleaned['bid_type'].str.contains('GRP'),
                                    mix_cleaned['Aimp'] * mix_cleaned['pop_grps'] / 100, mix_cleaned['Aimp'])
        mix_cleaned['aimp_weighted'] = np.where(mix_cleaned['Aimp'].isna(), None,
                                                mix_cleaned['Aimp'] * mix_cleaned['impact'])

        mix_cleaned['Areach_org'] = mix_cleaned['Areach']
        mix_cleaned['Areach'] = np.where(mix_cleaned['bid_type'].str.contains('GRP'),
                                        mix_cleaned['Areach'] * mix_cleaned['pop_grps'], mix_cleaned['Areach'])

        # TV / Digital 분리
        mix_cleaned_ntv = mix_cleaned[mix_cleaned['platform'].apply(lambda x: x not in self.tv_list)]
        if mix_cleaned_ntv.shape[0] > 0:
            mix_cleaned_ntv['Areach_org'] = np.where(mix_cleaned_ntv['bid_type'].str.contains('GRP'),
                                                mix_cleaned_ntv['Areach_org'] * mix_cleaned_ntv['pop_grps'], mix_cleaned_ntv['Areach_org'])
            
        mix_cleaned_tv = mix_cleaned[mix_cleaned['platform'].apply(lambda x: x in self.tv_list)]

        if mix_cleaned_tv.shape[0] > 0:

            # TV매체 기대노출량
            tv_eimp = []
            tv_eimp_weighted = []
            tv_aimp = []
            tv_aimp_weighted = []
            tv_areach = []
            tv_areach_org = []

            tv_dist = self.distribution_DB[self.distribution_DB['platform'].apply(lambda x: x in self.tv_list)].drop(['date', 'year', 'month'], axis=1)
            tv_params = self.parameter_DB[self.parameter_DB['platform'].apply(lambda x: x in self.tv_list)].drop(['date', 'year'], axis=1)

            for g in mix_cleaned_tv.index.tolist():
                df = self.get_age_range(mix_cleaned_tv['gender'][g], mix_cleaned_tv['min'][g], mix_cleaned_tv['max'][g]). \
                    assign(campaign=mix_cleaned_tv['campaign'][g], line=mix_cleaned_tv['line'][g],
                        platform=mix_cleaned_tv['platform'][g], product=mix_cleaned_tv['product'][g],
                        Eimp=mix_cleaned_tv['Eimp'][g], impact=mix_cleaned_tv['impact'][g],
                        Aimp=mix_cleaned_tv['Aimp'][g], Areach=mix_cleaned_tv['Areach'][g],
                        gender_org=mix_cleaned_tv['gender_org'][g], min_org=mix_cleaned_tv['min_org'][g],
                        max_org=mix_cleaned_tv['max_org'][g])

                df['gender_org'] = np.where(df['gender_org'] == "P", df['gender'], df['gender_org'])
                df['isDemo'] = np.where(((df['gender'] == df['gender_org']) & (df['age_min'] >= df['min_org']) & (
                            df['age_max'] <= df['max_org'])), 1, 0)
                df = df.merge(tv_dist, on=['platform', 'gender', 'age_min', 'age_max'])

                df['dist_sum'] = np.dot(df['distribution'], df['isDemo'])
                df.eval('''
                        dist_rat = distribution / dist_sum
                        Eimp = Eimp * dist_rat 
                        eimp_weighted = Eimp * impact
                        a_imp = Aimp * dist_rat 
                        aimp_weighted = a_imp * impact''', inplace=True)

                df = df.merge(tv_params, on=['platform', 'product', 'gender', 'age_min', 'age_max'])
                df['Simp_grps'] = df['a_imp'] / df['population'] * 100
                df['Simp_reach_p'] = np.where(df['Simp_grps'] > .0,
                                            df['c'] / (1 + np.exp(-(df['a'] + df['b'] * np.log(df['Simp_grps'])))), .0)
                df['Simp_reach_n'] = df['Simp_reach_p'] * df['population']
                df['Simp_grps_weighted'] = df['aimp_weighted'] / df['population'] * 100
                df['Simp_reach_p_weighted'] = np.where(df['Simp_grps_weighted'] > .0, df['c'] / (
                            1 + np.exp(-(df['a'] + df['b'] * np.log(df['Simp_grps_weighted'])))), .0)
                df['Simp_reach_n_weighted'] = df['Simp_reach_p_weighted'] * df['population']

                tv_eimp.append(np.sum(df['Eimp']))
                tv_eimp_weighted.append(np.sum(df['eimp_weighted']))
                tv_aimp.append(np.sum(df['a_imp']))
                tv_aimp_weighted.append(np.sum(df['aimp_weighted']))

                df['Simp_reach_n_sum'] = np.dot(df['Simp_reach_n'], df['isDemo'])
                df['Simp_reach_n_sum_weighted'] = np.dot(df['Simp_reach_n_weighted'], df['isDemo'])
                df['over_rate'] = np.where(df['Simp_reach_n_sum'] > .0, df['Areach'] / df['Simp_reach_n_sum'], .0)
                df['over_rate_weighted'] = np.where(df['Simp_reach_n_sum_weighted'] > .0,
                                                    df['Areach'] / df['Simp_reach_n_sum_weighted'], .0)
                df.eval('''
                        Simp_reach_areach = over_rate * Simp_reach_n
                        Simp_reach_areach_weighted = over_rate_weighted * Simp_reach_n_weighted''', inplace=True)

                tv_areach.append(np.sum(df['Simp_reach_areach']))
                tv_areach_org.append(np.mean(df['Areach']))

            mix_cleaned_tv['Eimp'] = tv_eimp
            mix_cleaned_tv['eimp_weighted'] = tv_eimp_weighted
            mix_cleaned_tv['Aimp'] = tv_aimp
            mix_cleaned_tv['aimp_weighted'] = tv_aimp_weighted
            mix_cleaned_tv['Areach'] = tv_areach
            mix_cleaned_tv['Areach_org'] = tv_areach_org

        mix_cleaned = pd.concat([mix_cleaned_tv, mix_cleaned_ntv], axis=0).sort_values('line', ascending=True)

        # 모든 float type에 대한 반올림 & infinity 처리
        mix_cleaned = self.round_float(mix_cleaned)
        
        return (mix_cleaned)


    # 예산 총합
    def sum_budget(self, input_mix):
        mix_cleaned = self.get_eimp(self.mix_clean(input_mix))
        sum_budget = pd.DataFrame({'sum_budget': [(mix_cleaned['budget'].sum())]}).to_json(force_ascii=False)

        return (sum_budget)