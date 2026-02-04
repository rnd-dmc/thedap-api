from datetime import datetime
import pandas as pd
import numpy as np 
from THEDAP_UTILS.DapMixClean_v5 import DapMixClean_v5

class DapPhase1_v5(DapMixClean_v5):
    
    def __init__(self):
        super().__init__()

    ### 결과 계산에 필요한 함수
    def get_tidy(self, input_mix, input_age, input_gender):
        mix_cleaned = self.get_eimp(self.mix_clean(input_mix)).reset_index(drop=True)
        age = pd.read_json(self.trans_age(input_age))
        trans_min = age['trans_min'][0]
        trans_max = age['trans_max'][0]
        gender_list = (['M', 'F'] if pd.read_json(self.get_gender(input_gender))['gender'][0] == 'P' else [
            pd.read_json(self.get_gender(input_gender))['gender'][0]])

        pop_db_ = self.population_DB.drop(['date', 'year', 'month'], axis=1)
        dist_db_ = self.distribution_DB.drop(['date', 'year', 'month'], axis=1)
        param_db_ = self.parameter_DB.drop(['date', 'year'], axis=1)
        param_ovr_db_ = self.parameter_DB.query('product == "overall"').drop(['product', 'date', 'year'], axis=1).rename(
                columns={'a': 'a_ovr', 'b': 'b_ovr', 'c': 'c_ovr'})
        param_npl_db_ = self.parameter_nplus_DB.filter(['gender', 'age_min', 'age_max'] + [x for x in self.parameter_nplus_DB.columns if 'ratio' in x]).drop_duplicates()
        
        tidy_rows = []
        tidy = pd.DataFrame()
        for i in range(mix_cleaned.shape[0]):
            df = self.get_age_range(mix_cleaned['gender'][i], mix_cleaned['min'][i], mix_cleaned['max'][i]). \
                assign(platform=mix_cleaned['platform'][i], product=mix_cleaned['product'][i]). \
                drop('population', axis=1). \
                merge(pop_db_, on=['gender', 'age_min', 'age_max'],
                    how='right'). \
                merge(dist_db_,
                    on=['platform', 'gender', 'age_min', 'age_max'], how='left'). \
                merge(param_db_,
                    on=['platform', 'product', 'gender', 'age_min', 'age_max'], how='left'). \
                merge(param_ovr_db_, how='left'). \
                merge(param_npl_db_). \
                assign(line=mix_cleaned['line'][i])

            df['distribution'].fillna(0., inplace=True)
            df['isTarget'] = np.where(
                (df['age_min'] >= trans_min) & (df['age_max'] <= trans_max) & (df['gender'].isin(gender_list)), 1, 0)
            df = df.merge(mix_cleaned.filter(
                ['line', 'impact', 'Eimp', 'eimp_weighted', 'min', 'max', 'Aimp', 'aimp_weighted', 'Areach', 'gender_org',
                'min_org', 'max_org', 'Areach_org', 'retargeting']), how='left')
            df['isDemo_org'] = np.where((df['age_min'] >= df['min_org']) & (df['age_max'] <= df['max_org']) & (
                        (df['gender_org'] == df['gender']) | (df['gender_org'] == "P")), 1, 0)
            df = df.assign(campaign=mix_cleaned['campaign'][i], line=mix_cleaned['line'][i],
                        platform=mix_cleaned['platform'][i], product=mix_cleaned['product'][i])

            df['dist_sum'] = np.sum(df['distribution'])
            df['dist_org_sum'] = np.dot(df['distribution'], df['isDemo_org'])
            
            df['dist'] = df['distribution'] / df['dist_sum']
            df['dist_org'] = df['distribution'] * df['isDemo_org'] / df['dist_org_sum']
            df['dist_sum_diff'] = df['dist_sum'] - df['dist_org_sum']
            
            df['dist_diff'] = np.where(df['dist_sum_diff'] > .0,
                                    df['distribution'] * (1 - df['isDemo_org']) / df['dist_sum_diff'], .0)
            df['Eimp'] = df['Eimp'] * df['dist']
            df['eimp_weighted'] = df['eimp_weighted'] * df['dist']
            df['retargeting'] = np.where(df['retargeting'] > .0, df['retargeting'] * df['dist'], .0)

            tidy_rows.append(df.fillna(.0))
            
        tidy = self.round_float(pd.concat(tidy_rows, ignore_index=True))

        return (tidy)


    ## 라인별 결과값
    def phase1(self, input_mix, input_age, input_gender):
        df = self.get_tidy(input_mix, input_age, input_gender)
        age = pd.read_json(self.trans_age(input_age))
        df['c'] = np.where(df['c'] > 0.9999, 0.9999, df['c'])
        df['c_ovr'] = np.where(df['c_ovr'] > 0.9999, 0.9999, df['c_ovr'])

        df['Simp_areach'] = df['Aimp'] * df['dist']
        df['Simp_grps'] = df['Simp_areach'] / df['population'] * 100
        df['Simp_areach_weighted'] = df['aimp_weighted'] * df['dist']
        df['Simp_grps_weighted'] = df['Simp_areach_weighted'] / df['population'] * 100
        
        df['Simp_reach_p'] = np.where(df['Simp_grps'] > .0,
                                    df['c'] / (1 + np.exp(-(df['a'] + df['b'] * np.log(df['Simp_grps'])))), .0)
        df['Simp_reach_p_weighted'] = np.where(df['Simp_grps_weighted'] > .0, df['c'] / (
                    1 + np.exp(-(df['a'] + df['b'] * np.log(df['Simp_grps_weighted'])))), .0)
        
        df['Simp_reach_n'] = df['Simp_reach_p'] * df['population']
        df['Simp_reach_n_weighted'] = df['Simp_reach_p_weighted'] * df['population']
        df['Vreach_n'] = df['Areach_org'] * df['dist_org']
        df['Vreach_p'] = df['Vreach_n'] / df['population']

        df['Vgrps'] = np.where(df['dist_org'] > .0, np.exp((-(df['a']) - np.log((df['c'] / df['Vreach_p']) - 1)) / df['b']), 0.)
        df['Vgrps_weighted'] = df['Vgrps'] * df['impact']
        df['Vimp'] = np.where(df['Vgrps'] > .0, df['Vgrps'] * df['population'] / 100, .0)
        df['Vimp_weighted'] = np.where(df['Vgrps_weighted'] > .0, df['Vgrps_weighted'] * df['population'] / 100, .0)

        # 기집행 도달 - 커버리지 초과문제 방지
        over_c = list(set(df.query('Vreach_p > c')['line']))
        if len(over_c) > 0:
            line_pop_sum = {}
            for g in df.groupby('line'):
                line_pop_sum[g[0]] = np.dot(g[1]['dist_org'] > .0, g[1]['population'])

            df['pop_grps'] = df['line'].apply(lambda x: line_pop_sum[x])
            df['Vreach_p'] = np.where(df['line'].isin(over_c), df['Areach_org'] / df['pop_grps'] * (df['dist_org'] > .0),
                                    df['Vreach_p'])
            df['Vreach_n'] = df['Vreach_p'] * df['population']
            df['Vgrps'] = np.where(df['dist_org'] > .0,
                                np.exp((-(df['a']) - np.log((df['c'] / df['Vreach_p']) - 1)) / df['b']), 0.)
            df['Vgrps_weighted'] = df['Vgrps'] * df['impact']
            df['Vimp'] = np.where(df['Vgrps'] > .0, df['Vgrps'] * df['population'] / 100, .0)
            df['Vimp_weighted'] = np.where(df['Vgrps_weighted'] > .0, df['Vgrps_weighted'] * df['population'] / 100, .0)

        df = df.groupby(['campaign', 'line']). \
            agg(
            Simp_reach_n_sum=('Simp_reach_n', lambda x: np.sum(x)),
            Simp_reach_n_sum_weighted=('Simp_reach_n_weighted', lambda x: np.sum(x)),
            Vimp_sum=('Vimp', lambda x: np.sum(x)),
            Vimp_weighted_sum=('Vimp_weighted', lambda x: np.sum(x))
        ).reset_index().merge(df, how='right')

        df['Vimp'] = np.where(df['isDemo_org'] == 1, df['Vimp'],
                            df['Vimp_sum'] * df['dist_sum_diff'] / df['dist_org_sum'] * df['dist_diff'])
        df['Vimp_weighted'] = np.where(df['isDemo_org'] == 1, df['Vimp_weighted'],
                                    df['Vimp_weighted_sum'] * df['dist_sum_diff'] / df['dist_org_sum'] * df['dist_diff'])
            
        df['Simp_Eimp'] = df['Eimp'] + df['Vimp']
        df['Simp_Eimp_weighted'] = df['eimp_weighted'] + df['Vimp_weighted']

        df['simulation_grps'] = np.where(df['retargeting'] > .0, df['Simp_Eimp_weighted'] / df['retargeting'] * 100,
                                        df['Simp_Eimp_weighted'] / df['population'] * 100)
        df['simulation_reach_p'] = np.where(df['simulation_grps'] > .0,
                                            df['c'] / (1 + np.exp(-(df['a'] + df['b'] * np.log(df['simulation_grps'])))),
                                            .0)
        df['simulation_reach_n'] = np.where(df['retargeting'] > .0, df['retargeting'] * df['simulation_reach_p'],
                                            df['population'] * df['simulation_reach_p'])
        df['simulation_reach_n'] = np.where(df['simulation_reach_n'] > df['Simp_Eimp_weighted'], df['Simp_Eimp_weighted'],
                                            df['simulation_reach_n'])

        df['E_imp_a'] = df['Eimp'] + df['Simp_areach']
        df['E_imp_a_weighted'] = df['eimp_weighted'] + df['Simp_areach_weighted']
        df['E_imp'] = np.where(df['Vimp'] > .0, df['E_imp_a'], df['Simp_Eimp']) # 
        df['E_imp_weighted'] = np.where(df['Vimp'] > .0, df['E_imp_a_weighted'], df['Simp_Eimp_weighted']) #
        df['E_reach_n'] = df['simulation_reach_n']

        df['E_reach_n'] = np.where(df['E_reach_n'] > df['E_imp'], df['E_imp'], df['E_reach_n'])
        df['isDemo'] = np.where(df['E_imp'] > .0, 1, 0)

        df['target_impression_a'] = df['E_imp_a'] * df['isTarget']
        df['target_impression_a_weighted'] = df['E_imp_a_weighted'] * df['isTarget']
        df['target_impression'] = df['E_imp'] * df['isTarget']
        df['target_impression_weighted'] = df['E_imp_weighted'] * df['isTarget']
        df['target_reach_n'] = df['E_reach_n'] * df['isTarget']
        df['line_pop'] = df['population'] * df['isDemo']
        
        df = df.groupby(['campaign', 'line']).agg(line_pop=('line_pop', lambda x: np.sum(x))).reset_index(). \
            merge(df.drop('line_pop', axis=1), how='right'). \
            groupby(['campaign', 'line', 'platform', 'product', 'gender', 'age_min', 'age_max']). \
            agg({'E_reach_n': 'sum', 'E_imp_a': 'sum', 'E_imp_a_weighted': 'sum', 'E_imp': 'sum', 'E_imp_weighted': 'sum',
                'target_reach_n': 'sum', 'target_impression_a': 'sum', 'target_impression_a_weighted': 'sum', 
                'target_impression': 'sum', 'target_impression_weighted': 'sum',
                'retargeting':'max',
                'population': 'mean', 'isTarget': 'mean', 'isDemo': 'mean', 'a_ovr': 'min', 'b_ovr': 'max', 'c_ovr': 'max',
                'ratio2_a': 'min', 'ratio2_af': 'max', 'ratio2_grps': 'max', 'ratio3_a': 'min', 'ratio3_af': 'max',
                'ratio3_grps': 'max', 'ratio4_a': 'min', 'ratio4_af': 'max', 'ratio4_grps': 'max',
                'ratio5_a': 'min', 'ratio5_af': 'max', 'ratio5_grps': 'max', 'ratio6_a': 'min', 'ratio6_af': 'max',
                'ratio6_grps': 'max', 'ratio7_a': 'min', 'ratio7_af': 'max', 'ratio7_grps': 'max',
                'ratio8_a': 'min', 'ratio8_af': 'max', 'ratio8_grps': 'max', 'ratio9_a': 'max', 'ratio9_af': 'max',
                'ratio9_grps': 'max', 'ratio10_a': 'max', 'ratio10_af': 'max', 'ratio10_grps': 'max'}).reset_index(). \
            rename(columns={'E_reach_n': 'e_reach_n', 'E_imp_a': 'e_imp_a', 'E_imp_a_weighted': 'eimp_a_weighted',
                            'E_imp': 'e_imp', 'E_imp_weighted': 'eimp_weighted'})

        df['e_grps_a'] = df['e_imp_a'] / df['population'] * 100
        df['e_grps'] = df['eimp_weighted'] / df['population'] * 100
        df['target_grps_a'] = df['target_impression_a'] / df['population'] * 100
        df['target_grps'] = df['target_impression_weighted'] / df['population'] * 100
        df['e_reach_p'] = df['e_reach_n'] / df['population']
        df['target_reach_p'] = df['target_reach_n'] / df['population']
        
        df['af_a'] = df['e_imp_a'] / df['e_reach_n']
        df['af'] = df['eimp_weighted'] / df['e_reach_n']
        
        df['target_af_a'] = df['target_impression_a'] / df['target_reach_n']
        df['target_af'] = df['target_impression_weighted'] / df['target_reach_n']

        for r in range(2, 11):
            e_ratio = 'e_ratio' + str(r)
            e_reach_p = 'e_reach' + str(r) + '_p'
            e_reach_n = 'e_reach' + str(r) + '_n'

            target_ratio = 'target_ratio' + str(r)
            target_reach_p = 'target_reach' + str(r) + '_p'
            target_reach_n = 'target_reach' + str(r) + '_n'

            ratio_a = 'ratio' + str(r) + '_a'
            ratio_af = 'ratio' + str(r) + '_af'
            ratio_grps = 'ratio' + str(r) + '_grps'

            ###
            df[e_ratio] = (1 / (1 + np.exp(
                -(df[ratio_a] + df[ratio_af] * np.log(df['af']) + df[ratio_grps] * np.log(df['e_grps'])))))
            df[target_ratio] = (1 / (1 + np.exp(
                -(df[ratio_a] + df[ratio_af] * np.log(df['target_af']) + df[ratio_grps] * np.log(df['target_grps'])))))

            ###
            if r == 2:
                _e_reach_p = 'e_reach_p'
                _target_reach_p = 'target_reach_p'
            else:
                _e_reach_p = 'e_reach' + str(r - 1) + '_p'
                _target_reach_p = 'target_reach' + str(r - 1) + '_p'

            df[e_reach_p] = df[_e_reach_p] * df[e_ratio]
            df[target_reach_p] = df[_target_reach_p] * df[target_ratio]
            df[e_reach_n] = df[e_reach_p] * df['population']
            df[target_reach_n] = df[target_reach_p] * df['population']

        df = self.round_float(df.fillna(0.))

        return (df)


    def summary_each_line(self, input_mix, input_age, input_gender):
        ph1 = self.phase1(input_mix, input_age, input_gender)
        mix_cleaned = self.get_eimp(self.mix_clean(input_mix)).reset_index(drop=True)
        trans_pop = pd.read_json(self.get_population(pd.read_json(self.get_gender(input_gender))['gender'][0],
                                                pd.read_json(self.trans_age(input_age))['trans_min'][0],
                                                pd.read_json(self.trans_age(input_age))['trans_max'][0]))['trans_pop'][0]

        df = ph1.query('e_grps_a != 0')
        df = df.groupby(['campaign', 'line', 'platform', 'product']). \
            agg({'age_min': 'min', 'age_max': 'max', 'population': 'sum',
                'e_imp_a': 'sum', 'eimp_a_weighted': 'sum', 'e_imp': 'sum', 'eimp_weighted': 'sum',
                'target_impression_a': 'sum', 'target_impression_a_weighted': 'sum', 'target_impression': 'sum',
                'target_impression_weighted': 'sum',
                'e_reach_n': 'sum', 'e_reach2_n': 'sum', 'e_reach3_n': 'sum', 'e_reach4_n': 'sum', 'e_reach5_n': 'sum',
                'e_reach6_n': 'sum', 'e_reach7_n': 'sum', 'e_reach8_n': 'sum', 'e_reach9_n': 'sum', 'e_reach10_n': 'sum',
                'target_reach_n': 'sum', 'target_reach2_n': 'sum', 'target_reach3_n': 'sum', 'target_reach4_n': 'sum',
                'target_reach5_n': 'sum',
                'target_reach6_n': 'sum', 'target_reach7_n': 'sum', 'target_reach8_n': 'sum', 'target_reach9_n': 'sum',
                'target_reach10_n': 'sum'}).reset_index()

        df = df.merge(mix_cleaned[['campaign', 'line', 'budget', 'gender']])
        df['e_grps_a'] = df['e_imp_a'] / df['population'] * 100
        df['e_grps'] = df['eimp_weighted'] / df['population'] * 100
        df['af_a'] = df['e_imp_a'] / df['e_reach_n']
        df['af'] = df['eimp_weighted'] / df['e_reach_n']
        
        df['target_grps_a'] = df['target_impression_a'] / trans_pop * 100
        df['target_grps'] = df['target_impression_weighted'] / trans_pop * 100
        df['target_af_a'] = df['target_impression_a'] / df['target_reach_n']
        df['target_af'] = df['target_impression_weighted'] / df['target_reach_n']

        for r in range(1, 11):
            if r == 1:
                reach = 'reach'
            else:
                reach = 'reach' + str(r)

            e_reach_p = 'e_' + reach + '_p'
            e_reach_n = 'e_' + reach + '_n'
            target_reach_p = 'target_' + reach + '_p'
            target_reach_n = 'target_' + reach + '_n'

            df[e_reach_p] = np.where(df[e_reach_n] < 1.0, 0.0, df[e_reach_n] / df['population'])
            df[target_reach_p] = np.where(df[target_reach_n] < 1.0, 0.0, df[target_reach_n] / trans_pop)

        select_columns = ['campaign', 'line', 'platform', 'product', 'gender', 'age_min', 'age_max', 'budget',
                        'target_impression_a', 'target_impression_weighted'] + \
                        [x for x in df.columns if 'target_reach' in x] + \
                        ['target_grps_a', 'target_grps', 'target_af_a', 'target_af']

        df = df.filter(select_columns). \
            rename(columns={'target_impression_a': 'target_impression',
                            'target_grps':'target_grps_weighted', 'target_grps_a': 'target_grps',
                            'target_af':'target_af_weighted', 'target_af_a': 'target_af'}). \
            fillna(0)

        df = df.merge(mix_cleaned[
                        ['campaign', 'line', 'gender_org', 'date_start', 'date_end', 'min_org', 'max_org', 'platform',
                        'product', 'budget']])
        # df['period'] = [((datetime.strptime(x, '%Y-%m-%d') - datetime.strptime(y, '%Y-%m-%d')).days + 1)
        #                 for x, y in zip(df['date_end'], df['date_start'])]
        df['period'] = [self.calc_period(x, y) for x, y in zip(df['date_end'], df['date_start'])]
        
        df['target_af_day'] = df['target_af'] / df['period']
        df['target_af_week'] = df['target_af'] / df['period'] * 7
        df['target_af_30'] = df['target_af'] / df['period'] * 30
        df['imp_interval'] = df['period'] / df['target_af']
        
        df['target_af_day_weighted'] = df['target_af_weighted'] / df['period']
        df['target_af_week_weighted'] = df['target_af_weighted'] / df['period'] * 7
        df['target_af_30_weighted'] = df['target_af_weighted'] / df['period'] * 30
        df['imp_interval_weighted'] = df['period'] / df['target_af_weighted']
        
        df['imp_interval'] = df['imp_interval'].apply(lambda x: str(np.round(x, 2)) + '일당 1회 노출')
        df['imp_interval_weighted'] = df['imp_interval_weighted'].apply(lambda x: str(np.round(x, 2)) + '일당 1회 노출')
        
        df['gender'] = df['gender_org']
        df['age_min'] = df['min_org']
        df['age_max'] = df['max_org']
        df.drop(['gender_org', 'min_org', 'max_org', 'period'], axis=1, inplace=True)
        df = self.round_float(df)

        return (ph1, df)

